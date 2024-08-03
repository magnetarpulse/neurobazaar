import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import vuetify from 'vite-plugin-vuetify';
import { resolve } from 'path';

const mainJsPath = resolve(__dirname, 'main.js');

export default defineConfig({
    plugins: [
        vue(),
        vuetify({ autoImport: true }),
    ],
    root: __dirname,
    base: '/static/',
    server: {
        host: 'localhost',
        port: 5173,
        open: false,
        watch: {
            usePolling: true,
            disableGlobbing: false,
        },
    },
    resolve: {
        alias: {
            vue: 'vue/dist/vue.esm-bundler.js'
        },
        extensions: ['.js', '.json'],
    },
    build: {
        outDir: resolve(__dirname, 'dist'),
        assetsDir: '',
        manifest: true,
        emptyOutDir: true,
        target: 'es2015',
        rollupOptions: {
            input: {
                main: mainJsPath,
            },
            output: {
                chunkFileNames: undefined,
            },
        },
    },
});