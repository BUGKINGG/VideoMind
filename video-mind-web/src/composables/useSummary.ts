import { reactive, type Ref } from 'vue'
import { usePlaceholder } from './usePlaceholder'
import { parseSseChunk } from '../utils/sseParser'
import { renderMarkdown } from '../utils/markdown'
import request from '../utils/request'
import type { Message } from '../types/message'

export type SummaryStage = 'parsing' | 'summarizing' | 'done'

export function useSummary(messages: Ref<Message[]>) {
    const { start: startAnim, stop: stopAnim } = usePlaceholder()

    const summary = reactive({
        isLoading: false,
        confirmText: '开始总结',
        stage: 'parsing' as SummaryStage,
        currentVideoTitle: '',
        subtitleCount: 0,
        currentConversationId: null as number | null,
        currentVideoId: null as number | null,

        // 处理chunk流
        processChunk(chunk: string): { type?: 'done' | 'error' } | void {
            // result 被函数拆分为 {eventName, data}
            const result = parseSseChunk(chunk)
            if (!result) return
            const { eventName, data } = result

            if (eventName === 'connect') {
                console.log('SSE 已连接')
                return
            }

            // 后端定时心跳保活（防止nginx死亡）
            if(eventName === 'message' && data.content === ''){
                return
            }

            // 收到meta数据
            if (eventName === 'message' && data.type === 'metadata') {
                summary.currentVideoTitle = data.title || summary.currentVideoTitle
                summary.subtitleCount = data.subtitleCount || 0
                summary.stage = 'summarizing'
                return
            }

            // 收到正常的chunk流
            if (eventName === 'message' && data.type === 'chunk') {
                if (!data.content) return
                // 如果是第一条chunk，就改变占位符
                const placeholderIndex = messages.value.findIndex(m => m.isPlaceholder)
                if (placeholderIndex !== -1) {
                    stopAnim()
                    // 第一个chunk进行渲染
                    messages.value.splice(placeholderIndex, 1, {
                        id: messages.value[placeholderIndex].id,
                        role: 'ai',
                        content: renderMarkdown(data.content),
                        rawContent: data.content,
                        isStreaming: true
                    })
                } else {
                    // 追加chunk
                    const idx = messages.value.findIndex(m => m.isStreaming)
                    if (idx !== -1) {
                        const raw = (messages.value[idx].rawContent || '') + data.content
                        messages.value.splice(idx, 1, {
                            id: messages.value[idx].id,
                            role: 'ai',
                            content: renderMarkdown(raw),
                            rawContent: raw,
                            isStreaming: true
                        })
                    }
                }
                return
            }

            if (eventName === 'message' && data.type === 'done') {
                stopAnim()
                summary.currentVideoTitle = data.title || summary.currentVideoTitle
                summary.subtitleCount = data.subtitleCount || 0
                summary.currentConversationId = data.conversationId || null
                summary.currentVideoId = data.videoId || null
                summary.stage = 'done'
                const idx = messages.value.findIndex(m => m.isStreaming)
                if (idx !== -1) {
                    const raw = messages.value[idx].rawContent || ''

                    messages.value.splice(idx, 1, {
                        id: messages.value[idx].id,
                        role: 'ai',
                        content: renderMarkdown(raw)
                    })
                }
                summary.isLoading = false
                summary.confirmText = '开始总结'
                return { type: 'done' }
            }

            if (eventName === 'error') {
                stopAnim()
                const msg = data.message || '未知错误'
                const placeholderIndex = messages.value.findIndex(m => m.isPlaceholder)
                if (placeholderIndex !== -1) {

                    messages.value.splice(placeholderIndex, 1, {
                        id: messages.value[placeholderIndex].id,
                        role: 'ai',
                        content: '处理失败: ' + msg
                    })
                }
                summary.isLoading = false
                summary.confirmText = '开始总结'
                return { type: 'error' }
            }
        },

        // 点击开始总结后走这里
        async start(videoUrl: string, cookie: string, token: string): Promise<'cached' | 'streaming' | 'error'> {
            if (!videoUrl) {
                alert('请先上传视频或输入链接')
                return 'error'
            }
            if (!cookie) {
                alert('请先在设置里设置cookie')
                return 'error'
            }
            if (summary.isLoading) return 'error'

            try {
                summary.isLoading = true
                summary.confirmText = '解析中...'

                const res = await request.post('/agent/summary', { url: videoUrl, cookie })
                const { sessionId, status } = res.data

                // 如果击中缓存
                if (status === 1) {
                    summary.currentVideoTitle = res.data.title || ''
                    summary.subtitleCount = res.data.subtitleCount || 0
                    summary.currentConversationId = res.data.conversationId || null
                    summary.currentVideoId = res.data.videoId || null
                    summary.stage = 'done'
                    messages.value = [{
                        id: Date.now() + '_summary',
                        role: 'ai',
                        content: renderMarkdown(res.data.summary || '')
                    }]
                    summary.isLoading = false
                    summary.confirmText = '开始总结'
                    return 'cached'
                }

                // 没击中缓存，则先使用默认数据占位
                summary.currentVideoTitle = videoUrl
                summary.subtitleCount = 0
                summary.stage = 'parsing'
                startAnim()
                messages.value = [{
                    id: Date.now() + '_placeholder',
                    role: 'ai',
                    isPlaceholder: true,
                    placeholderType: 'summary'
                }]

                // 启动 SSE，不等待
                runSSE(sessionId, token)

                return 'streaming'

            } catch (error: any) {
                stopAnim()
                console.error('总结流程异常:', error)
                alert('请求失败: ' + (error.message || '请检查网络或登录状态'))
                summary.isLoading = false
                summary.confirmText = '开始总结'
                return 'error'
            }
        }
    })

    // 向后端发送SSE请求
    async function runSSE(sessionId: string, token: string) {
        let isStreamCompleted = false

        try {
            // 向后端发送SSE请求，由于axios不支持SSE，因此使用fetch和自定义header
            const response = await fetch(`/agent/summary/stream?sid=${sessionId}`, {
                headers: { 'token': token }
            })
            if (!response.ok) throw new Error(`SSE 连接失败: ${response.status}`)

            const reader = response.body!.getReader()
            const decoder = new TextDecoder()
            let buffer = ''

            while (true) {
                const { done, value } = await reader.read()

                if (done) {
                    const remaining = buffer.split('\n\n')
                    for (const chunk of remaining) {
                        const result = summary.processChunk(chunk)
                        if (result?.type === 'done' || result?.type === 'error') {
                            isStreamCompleted = true
                        }
                    }
                    break
                }

                buffer += decoder.decode(value, { stream: true })
                const chunks = buffer.split('\n\n')
                buffer = chunks.pop() || ''

                for (const chunk of chunks) {
                    const result = summary.processChunk(chunk)
                    if (result?.type === 'done' || result?.type === 'error') {
                        isStreamCompleted = true
                    }
                }
            }

            if (!isStreamCompleted) {
                alert('连接意外中断，视频可能已解析完成，请刷新页面查看历史记录')
            }

        } catch (error: any) {
            stopAnim()
            console.error('SSE 异常:', error)
            alert('SSE 连接失败: ' + (error.message || '请检查网络'))
        } finally {
            if (summary.isLoading) {
                summary.isLoading = false
                summary.confirmText = '开始总结'
            }
            stopAnim()
        }
    }

    return summary
}
