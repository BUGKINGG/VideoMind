/**
 * 与agent对话的方法
 * 支持断线续传：catchup 事件 + 指数退避自动重连 + sessionStorage 持久化
 */
import {reactive, ref, type Ref} from 'vue'
import { usePlaceholder } from './usePlaceholder'
import { parseSseChunk } from '../utils/sseParser'
import { renderMarkdown } from '../utils/markdown'
import request from '../utils/request'
import type { Message } from '../types/message'
import { saveSseState, clearSseState } from './sseSession'

export function useChat(messages: Ref<Message[]>) {
    const { start: startAnim, stop: stopAnim } = usePlaceholder()
    const isProcess = ref(false)
    // 当前会话的 sid，用于重连
    let currentSid: string | null = null

    /**
     * 处理从java端返回的每个chunk
     * @param chunk
     * @param aiIndex
     */
    function processChunk(chunk: string, aiIndex: number): { type?: 'done' | 'error' } | void {
        const result = parseSseChunk(chunk)
        if (!result) return
        const { eventName, data } = result

        if (eventName === 'message' && data.type === 'chunk') {
            const current = messages.value[aiIndex]
            if (!current) return
            if (!data.content) return

            if (current.isPlaceholder) {
                stopAnim()
                messages.value.splice(aiIndex, 1, {
                    id: current.id,
                    role: 'ai',
                    content: renderMarkdown(data.content),
                    rawContent: data.content,
                    isStreaming: true
                })
            } else {
                const raw = (current.rawContent || '') + data.content
                messages.value.splice(aiIndex, 1, {
                    id: current.id,
                    role: 'ai',
                    content: renderMarkdown(raw),
                    rawContent: raw,
                    isStreaming: true
                })
            }
        }
        // 断线续传：收到 catchup 事件，一次性替换累积内容
        else if (eventName === 'message' && data.type === 'catchup') {
            const current = messages.value[aiIndex]
            if (!current || !data.content) return
            stopAnim()
            messages.value.splice(aiIndex, 1, {
                id: current.id,
                role: 'ai',
                content: renderMarkdown(data.content),
                rawContent: data.content,
                isStreaming: true
            })
        }
        else if (eventName === 'message' && data.type === 'done') {
            stopAnim()
            const current = messages.value[aiIndex]
            if (!current) return
            const raw = current.rawContent || ''
            messages.value.splice(aiIndex, 1, {
                id: current.id,
                role: 'ai',
                content: renderMarkdown(data.answer || raw)
            })
            clearSseState()
            return { type: 'done' }
        }
        else if (eventName === 'error') {
            stopAnim()
            messages.value.splice(aiIndex, 1, {
                id: messages.value[aiIndex]?.id,
                role: 'ai',
                content: '出错: ' + (data.message || '未知错误')
            })
            clearSseState()
            return { type: 'error' }
        }
    }

    async function send(text: string, conversationId: number | null, token: string): Promise<boolean> {
        if (!text.trim() || isProcess.value) return false

        isProcess.value = true

        const userId = Date.now() + '_user'
        messages.value.push({ id: userId, role: 'user', content: text })

        const aiIndex = messages.value.length
        const aiId = Date.now() + '_ai'
        messages.value.push({
            id: aiId,
            role: 'ai',
            isPlaceholder: true,
            placeholderType: 'chat'
        })
        startAnim()

        try {
            const res = await request.post('/agent/chat', {
                conversationId,
                message: text
            })
            const { sessionId } = res.data
            currentSid = sessionId

            // 保存会话状态到 sessionStorage，供刷新后恢复
            saveSseState({ sid: sessionId, type: 'chat', conversationId })

            await runSSE(sessionId, token, aiIndex)

            return true

        } catch (error: any) {
            stopAnim()
            console.error('发送失败:', error)
            messages.value.splice(aiIndex, 1, {
                id: messages.value[aiIndex]?.id,
                role: 'ai',
                content: '发送失败，请重试'
            })
            clearSseState()
            return false
        } finally {
            stopAnim()
            isProcess.value = false
        }
    }

    /**
     * SSE 流读取，带指数退避自动重连
     */
    async function runSSE(sessionId: string, token: string, aiIndex: number, retryCount = 0): Promise<void> {
        const MAX_RETRIES = 3
        const delays = [1000, 2000, 4000]

        try {
            const response = await fetch(`/agent/chat/stream?sid=${sessionId}`, {
                headers: { 'token': token }
            })
            if (!response.ok) throw new Error(`SSE ${response.status}`)

            const reader = response.body!.getReader()
            const decoder = new TextDecoder()
            let buffer = ''

            while (true) {
                const { done, value } = await reader.read()
                if (done) {
                    const remaining = buffer.split('\n\n')
                    for (const chunk of remaining) {
                        const result = processChunk(chunk, aiIndex)
                        if (result?.type === 'done' || result?.type === 'error') return
                    }
                    break
                }
                buffer += decoder.decode(value, { stream: true })
                const chunks = buffer.split('\n\n')
                buffer = chunks.pop() || ''
                for (const chunk of chunks) {
                    const result = processChunk(chunk, aiIndex)
                    if (result?.type === 'done' || result?.type === 'error') return
                }
            }

            // 流结束但没收到 done/error，尝试重连
            if (retryCount < MAX_RETRIES) {
                console.log(`[Chat SSE] ${delays[retryCount]}ms 后进行第 ${retryCount + 1} 次重连...`)
                await sleep(delays[retryCount])
                return runSSE(sessionId, token, aiIndex, retryCount + 1)
            }

        } catch (error: any) {
            // AbortError 是用户主动切换导致的，静默处理
            if (error.name === 'AbortError') {
                console.log('[Chat SSE] 连接已被中断')
                return
            }
            console.error('[Chat SSE] 异常:', error)
            if (retryCount < MAX_RETRIES) {
                console.log(`[Chat SSE] ${delays[retryCount]}ms 后进行第 ${retryCount + 1} 次重连...`)
                await sleep(delays[retryCount])
                return runSSE(sessionId, token, aiIndex, retryCount + 1)
            }
            // 最终失败
            stopAnim()
            messages.value.splice(aiIndex, 1, {
                id: messages.value[aiIndex]?.id,
                role: 'ai',
                content: '发送失败，请重试'
            })
        }
    }

    /**
     * 供 Home.vue 在页面刷新后自动重连使用
     * @param sessionId SSE 会话 ID
     * @param token JWT token
     * @param aiIndex 消息列表中 AI 回复占位符的索引
     */
    async function reconnect(sessionId: string, token: string, aiIndex: number): Promise<void> {
        currentSid = sessionId
        await runSSE(sessionId, token, aiIndex)
    }

    function sleep(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms))
    }

    return reactive({ isProcess, send, reconnect })
}
