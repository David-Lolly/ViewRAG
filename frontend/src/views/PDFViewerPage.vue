<template>
  <div class="pdf-viewer-page min-h-screen bg-gray-100 flex flex-col">
    <!-- 顶部工具栏 -->
    <div class="bg-white border-b border-gray-200 px-4 py-2.5 flex items-center justify-between shadow-sm">
      <div class="flex items-center space-x-3 min-w-0">
        <!-- 侧边栏切换 -->
        <button
          class="p-1.5 rounded-lg transition-colors flex-shrink-0"
          :class="sidebarOpen ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100 text-gray-500'"
          @click="sidebarOpen = !sidebarOpen"
          title="切换侧边栏"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"/>
          </svg>
        </button>
        <svg class="w-5 h-5 text-red-500 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zM6 20V4h7v5h5v11H6z"/>
        </svg>
        <span class="text-sm font-medium text-gray-900 truncate">{{ fileName }}</span>
      </div>

      <!-- 中间：页码 + 缩放 -->
      <div class="flex items-center space-x-4">
        <span class="text-sm text-gray-600 select-none whitespace-nowrap">
          第 {{ currentVisiblePage }} 页 / 共 {{ totalPages }} 页
        </span>

        <div class="flex items-center space-x-1.5 border-l border-gray-200 pl-4">
          <button
            class="p-1 rounded transition-colors"
            :class="canZoomOut ? 'hover:bg-gray-100 text-gray-600' : 'text-gray-300 cursor-not-allowed'"
            :disabled="!canZoomOut"
            @click="zoomOut"
            title="缩小"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/>
            </svg>
          </button>
          <span class="text-sm text-gray-600 select-none w-12 text-center">{{ zoomPercent }}%</span>
          <button
            class="p-1 rounded transition-colors"
            :class="canZoomIn ? 'hover:bg-gray-100 text-gray-600' : 'text-gray-300 cursor-not-allowed'"
            :disabled="!canZoomIn"
            @click="zoomIn"
            title="放大"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
          </button>
          <button
            class="px-2 py-0.5 text-xs text-gray-500 hover:bg-gray-100 rounded transition-colors"
            @click="resetZoom"
            title="重置缩放"
          >
            重置
          </button>
        </div>
      </div>
    </div>

    <!-- 主体：侧边栏 + PDF -->
    <div class="flex-1 flex overflow-hidden">
      <!-- 侧边栏缩略图 -->
      <Transition name="sidebar-slide">
        <div v-if="sidebarOpen && totalPages > 0" class="sidebar-panel flex-shrink-0 bg-gray-50 border-r border-gray-200 overflow-y-auto py-2 px-2 space-y-2"
             :style="{ width: sidebarWidth + 'px' }">
          <div
            v-for="pageNum in totalPages"
            :key="pageNum"
            class="cursor-pointer rounded-lg border-2 transition-all duration-150 overflow-hidden bg-white"
            :class="currentVisiblePage === pageNum ? 'border-blue-500 shadow-md' : 'border-gray-200 hover:border-gray-400'"
            @click="scrollToPage(pageNum)"
          >
            <canvas :ref="el => setThumbRef(el, pageNum)"></canvas>
            <div class="text-center text-[10px] py-0.5"
                 :class="highlightPages.has(pageNum) ? 'text-blue-600 font-medium' : 'text-gray-400'">
              {{ pageNum }}
              <span v-if="highlightPages.has(pageNum)" class="inline-block w-1 h-1 bg-blue-500 rounded-full ml-0.5 align-middle"></span>
            </div>
          </div>
        </div>
      </Transition>

      <!-- PDF 渲染区域：连续滚动 -->
      <div class="flex-1 overflow-auto" ref="scrollContainer" @scroll="onScroll">
        <!-- 加载中 -->
        <div v-if="loading" class="flex items-center justify-center h-96">
          <div class="text-center space-y-3">
            <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p class="text-sm text-gray-500">正在加载 PDF...</p>
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
              <p class="text-sm font-medium text-gray-900">PDF 加载失败</p>
              <p class="text-xs text-gray-500 mt-1">{{ error }}</p>
            </div>
            <button
              class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-lg transition-colors"
              @click="loadPdf"
            >
              重试
            </button>
          </div>
        </div>

        <!-- 所有页面（懒加载占位） -->
        <div v-else class="flex flex-col items-center py-6 space-y-4" ref="pagesContainer">
          <div
            v-for="pageNum in totalPages"
            :key="pageNum"
            :ref="el => setPageRef(el, pageNum)"
            class="relative shadow-lg bg-white flex items-center justify-center"
            :style="getPageStyle(pageNum)"
          >
            <!-- 未渲染时显示占位 -->
            <div v-if="!renderedPages.has(pageNum)" class="text-gray-300 text-sm">
              第 {{ pageNum }} 页
            </div>
            <!-- 已渲染的 canvas -->
            <canvas v-show="renderedPages.has(pageNum)" :ref="el => setCanvasRef(el, pageNum, 'pdf')"></canvas>
            <canvas v-show="renderedPages.has(pageNum)" :ref="el => setCanvasRef(el, pageNum, 'highlight')" class="absolute top-0 left-0 pointer-events-none"></canvas>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
