import { ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAviso } from '../app/aviso';
import { BotonesCaptura } from '../app/Dock';
import { useInicio } from '../app/hooks';
import { useServicios } from '../app/servicios';
import { PALETA } from '../components/colores';
import { Mancha } from '../components/Mancha';
import { etiquetaDia, type DiaSemana, type EstadoRegistro } from '../lib/inicio';
import type { Sala } from '../lib/tipos';
import { fechaLarga } from '../lib/vistas';

/**
 * Pantalla de inicio (reemplaza a la agenda): arriba la semana con lo que se
 * registró cada día y el aviso de lo que falta revisar; abajo, al alcance del
 * pulgar, la sala del registro y los 4 botones para registrar: subir foto,
 * grabar audio, escribir y subir audio.
 */
export function Inicio() {
  const navegar = useNavigate();
  const { datos } = useServicios();
  const aviso = useAviso();
  const vista = useInicio();

  if (vista.cargando && !vista.valor) {
    return (
      <p role="status" className="py-10 text-center text-tinta-2">
        Cargando…
      </p>
    );
  }
  if (!vista.valor) {
    return (
      <p className="rounded-tarjeta border border-linea bg-papel p-4 text-tinta-2">
        {vista.error ?? 'No pudimos cargar el inicio.'}
      </p>
    );
  }

  const v = vista.valor;

  const cambiarSala = (id: string) => {
    if (id === v.sala.id) return;
    const nombre = v.salas.find((s) => s.id === id)?.nombre ?? 'la sala elegida';
    void datos.cambiarSala(id).then(
      () => aviso(`Ahora registras en ${nombre}`),
      () => aviso('No pudimos cambiar de sala. Inténtalo de nuevo.'),
    );
  };

  return (
    /*
     * En escritorio se abre en dos columnas: a la izquierda la semana y los
     * botones para registrar; a la derecha el aviso de pendientes y el
     * resumen. En celular va todo en una columna (todas las clases son `lg:`).
     */
    <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start lg:gap-x-6">
      <p className="rotulo lg:col-span-2 lg:row-start-1">Inicio · {v.sala.nombre}</p>
      <div className="mb-3 flex items-center justify-between gap-2 lg:col-span-2 lg:row-start-2">
        <h1>{fechaLarga(v.hoy)}</h1>
        <span className="rounded-chip bg-rosado-oscuro px-[10px] py-[3px] text-[13px] font-bold text-white">
          Hoy
        </span>
      </div>

      <Semana dias={v.semana} />

      <div className="lg:col-start-2 lg:row-span-2 lg:row-start-3 lg:sticky lg:top-6 lg:flex lg:flex-col lg:gap-2">
        {v.pendientes > 0 ? (
          <button
            type="button"
            onClick={() => navegar('/revisar')}
            className="aviso mb-2 flex min-h-tactil w-full items-center justify-between gap-2 px-3 py-2 text-left text-[15px] lg:mb-0"
          >
            <span>
              <b>{v.pendientes} por revisar</b>
              <span className="text-naranjo-texto"> · confirma lo que leyó Huellita</span>
            </span>
            <span className="flex flex-none items-center font-bold text-integra">
              Revisar
              <ChevronRight aria-hidden="true" className="h-4 w-4" />
            </span>
          </button>
        ) : null}

        <p className="mb-4 text-[14px] text-tinta-2 lg:mb-0 lg:rounded-tarjeta lg:border lg:border-linea lg:bg-papel lg:p-3 lg:shadow-tarjeta">
          Próximo: <b className="text-tinta">{v.iea.numero}º registro IEA ({v.iea.mes})</b> ·
          observados en 30 días: <b className="text-tinta">{v.partesResumen.observados}</b>
        </p>
      </div>

      <section aria-labelledby="titulo-registrar" className="lg:col-start-1 lg:row-start-4">
        <SelectorSala salas={v.salas} actual={v.sala} onCambiar={cambiarSala} />
        <BotonesCaptura disposicion="grande" />
        <p className="mt-3 text-[14px] text-tinta-2">
          Huellita lee tu nota y la deja en Revisar para que la confirmes.
        </p>
      </section>
    </div>
  );
}

