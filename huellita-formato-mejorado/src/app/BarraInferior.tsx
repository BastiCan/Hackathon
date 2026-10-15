import { Link, useLocation } from 'react-router-dom';
import { destinos, type Destino as DestinoNav } from './destinos';
import { useOpciones } from './opciones';

/**
 * Barra inferior fija del celular: Agenda · Sala · Revisar (con el contador de
 * pendientes) · Directora (solo para el rol directora).
 *
 * Desde 1024 px (`lg:`) desaparece: en el computador los mismos destinos viven
 * en la barra lateral (`NavegacionLateral`).
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
  const { agenda } = useOpciones();

  return (
    <nav
      aria-label="Principal"
      className={`barra-segura fixed bottom-0 left-1/2 z-10 box-content flex h-[64px] w-full -translate-x-1/2 border-t border-linea bg-papel lg:hidden ${ancho}`}
    >
      {destinos(esDirectora, agenda).map((d) => (
        <Destino
          key={d.a}
          destino={d}
          activo={d.esActivo(pathname)}
          contador={d.conContador ? pendientes : undefined}
        />
      ))}
    </nav>
  );
}

function Destino({
  destino,
  activo,
  contador,
}: {
  destino: DestinoNav;
  activo: boolean;
  contador?: number;
}) {
  const Icono = destino.icono;
  return (
    <Link
      to={destino.a}
      aria-current={activo ? 'page' : undefined}
      className={`relative flex flex-1 flex-col items-center justify-center gap-[2px] text-[13px] font-bold ${
        activo ? 'text-integra' : 'text-tinta-2'
      }`}
    >
      {activo ? (
        <>
          <span
            aria-hidden="true"
            className="absolute left-4 right-4 top-0 h-[3px] rounded-full bg-integra"
          />
          {/* Manchita rosada del manual: marca el destino en el que estoy. */}
          <span
            aria-hidden="true"
            className="absolute bottom-[7px] h-[5px] w-[5px] rounded-full bg-rosado"
          />
        </>
      ) : null}
      <Icono aria-hidden className="h-[22px] w-[22px]" />
      {destino.texto}
      {contador && contador > 0 ? (
        <span
          className="absolute top-[6px] grid h-5 min-w-5 place-items-center rounded-full bg-aviso-globo px-[6px] text-[13px] font-bold text-white"
          style={{ left: 'calc(50% + 6px)' }}
        >
          {contador}
          <span className="sr-only"> por revisar</span>
        </span>
      ) : null}
    </Link>
  );
}
