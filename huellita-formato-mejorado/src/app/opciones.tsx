/**
 * Opciones de la interfaz que dependen de la versión que se compiló (ver
 * `config.ts`). Van en un contexto para que las pruebas monten las dos
 * versiones sin recompilar.
 */
import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { CONFIG } from './config';

export interface OpcionesApp {
  /** Con agenda, el inicio es "/"; sin agenda (versión AWS), Mi sala. */
  agenda: boolean;
  /** Tope de grabación de audio, en segundos. */
  audioMaxSegundos: number;
}

const PREDETERMINADAS: OpcionesApp = {
  agenda: CONFIG.agenda,
  audioMaxSegundos: CONFIG.audioMaxSegundos,
};

const ContextoOpciones = createContext<OpcionesApp>(PREDETERMINADAS);

export function ProveedorOpciones({
  children,
  agenda,
  audioMaxSegundos,
}: Partial<OpcionesApp> & { children: ReactNode }) {
  const valor = useMemo<OpcionesApp>(
    () => ({
      agenda: agenda ?? PREDETERMINADAS.agenda,
      audioMaxSegundos: audioMaxSegundos ?? PREDETERMINADAS.audioMaxSegundos,
    }),
    [agenda, audioMaxSegundos],
  );
  return <ContextoOpciones.Provider value={valor}>{children}</ContextoOpciones.Provider>;
}

export function useOpciones(): OpcionesApp {
  return useContext(ContextoOpciones);
}

/** Pantalla de inicio de las tías: la agenda o, si está oculta, Mi sala. */
export function rutaInicio(opciones: Pick<OpcionesApp, 'agenda'>): string {
  return opciones.agenda ? '/' : '/sala';
}
