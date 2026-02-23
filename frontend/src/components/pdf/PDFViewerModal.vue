<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="visible"
        class="fixed inset-0 z-[100] flex items-center justify-center bg-black/50"
        @click.self="$emit('close')"
      >
        <div class="bg-white rounded-xl shadow-2xl w-[92vw] max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">
          <!-- 头部 -->
          <div class="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
            <div class="flex items-center space-x-2 min-w-0">
              <svg class="w-5 h-5 text-red-500 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zM6 20V4h7v5h5v11H6z"/>
              </svg>
              <span class="text-sm font-medium text-text-primary truncate">{{ fileName }}</span>
            </div>
            <div class="flex items-center space-x-2">
              <!-- 侧边栏切换按钮 -->
              <button
                class="p-1.5 rounded-lg transition-colors"
                :class="sidebarOpen ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-200 text-gray-500'"
                @click="sidebarOpen = !sidebarOpen"
                title="切换侧边栏"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"/>
                </svg>
              </button>
              <!-- 关闭按钮 -->
              <button
                class="p-1.5 hover:bg-gray-200 rounded-lg transition-colors"
                @click="$emit('close')"
                title="关闭"
              >
                <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- 主体区域：侧边栏 + PDF -->
          <div class="flex-1 flex overflow-hidden">
            <!-- 侧边栏 -->
            <Transition name="sidebar-slide">
              <div v-if="sidebarOpen" class="sidebar-panel flex-shrink-0 bg-gray-50 border-r border-gray-200 overflow-y-auto overflow-x-hidden py-2 px-2 space-y-2">
                <div
                  v-for="(page, idx) in pageList"
                  :key="page"
                  class="thumb-item cursor-pointer rounded-lg border-2 transition-all duration-150"
                  :class="currentPageIndex === idx ? 'border-blue-500 shadow-md' : 'border-gray-200 hover:border-gray-400'"
                  @click="goToPage(idx)"
                >
                  <canvas
                    :ref="el => { if (el) thumbRefs[idx] = el }"
                    class="thumb-canvas"
                  ></canvas>
                  <div class="text-center text-[10px] text-gray-500 py-0.5 bg-white">{{ page }}</div>
                </div>
              </div>
            </Transition>

            <!-- PDF 渲染区域 -->
            <div class="flex-1 overflow-auto bg-gray-100 relative" ref="scrollContainer">
              <!-- 加载中 -->
              <div v-if="loading" class="flex items-center justify-center h-96">
                <div class="text-center space-y-3">
                  <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                  <p class="text-sm text-text-secondary">正在加载 PDF...</p>
                </div>
              </div>

              <!-- 加载失败 -->
              <div v-else-if="error" class="flex items-center justify-center h-96">
                <div class="text-center space-y-4 max-w-sm">
                  <svg class="w-12 h-12 text-red-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <div>
                    <p class="text-sm font-medium text-text-primary">PDF 加载失败</p>
                    <p class="text-xs text-text-secondary mt-1">{{ error }}</p>
                  </div>
                  <button
                    class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-lg transition-colors"
                    @click="loadPdf"
                  >
                    重试
                  </button>
                </div>
              </div>

              <!-- PDF Canvas -->
              <div v-else class="flex justify-center py-4">
                <div class="relative inline-block" ref="canvasWrapper">
                  <canvas ref="pdfCanvas"></canvas>
                  <canvas ref="highlightCanvas" class="absolute top-0 left-0 pointer-events-none"></canvas>
                </div>
              </div>
            </div>
          </div>

          <!-- 底部导航栏 + 缩放控制 -->
          <div v-if="!loading && !error && pageList.length > 0"
            class="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-t border-gray-200"
          >
            <!-- 左侧：页码导航 -->
            <div class="flex items-center space-x-3">
              <button
                class="p-1.5 rounded-lg transition-colors"
                :class="canGoPrev ? 'hover:bg-gray-200 text-gray-700' : 'text-gray-300 cursor-not-allowed'"
                :disabled="!canGoPrev"
                @click="goToPrevPage"
                title="上一页"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                </svg>
              </button>

              <span class="text-sm text-text-secondary select-none whitespace-nowrap">
                {{ currentPage }} / {{ pageList.length }} 页
              </span>

              <button
                class="p-1.5 rounded-lg transition-colors"
                :class="canGoNext ? 'hover:bg-gray-200 text-gray-700' : 'text-gray-300 cursor-not-allowed'"
                :disabled="!canGoNext"
                @click="goToNextPage"
                title="下一页"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
              </button>
            </div>

            <!-- 右侧：缩放控制 -->
            <div class="flex items-center space-x-2">
              <button
                class="p-1.5 rounded-lg transition-colors"
                :class="canZoomOut ? 'hover:bg-gray-200 text-gray-700' : 'text-gray-300 cursor-not-allowed'"
                :disabled="!canZoomOut"
                @click="zoomOut"
                title="缩小"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/>
                </svg>
              </button>

              <span class="text-sm text-text-secondary select-none w-14 text-center">{{ zoomPercent }}%</span>

              <button
                class="p-1.5 rounded-lg transition-colors"
                :class="canZoomIn ? 'hover:bg-gray-200 text-gray-700' : 'text-gray-300 cursor-not-allowed'"
                :disabled="!canZoomIn"
                @click="zoomIn"
                title="放大"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                </svg>
              </button>

              <button
                class="px-2 py-1 text-xs text-gray-500 hover:bg-gray-200 rounded-lg transition-colors"
                @click="resetZoom"
                title="重置缩放"
              >
                重置
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
// 显式导入 worker，利用 Vite 的 ?worker 处理打包
import PdfWorker from 'pdfjs-dist/build/pdf.worker.mjs?worker'
import { pdfToCanvasCoords, filterBboxesByPage, getPageList as computePageList } from '@/utils/pdfCoordinates.js'

