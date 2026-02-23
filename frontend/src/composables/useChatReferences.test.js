import { describe, it, expect } from 'vitest'
import { useChatReferences } from './useChatReferences.js'
import { mockReferenceItems } from '../mock/mockReferences.js'

describe('useChatReferences', () => {
    it('handleReferences 应缓存所有引用', () => {
        const { handleReferences, references } = useChatReferences()
        handleReferences(mockReferenceItems)

        expect(references.value.size).toBe(mockReferenceItems.length)
        // ref_id=1 是 IMAGE 类型
        expect(references.value.get(1).chunk_type).toBe('IMAGE')
        // ref_id=2 是 TEXT 类型
        expect(references.value.get(2).chunk_type).toBe('TEXT')
    })

    it('handleReferences 应构建图片映射（仅 IMAGE 类型）', () => {
        const { handleReferences, imageMapping } = useChatReferences()
        handleReferences(mockReferenceItems)

        // mock 数据中 ref_id=1 和 ref_id=3 是 IMAGE 类型，各有 image_alias
        const expectedImageCount = mockReferenceItems.filter(
            r => r.chunk_type === 'IMAGE' && r.image_alias && r.image_url
        ).length
        expect(imageMapping.value.size).toBe(expectedImageCount)
        expect(imageMapping.value.has('图片1')).toBe(true)
        expect(imageMapping.value.has('图片2')).toBe(true)
    })

    it('activateInteraction 应将 isInteractive 设为 true', () => {
        const { isInteractive, activateInteraction } = useChatReferences()
        expect(isInteractive.value).toBe(false)

        activateInteraction()
        expect(isInteractive.value).toBe(true)
    })

    it('getReference 应返回对应引用', () => {
        const { handleReferences, getReference } = useChatReferences()
        handleReferences(mockReferenceItems)

        const ref = getReference(3)
        expect(ref).toBeDefined()
        expect(ref.chunk_type).toBe('IMAGE')
        expect(ref.chunk_bboxes).toHaveLength(1)
    })

    it('getImageUrl 应返回图片 URL', () => {
        const { handleReferences, getImageUrl } = useChatReferences()
        handleReferences(mockReferenceItems)

        const expectedUrl = mockReferenceItems.find(r => r.image_alias === '图片1')?.image_url
        expect(getImageUrl('图片1')).toBe(expectedUrl)
        expect(getImageUrl('图片99')).toBeUndefined()
    })

    it('groupedByDocument 应按文档分组', () => {
        const { handleReferences, groupedByDocument } = useChatReferences()
        handleReferences(mockReferenceItems)

        const groups = groupedByDocument.value
        // 所有 mock 数据来自同一文档
        expect(groups).toHaveLength(1)
        expect(groups[0].items).toHaveLength(mockReferenceItems.length)
    })

    it('reset 应清空所有状态', () => {
        const { handleReferences, activateInteraction, reset, references, imageMapping, isInteractive } = useChatReferences()
        handleReferences(mockReferenceItems)
        activateInteraction()

        reset()

        expect(references.value.size).toBe(0)
        expect(imageMapping.value.size).toBe(0)
        expect(isInteractive.value).toBe(false)
    })

    it('handleReferences 传入非数组时不应报错', () => {
        const { handleReferences, references } = useChatReferences()
        handleReferences(null)
        expect(references.value.size).toBe(0)

        handleReferences(undefined)
        expect(references.value.size).toBe(0)
    })
})