// 显式导入 worker，利用 Vite 的 ?worker 处理打包
import PdfWorker from 'pdfjs-dist/build/pdf.worker.mjs?worker'
import { pdfToCanvasCoords, filterBboxesByPage, getPageList as computePageList } from '@/utils/pdfCoordinates.js'
import { useRoute } from 'vue-router'

// 使用 workerPort 而不是 workerSrc，彻底规避 Nginx 静态文件 MIME/路径问题
pdfjsLib.GlobalWorkerOptions.workerPort = new PdfWorker()

const ZOOM_STEP = 0.25
const ZOOM_MIN = 0.5
const ZOOM_MAX = 3.0
const THUMB_SCALE = 0.2
const SIDEBAR_PADDING = 20
const PRELOAD_PAGES = 1 // 前后预加载页数

const route = useRoute()

// URL 参数
const fileName = computed(() => route.query.fileName || '')
const docId = computed(() => route.query.docId || '')
const chunkType = computed(() => route.query.chunkType || 'TEXT')
const chunkBboxes = computed(() => {
  try { return JSON.parse(route.query.bboxes || '[]') } catch { return [] }
})

// DOM refs
const scrollContainer = ref(null)
const pagesContainer = ref(null)
const pageRefs = {}
const canvasRefs = {}
const thumbRefs = {}

function setPageRef(el, pageNum) { if (el) pageRefs[pageNum] = el }
function setCanvasRef(el, pageNum, type) { if (el) canvasRefs[`${type}-${pageNum}`] = el }
function setThumbRef(el, pageNum) { if (el) thumbRefs[pageNum] = el }

// 状态
const loading = ref(false)
const error = ref(null)
const totalPages = ref(0)
const currentVisiblePage = ref(1)
const scale = ref(1)
const sidebarOpen = ref(true)
let pdfDoc = null
// 正在进行的 page.render() 任务，key = pageNum，用于取消并发渲染
const activeRenderTasks = {}

// 懒加载状态
const renderedPages = reactive(new Set())
const pageDimensions = reactive({}) // { pageNum: { width, height } }
let renderQueue = []
let isRendering = false

// 计算属性
const sidebarWidth = computed(() => Math.max(120, Math.min(220, Math.round(160 * Math.sqrt(scale.value)))))
const thumbCssWidth = computed(() => sidebarWidth.value - SIDEBAR_PADDING)
const pageList = computed(() => computePageList(chunkBboxes.value))
const highlightPages = computed(() => new Set(pageList.value))
const zoomPercent = computed(() => Math.round(scale.value * 100))
const canZoomIn = computed(() => scale.value < ZOOM_MAX)
const canZoomOut = computed(() => scale.value > ZOOM_MIN)

function zoomIn() {
  if (canZoomIn.value) {
    scale.value = Math.min(ZOOM_MAX, +(scale.value + ZOOM_STEP).toFixed(2))
  }
}
function zoomOut() {
  if (canZoomOut.value) {
    scale.value = Math.max(ZOOM_MIN, +(scale.value - ZOOM_STEP).toFixed(2))
  }
}
function resetZoom() {
  if (!scrollContainer.value || !pageDimensions[1]) { scale.value = 1; return }
  const PADDING = 48
  const scaleByWidth = (scrollContainer.value.clientWidth - PADDING) / pageDimensions[1].width
  const scaleByHeight = (scrollContainer.value.clientHeight - PADDING) / pageDimensions[1].height
  scale.value = Math.min(2.0, Math.max(0.5, +Math.min(scaleByWidth, scaleByHeight).toFixed(2)))
}

