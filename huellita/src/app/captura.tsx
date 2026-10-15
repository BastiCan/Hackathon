/**
 * Captura de evidencias desde cualquier pantalla. Abre la hoja que corresponde
 * y, al enviar, devuelve el control de inmediato con el aviso
 * "Listo, lo verás en Revisar": nunca se espera a que Huellita termine de leer
 * (requisito 1.5).
 */
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { HojaAudio, HojaFoto, HojaTexto } from '../components/Captura';
import type { Formato } from '../lib/tipos';
import { capturar } from '../services/captura';
import { useAviso } from './aviso';
import { useServicios } from './servicios';

export interface NinoAsociado {
  id: string;
  nombre: string;
}

const ContextoCaptura = createContext<(formato: Formato) => void>(() => {});

export function ProveedorCaptura({
  children,
  nino,
}: {
  children: ReactNode;
  /** Si la captura empieza en la ficha, la evidencia queda asociada al niño/a. */
  nino?: NinoAsociado | null;
}) {
  const { datos, ia } = useServicios();
  const aviso = useAviso();
  const [hoja, setHoja] = useState<Formato | null>(null);

  const servicios = useMemo(() => ({ datos, ia }), [datos, ia]);

  const enviar = useCallback(
    (formato: Formato, archivo?: Blob, texto?: string) => {
      setHoja(null);
      void capturar(formato, archivo, texto, nino?.id, servicios).then(
        () => aviso('Listo, lo verás en Revisar'),
        () => aviso('No pudimos guardar la nota. Inténtalo de nuevo.'),
      );
    },
    [aviso, nino?.id, servicios],
  );

  const enviarFoto = useCallback((archivo: Blob) => enviar('foto', archivo), [enviar]);
  const enviarAudio = useCallback((archivo: Blob) => enviar('audio', archivo), [enviar]);
  const enviarTexto = useCallback((texto: string) => enviar('texto', undefined, texto), [enviar]);
  const cerrar = useCallback(() => setHoja(null), []);
  const abrirTexto = useCallback(() => setHoja('texto'), []);

  return (
    <ContextoCaptura.Provider value={setHoja}>
      {children}
      {hoja === 'foto' ? <HojaFoto onEnviar={enviarFoto} onCerrar={cerrar} /> : null}
      {hoja === 'audio' ? (
        <HojaAudio onEnviar={enviarAudio} onCerrar={cerrar} onEscribir={abrirTexto} />
      ) : null}
      {hoja === 'texto' ? <HojaTexto onEnviar={enviarTexto} onCerrar={cerrar} /> : null}
    </ContextoCaptura.Provider>
  );
}

/** Abre la captura: `abrirCaptura('audio')`. */
export function useCaptura() {
  return useContext(ContextoCaptura);
}