// 使用 workerPort 而不是 workerSrc，彻底规避 Nginx 静态文件 MIME/路径问题
pdfjsLib.GlobalWorkerOptions.workerPort = new PdfWorker()

const ZOOM_STEP = 0.25
const ZOOM_MIN = 0.5
const ZOOM_MAX = 3.0
const THUMB_SCALE = 0.33
const SIDEBAR_WIDTH = 160 // 侧边栏宽度(px)
const SIDEBAR_PADDING = 16 // 侧边栏左右padding总和(px)
const THUMB_BORDER = 4 // 缩略图边框总宽度(px)

const props = defineProps({
  visible: { type: Boolean, default: false },
  docId: { type: String, default: '' },
  fileName: { type: String, default: '' },
  chunkBboxes: { type: Array, default: () => [] },
  chunkType: { type: String, default: 'TEXT' }
})

const API_BASE_URL = '/backend'

const emit = defineEmits(['close'])

// DOM refs
const scrollContainer = ref(null)
const canvasWrapper = ref(null)
const pdfCanvas = ref(null)
const highlightCanvas = ref(null)
const thumbRefs = ref({})

// 状态
const loading = ref(false)
const error = ref(null)
const currentPageIndex = ref(0)
const scale = ref(1)
const sidebarOpen = ref(true)
let pdfDoc = null

const pageList = computed(() => computePageList(props.chunkBboxes))
const currentPage = computed(() => pageList.value[currentPageIndex.value] || 1)
const canGoPrev = computed(() => currentPageIndex.value > 0)
const canGoNext = computed(() => currentPageIndex.value < pageList.value.length - 1)

const zoomPercent = computed(() => Math.round(scale.value * 100))
const canZoomIn = computed(() => scale.value < ZOOM_MAX)
const canZoomOut = computed(() => scale.value > ZOOM_MIN)

function zoomIn() {
  if (canZoomIn.value) {
    scale.value = Math.min(ZOOM_MAX, +(scale.value + ZOOM_STEP).toFixed(2))
    renderCurrentPage()
  }
}

function zoomOut() {
  if (canZoomOut.value) {
    scale.value = Math.max(ZOOM_MIN, +(scale.value - ZOOM_STEP).toFixed(2))
    renderCurrentPage()
  }
}

function resetZoom() {
  scale.value = 1
  renderCurrentPage()
}

function goToPrevPage() {
  if (canGoPrev.value) {
    currentPageIndex.value--
    renderCurrentPage()
  }
}

function goToNextPage() {
  if (canGoNext.value) {
    currentPageIndex.value++
    renderCurrentPage()
  }
}

function goToPage(idx) {
  if (idx !== currentPageIndex.value && idx >= 0 && idx < pageList.value.length) {
    currentPageIndex.value = idx
    renderCurrentPage()
  }
}

function getPdfUrl() {
  // 通过 doc_id 从后端 API 获取 PDF（MinIO）
  return `${API_BASE_URL}/api/v1/documents/${props.docId}/pdf`
}

async function loadPdf() {
  if (!props.visible) return

  loading.value = true
  error.value = null
  currentPageIndex.value = 0
  scale.value = 1
  thumbRefs.value = {}

  if (pdfDoc) {
    pdfDoc.destroy()
    pdfDoc = null
  }

  try {
    const url = getPdfUrl()
    console.time('[PDFViewerModal] 总加载耗时')
    console.time('[PDFViewerModal] 网络请求+PDF解析')
    const loadingTask = pdfjsLib.getDocument({
      url,
      // 本地 cmaps（public/cmaps/），消除中文字体警告，开发/生产均有效
      cMapUrl: '/cmaps/',
      cMapPacked: true,
    })
    pdfDoc = await loadingTask.promise
    console.timeEnd('[PDFViewerModal] 网络请求+PDF解析')
    await nextTick()
    console.time('[PDFViewerModal] 首页渲染')
    await renderCurrentPage()
    console.timeEnd('[PDFViewerModal] 首页渲染')
    console.time('[PDFViewerModal] 缩略图渲染')
    renderThumbnails()
    console.timeEnd('[PDFViewerModal] 缩略图渲染')
    console.timeEnd('[PDFViewerModal] 总加载耗时')
  } catch (err) {
    console.error('[PDFViewerModal] 加载失败:', err)
    error.value = err.message || '无法加载 PDF 文件'
  } finally {
    loading.value = false
  }
}

