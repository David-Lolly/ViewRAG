import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import fs from 'fs'
import { viteStaticCopy } from 'vite-plugin-static-copy'

export default defineConfig({
  plugins: [
    vue(),
    // 构建时自动把 pdfjs-dist 的 cmaps 复制到 dist/cmaps/
    // 其他人 npm install 后直接可用，无需手动操作
    viteStaticCopy({
      targets: [
        {
          src: 'node_modules/pdfjs-dist/cmaps/*',
          dest: 'cmaps',
        },
      ],
    }),
    // 自定义插件：提供 dev/ 目录下的静态文件，以及开发时的 cmaps
    {
      name: 'serve-dev-static',
      configureServer(server) {
        // dev 环境提供 pdfjs-dist cmaps（viteStaticCopy 仅在 build 时运行）
        server.middlewares.use('/cmaps', (req, res, next) => {
          const filePath = path.resolve(__dirname, 'node_modules/pdfjs-dist/cmaps', decodeURIComponent(req.url.slice(1)))
          if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
            res.setHeader('Content-Type', 'application/octet-stream')
            fs.createReadStream(filePath).pipe(res)
          } else {
            next()
          }
        })
        server.middlewares.use('/dev', (req, res, next) => {
          const filePath = path.resolve(__dirname, 'dev', decodeURIComponent(req.url))
          if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
            res.setHeader('Content-Type', 'application/pdf')
            fs.createReadStream(filePath).pipe(res)
          } else {
            next()
          }
        })
      }
    }
  ],
  test: {
    environment: 'jsdom',
    globals: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    proxy: {
      '/backend': {
        target: 'http://localhost:5001', // 你的后端地址
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/backend/, ''),
        // 禁用代理缓冲，直接流式转发
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            // 对于大文件（如PDF），禁用缓冲
            if (proxyRes.headers['content-type']?.includes('pdf')) {
              proxyRes.headers['x-accel-buffering'] = 'no'
            }
          })
        },
      },
      // 其他代理规则可以继续添加
      '/login': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/register': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/session': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/sessions': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/search': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },

    },
  },
})