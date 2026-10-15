import {
  ChevronRight,
  Coffee,
  Hand,
  Moon,
  Palette,
  Puzzle,
  Sunrise,
  Trees,
  Utensils,
  type LucideIcon,
} from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAgenda } from '../app/hooks';
import { COLOR_AMBITO } from '../components/ambitos';
import { NumeroNivel } from '../components/ChipNivel';
import { PALETA } from '../components/colores';
import { Mancha, type FormaMancha } from '../components/Mancha';
import { EtiquetaNucleo, Miniatura } from '../components/Miniatura';
import type { DiaSemana, RegistroAgenda } from '../lib/agenda';
import { fechaLarga } from '../lib/vistas';

const COLOR_PUNTO: Record<DiaSemana['puntos'][number], string> = {
  ...COLOR_AMBITO,
  sala: PALETA.gris,
};

/**
 * Tono de cada período de la jornada: los colores de la paleta oficial rotan
 * en un orden fijo (azul, naranjo, verde, rosado, amarillo), nunca al azar, así
 * que un período se ve siempre del mismo color. Donde el color pleno no da
 * contraste AA con blanco (naranjo, verde y amarillo), el texto va en tinta.
 */
const TONOS = [
  { banda: 'bg-integra text-white', icono: 'text-integra', mancha: PALETA.amarillo },
  { banda: 'bg-naranjo text-tinta', icono: 'text-naranjo-texto', mancha: PALETA.rosado },
  { banda: 'bg-logo-verde text-tinta', icono: 'text-ambito-ent-texto', mancha: PALETA.azul },
  { banda: 'bg-rosado-oscuro text-white', icono: 'text-rosado-oscuro', mancha: PALETA.amarillo },
  { banda: 'bg-logo-amarillo text-tinta', icono: 'text-ambito-com-texto', mancha: PALETA.azul },
];

/** Un ícono por período de la jornada, en el orden de `JORNADA`. */
const ICONOS: LucideIcon[] = [Sunrise, Coffee, Puzzle, Trees, Utensils, Moon, Palette, Hand];

const FORMAS: FormaMancha[] = ['a', 'b', 'c'];

/**
 * Pantalla de inicio: la agenda de la tía. La semana arriba, el aviso de lo que
 * falta revisar y el día ordenado por los períodos de la jornada, con la foto
 * de cada post-it en el momento en que se tomó.
 */
