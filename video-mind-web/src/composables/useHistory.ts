import { reactive } from 'vue'
import request from '../utils/request'

export interface HistoryItem {
    id: number
    title: string
    time: string
    status: number
}

/** 前端内存缓存：只缓存已完成记录（数据不变），处理中记录每次重新拉取 */
interface CacheEntry {
    data: any
    accessOrder: number  // LRU 用：越大表示越近访问
}

const MAX_CACHE_SIZE = 20

/**
 * 历史记录查询功能
 */
export function useHistory() {
    /** 缓存已完成对话的 loadDetail 结果，避免频繁查库 */
    const detailCache = new Map<number, CacheEntry>()
    let accessCounter = 0

    const history = reactive({
        list: [] as HistoryItem[],
        activeId: null as number | null,

        formatTime(timeStr: string): string {
            const date = new Date(timeStr)
            const now = new Date()
            const diff = Math.floor((now.getTime() - date.getTime()) / 1000)

            if (diff < 60) return '刚刚'
            if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
            if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
            if (diff < 604800) return `${Math.floor(diff / 86400)}天前`
            return date.toLocaleDateString()
        },

        /**
         * 发送请求从数据库查询历史记录
         */
        async load() {
            try {
                const res = await request.get('/user/conversation/list')
                if (res.code === 200) {
                    history.list = res.data.map((item: any) => ({
                        id: item.id,
                        title: item.title || '未命名视频',
                        time: history.formatTime(item.createdAt),
                        status: item.status
                    }))
                }
            } catch (e) {
                console.error('历史记录加载失败', e)
            }
        },

        /**
         * 加载单条对话详情
         * - 已完成（status=1）：优先走缓存，数据永不变化
         * - 处理中（status=0）：不走缓存，每次重新请求获取最新 sid 和状态
         */
        async loadDetail(id: number): Promise<any> {
            // 先查缓存
            const cached = detailCache.get(id)
            if (cached) {
                // 已完成记录缓存命中，更新访问顺序
                cached.accessOrder = ++accessCounter
                return cached.data
            }

            try {
                const res = await request.get(`/user/conversation/${id}`)
                if (res.code !== 200) {
                    alert('加载失败：' + res.message)
                    return null
                }
                const data = res.data
                if (data.status === 2) {
                    alert('视频解析失败，请重新提交')
                    return null
                }
                // 已完成记录且没有进行中的 chat 才写入缓存
                // 有 pendingChatSid 说明 chat 还在生成中，数据会变，不能缓存
                if (data.status === 1 && !data.pendingChatSid) {
                    detailCache.set(id, {
                        data: data,
                        accessOrder: ++accessCounter
                    })
                    // 超过容量限制，淘汰最老的
                    evictIfNeeded()
                }
                return data
            } catch (e) {
                console.error('加载记录失败', e)
                alert('加载失败')
                return null
            }
        },

        /**
         * 清除指定对话的缓存
         * 当用户发送新 chat 或数据发生变化时调用，确保下次 loadDetail 拉取最新数据
         */
        invalidateCache(id: number) {
            detailCache.delete(id)
        }
    })

    /** LRU 淘汰：缓存超过 MAX_CACHE_SIZE 时，移除 accessOrder 最小的条目 */
    function evictIfNeeded() {
        while (detailCache.size > MAX_CACHE_SIZE) {
            let minKey: number | null = null
            let minOrder = Infinity
            for (const [key, entry] of detailCache) {
                if (entry.accessOrder < minOrder) {
                    minOrder = entry.accessOrder
                    minKey = key
                }
            }
            if (minKey !== null) {
                detailCache.delete(minKey)
            }
        }
    }

    return history
}
