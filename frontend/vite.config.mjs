import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

const file = (path) => fileURLToPath(new URL(path, import.meta.url));

export default defineConfig({
  esbuild: { jsx: 'automatic' },
  build: {
    outDir: file('../backend/static/mantine'),
    emptyOutDir: true,
    cssCodeSplit: false,
    target: 'es2022',
    rollupOptions: {
      input: {
        shell: file('./src/shell.js'),
        workspace: file('./src/workspace.jsx'),
        workbench: file('./src/workbench.jsx'),
      },
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: 'chunks/[name]-[hash].js',
        assetFileNames: (asset) =>
          asset.name?.endsWith('.css') ? 'workspace.css' : 'assets/[name]-[hash][extname]',
      },
    },
  },
});
