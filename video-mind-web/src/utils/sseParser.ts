export interface SseParseResult {
    eventName: string
    data: any
}

/**
 * 解析chunk里的数据，把事件名称与内容提取出来
 * @param chunk
 */
export function parseSseChunk(chunk: string): SseParseResult | null {
    if (!chunk.trim()) return null
    const lines = chunk.split('\n')
    let eventName = 'message'
    let dataStr = ''

    for (const line of lines) {
        if (line.startsWith('event:')) {
            eventName = line.slice(6).trim()
        } else if (line.startsWith('data:')) {
            dataStr = line.slice(5).trim()
        }
    }

    if (!dataStr) return null
    try {
        return { eventName, data: JSON.parse(dataStr) }
    } catch (e) {
        console.error('[SSE] JSON 解析失败:', e, '原始数据:', dataStr)
        return null
    }
}