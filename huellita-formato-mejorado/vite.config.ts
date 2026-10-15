import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  /*
   * Carpeta desde la que se sirve la app. Por omisión la raíz del dominio; para
   * publicarla en una subcarpeta (por ejemplo GitHub Pages en `/Hackathon/`) se
   * compila con `BASE_URL=/Hackathon/ npm run build`.
   *
   * No se usa `base: './'`: con rutas relativas, al recargar una dirección
   * anidada (`/nino/NINO-00042`) el navegador buscaría el JS en
   * `/nino/assets/…` y la app queda en blanco. Con una base explícita, las
   * rutas de los archivos son absolutas y el enlace directo sigue funcionando.
   */
  base: process.env.BASE_URL ?? '/',
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icono.svg'],
      manifest: {
        name: 'Huellita',
        short_name: 'Huellita',
        description: 'Registra evidencias del desarrollo de los niños y niñas en 2 toques.',
        lang: 'es-CL',
        start_url: './',
        scope: './',
        display: 'standalone',
        background_color: '#ffffff',
        // Azul oficial de Integra (Pantone 300C), igual que en `index.html`.
        theme_color: '#0063BD',
        icons: [
          { src: 'icono.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' },
          { src: 'icono.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'maskable' },
        ],
      },
      workbox: {
        /*
         * Todo lo que la app necesita sin conexión: el HTML, el JS (que ya
         * incluye la rúbrica y la semilla de la demo), los estilos, el ícono y
         * las tipografías autoalojadas.
         */
        globPatterns: ['**/*.{js,css,html,svg,png,ico,webmanifest,woff,woff2}'],
        // La app es de una sola página: cualquier ruta (/revisar, /nino/ID)
        // se sirve desde el index cacheado.
        navigateFallback: 'index.html',
        navigateFallbackDenylist: [/^\/api\//],
        cleanupOutdatedCaches: true,
        clientsClaim: true,
      },
    }),
  ],
  resolve: {
    alias: {
      '@data': fileURLToPath(new URL('./data', import.meta.url)),
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
  },
});
