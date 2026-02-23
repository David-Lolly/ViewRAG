/**
 * Mock SSE 流服务
 * 模拟后端 SSE 流式响应，按顺序发送 references → 多个 token → done 事件
 */

import { mockReferenceItems, mockStreamContent, mockRetrievedDocuments } from './mockReferences.js'

/**
 * 将文本拆分为模拟 token 片段
 * 按字符级别拆分，每个 token 包含 2-8 个字符，模拟真实 LLM 输出
 * @param {string} text - 完整文本
 * @returns {string[]} token 片段数组
 */
function splitIntoTokens(text) {
    const tokens = []
    let i = 0
    while (i < text.length) {
        const chunkSize = Math.floor(Math.random() * 7) + 2 // 2-8 字符
        tokens.push(text.slice(i, i + chunkSize))
        i += chunkSize
    }
    return tokens
}

/**
 * 模拟 SSE 流式聊天响应
 *
 * 事件发送顺序：
 * 1. 延迟 200ms 发送 references 事件（ReferenceItem[]）
 * 2. 每 50-100ms 发送一个 token 事件（string）
 * 3. 所有 token 发送完毕后发送 done 事件（null）
 *
 * @param {string} query - 用户问题
 * @param {Object} callbacks - 回调函数集合
 * @param {Function} [callbacks.onRetrievedDocs] - 接收 retrieved_documents 事件
 * @param {Function} callbacks.onReferences - 接收 references 事件
 * @param {Function} callbacks.onToken - 接收 token 事件
 * @param {Function} callbacks.onDone - 接收 done 事件
 * @param {Function} [callbacks.onError] - 接收 error 事件
 * @returns {{ abort: Function }} 可中断的控制器
 */
export function mockChatStream(query, callbacks) {
    const { onReferences, onToken, onDone, onError, onRetrievedDocs } = callbacks
    let aborted = false
    const timers = []

    function schedule(fn, delay) {
        if (aborted) return
        const id = setTimeout(() => {
            if (!aborted) fn()
        }, delay)
        timers.push(id)
    }

    // 1. 延迟 100ms 发送 retrieved_documents 事件
    schedule(() => {
        if (onRetrievedDocs) {
            onRetrievedDocs(mockRetrievedDocuments)
        }
    }, 100)

    // 2. 延迟 200ms 发送 references 事件
    schedule(() => {
        if (onReferences) {
            onReferences(mockReferenceItems)
        }
    }, 200)

    // 2. 拆分文本为 token 并逐个发送
    const tokens = splitIntoTokens(mockStreamContent)
    let delay = 300 // references 之后 100ms 开始发送 token

    tokens.forEach((token) => {
        const tokenDelay = Math.floor(Math.random() * 51) + 50 // 50-100ms
        delay += tokenDelay
        schedule(() => {
            if (onToken) {
                onToken(token)
            }
        }, delay)
    })

    // 3. 所有 token 发送完毕后发送 done 事件
    delay += 100
    schedule(() => {
        if (onDone) {
            onDone()
        }
    }, delay)

    return {
        abort() {
            aborted = true
            timers.forEach(id => clearTimeout(id))
            timers.length = 0
        }
    }
}
