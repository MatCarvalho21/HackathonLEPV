import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: '127.0.0.1',
    proxy: { '/api': 'http://127.0.0.1:8000' },
    // O front fica em src/; vigiar o resto (venv, base vetorial, banco, PDFs) estoura o limite de watchers do sistema.
    watch: {
      ignored: ['**/.venv/**', '**/chroma_db/**', '**/backend/**', '**/pdfs/**', '**/data/**', '**/prompts/**',
                '**/frontend/**', '**/src/agente_perfil/**', '**/src/rag/**', '**/*.sqlite3*'],
    },
  },
});
