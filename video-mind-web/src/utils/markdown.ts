import { marked } from 'marked'

// 配置 marked：支持换行转 <br>，禁用标题 ID 减少 DOM 抖动
marked.setOptions({
    breaks: true,
    gfm: true,
})

// 渲染 Markdown 为 HTML
export function renderMarkdown(text: string) : string {
    return marked.parse(text || '') as string
}