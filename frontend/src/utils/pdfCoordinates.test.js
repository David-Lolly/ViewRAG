import { describe, it, expect } from 'vitest'
import { pdfToCanvasCoords, filterBboxesByPage, getPageList } from './pdfCoordinates.js'

describe('pdfToCanvasCoords', () => {
    it('应正确转换 bbox 坐标到 Canvas 坐标（带缩放）', () => {
        const bbox = [72, 456, 540, 520]
        const scale = 1.5

        const result = pdfToCanvasCoords(bbox, scale)

        expect(result.x).toBeCloseTo(72 * 1.5)
        expect(result.y).toBeCloseTo(456 * 1.5)
        expect(result.width).toBeCloseTo((540 - 72) * 1.5)
        expect(result.height).toBeCloseTo((520 - 456) * 1.5)
    })

    it('scale=1 时坐标值等于原始值', () => {
        const bbox = [10, 20, 100, 80]
        const result = pdfToCanvasCoords(bbox, 1)

        expect(result.x).toBe(10)
        expect(result.y).toBe(20)
        expect(result.width).toBe(90)
        expect(result.height).toBe(60)
    })

    it('默认 scale=1', () => {
        const bbox = [10, 20, 100, 80]
        const result = pdfToCanvasCoords(bbox)

        expect(result.x).toBe(10)
        expect(result.y).toBe(20)
        expect(result.width).toBe(90)
        expect(result.height).toBe(60)
    })
})

describe('filterBboxesByPage', () => {
    // 注意：bboxes 中 page 是 0-based，参数 page 是 1-based
    const bboxes = [
        { page: 0, bbox: [0, 0, 100, 100] },
        { page: 1, bbox: [10, 10, 50, 50] },
        { page: 0, bbox: [20, 20, 80, 80] },
        { page: 2, bbox: [0, 0, 200, 200] },
    ]

    it('应只返回指定页码的 bbox（1-based 页码转 0-based）', () => {
        const result = filterBboxesByPage(bboxes, 1)
        expect(result).toHaveLength(2)
        expect(result.every(b => b.page === 0)).toBe(true)
    })

    it('无匹配时返回空数组', () => {
        expect(filterBboxesByPage(bboxes, 99)).toHaveLength(0)
    })
})

describe('getPageList', () => {
    it('应返回升序去重的 1-based 页码列表', () => {
        // page 是 0-based，getPageList 返回 1-based
        const bboxes = [
            { page: 2, bbox: [0, 0, 1, 1] },
            { page: 0, bbox: [0, 0, 1, 1] },
            { page: 2, bbox: [0, 0, 1, 1] },
            { page: 1, bbox: [0, 0, 1, 1] },
        ]
        expect(getPageList(bboxes)).toEqual([1, 2, 3])
    })

    it('空数组返回空列表', () => {
        expect(getPageList([])).toEqual([])
    })
})
