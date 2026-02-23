/**
 * 引用标记渲染器
 * 在 marked 渲染之后执行后处理，将引用标记转换为交互式 HTML 元素
 *
 * 处理两种引用格式：
 * 1. [N] → <sup> 上标元素（文本引用）
 * 2. ![描述](image:图片N) → <figure> 包裹的 <img> 元素（图片引用）
 */

/**
 * 尝试将一个多位数引用ID拆分为多个有效的单独引用
 * 例如：52 → [5, 2]（如果5和2都存在于references中）
 * 
 * @param {string} refIdStr - 引用ID字符串
 * @param {Map} references - ref_id → ReferenceItem 映射
 * @returns {number[]|null} 拆分后的引用ID数组，如果无法拆分则返回null
 */
function trySplitRefId(refIdStr, references) {
    // 如果引用ID本身存在，不需要拆分
    const refId = Number(refIdStr)
    if (references.has(refId)) {
        return null
    }

    // 尝试将多位数拆分为单个数字
    const digits = refIdStr.split('').map(Number)

    // 检查所有拆分出的数字是否都存在于references中
    const allExist = digits.every(d => references.has(d))

    if (allExist && digits.length > 1) {
        return digits
    }

    return null
}

/**
 * 将 Markdown 渲染后的 HTML 中的引用标记转换为交互式元素
 *
 * @param {string} html - marked 渲染后的 HTML
 * @param {Object} options
 * @param {boolean} options.isInteractive - 是否可交互（流结束后为 true）
 * @param {Map} options.imageMapping - 图片别名 → URL 映射
 * @param {Map} [options.references] - ref_id → ReferenceItem 映射，用于图片 figcaption
 * @returns {string} 处理后的 HTML
 */
export function processReferences(html, options = {}) {
    const { isInteractive = false, imageMapping = new Map(), references = new Map() } = options

    let result = html

    // 1. 替换图片引用 ![描述](image:图片N)
    //    需要先处理图片，避免被 [N] 的正则误匹配
    //    同时处理 marked 已渲染为 <img> 标签的情况
    result = result.replace(
        /!\[([^\]]*)\]\(image:([^)]+)\)/g,
        (match, description, alias) => {
            const url = imageMapping.get(alias)
            if (!url) return match

            return `<figure class="ref-image-container" data-image-alias="${alias}">` +
                `<img src="${url}" alt="${description}" class="ref-image" />` +
                `</figure>`
        }
    )

    // 1b. 处理 marked 已渲染为 <img src="image:图片N"> 的情况
    result = result.replace(
        /<img\s+src="image:([^"]+)"(?:\s+alt="([^"]*)")?[^>]*\/?>/g,
        (match, rawAlias, description) => {
            // 浏览器/marked 可能对中文做 URL 编码，需要解码
            const alias = decodeURIComponent(rawAlias)
            const url = imageMapping.get(alias)
            if (!url) return match

            return `<figure class="ref-image-container" data-image-alias="${alias}">` +
                `<img src="${url}" alt="${description || ''}" class="ref-image" />` +
                `</figure>`
        }
    )

    // 2. 替换文本引用 [N]（N 为正整数）
    //    使用负向前瞻排除已被处理为 HTML 属性的情况
    //    支持自动拆分：如 [52] 当52不存在但5和2都存在时，拆分为 [5][2]
    const stateClass = isInteractive ? 'ref-active' : 'ref-inactive'
    result = result.replace(
        /(?<!!)\[(\d+)\](?!\()/g,
        (match, refIdStr) => {
            // 尝试拆分多位数引用
            const splitIds = trySplitRefId(refIdStr, references)

            if (splitIds) {
                // 拆分成功，生成多个独立的引用标记
                return splitIds.map(id =>
                    `<sup class="ref-marker ${stateClass}" data-ref-id="${id}">${id}</sup>`
                ).join('')
            }

            // 不需要拆分，直接渲染
            return `<sup class="ref-marker ${stateClass}" data-ref-id="${refIdStr}">${refIdStr}</sup>`
        }
    )

    return result
}
