/**
 * 与agent对话的方法
 */
import {reactive, ref, type Ref} from 'vue'
import { usePlaceholder } from './usePlaceholder'
import { parseSseChunk } from '../utils/sseParser'
import { renderMarkdown } from '../utils/markdown'
import request from '../utils/request'
import type { Message } from '../types/message'

export function useChat(messages: Ref<Message[]>) {
    const { start: startAnim, stop: stopAnim } = usePlaceholder()
    const isProcess = ref(false)

    /**
     * 处理从java端返回的每个chunk
     * @param chunk
     * @param aiIndex
     */
    function processChunk(chunk: string, aiIndex: number) {
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
        }
        else if (eventName === 'error') {
            stopAnim()
            messages.value.splice(aiIndex, 1, {
                id: messages.value[aiIndex]?.id,
                role: 'ai',
                content: '出错: ' + (data.message || '未知错误')
            })
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
                    for (const chunk of remaining) processChunk(chunk, aiIndex)
                    break
                }
                buffer += decoder.decode(value, { stream: true })
                const chunks = buffer.split('\n\n')
                buffer = chunks.pop() || ''
                for (const chunk of chunks) processChunk(chunk, aiIndex)
            }

            return true

        } catch (error: any) {
            stopAnim()
            console.error('发送失败:', error)
            messages.value.splice(aiIndex, 1, {
                id: messages.value[aiIndex]?.id,
                role: 'ai',
                content: '发送失败，请重试'
            })
            return false
        } finally {
            stopAnim()
            isProcess.value = false
        }
    }

    return reactive({ isProcess, send })
}