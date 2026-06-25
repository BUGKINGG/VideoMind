import { reactive } from 'vue'
import request from '../utils/request'

export interface HistoryItem {
    id: number
    title: string
    time: string
    status: number
}

/**
 * 历史记录查询功能
 */
export function useHistory() {
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

        async loadDetail(id: number): Promise<any> {
            try {
                const res = await request.get(`/user/conversation/${id}`)
                if (res.code !== 200) {
                    alert('加载失败：' + res.message)
                    return null
                }
                const data = res.data
                if (data.status === 0) {
                    alert('视频还在处理中，请稍后')
                    return null
                }
                if (data.status === 2) {
                    alert('视频解析失败，请重新提交')
                    return null
                }
                return data
            } catch (e) {
                console.error('加载记录失败', e)
                alert('加载失败')
                return null
            }
        }
    })

    return history
}