export function Agenda() {
  const navegar = useNavigate();
  const [dia, setDia] = useState<string | null>(null);
  const vista = useAgenda(dia);

  if (vista.cargando && !vista.valor) {
    return (
      <p role="status" className="py-10 text-center text-tinta-2">
        Cargando tu agenda…
      </p>
    );
  }
  if (!vista.valor) {
    return (
      <p className="rounded-tarjeta border border-linea bg-papel p-4 text-tinta-2">
        {vista.error ?? 'No pudimos cargar tu agenda.'}
      </p>
    );
  }

  const v = vista.valor;
  const esHoy = v.dia === v.hoy;
  const conRegistros = v.periodos.filter((p) => p.registros.length > 0).length;

  return (
    /*
     * En escritorio la agenda se abre en dos columnas: a la izquierda la semana
     * y la jornada; a la derecha el aviso de pendientes y el resumen. En
     * celular el orden es el mismo de siempre (todas las clases son `lg:`).
     */
    <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start lg:gap-6">
      <p className="rotulo lg:col-span-2 lg:row-start-1">Agenda · {v.sala.nombre}</p>
      <div className="mb-3 flex items-center justify-between gap-2 lg:col-span-2 lg:row-start-2">
        <h1>{fechaLarga(v.dia)}</h1>
        {esHoy ? (
          <span className="rounded-chip bg-rosado-oscuro px-[10px] py-[3px] text-[13px] font-bold text-white">
            Hoy
          </span>
        ) : (
          <button
            type="button"
            onClick={() => setDia(null)}
            className="min-h-tactil text-[15px] font-bold text-integra underline"
          >
            Volver a hoy
          </button>
        )}
      </div>

      <div
        role="group"
        aria-label="Días de la semana"
        className="-mx-4 mb-3 grid grid-cols-5 gap-[6px] border-y border-linea bg-integra-claro px-3 py-[10px] lg:col-start-1 lg:row-start-3 lg:mx-0 lg:gap-3 lg:rounded-tarjeta lg:border lg:px-4 lg:py-3"
      >
        {v.semana.map((d) => {
          const activo = d.fecha === v.dia;
          return (
            <button
              key={d.fecha}
              type="button"
              aria-pressed={activo}
              aria-label={`${d.nombreCorto} ${d.numero}, ${d.puntos.length} registros`}
              onClick={() => setDia(d.fecha === v.hoy ? null : d.fecha)}
              className={`relative flex min-h-[56px] flex-col items-center justify-center overflow-hidden rounded-chip text-[13px] lg:min-h-[76px] lg:text-[14px] ${
                activo
                  ? 'bg-integra text-white shadow-tarjeta'
                  : 'border border-linea bg-papel text-tinta-2'
              }`}
            >
              {activo ? (
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
              <span className="relative">{d.nombreCorto}</span>
              <b className={`tabular relative text-[17px] ${activo ? 'text-white' : 'text-tinta'}`}>
                {d.numero}
              </b>
              <span className="relative flex h-[6px] gap-[2px]">
                {d.puntos.map((p, i) => (
                  <i
                    key={i}
                    className="block h-[5px] w-[5px] rounded-full"
                    style={{ background: activo ? '#FFFFFF' : COLOR_PUNTO[p] }}
                  />
                ))}
              </span>
            </button>
          );
        })}
      </div>

      <div className="lg:col-start-2 lg:row-start-3 lg:row-span-2 lg:sticky lg:top-6 lg:flex lg:flex-col lg:gap-2">
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

        <p className="mb-3 text-[14px] text-tinta-2 lg:mb-0 lg:rounded-tarjeta lg:border lg:border-linea lg:bg-papel lg:p-3 lg:shadow-tarjeta">
          Próximo: <b className="text-tinta">{v.iea.numero}º registro IEA ({v.iea.mes})</b> ·
          observados en 30 días: <b className="text-tinta">{v.partesResumen.observados}</b>
        </p>
      </div>

      <section aria-label="Jornada" className="flex flex-col gap-2 lg:col-start-1 lg:row-start-4">
        {v.periodos.map((p, i) => {
          const conNotas = p.registros.length > 0;
          const tono = TONOS[i % TONOS.length];
          const Icono = ICONOS[i % ICONOS.length];
          return (
            <div
              key={p.inicio}
              className={`relative overflow-hidden rounded-tarjeta border border-linea bg-papel ${
                conNotas ? 'shadow-tarjeta' : ''
              }`}
            >
              <Mancha
                color={tono.mancha}
                forma={FORMAS[i % FORMAS.length]}
                opacidad={conNotas ? 0.16 : 0.06}
                className={
                  conNotas ? '-bottom-7 -right-6 h-28 w-28' : '-bottom-5 -right-4 h-16 w-16'
                }
              />
              <div
                className={`relative grid grid-cols-[52px_1fr] items-center gap-1 px-3 ${
                  conNotas ? `${tono.banda} py-2` : 'py-[7px]'
                }`}
              >
                <span
                  className={`tabular text-[13px] ${conNotas ? 'font-bold' : 'text-tinta-2'}`}
                >
                  {p.inicio}
                </span>
                <span className="flex items-center gap-2">
                  <span
                    className={`grid h-7 w-7 flex-none place-items-center rounded-full ${
                      conNotas ? 'bg-papel' : 'bg-fondo'
                    }`}
                  >
                    <Icono
                      aria-hidden="true"
                      className={`h-4 w-4 ${conNotas ? tono.icono : 'text-tinta-3'}`}
                    />
                  </span>
                  {conNotas ? (
                    <h2 className="text-[16px]">{p.nombre}</h2>
                  ) : (
                    <p className="text-[14px] text-tinta-3">{p.nombre}</p>
                  )}
                </span>
              </div>
              {conNotas ? (
                <ul className="relative flex flex-col gap-2 px-3 py-[10px]">
                  {p.registros.map((r) => (
                    <li key={r.evidenciaId}>
                      <Registro
                        registro={r}
                        autora={v.nombreAutora[r.autorId] ?? 'Tía'}
                        onAbrir={(ninoId, pendiente) =>
                          navegar(pendiente || !ninoId ? '/revisar' : `/nino/${ninoId}`)
                        }
                      />
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          );
        })}
      </section>

      {conRegistros === 0 ? (
        <p className="mt-3 text-center text-[15px] text-tinta-2 lg:col-start-1 lg:row-start-5">
          {esHoy
            ? 'Todavía no hay registros hoy. Usa Foto, Grabar o Escribir.'
            : v.dia > v.hoy
              ? 'Ese día todavía no llega.'
              : 'Ese día no hubo registros.'}
        </p>
      ) : null}
    </div>
  );
}

function Registro({
  registro: r,
  autora,
  onAbrir,
}: {
  registro: RegistroAgenda;
  autora: string;
  onAbrir: (ninoId: string | undefined, pendiente: boolean) => void;
}) {
  const primera = r.entradas[0];
  const pendiente = r.estado !== 'lista' || r.entradas.some((e) => e.pendiente);
  const procesando = r.estado === 'procesando';
  const nombres = r.entradas.map((e) => e.nombre).join(', ');

  return (
    <button
      type="button"
      onClick={() => onAbrir(primera?.ninoId, pendiente)}
      className="flex min-h-tactil w-full items-start gap-[10px] text-left"
    >
      <Miniatura formato={r.formato} foto={r.foto} tamano={56} conMancha />
      <span className="min-w-0 flex-1">
        <span className="block text-[15px]">
          <b>{procesando ? 'Leyendo tu nota…' : nombres || 'Nota'}</b>
          <span className="text-tinta-2"> · {r.hora} · {autora}</span>
        </span>
        {r.texto ? (
          <span
            className="mt-[1px] block overflow-hidden text-[14px] text-tinta-2"
            style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}
          >
            {r.texto}
          </span>
        ) : null}
        <span className="mt-1 flex flex-wrap items-center gap-1">
          {primera?.nucleo ? <EtiquetaNucleo nucleo={primera.nucleo} /> : null}
          {primera?.nivel && primera.nucleo ? (
            <NumeroNivel nivel={primera.nivel} nucleo={primera.nucleo} tamano={20} />
          ) : null}
          {primera?.tipo === 'nota_sala' ? (
            <span className="rounded-chip bg-cuadricula px-[6px] py-[1px] text-[13px] text-tinta-2">
              Nota de la sala
            </span>
          ) : null}
          {pendiente && !procesando ? (
            <span className="rounded-chip border border-naranjo bg-naranjo-suave px-[6px] py-[1px] text-[13px] font-bold text-naranjo-texto">
              Por revisar
            </span>
          ) : null}
        </span>
      </span>
    </button>
  );
}
