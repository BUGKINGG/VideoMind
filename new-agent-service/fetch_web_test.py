import requests
import re
import time
import json
import os
from typing import List, Dict, Any
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

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


def get_video_info(bvid: str, part: int = 1):
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取视频信息失败: {data.get('message')}")

    d = data["data"]
    aid = d["aid"]
    title = d["title"]

    # 分P处理：B站 pages 数组里 page 字段就是 P 数
    pages = d.get("pages", [])
    if pages:
        target = next((p for p in pages if p.get("page") == part), pages[0])
        cid = target["cid"]
        part_name = target.get("part", "")
        if part_name and len(pages) > 1:
            title = f"{title} P{part} {part_name}"
    else:
        cid = d.get("cid")

    return aid, cid, title



def get_subtitles(
    bvid: str, cid: int, aid: int, cookies: Dict[str, str], retry: bool = True
):
    """获取字幕元数据列表（带aid参数，空URL时自动重试）"""
    url = f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}&aid={aid}"
    resp = requests.get(url, headers=HEADERS, cookies=cookies, timeout=10)
    data = resp.json()

    print(f"[调试] B站API返回: {data}")

    if data.get("code") != 0:
        raise RuntimeError(f"获取播放器信息失败: {data.get('message')}")

    subs = data.get("data", {}).get("subtitle", {}).get("subtitles", [])
    print(f"[调试] 原始字幕列表: {subs}")

    # 检查是否有空URL的字幕，有则重试一次（B站接口延迟问题）
    has_empty = any(not s.get("subtitle_url") for s in subs)
    if has_empty and retry:
        time.sleep(2)
        return get_subtitles(bvid, cid, aid, cookies, retry=False)

    # 过滤掉空的
    valid_subs = [s for s in subs if s.get("subtitle_url")]
    print(f"[调试] 过滤后有效字幕: {valid_subs}")
    return valid_subs


def fetch_subtitle_body(sub_url: str) -> List[Dict[str, Any]]:
    """直接拉取字幕JSON内容，返回body数组"""
    if sub_url.startswith("//"):
        sub_url = "https:" + sub_url
    elif not sub_url.startswith("http"):
        raise ValueError(f"非法的字幕URL: {sub_url!r}")

    resp = requests.get(sub_url, headers=HEADERS, timeout=10)
    sub_data = resp.json()
    return sub_data.get("body", [])


def parse_cookie_string(cookie_str: str) -> Dict[str, str]:
    """把 'SESSDATA=xxx; bili_jct=yyy' 转成 requests 用的 dict"""
    cookies = {}
    if not cookie_str:
        return cookies
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def save_to_files(
    title: str, results: List[Dict[str, Any]], out_dir: str = r"D:\Projects\subs"
):
    """
    测试阶段：生成 JSON 和 TXT 文件到本地
    - JSON: 完整字幕数据结构
    - TXT: 纯 content 内容
    """
    print(f"[调试] 进入保存函数，准备写入 {out_dir}")
    os.makedirs(out_dir, exist_ok=True)
    safe_name = re.sub(r'[\\/:*?"<>|]', "_", title)

    # 1. 保存完整 JSON
    json_path = os.path.join(out_dir, f"{safe_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[测试] JSON 已保存: {json_path}")

    # 2. 保存纯文本 TXT（所有 content 拼接）
    txt_path = os.path.join(out_dir, f"{safe_name}.txt")
    lines = []
    for track in results:
        lines.append(f"=== [{track.get('lan_doc', '未知')}] ===")
        for item in track.get("body", []):
            lines.append(item.get("content", "").strip())
        lines.append("")  # 轨道之间空一行

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[测试] TXT 已保存: {txt_path}")

    return json_path, txt_path


# ========== FastAPI 接口 ==========


class ParseRequest(BaseModel):
    url: str
    cookie: str = ""  # 传完整的 cookie 字符串，如 "SESSDATA=xxx; bili_jct=yyy"
    part: int = 1


@app.post("/parse")
def parse_video(req: ParseRequest):
    """
    Java 调用示例：
    POST http://localhost:8001/parse
    Body: {"url": "https://www.bilibili.com/video/BV1DAL56hEPe/?p=2", "cookie": "SESSDATA=xxx"}
    """
    print("Action!!!")
    try:
        bvid = extract_bvid(req.url)
        aid, cid, title = get_video_info(bvid, req.part)

        # 把前端/Java传来的 cookie 字符串转成 dict
        cookies = parse_cookie_string(req.cookie)
        subtitles_meta = get_subtitles(bvid, cid, aid, cookies)

        if not subtitles_meta:
            return {"code": 200, "title": title, "bvid": bvid, "subtitles": []}

        results = []
        for s in subtitles_meta:
            lang = s.get("lan", "unknown")
            lan_doc = s.get("lan_doc", "未知")
            body = fetch_subtitle_body(s["subtitle_url"])

            # 清洗成 Java 方便解析的结构：start/end/content
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

        # ========== 测试阶段：生成本地文件 ==========
        try:
            json_path, txt_path = save_to_files(title, results)
        except Exception as e:
            print(f"[警告] 文件保存失败（不影响接口返回）: {e}")
        # ==========================================

        return {
            "code": 200,
            "title": title,
            "bvid": bvid,
            "subtitles": results,  # 每个元素是一个语言轨道
        }

    except ValueError as e:
        return {"code": 400, "message": str(e)}
    except RuntimeError as e:
        return {"code": 500, "message": str(e)}
    except Exception as e:
        return {"code": 500, "message": f"内部错误: {str(e)}"}


class SummarizeRequest(BaseModel):
    text: str  # 拼接后的完整字幕文本
    title: str = ""  # 视频标题


@app.post("/summarize")
def summarize(req: SummarizeRequest):
    """Mock 视频总结 Agent，后续替换为真实 LLM/Agent 调用"""
    text = req.text[:1000] if req.text else "无字幕内容"
    title = req.title or "未知视频"

    # Mock 逻辑：简单返回前300字 + 固定话术
    mock_summary = f"""【Mock 总结】视频《{title}》内容摘要：

{text[:300]}...

（此处为 Mock 数据，仅用于前后端联调。真实 Agent 接入后，此接口返回真实 AI 总结。）
"""
    return {"code": 200, "summary": mock_summary}


# ========== 启动命令 ==========
# 方式1：直接运行此文件
#   python main.py
# 方式2：用 uvicorn 命令（推荐开发时带热重载）
#   uvicorn main:app --host 0.0.0.0 --port 8001 --reload

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
