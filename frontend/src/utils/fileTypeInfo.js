/**
 * 根据文件名扩展名返回文件类型信息（图标颜色、标签）
 * @param {string} fileName - 文件名
 * @returns {{ bgClass: string, textClass: string, label: string }}
 */
export function getFileTypeInfo(fileName) {
    const ext = (fileName || '').split('.').pop().toLowerCase()
    switch (ext) {
        case 'pdf':
            return { bgClass: 'bg-red-50', textClass: 'text-red-500', label: 'PDF' }
        case 'doc':
        case 'docx':
            return { bgClass: 'bg-blue-50', textClass: 'text-blue-500', label: 'DOC' }
        case 'xlsx':
            return { bgClass: 'bg-green-50', textClass: 'text-green-500', label: 'XLS' }
        case 'pptx':
            return { bgClass: 'bg-orange-50', textClass: 'text-orange-500', label: 'PPT' }
        case 'txt':
            return { bgClass: 'bg-gray-100', textClass: 'text-gray-500', label: 'TXT' }
        default:
            return { bgClass: 'bg-gray-100', textClass: 'text-gray-400', label: 'FILE' }
    }
}