// 缩放时清空已渲染页面，重新懒加载
watch(scale, () => {
  if (pdfDoc) {
    // 取消所有正在进行的渲染任务，避免 scale 变化时并发 render 同一 canvas
    for (const task of Object.values(activeRenderTasks)) {
      try { task.cancel() } catch (_) {}
    }
    Object.keys(activeRenderTasks).forEach(k => delete activeRenderTasks[k])
    renderedPages.clear()
    renderVisiblePages()
  }
})

const API_BASE_URL = '/backend'
// PDF 大文件直接访问后端，绕过 Vite 代理
const PDF_DIRECT_URL = 'http://localhost:5001'

function getPdfUrl() {
  // 开发环境直接访问后端，避免 Vite 代理的性能问题
  if (import.meta.env.DEV) {
    return `${PDF_DIRECT_URL}/api/v1/documents/${docId.value}/pdf`
  }
  return `${API_BASE_URL}/api/v1/documents/${docId.value}/pdf`
}

// 获取页面占位样式
function getPageStyle(pageNum) {
  const dim = pageDimensions[pageNum]
  if (dim) {
    return { width: `${dim.width * scale.value}px`, height: `${dim.height * scale.value}px` }
  }
  // 默认 A4 比例
  return { width: `${595 * scale.value}px`, height: `${842 * scale.value}px` }
}

async function loadPdf() {
  loading.value = true
  error.value = null
  renderedPages.clear()

  if (pdfDoc) { pdfDoc.destroy(); pdfDoc = null }

  try {
    const url = getPdfUrl()
    console.time('[PDFViewerPage] 总加载耗时')

    // 验证 Worker 配置 (workerSrc 可能为空，因已使用 port)
    console.log('[PDFViewerPage] Worker配置:', pdfjsLib.GlobalWorkerOptions.workerPort ? '使用内联Worker' : '未知')

    // 方案四：直接传 URL 给 PDF.js，利用 Range 请求按需加载，无需先 fetch 全量
    console.time('[PDFViewerPage] 2.PDF解析')
    const loadingTask = pdfjsLib.getDocument({
      url,
      // 本地 cmaps（public/cmaps/），消除中文字体警告，开发/生产均有效
      cMapUrl: '/cmaps/',
      cMapPacked: true,
    })
    pdfDoc = await loadingTask.promise
    console.timeEnd('[PDFViewerPage] 2.PDF解析')

    totalPages.value = pdfDoc.numPages
    document.title = fileName.value || 'PDF 查看器'

    // 预获取所有页面尺寸（很快，不渲染）
    console.time('[PDFViewerPage] 获取页面尺寸')
    for (let i = 1; i <= totalPages.value; i++) {
      const page = await pdfDoc.getPage(i)
      const vp = page.getViewport({ scale: 1 })
      pageDimensions[i] = { width: vp.width, height: vp.height }
    }
    console.timeEnd('[PDFViewerPage] 获取页面尺寸')

    // 自适应初始缩放：让第一页完整显示在视口内（fit-page，宽高均不溢出）
    await nextTick()
    const containerWidth = scrollContainer.value?.clientWidth ?? 800
    const containerHeight = scrollContainer.value?.clientHeight ?? 600
    const firstPageWidth = pageDimensions[1]?.width ?? 595
    const firstPageHeight = pageDimensions[1]?.height ?? 842
    const PADDING = 48 // 四周留白
    const scaleByWidth = (containerWidth - PADDING) / firstPageWidth
    const scaleByHeight = (containerHeight - PADDING) / firstPageHeight
    const fitScale = Math.min(scaleByWidth, scaleByHeight)
    // 限制在 [0.5, 2.0] 范围内，避免过小或过大
    scale.value = Math.min(2.0, Math.max(0.5, +fitScale.toFixed(2)))

    loading.value = false
    await nextTick()

    // 只渲染可视区域
    console.time('[PDFViewerPage] 首屏渲染')
    await renderVisiblePages()
    console.timeEnd('[PDFViewerPage] 首屏渲染')

    // 缩略图在首屏渲染完全 settled 后再启动，避免与首屏 render() 任务并发同一 page 对象
    setTimeout(() => renderThumbnailsAsync(), 0)

    scrollToFirstHighlight()
    console.timeEnd('[PDFViewerPage] 总加载耗时')
  } catch (err) {
    console.error('[PDFViewerPage] 加载失败:', err)
    error.value = err.message || '无法加载 PDF 文件'
    loading.value = false
  }
}

