import { useEffect, useRef, type ReactNode } from 'react';

const ENFOCABLES =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

/**
 * Hoja que sube desde abajo (captura, cambiar, leyenda, detalle de núcleo).
 * Esquinas de 24 px, asa arriba, se cierra con Escape o tocando el velo. El
 * foco queda dentro mientras está abierta y vuelve a su lugar al cerrarse.
 *
 * En el computador (desde 1024 px) la misma hoja se muestra como diálogo
 * centrado de 520 px, con las 4 esquinas redondeadas.
 */
export function HojaInferior({
  titulo,
  etiqueta,
  onCerrar,
  children,
}: {
  titulo?: string;
  /** Para `aria-label` cuando la hoja no tiene título visible. */
  etiqueta?: string;
  onCerrar: () => void;
  children: ReactNode;
}) {
  const hoja = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const anterior = document.activeElement as HTMLElement | null;
    hoja.current?.focus();
    const alTeclear = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCerrar();
        return;
      }
      if (e.key !== 'Tab' || !hoja.current) return;
      // Ciclo de foco: con la hoja abierta no se sale al fondo con el tabulador.
      const dentro = [...hoja.current.querySelectorAll<HTMLElement>(ENFOCABLES)];
      if (dentro.length === 0) return;
      const primero = dentro[0];
      const ultimo = dentro[dentro.length - 1];
      const activo = document.activeElement;
      if (e.shiftKey && (activo === primero || activo === hoja.current)) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && activo === ultimo) {
        e.preventDefault();
        primero.focus();
      }
    };
    document.addEventListener('keydown', alTeclear);
    return () => {
      document.removeEventListener('keydown', alTeclear);
      // Al cerrar, el foco vuelve a donde estaba la tía.
      anterior?.focus?.();
    };
  }, [onCerrar]);

  return (
    <div
      className="fixed inset-0 z-20 flex items-end justify-center bg-[rgba(34,38,46,0.42)] lg:items-center lg:p-6"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onCerrar();
      }}
    >
      <div
        ref={hoja}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={etiqueta ?? titulo}
        className="max-h-[88%] w-full max-w-tia animate-sube overflow-auto rounded-t-hoja bg-papel shadow-[0_-4px_16px_rgba(0,40,90,0.14)] px-[18px] pb-7 pt-[10px] outline-none md:max-w-[640px] lg:max-w-[520px] lg:rounded-hoja lg:pb-6 lg:shadow-[0_8px_28px_rgba(0,40,90,0.22)]"
      >
        {/* El asa del prototipo, que además es el botón para cerrar: así la
            hoja siempre tiene un control alcanzable con teclado. */}
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Cerrar"
          className="mx-auto mb-1 grid min-h-tactil w-16 place-items-center"
        >
          <span aria-hidden="true" className="block h-[5px] w-11 rounded-[9px] bg-linea" />
        </button>
        {titulo ? <h2>{titulo}</h2> : null}
        {children}
      </div>
    </div>
  );
}
