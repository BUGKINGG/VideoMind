import { ref } from 'vue'

/**
 * 动态占位消息
 */
export function usePlaceholder() {
    const dots = ref(1)
    let timer: ReturnType<typeof setInterval> | null = null

    const start = () => {
        stop()
        dots.value = 1
        timer = setInterval(() => {
            dots.value = dots.value % 3 + 1
        }, 500)
    }

    const stop = () => {
        if (timer) {
            clearInterval(timer)
            timer = null
        }
    }

    const summaryText = () => '正在解析视频内容并生成总结' + '.'.repeat(dots.value)
    const chatText = () => '思考中' + '.'.repeat(dots.value)

    return { dots, start, stop, summaryText, chatText }
}