// 获取当前可视页面范围
function getVisiblePageRange() {
  if (!scrollContainer.value) return { start: 1, end: 1 }
  const container = scrollContainer.value
  const containerRect = container.getBoundingClientRect()
  const scrollTop = container.scrollTop
  const viewHeight = containerRect.height

  let start = 1, end = 1
  for (let pageNum = 1; pageNum <= totalPages.value; pageNum++) {
    const el = pageRefs[pageNum]
    if (!el) continue
    const top = el.offsetTop
    const height = el.offsetHeight
    if (top + height >= scrollTop && top <= scrollTop + viewHeight) {
      if (start === 1 || pageNum < start) start = pageNum
      end = pageNum
    }
  }
  // 扩展预加载范围
  start = Math.max(1, start - PRELOAD_PAGES)
  end = Math.min(totalPages.value, end + PRELOAD_PAGES)
  return { start, end }
}

// 渲染可视区域页面
async function renderVisiblePages() {
  if (!pdfDoc) return
  const { start, end } = getVisiblePageRange()

  for (let pageNum = start; pageNum <= end; pageNum++) {
    if (!renderedPages.has(pageNum)) {
      await renderPage(pageNum)
    }
  }
}

// 渲染单页
async function renderPage(pageNum) {
  if (!pdfDoc || renderedPages.has(pageNum)) return

  // 若该页已有正在进行的渲染任务，先取消，避免 "same canvas" 并发错误
  if (activeRenderTasks[pageNum]) {
    try { activeRenderTasks[pageNum].cancel() } catch (_) {}
    delete activeRenderTasks[pageNum]
  }

  try {
    const page = await pdfDoc.getPage(pageNum)
    const dpr = window.devicePixelRatio || 1
    const cssViewport = page.getViewport({ scale: scale.value })
    const renderViewport = page.getViewport({ scale: scale.value * dpr })

    const canvas = canvasRefs[`pdf-${pageNum}`]
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    canvas.width = renderViewport.width
    canvas.height = renderViewport.height
    canvas.style.width = `${cssViewport.width}px`
    canvas.style.height = `${cssViewport.height}px`

    const renderTask = page.render({ canvasContext: ctx, viewport: renderViewport })
    activeRenderTasks[pageNum] = renderTask
    await renderTask.promise
    delete activeRenderTasks[pageNum]

    renderedPages.add(pageNum)
    drawHighlights(cssViewport, pageNum, dpr)
  } catch (err) {
    delete activeRenderTasks[pageNum]
    // cancelled 是主动取消，不是真正的错误，忽略
    if (err?.name !== 'RenderingCancelledException') {
      console.error(`[PDFViewerPage] 渲染第 ${pageNum} 页失败:`, err)
    }
  }
}

function drawHighlights(cssViewport, pageNum, dpr) {
  const canvas = canvasRefs[`highlight-${pageNum}`]
  if (!canvas) return

  canvas.width = cssViewport.width * dpr
  canvas.height = cssViewport.height * dpr
  canvas.style.width = `${cssViewport.width}px`
  canvas.style.height = `${cssViewport.height}px`

  const ctx = canvas.getContext('2d')
  ctx.scale(dpr, dpr)
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const pageBboxes = filterBboxesByPage(chunkBboxes.value, pageNum)
  for (const item of pageBboxes) {
    const coords = pdfToCanvasCoords(item.bbox, scale.value)
    if (chunkType.value === 'IMAGE') {
      ctx.strokeStyle = '#1890ff'
      ctx.lineWidth = 3
      ctx.strokeRect(coords.x, coords.y, coords.width, coords.height)
    } else {
      ctx.fillStyle = 'rgba(255, 255, 0, 0.3)'
      ctx.fillRect(coords.x, coords.y, coords.width, coords.height)
    }
  }
}

