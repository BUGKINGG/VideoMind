/**
 * 消息实体
 */
export interface Message{
    id: string
    role: 'user' | 'ai'
    content?: string
    rawContent?: string
    isPlaceholder?: boolean
    placeholderType?: 'summary' | 'chat'
    isStreaming?: boolean
}