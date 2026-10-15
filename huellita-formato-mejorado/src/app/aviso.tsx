/**
 * Aviso oscuro sobre el dock, con "Deshacer" cuando aplica. Dura 5 segundos
 * (el plazo para deshacer de "Aceptar las seguras", requisito 3.5).
 */
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';

type Deshacer = () => void | Promise<void>;

interface Aviso {
  texto: string;
  deshacer?: Deshacer;
}

const DURACION_MS = 5000;

const ContextoAviso = createContext<(texto: string, deshacer?: Deshacer) => void>(() => {});

export function ProveedorAviso({
  children,
  conDock = false,
}: {
  children: ReactNode;
  conDock?: boolean;
}) {
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const reloj = useRef<number | null>(null);

  const limpiar = useCallback(() => {
    if (reloj.current !== null) window.clearTimeout(reloj.current);
    reloj.current = null;
  }, []);

  const mostrar = useCallback(
    (texto: string, deshacer?: Deshacer) => {
      limpiar();
      setAviso({ texto, deshacer });
      reloj.current = window.setTimeout(() => setAviso(null), DURACION_MS);
    },
    [limpiar],
  );

  useEffect(() => limpiar, [limpiar]);

  return (
    <ContextoAviso.Provider value={mostrar}>
      {children}
      {aviso ? (
        <div
          className="pointer-events-none fixed left-1/2 z-30 w-full max-w-tia -translate-x-1/2 px-4"
          style={{ bottom: conDock ? 136 : 76 }}
        >
          <div
            role="status"
            className="pointer-events-auto flex animate-sube items-center justify-between gap-[10px] rounded-tarjeta bg-tinta px-4 py-3 text-white"
          >
            <span>{aviso.texto}</span>
            {aviso.deshacer ? (
              <button
                type="button"
                className="min-h-tactil font-bold text-logo-amarillo"
                onClick={() => {
                  const accion = aviso.deshacer;
                  limpiar();
                  setAviso(null);
                  void accion?.();
                }}
              >
                Deshacer
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
    </ContextoAviso.Provider>
  );
}

/** Muestra un aviso: `aviso('Listo, lo verás en Revisar')`. */
export function useAviso() {
  return useContext(ContextoAviso);
}
