/**
 * PDF 坐标转换工具函数
 *
 * 后端返回的 bbox 坐标基于 PDF 原始页面尺寸（左上角原点）。
 * PDF 以原始大小（scale=1）渲染时，bbox 坐标可直接使用。
 */

/**
 * 将 bbox 坐标转换为 Canvas 坐标（支持缩放）
 *
 * @param {number[]} bbox - [x0, y0, x1, y1] 基于 PDF 原始尺寸的坐标（左上角原点）
 * @param {number} [scale=1] - 缩放比例
 * @returns {{ x: number, y: number, width: number, height: number }} Canvas 坐标
 */
export function pdfToCanvasCoords(bbox, scale = 1) {
    const [x0, y0, x1, y1] = bbox
    return {
        x: x0 * scale,
        y: y0 * scale,
        width: (x1 - x0) * scale,
        height: (y1 - y0) * scale
    }
}

/**
 * 过滤指定页码的 bbox
 * 注意：后端 page 是 0-based index，参数 page 是 PDF.js 的 1-based 页码
 *
 * @param {Array<{ page: number, bbox: number[] }>} bboxes - chunk_bboxes 数组（page 从 0 开始）
 * @param {number} page - 目标页码（从 1 开始，PDF.js 格式）
 * @returns {Array<{ page: number, bbox: number[] }>} 该页码的 bbox 列表
 */
export function filterBboxesByPage(bboxes, page) {
    return bboxes.filter(b => b.page + 1 === page)
}

/**
 * 获取包含引用的页面列表（升序去重，返回 1-based 页码）
 *
 * @param {Array<{ page: number, bbox: number[] }>} bboxes - chunk_bboxes 数组（page 从 0 开始）
 * @returns {number[]} 升序排列的页码列表（从 1 开始）
 */
export function getPageList(bboxes) {
    return [...new Set(bboxes.map(b => b.page + 1))].sort((a, b) => a - b)
}
