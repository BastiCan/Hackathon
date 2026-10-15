import { Building2, ClipboardCheck, LayoutGrid, type LucideIcon } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

/**
 * Barra inferior fija: Mi sala · Revisar (con el contador de pendientes) ·
 * Directora (solo para el rol directora).
 */
export function BarraInferior({
  pendientes,
  esDirectora,
  ancho = 'max-w-tia',
}: {
  pendientes: number;
  esDirectora: boolean;
  /** Mismo ancho que el contenido: 480 px para la tía, 1100 para la directora. */
  ancho?: string;
}) {
  const { pathname } = useLocation();
  const enSala = pathname === '/' || pathname.startsWith('/nino/');

  return (
    <nav
      aria-label="Principal"
      className={`fixed bottom-0 left-1/2 z-10 flex h-[72px] w-full -translate-x-1/2 border-t border-linea bg-papel ${ancho}`}
    >
      <Destino a="/" icono={LayoutGrid} texto="Mi sala" activo={enSala} />
      <Destino
        a="/revisar"
        icono={ClipboardCheck}
        texto="Revisar"
        activo={pathname === '/revisar'}
        contador={pendientes}
      />
      {esDirectora ? (
        <Destino
          a="/directora"
          icono={Building2}
          texto="Directora"
          activo={pathname.startsWith('/directora')}
        />
      ) : null}
    </nav>
  );
}

function Destino({
  a,
  icono: Icono,
  texto,
  activo,
  contador,
}: {
  a: string;
  icono: LucideIcon;
  texto: string;
  activo: boolean;
  contador?: number;
}) {
  return (
    <Link
      to={a}
      aria-current={activo ? 'page' : undefined}
      // El destino inactivo va en `tinta-2` y no en `tinta-3`: con 12 px,
      // `tinta-3` sobre papel no llega al contraste AA (tarea 10).
      className={`relative flex flex-1 flex-col items-center justify-center gap-[2px] text-[12px] font-bold ${
        activo ? 'text-integra' : 'text-tinta-2'
      }`}
    >
      <Icono aria-hidden className="h-[22px] w-[22px]" />
      {texto}
      {contador && contador > 0 ? (
        <span
          className="absolute top-2 grid h-5 min-w-5 place-items-center rounded-full bg-aviso px-[6px] text-[12px] font-bold text-white"
          style={{ left: 'calc(50% + 6px)' }}
        >
          {contador}
          <span className="sr-only"> por revisar</span>
        </span>
      ) : null}
    </Link>
  );
}