/** Lunes a viernes: hoy en azul y un punto por cada registro del día. */
function Semana({ dias }: { dias: DiaSemana[] }) {
  return (
    <div className="-mx-4 mb-3 border-y border-linea bg-integra-claro px-3 py-[10px] lg:col-start-1 lg:row-start-3 lg:mx-0 lg:rounded-tarjeta lg:border lg:px-4 lg:py-3">
      <ul aria-label="Días de la semana" className="grid grid-cols-5 gap-[6px] lg:gap-3">
        {dias.map((d) => (
          <Dia key={d.fecha} dia={d} />
        ))}
      </ul>
      <p className="mt-2 text-center text-[13px] text-tinta-2">
        Cada punto es un registro; en naranjo, los que faltan por revisar.
      </p>
    </div>
  );
}

function colorPunto(estado: EstadoRegistro, esHoy: boolean): string {
  if (estado === 'pendiente') return PALETA.naranjo;
  return esHoy ? '#FFFFFF' : PALETA.azul;
}

function Dia({ dia: d }: { dia: DiaSemana }) {
  return (
    <li
      className={`relative flex min-h-[56px] flex-col items-center justify-center overflow-hidden rounded-chip text-[13px] lg:min-h-[76px] lg:text-[14px] ${
        d.esHoy
          ? 'bg-integra text-white shadow-tarjeta'
          : `border bg-papel text-tinta-2 ${d.esFuturo ? 'border-dashed border-linea' : 'border-linea'}`
      }`}
    >
      {d.esHoy ? (
        <>
          <Mancha
            color={PALETA.amarillo}
            forma="b"
            opacidad={0.35}
            className="-right-3 -top-4 h-10 w-10"
          />
          <Mancha
            color={PALETA.rosado}
            forma="c"
            opacidad={0.35}
            className="-bottom-4 -left-3 h-9 w-9"
          />
        </>
      ) : null}
      <span className="sr-only">{etiquetaDia(d)}</span>
      <span aria-hidden="true" className="relative">
        {d.nombreCorto}
      </span>
      <b
        aria-hidden="true"
        className={`tabular relative text-[17px] ${d.esHoy ? 'text-white' : 'text-tinta'}`}
      >
        {d.numero}
      </b>
      <span aria-hidden="true" className="relative flex h-[7px] items-center gap-[2px]">
        {d.puntos.map((p, i) => (
          <i
            key={i}
            className="block h-[5px] w-[5px] rounded-full"
            style={{
              background: colorPunto(p, d.esHoy),
              // En el azul de hoy, el naranjo lleva un borde blanco para verse.
              boxShadow: d.esHoy && p === 'pendiente' ? '0 0 0 1px #FFFFFF' : undefined,
            }}
          />
        ))}
      </span>
    </li>
  );
}

/**
 * Título del bloque y sala donde queda lo que se registre: "Registrar en
 * [Medio Menor A ▾]", en una sola línea para que los botones queden a la vista
 * en celulares chicos. Cambiar la sala cambia la sala de trabajo (la misma de
 * Sala y Revisar), así la tía revisa después lo que registró. Solo aparecen
 * las salas de la usuaria (privacidad.md 6).
 */
function SelectorSala({
  salas,
  actual,
  onCambiar,
}: {
  salas: Sala[];
  actual: Sala;
  onCambiar: (id: string) => void;
}) {
  if (salas.length <= 1) {
    return (
      <h2 id="titulo-registrar" className="mb-3">
        Registrar en {actual.nombre}
      </h2>
    );
  }
  return (
    <div className="mb-3">
      <div className="flex items-center gap-3">
        <h2 id="titulo-registrar" className="flex-none">
          <label htmlFor="sala-registro">Registrar en</label>
        </h2>
        <select
          id="sala-registro"
          value={actual.id}
          onChange={(e) => onCambiar(e.target.value)}
          aria-describedby="sala-registro-ayuda"
          className="min-h-tactil min-w-0 flex-1 rounded-campo border border-linea bg-papel px-[10px] py-2 text-base text-tinta lg:max-w-[320px]"
        >
          {salas.map((s) => (
            <option key={s.id} value={s.id}>
              {s.nombre}
            </option>
          ))}
        </select>
      </div>
      <p id="sala-registro-ayuda" className="mt-1 text-[13px] text-tinta-2">
        Sala y Revisar también muestran esta sala.
      </p>
    </div>
  );
}
