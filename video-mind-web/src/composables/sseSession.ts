/**
 * SSE 会话状态持久化
 * 使用 sessionStorage 保存进行中的 SSE 会话信息，
 * 使得页面刷新后可以自动重连恢复流式输出。
 */
const SSE_STATE_KEY = 'vm-sse-state'

export interface SseState {
    /** SSE 会话 ID */
    sid: string
    /** 会话类型：summary=视频总结, chat=AI对话 */
    type: 'summary' | 'chat'
    /** 对话 ID（chat 类型时需要） */
    conversationId?: number | null
    /** 视频 ID（summary 类型时需要） */
    videoId?: number | null
}

export function saveSseState(state: SseState): void {
    try {
        sessionStorage.setItem(SSE_STATE_KEY, JSON.stringify(state))
    } catch (e) {
        console.warn('[SSE Session] 保存会话状态失败:', e)
    }
}

export function loadSseState(): SseState | null {
    try {
        const raw = sessionStorage.getItem(SSE_STATE_KEY)
        if (!raw) return null
        return JSON.parse(raw) as SseState
    } catch (e) {
        console.warn('[SSE Session] 加载会话状态失败:', e)
        return null
    }
}

export function clearSseState(): void {
    try {
        sessionStorage.removeItem(SSE_STATE_KEY)
    } catch (e) {
        console.warn('[SSE Session] 清除会话状态失败:', e)
    }
}
