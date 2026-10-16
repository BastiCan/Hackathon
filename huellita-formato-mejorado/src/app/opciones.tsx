/**
 * Opciones de la interfaz que dependen de la versión que se compiló (ver
 * `config.ts`). Van en un contexto para que las pruebas monten las dos
 * versiones sin recompilar.
 */
import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { CONFIG } from './config';

export interface OpcionesApp {
  /** Tope de grabación de audio, en segundos. */
  audioMaxSegundos: number;
}

const PREDETERMINADAS: OpcionesApp = {
  audioMaxSegundos: CONFIG.audioMaxSegundos,
};

const ContextoOpciones = createContext<OpcionesApp>(PREDETERMINADAS);

export function ProveedorOpciones({
  children,
  audioMaxSegundos,
}: Partial<OpcionesApp> & { children: ReactNode }) {
  const valor = useMemo<OpcionesApp>(
    () => ({
      audioMaxSegundos: audioMaxSegundos ?? PREDETERMINADAS.audioMaxSegundos,
    }),
    [audioMaxSegundos],
  );
  return <ContextoOpciones.Provider value={valor}>{children}</ContextoOpciones.Provider>;
}

export function useOpciones(): OpcionesApp {
  return useContext(ContextoOpciones);
}

/** Pantalla de inicio de las tías: Inicio reemplaza a la antigua agenda. */
export function rutaInicio(): string {
  return '/';
}
