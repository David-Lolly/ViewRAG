import { ref, computed } from 'vue'

/**
 * 管理聊天引用的状态
 * - 缓存 ReferenceItem 数据
 * - 构建图片别名 → URL 映射
 * - 控制引用交互状态
 * - 按文档分组引用
 *
 * @returns {Object} 引用状态和方法
 */
export function useChatReferences() {
    /** @type {import('vue').Ref<Map<number, import('../mock/mockReferences.js').ReferenceItem>>} */
    const references = ref(new Map())

    /** @type {import('vue').Ref<Map<string, string>>} 图片别名 → URL */
    const imageMapping = ref(new Map())

    /** 引用标记是否可交互（流结束后为 true） */
    const isInteractive = ref(false)

    /**
     * 处理 references 事件：缓存引用数据并构建图片映射
     * @param {Array} refList - ReferenceItem 数组
     */
    function handleReferences(refList) {
        if (!Array.isArray(refList)) return

        const refMap = new Map()
        const imgMap = new Map()

        for (const item of refList) {
            refMap.set(item.ref_id, item)

            if (item.chunk_type === 'IMAGE' && item.image_alias && item.image_url) {
                // image_url 是后端返回的 /api/images/... 路径，加上 /backend 前缀走 vite proxy
                const url = item.image_url.startsWith('/api/')
                    ? `/backend${item.image_url}`
                    : item.image_url
                imgMap.set(item.image_alias, url)
            }
        }

        references.value = refMap
        imageMapping.value = imgMap
    }

    /**
     * 激活引用交互状态（done 事件时调用）
     */
    function activateInteraction() {
        isInteractive.value = true
    }

    /**
     * 根据 ref_id 获取引用数据
     * @param {number} refId
     * @returns {import('../mock/mockReferences.js').ReferenceItem|undefined}
     */
    function getReference(refId) {
        return references.value.get(refId)
    }

    /**
     * 根据图片别名获取 URL
     * @param {string} alias - 如 "图片1"
     * @returns {string|undefined}
     */
    function getImageUrl(alias) {
        return imageMapping.value.get(alias)
    }

    /**
     * 按文档分组引用
     * 返回格式: [{ doc_id, file_name, items: [ReferenceItem, ...] }, ...]
     */
    const groupedByDocument = computed(() => {
        const groups = new Map()

        for (const item of references.value.values()) {
            if (!groups.has(item.doc_id)) {
                groups.set(item.doc_id, {
                    doc_id: item.doc_id,
                    file_name: item.file_name,
                    items: []
                })
            }
            groups.get(item.doc_id).items.push(item)
        }

        return Array.from(groups.values())
    })

    /**
     * 重置所有状态
     */
    function reset() {
        references.value = new Map()
        imageMapping.value = new Map()
        isInteractive.value = false
    }

    return {
        references,
        imageMapping,
        isInteractive,
        handleReferences,
        activateInteraction,
        getReference,
        getImageUrl,
        groupedByDocument,
        reset
    }
}
