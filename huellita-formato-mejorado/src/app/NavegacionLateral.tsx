import { Link, useLocation } from 'react-router-dom';
import { BotonesCaptura, etiquetaRegistrar } from './Dock';
import { destinos, type Destino as DestinoNav } from './destinos';
import { useOpciones } from './opciones';

/**
 * Barra lateral del computador (desde 1024 px): arriba el bloque "Registrar"
 * con los mismos 3 botones de captura y debajo los mismos destinos de la barra
 * inferior. En el celular no existe: la reemplaza `BarraInferior` + `Dock`.
 */
export function NavegacionLateral({
  pendientes,
  esDirectora,
  conDock,
  nombreNino,
}: {
  pendientes: number;
  esDirectora: boolean;
  /** La captura solo acompaña al inicio y a la ficha, igual que en el celular. */
  conDock: boolean;
  nombreNino?: string;
}) {
  const { pathname } = useLocation();
  const { agenda } = useOpciones();

  return (
    <div className="sticky top-4 hidden w-[232px] flex-none flex-col gap-5 self-start py-6 pl-4 pr-2 lg:flex">
      {conDock ? (
        <div
          role="group"
          aria-label={etiquetaRegistrar(nombreNino)}
          className="rounded-tarjeta border border-linea bg-papel p-3 shadow-tarjeta"
        >
          <p className="rotulo mb-2">{etiquetaRegistrar(nombreNino)}</p>
          <BotonesCaptura columna />
        </div>
      ) : null}
      <nav aria-label="Secciones" className="flex flex-col gap-1">
        {destinos(esDirectora, agenda).map((d) => (
          <Destino
            key={d.a}
            destino={d}
            activo={d.esActivo(pathname)}
            contador={d.conContador ? pendientes : undefined}
          />
        ))}
      </nav>
    </div>
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
      className={`flex min-h-tactil items-center gap-3 rounded-boton px-3 py-2 text-[16px] font-bold ${
        activo ? 'bg-integra-claro text-integra' : 'text-tinta-2'
      }`}
    >
      <Icono aria-hidden="true" className="h-[22px] w-[22px] flex-none" />
      <span className="min-w-0 flex-1 truncate">{destino.texto}</span>
      {/* Manchita rosada del manual: marca el destino en el que estoy. */}
      {activo ? (
        <span aria-hidden="true" className="h-[6px] w-[6px] flex-none rounded-full bg-rosado" />
      ) : null}
      {contador && contador > 0 ? (
        <span className="grid h-5 min-w-5 flex-none place-items-center rounded-full bg-aviso-globo px-[6px] text-[13px] font-bold text-white">
          {contador}
          <span className="sr-only"> por revisar</span>
        </span>
      ) : null}
    </Link>
  );
}
