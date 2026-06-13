import asyncio
import json
import os
import re
import time
from typing import Any, Dict, List

import requests
import uvicorn
from bilibili_api import Credential, video
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="VideoMind Python Service")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com",
}


def extract_bvid(url: str) -> str:
    m = re.search(r"(BV[0-9A-Za-z]{10})", url)
    if not m:
        raise ValueError("URL里找不到BV号")
    return m.group(1)


def pick_chinese_subtitle(subs: List[Dict]) -> List[Dict]:
    """
    只保留中文字幕轨道。
    优先级：ai-zh > zh-CN/zh > 其他 zh*。
    如果完全没有中文，fallback 取第一个并打警告（避免直接报错）。
    """
    if not subs:
        return []

    # 1. 最优先：AI 中文
    for s in subs:
        if s.get("lan") == "ai-zh":
            return [s]

    # 2. 其次：人工中文（zh-CN, zh, zh-HK, zh-TW...）
    zh_subs = [s for s in subs if s.get("lan", "").startswith("zh")]
    if zh_subs:
        return zh_subs

    # 3. 调试
    print(f"[警告] 未找到中文字幕，可用轨道: {[s.get('lan') for s in subs]}，fallback 取第一个")
    return [subs[:1]]  # 只取第一个，避免多轨道都下载

def parse_cookie_string(cookie_str: str) -> Dict[str, str]:
    """把 'SESSDATA=xxx; bili_jct=yyy' 转成 dict"""
    cookies = {}
    if not cookie_str:
        return cookies
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def build_credential(cookie_str: str) -> Credential | None:
    """从 cookie 字符串构建 bilibili-api 的 Credential"""
    if not cookie_str:
        return None
    # Java 端可能只传了纯 SESSDATA 值（不含 =）
    if "=" not in cookie_str:
        return Credential(sessdata=cookie_str)
    cookies = parse_cookie_string(cookie_str)
    return Credential(
        sessdata=cookies.get("SESSDATA", ""),
        bili_jct=cookies.get("bili_jct", ""),
        buvid3=cookies.get("buvid3", ""),
    )


async def get_video_info_async(bvid: str, part: int = 1, credential=None):
    """使用 bilibili-api-python 获取视频信息（自动处理 WBI 签名）"""
    print(f"[DEBUG] 请求视频信息: bvid={bvid}, part={part}")
    v = video.Video(bvid=bvid, credential=credential)
    info = await v.get_info()

    aid = info["aid"]
    title = info["title"]
    pages = info.get("pages", [])

    # 防御：强制转 int 并排序
    part = int(part)
    pages = sorted(pages, key=lambda p: int(p.get("page", 999)))

    print(f"[DEBUG] 视频分P信息: pages数量={len(pages)}, 请求part={part}")
    if pages:
        target = next(
            (p for p in pages if int(p.get("page", 0)) == part), pages[0]
        )
        cid = target["cid"]
        part_name = target.get("part", "")
        actual_page = target.get("page", 1)
        print(f"[DEBUG] 选中分P: page={actual_page}, cid={cid}, part_name={part_name}")
        if part_name and len(pages) > 1:
            title = f"{title} P{part} {part_name}"
    else:
        cid = info.get("cid")
        if not cid:
            raise RuntimeError("无法获取视频 cid")

    return aid, cid, title


async def get_subtitles_async(bvid: str, cid: int, credential=None):
    """使用 bilibili-api-python 获取字幕元数据（自动 WBI 签名，避免被污染）"""
    print(f"[DEBUG] 请求字幕: bvid={bvid}, cid={cid}")
    v = video.Video(bvid=bvid, credential=credential)
    player_info = await v.get_player_info(cid=cid)

    subs = player_info.get("subtitle", {}).get("subtitles", [])
    print(f"[DEBUG] 字幕轨道数: {len(subs)}")
    return subs


