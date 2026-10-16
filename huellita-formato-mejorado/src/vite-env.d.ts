/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

/** Opciones de compilación de Huellita (ver `src/app/config.ts`). */
interface ImportMetaEnv {
  readonly VITE_DATOS?: 'local' | 'http';
  readonly VITE_AUDIO_MAX_SEGUNDOS?: string;
  readonly VITE_FECHA_HOY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