async function renderCurrentPage() {
  if (!pdfDoc || !pdfCanvas.value) return

  try {
    const pageNum = currentPage.value
    const page = await pdfDoc.getPage(pageNum)

    const dpr = window.devicePixelRatio || 1
    const cssViewport = page.getViewport({ scale: scale.value })
    const renderViewport = page.getViewport({ scale: scale.value * dpr })

    const canvas = pdfCanvas.value
    const ctx = canvas.getContext('2d')
    canvas.width = renderViewport.width
    canvas.height = renderViewport.height
    canvas.style.width = `${cssViewport.width}px`
    canvas.style.height = `${cssViewport.height}px`

    await page.render({ canvasContext: ctx, viewport: renderViewport }).promise

    drawHighlights(cssViewport, pageNum, dpr)
  } catch (err) {
    console.error('[PDFViewer] 渲染页面失败:', err)
    error.value = '页面渲染失败: ' + (err.message || '未知错误')
  }
}

function drawHighlights(cssViewport, pageNum, dpr) {
  const canvas = highlightCanvas.value
  if (!canvas) return

  canvas.width = cssViewport.width * dpr
  canvas.height = cssViewport.height * dpr
  canvas.style.width = `${cssViewport.width}px`
  canvas.style.height = `${cssViewport.height}px`

  const ctx = canvas.getContext('2d')
  ctx.scale(dpr, dpr)
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const pageBboxes = filterBboxesByPage(props.chunkBboxes, pageNum)

  for (const item of pageBboxes) {
    const coords = pdfToCanvasCoords(item.bbox, scale.value)

    if (props.chunkType === 'IMAGE') {
      ctx.strokeStyle = '#1890ff'
      ctx.lineWidth = 3
      ctx.strokeRect(coords.x, coords.y, coords.width, coords.height)
    } else {
      ctx.fillStyle = 'rgba(255, 255, 0, 0.3)'
      ctx.fillRect(coords.x, coords.y, coords.width, coords.height)
    }
  }
}

async function renderThumbnails() {
  if (!pdfDoc) return
  await nextTick()

  const thumbCssWidth = SIDEBAR_WIDTH - SIDEBAR_PADDING - THUMB_BORDER

  for (let i = 0; i < pageList.value.length; i++) {
    const pageNum = pageList.value[i]
    const canvas = thumbRefs.value[i]
    if (!canvas) continue

    try {
      const page = await pdfDoc.getPage(pageNum)
      const viewport = page.getViewport({ scale: THUMB_SCALE })
      // 设置canvas内部像素尺寸（用于渲染）
      canvas.width = viewport.width
      canvas.height = viewport.height
      // 设置canvas CSS显示尺寸（等比缩放适配侧边栏）
      const ratio = viewport.height / viewport.width
      canvas.style.width = thumbCssWidth + 'px'
      canvas.style.height = Math.round(thumbCssWidth * ratio) + 'px'
      canvas.style.display = 'block'
      const ctx = canvas.getContext('2d')
      await page.render({ canvasContext: ctx, viewport }).promise
    } catch (err) {
      console.error(`[PDFViewer] 缩略图渲染失败 (page ${pageNum}):`, err)
    }
  }
}

watch(() => props.visible, (val) => {
  if (val) {
    nextTick(() => loadPdf())
  } else {
    if (pdfDoc) {
      pdfDoc.destroy()
      pdfDoc = null
    }
  }
})

watch(() => props.chunkBboxes, () => {
  if (props.visible && pdfDoc) {
    currentPageIndex.value = 0
    renderCurrentPage()
    renderThumbnails()
  }
}, { deep: true })

onBeforeUnmount(() => {
  if (pdfDoc) {
    pdfDoc.destroy()
    pdfDoc = null
  }
})
</script>

<style scoped>
.modal-fade-enter-active {
  transition: opacity 0.2s ease-out;
}
.modal-fade-leave-active {
  transition: opacity 0.15s ease-in;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .bg-white {
  transition: transform 0.2s ease-out;
}
.modal-fade-leave-active .bg-white {
  transition: transform 0.15s ease-in;
}
.modal-fade-enter-from .bg-white {
  transform: scale(0.95);
}
.modal-fade-leave-to .bg-white {
  transform: scale(0.98);
}

/* 侧边栏过渡 */
.sidebar-slide-enter-active {
  transition: width 0.2s ease-out, opacity 0.2s ease-out;
}
.sidebar-slide-leave-active {
  transition: width 0.15s ease-in, opacity 0.15s ease-in;
}
.sidebar-slide-enter-from,
.sidebar-slide-leave-to {
  width: 0 !important;
  opacity: 0;
  overflow: hidden;
}

/* 侧边栏面板 */
.sidebar-panel {
  width: 160px;
}

/* 缩略图项 */
.thumb-item {
  overflow: hidden;
  background: #fff;
}

/* 缩略图canvas：不使用tailwind class，完全由JS控制尺寸 */
.thumb-canvas {
  /* 不设置任何宽高，由renderThumbnails中JS显式设置style.width/height */
}
</style>
