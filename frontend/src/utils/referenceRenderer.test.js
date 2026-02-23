import { describe, it, expect } from 'vitest'
import { processReferences } from './referenceRenderer.js'

describe('processReferences', () => {
    it('应将 [N] 替换为 sup 元素（非交互状态）', () => {
        const html = '<p>注意力机制[1]是核心</p>'
        const result = processReferences(html, { isInteractive: false })

        expect(result).toContain('data-ref-id="1"')
        expect(result).toContain('ref-inactive')
        expect(result).not.toContain('ref-active')
    })

    it('应将 [N] 替换为 sup 元素（交互状态）', () => {
        const html = '<p>注意力机制[1]是核心</p>'
        const result = processReferences(html, { isInteractive: true })

        expect(result).toContain('data-ref-id="1"')
        expect(result).toContain('ref-active')
        expect(result).not.toContain('ref-inactive')
    })

    it('应将图片引用替换为 img 元素', () => {
        const html = '<p>架构图：![Transformer架构](image:图片1)</p>'
        const imageMapping = new Map([['图片1', 'http://example.com/img.jpg']])
        const result = processReferences(html, { imageMapping })

        expect(result).toContain('<img src="http://example.com/img.jpg"')
        expect(result).toContain('alt="Transformer架构"')
        expect(result).toContain('ref-image-container')
    })

    it('图片映射中无对应别名时保留原文', () => {
        const html = '<p>![描述](image:图片99)</p>'
        const result = processReferences(html, { imageMapping: new Map() })

        expect(result).toContain('![描述](image:图片99)')
    })

    it('应处理多个引用标记', () => {
        const html = '<p>第一点[1]和第二点[2]</p>'
        const result = processReferences(html, { isInteractive: true })

        expect(result).toContain('data-ref-id="1"')
        expect(result).toContain('data-ref-id="2"')
    })

    it('不应替换 Markdown 链接格式 [text](url)', () => {
        const html = '<p>查看<a href="http://example.com">链接</a></p>'
        const result = processReferences(html)
        // 已渲染为 HTML 的链接不应被修改
        expect(result).toContain('<a href="http://example.com">链接</a>')
    })
})