async def fetch_subtitle_body(sub_url: str, cookies: Dict[str, str] = None) -> List[Dict[str, Any]]:
    """异步安全地下载字幕 JSON（在线程池中执行 requests，避免阻塞事件循环）"""
    if sub_url.startswith("//"):
        sub_url = "https:" + sub_url
    elif not sub_url.startswith("http"):
        raise ValueError(f"非法的字幕URL: {sub_url!r}")

    print(f"[DEBUG] 拉取字幕内容: {sub_url[:80]}...")

    def _sync_get():
        return requests.get(
            sub_url,
            headers={**HEADERS, "Connection": "close"},
            cookies=cookies or {},
            timeout=15,
            proxies={"http": None, "https": None},
        )

    # Python 3.9+ 可用 asyncio.to_thread；3.8 请换成 loop.run_in_executor
    resp = await asyncio.to_thread(_sync_get)
    sub_data = resp.json()
    body = sub_data.get("body", [])
    print(f"[DEBUG] 字幕内容条数: {len(body)}")
    return body


# FIXME :这里用的绝对路径，要改，放的是字幕文件保存的位置
def save_to_files(
        title: str, bvid: str, results: List[Dict[str, Any]], out_dir: str = r"D:\Projects\subs"
):
    """生成 JSON 和 TXT 到本地（文件名加入 BV 号 + 时间戳，防止覆盖）"""
    print(f"[调试] 进入保存函数，准备写入 {out_dir}")
    os.makedirs(out_dir, exist_ok=True)
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)
    timestamp = int(time.time())
    safe_name = f"{safe_title}_{bvid}_{timestamp}"

    # 1. 保存完整 JSON
    json_path = os.path.join(out_dir, f"{safe_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[测试] JSON 已保存: {json_path}")

    # 2. 保存纯文本 TXT
    txt_path = os.path.join(out_dir, f"{safe_name}.txt")
    lines = []
    for track in results:
        lines.append(f"=== [{track.get('lan_doc', '未知')}] ===")
        for item in track.get("body", []):
            lines.append(item.get("content", "").strip())
        lines.append("")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[测试] TXT 已保存: {txt_path}")

    return json_path, txt_path


# ========== FastAPI 接口 ==========


class ParseRequest(BaseModel):
    url: str
    cookie: str = ""
    part: int = 1


@app.post("/parse")
async def parse_video(req: ParseRequest):
    """
    Java 调用示例：
    POST http://localhost:8001/parse
    Body: {"url": "https://www.bilibili.com/video/BV1DAL56hEPe/?p=2", "cookie": "SESSDATA=xxx"}
    """
    print(f"\n{'='*60}")
    print(f"[DEBUG] /parse 收到请求: url={req.url}, part={req.part}")
    print(f"[DEBUG] cookie长度: {len(req.cookie) if req.cookie else 0}")

    try:
        bvid = extract_bvid(req.url)
        print(f"[DEBUG] 提取到BV号: {bvid}")

        credential = build_credential(req.cookie)
        aid, cid, title = await get_video_info_async(bvid, req.part, credential)
        print(f"[DEBUG] 视频信息: aid={aid}, cid={cid}, title={title}")

        subtitles_meta = await get_subtitles_async(bvid, cid, credential)
        if not subtitles_meta:
            return {"code": 200, "title": title, "bvid": bvid, "subtitles": []}

        # 下载各轨道字幕
        results = []
        for s in pick_chinese_subtitle(subtitles_meta):
            lang = s.get("lan", "unknown")
            lan_doc = s.get("lan_doc", "未知")
            body = await fetch_subtitle_body(s["subtitle_url"])

            cleaned_body = []
            for item in body:
                cleaned_body.append(
                    {
                        "start": item.get("from"),
                        "end": item.get("to"),
                        "content": item.get("content", "").strip(),
                    }
                )
            results.append({"lang": lang, "lan_doc": lan_doc, "body": cleaned_body})

        # 测试阶段：生成本地文件（文件名已加 BV + 时间戳，不会覆盖）
        try:
            json_path, txt_path = save_to_files(title, bvid, results)
        except Exception as e:
            print(f"[警告] 文件保存失败（不影响接口返回）: {e}")

        print(
            f"[DEBUG] /parse 返回: title={title}, bvid={bvid}, subtitles条数={len(results)}"
        )
        return {
            "code": 200,
            "title": title,
            "bvid": bvid,
            "subtitles": results,
        }

    except ValueError as e:
        return {"code": 400, "message": str(e)}
    except RuntimeError as e:
        return {"code": 500, "message": str(e)}
    except Exception as e:
        return {"code": 500, "message": f"内部错误: {str(e)}"}


class SummarizeRequest(BaseModel):
    text: str
    title: str = ""


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
