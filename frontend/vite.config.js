import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/',  // Важно для корректных путей к статике
  build: {
    outDir: 'dist',  // Папка сборки
    emptyOutDir: true,  // Очищать папку перед сборкой
    rollupOptions: {
      output: {
        // Фиксированные имена файлов (опционально)
        entryFileNames: 'assets/[name].js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name].[ext]'
      }
    }
  },
  server: {
    // Настройки для разработки (опционально)
    host: true,
    port: 3000,
    strictPort: true
  }
});