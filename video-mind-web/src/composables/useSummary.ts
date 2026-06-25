import { reactive, type Ref } from 'vue'
import { usePlaceholder } from './usePlaceholder'
import { parseSseChunk } from '../utils/sseParser'
import { renderMarkdown } from '../utils/markdown'
import request from '../utils/request'
import type { Message } from '../types/message'
import { saveSseState, clearSseState } from './sseSession'

export type SummaryStage = 'parsing' | 'summarizing' | 'done'

export function useSummary(messages: Ref<Message[]>) {
    const { start: startAnim, stop: stopAnim } = usePlaceholder()

    // SSE fetch 的 AbortController，用于切换历史记录时中断旧连接
    let abortController: AbortController | null = null

    const summary = reactive({
        isLoading: false,
        confirmText: '开始总结',
        stage: 'parsing' as SummaryStage,
        currentVideoTitle: '',
        subtitleCount: 0,
        currentConversationId: null as number | null,
        currentVideoId: null as number | null,

        /** 中断当前 SSE 连接（切换历史记录时调用） */
        abort() {
            if (abortController) {
                abortController.abort()
                abortController = null
            }
        },

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
                if (data.conversationId) {
                    summary.currentConversationId = data.conversationId
                }
                return
            }

            // 断线续传：收到 catchup 事件，将累积内容一次性替换到界面上
            if (eventName === 'message' && data.type === 'catchup') {
                if (!data.content) return
                // 更新元数据
                if (data.title) summary.currentVideoTitle = data.title
                if (data.subtitleCount) summary.subtitleCount = data.subtitleCount
                if (data.conversationId) summary.currentConversationId = data.conversationId
                summary.stage = 'summarizing'
                stopAnim()
                // 替换占位符为累积内容
                const placeholderIndex = messages.value.findIndex(m => m.isPlaceholder)
                if (placeholderIndex !== -1) {
                    const msgId = messages.value[placeholderIndex].id
                    // 如果已经有 streaming 消息（重连场景），替换它
                    const streamingIdx = messages.value.findIndex(m => m.isStreaming)
                    if (streamingIdx !== -1) {
                        messages.value.splice(streamingIdx, 1, {
                            id: messages.value[streamingIdx].id,
                            role: 'ai',
                            content: renderMarkdown(data.content),
                            rawContent: data.content,
                            isStreaming: true
                        })
                    } else if (placeholderIndex !== -1) {
                        messages.value.splice(placeholderIndex, 1, {
                            id: msgId,
                            role: 'ai',
                            content: renderMarkdown(data.content),
                            rawContent: data.content,
                            isStreaming: true
                        })
                    }
                } else {
                    // 没有占位符，说明是重连到已有消息
                    const streamingIdx = messages.value.findIndex(m => m.isStreaming)
                    if (streamingIdx !== -1) {
                        messages.value.splice(streamingIdx, 1, {
                            id: messages.value[streamingIdx].id,
                            role: 'ai',
                            content: renderMarkdown(data.content),
                            rawContent: data.content,
                            isStreaming: true
                        })
                    }
                }
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
                // 匹配流式消息或占位符（重连场景下可能是纯 placeholder）
                const idx = messages.value.findIndex(m => m.isStreaming || m.isPlaceholder)
                if (idx !== -1) {
                    const raw = messages.value[idx].rawContent || data.summary || ''
                    messages.value.splice(idx, 1, {
                        id: messages.value[idx].id,
                        role: 'ai',
                        content: renderMarkdown(raw)
                    })
                }
                summary.isLoading = false
                summary.confirmText = '开始总结'
                // 正常完成，清除会话状态
                clearSseState()
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
                // 错误结束，清除会话状态
                clearSseState()
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

                // 保存会话状态到 sessionStorage，供刷新后恢复
                saveSseState({ sid: sessionId, type: 'summary', view: 'chat' })

                // 启动 SSE，不等待
                runSSE(sessionId, token)

                return 'streaming'

            } catch (error: any) {
                stopAnim()
                console.error('总结流程异常:', error)
                alert('请求失败: ' + (error.message || '请检查网络或登录状态'))
                summary.isLoading = false
                summary.confirmText = '开始总结'
                clearSseState()
                return 'error'
            }
        },

        // 暴露给 Home.vue，用于页面刷新后自动重连
        reconnect(sessionId: string, token: string) {
            summary.isLoading = true
            summary.confirmText = '重连中...'
            summary.stage = 'parsing'
            startAnim()
            messages.value = [{
                id: Date.now() + '_placeholder',
                role: 'ai',
                isPlaceholder: true,
                isStreaming: true,
                placeholderType: 'summary'
            }]
            runSSE(sessionId, token)
        }
    })

    // 向后端发送SSE请求（带指数退避重连）
    async function runSSE(sessionId: string, token: string, retryCount = 0) {
        const MAX_RETRIES = 3
        const delays = [1000, 2000, 4000] // 指数退避
        let isStreamCompleted = false

        // 创建新的 AbortController（中断旧的）
        if (abortController) abortController.abort()
        abortController = new AbortController()
        const signal = abortController.signal

        try {
            // 向后端发送SSE请求，由于axios不支持SSE，因此使用fetch和自定义header
            const response = await fetch(`/agent/summary/stream?sid=${sessionId}`, {
                headers: { 'token': token },
                signal
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
                console.warn('[SSE] 连接中断，未收到 done/error 事件')
                // 自动重连
                if (retryCount < MAX_RETRIES) {
                    console.log(`[SSE] ${delays[retryCount]}ms 后进行第 ${retryCount + 1} 次重连...`)
                    await sleep(delays[retryCount])
                    return runSSE(sessionId, token, retryCount + 1)
                }
                alert('连接意外中断，视频可能已解析完成，请刷新页面查看历史记录')
            }

        } catch (error: any) {
            // AbortError 是用户主动切换导致的，静默处理，不重试
            if (error.name === 'AbortError') {
                console.log('[SSE] 连接已被中断（用户切换上下文）')
                return
            }
            stopAnim()
            console.error('SSE 异常:', error)
            // 自动重连
            if (retryCount < MAX_RETRIES) {
                console.log(`[SSE] 错误重连，${delays[retryCount]}ms 后进行第 ${retryCount + 1} 次重试...`)
                await sleep(delays[retryCount])
                // 重连前重建 SSE 流读取
                return runSSE(sessionId, token, retryCount + 1)
            }
            // 最终失败
            alert('SSE 连接失败: ' + (error.message || '请检查网络'))
        } finally {
            if (retryCount >= MAX_RETRIES || isStreamCompleted) {
                if (summary.isLoading) {
                    summary.isLoading = false
                    summary.confirmText = '开始总结'
                }
                stopAnim()
            }
        }
    }

    function sleep(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms))
    }

    return summary
}
