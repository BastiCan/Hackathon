import {
  Building2,
  CalendarDays,
  ClipboardCheck,
  Table2,
  type LucideIcon,
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

/**
 * Barra inferior fija: Agenda · Sala · Revisar (con el contador de pendientes)
 * · Directora (solo para el rol directora).
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

  return (
    <nav
      aria-label="Principal"
      className={`fixed bottom-0 left-1/2 z-10 flex h-[64px] w-full -translate-x-1/2 border-t border-linea bg-papel ${ancho}`}
    >
      <Destino a="/" icono={CalendarDays} texto="Agenda" activo={pathname === '/'} />
      <Destino
        a="/sala"
        icono={Table2}
        texto="Sala"
        activo={pathname === '/sala' || pathname.startsWith('/nino/')}
      />
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
      className={`relative flex flex-1 flex-col items-center justify-center gap-[2px] text-[12px] font-medium ${
        activo ? 'text-integra' : 'text-tinta-2'
      }`}
    >
      {activo ? (
        <span aria-hidden="true" className="absolute left-4 right-4 top-0 h-[3px] bg-integra" />
      ) : null}
      <Icono aria-hidden className="h-[22px] w-[22px]" />
      {texto}
      {contador && contador > 0 ? (
        <span
          className="absolute top-[6px] grid h-5 min-w-5 place-items-center rounded-full bg-aviso-globo px-[6px] text-[12px] font-bold text-white"
          style={{ left: 'calc(50% + 6px)' }}
        >
          {contador}
          <span className="sr-only"> por revisar</span>
        </span>
      ) : null}
    </Link>
  );
}
