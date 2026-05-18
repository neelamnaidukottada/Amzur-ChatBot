import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
    },
    build: {
        rollupOptions: {
            output: {
                manualChunks: {
                    markdown_core: ['react-markdown'],
                    markdown_code: ['react-syntax-highlighter', 'react-syntax-highlighter/dist/esm/styles/prism'],
                    markdown_math: ['react-katex', 'katex'],
                },
            },
        },
    },
});
