import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const target = env.VITE_API_TARGET || 'http://localhost:8000'

  return {
    plugins: [vue()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': {
          target,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
          timeout: 30000,
        },
        '/avatars': { target, changeOrigin: true },
        '/images': { target, changeOrigin: true },
      }
    }
  }
})