// 异步渲染缩略图（不阻塞）
async function renderThumbnailsAsync() {
  if (!pdfDoc) return
  await nextTick()

  for (let pageNum = 1; pageNum <= totalPages.value; pageNum++) {
    const canvas = thumbRefs[pageNum]
    if (!canvas) continue

    try {
      const page = await pdfDoc.getPage(pageNum)
      const dpr = window.devicePixelRatio || 1
      const cssViewport = page.getViewport({ scale: THUMB_SCALE })
      const renderViewport = page.getViewport({ scale: THUMB_SCALE * dpr })
      canvas.width = renderViewport.width
      canvas.height = renderViewport.height
      const ratio = cssViewport.height / cssViewport.width
      const w = thumbCssWidth.value
      canvas.style.width = w + 'px'
      canvas.style.height = Math.round(w * ratio) + 'px'
      canvas.style.display = 'block'
      const ctx = canvas.getContext('2d')
      await page.render({ canvasContext: ctx, viewport: renderViewport }).promise
    } catch (err) {
      console.error(`[PDFViewerPage] 缩略图渲染失败 (page ${pageNum}):`, err)
    }
    // 让出主线程，避免阻塞
    await new Promise(r => setTimeout(r, 0))
  }
}

function scrollToFirstHighlight() {
  if (pageList.value.length === 0) return
  const firstPage = pageList.value[0]
  const el = pageRefs[firstPage]
  if (el && scrollContainer.value) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

function scrollToPage(pageNum) {
  const el = pageRefs[pageNum]
  if (el && scrollContainer.value) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

let scrollTimer = null
function onScroll() {
  if (!scrollContainer.value) return

  // 更新当前页码
  const containerRect = scrollContainer.value.getBoundingClientRect()
  const midY = containerRect.top + containerRect.height / 2
  for (let pageNum = 1; pageNum <= totalPages.value; pageNum++) {
    const el = pageRefs[pageNum]
    if (!el) continue
    const rect = el.getBoundingClientRect()
    if (rect.top <= midY && rect.bottom >= midY) {
      currentVisiblePage.value = pageNum
      break
    }
  }

  // 防抖渲染可视页面
  clearTimeout(scrollTimer)
  scrollTimer = setTimeout(() => renderVisiblePages(), 100)
}

function onWheel(e) {
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault()
    if (e.deltaY < 0) zoomIn()
    else if (e.deltaY > 0) zoomOut()
  }
}

// 窗口 resize 时重新适应容器宽度（用户未手动调整过缩放时才自动响应）
let resizeTimer = null
function onResize() {
  if (!pdfDoc || !pageDimensions[1]) return
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    const containerWidth = scrollContainer.value?.clientWidth ?? 800
    const firstPageWidth = pageDimensions[1]?.width ?? 595
    const fitScale = (containerWidth - 48) / firstPageWidth
    scale.value = Math.min(2.0, Math.max(0.5, +fitScale.toFixed(2)))
  }, 150)
}

onMounted(() => {
  window.addEventListener('wheel', onWheel, { passive: false })
  window.addEventListener('resize', onResize)
  if (docId.value) {
    loadPdf()
  } else {
    error.value = '缺少文档ID参数'
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('wheel', onWheel)
  window.removeEventListener('resize', onResize)
  clearTimeout(scrollTimer)
  clearTimeout(resizeTimer)
  if (pdfDoc) { pdfDoc.destroy(); pdfDoc = null }
})
</script>

<style scoped>
.pdf-viewer-page { height: 100vh; }
.sidebar-slide-enter-active { transition: width 0.2s ease-out, opacity 0.2s ease-out; }
.sidebar-slide-leave-active { transition: width 0.15s ease-in, opacity 0.15s ease-in; }
.sidebar-slide-enter-from, .sidebar-slide-leave-to { width: 0 !important; opacity: 0; overflow: hidden; }
.sidebar-panel { scrollbar-width: thin; scrollbar-color: #d1d5db transparent; }
.sidebar-panel::-webkit-scrollbar { width: 4px; }
.sidebar-panel::-webkit-scrollbar-thumb { background-color: #d1d5db; border-radius: 2px; }
</style>
