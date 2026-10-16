/**
 * Opciones de compilación de Huellita, leídas de las variables `VITE_*` de Vite
 * (ver `src/vite-env.d.ts`). Sin variables, la app queda como en la Fase 1:
 * datos locales y audio de hasta 5 minutos.
 *
 * - `VITE_DATOS`: `local` (semilla y `localStorage`) o `http` (BFF en AWS, `/api`).
 * - `VITE_AUDIO_MAX_SEGUNDOS`: tope de grabación; nunca menos de 240 s.
 * - `VITE_FECHA_HOY`: fecha "hoy" fija (`YYYY-MM-DD`) para una demo reproducible.
 */

export interface ConfigApp {
  datos: 'local' | 'http';
  audioMaxSegundos: number;
  fechaHoy?: string;
}

/** Tope de grabación por omisión (design.md, D12). */
export const AUDIO_MAX_POR_DEFECTO = 300;
/** Ninguna configuración puede bajar el tope de audio de 4 minutos (D12). */
export const AUDIO_MAX_MINIMO = 240;
/** El transcriptor acepta hasta 4 MiB de audio por nota. */
export const MAX_BYTES_AUDIO = 4 * 1024 * 1024;

type Entorno = Record<string, string | boolean | undefined>;

function texto(entorno: Entorno, clave: string): string | undefined {
  const valor = entorno[clave];
  return typeof valor === 'string' && valor.trim() !== '' ? valor.trim() : undefined;
}

/** Interpreta las variables de entorno. Pura, para poder probarla. */
export function leerConfig(entorno: Entorno): ConfigApp {
  const segundos = Number(texto(entorno, 'VITE_AUDIO_MAX_SEGUNDOS') ?? AUDIO_MAX_POR_DEFECTO);
  const fechaHoy = texto(entorno, 'VITE_FECHA_HOY');
  return {
    datos: texto(entorno, 'VITE_DATOS')?.toLowerCase() === 'http' ? 'http' : 'local',
    audioMaxSegundos: Number.isFinite(segundos)
      ? Math.max(AUDIO_MAX_MINIMO, Math.round(segundos))
      : AUDIO_MAX_POR_DEFECTO,
    ...(fechaHoy && /^\d{4}-\d{2}-\d{2}$/.test(fechaHoy) ? { fechaHoy } : {}),
  };
}

export const CONFIG: ConfigApp = leerConfig(import.meta.env as unknown as Entorno);
