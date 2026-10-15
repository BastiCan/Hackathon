import { ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAgenda } from '../app/hooks';
import { COLOR_AMBITO } from '../components/ambitos';
import { NumeroNivel } from '../components/ChipNivel';
import { EtiquetaNucleo, Miniatura } from '../components/Miniatura';
import type { DiaSemana, RegistroAgenda } from '../lib/agenda';
import { fechaLarga } from '../lib/vistas';

const COLOR_PUNTO: Record<DiaSemana['puntos'][number], string> = {
  ...COLOR_AMBITO,
  sala: '#8A93A6',
};

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
    <>
      <p className="rotulo">Agenda · {v.sala.nombre}</p>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h1>{fechaLarga(v.dia)}</h1>
        {esHoy ? (
          <span className="rounded-[3px] bg-integra px-2 py-[2px] text-[12px] font-medium text-white">
            Hoy
          </span>
        ) : (
          <button
            type="button"
            onClick={() => setDia(null)}
            className="min-h-tactil text-[14px] font-medium text-integra underline"
          >
            Volver a hoy
          </button>
        )}
      </div>

      <div
        role="group"
        aria-label="Días de la semana"
        className="-mx-4 mb-3 grid grid-cols-5 gap-1 border-y border-linea bg-[#EAF0F8] px-3 py-2"
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
              className={`flex min-h-[54px] flex-col items-center justify-center rounded-[4px] text-[12px] ${
                activo ? 'bg-integra text-white' : 'text-tinta-2'
              }`}
            >
              {d.nombreCorto}
              <b className={`tabular text-[16px] ${activo ? 'text-white' : 'text-tinta'}`}>
                {d.numero}
              </b>
              <span className="flex h-[6px] gap-[2px]">
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

      {v.pendientes > 0 ? (
        <button
          type="button"
          onClick={() => navegar('/revisar')}
          className="aviso mb-2 flex min-h-tactil w-full items-center justify-between gap-2 px-3 py-2 text-left text-[14px]"
        >
          <span>
            <b>{v.pendientes} por revisar</b>
            <span className="text-tinta-2"> · confirma lo que leyó Huellita</span>
          </span>
          <span className="flex flex-none items-center font-medium text-integra">
            Revisar
            <ChevronRight aria-hidden="true" className="h-4 w-4" />
          </span>
        </button>
      ) : null}

      <p className="mb-3 text-[13px] text-tinta-2">
        Próximo: <b className="text-tinta">{v.iea.numero}º registro IEA ({v.iea.mes})</b> ·
        observados en 30 días: <b className="text-tinta">{v.partesResumen.observados}</b>
      </p>

      <section
        aria-label="Jornada"
        className="overflow-hidden rounded-tarjeta border border-linea bg-papel"
      >
        {v.periodos.map((p) => (
          <div
            key={p.inicio}
            className="grid grid-cols-[52px_1fr] border-b border-dashed border-linea last:border-b-0"
          >
            <span
              className={`tabular pl-3 font-rotulo text-[13px] text-tinta-2 ${
                p.registros.length === 0 ? 'pt-[7px]' : 'pt-[10px]'
              }`}
            >
              {p.inicio}
            </span>
            <div className={p.registros.length === 0 ? 'py-[6px] pr-3' : 'py-[9px] pr-3'}>
              {p.registros.length === 0 ? (
                <p className="text-[13px] text-tinta-3">{p.nombre}</p>
              ) : (
                <h2 className="text-[14px] font-medium">{p.nombre}</h2>
              )}
              {p.registros.length === 0 ? null : (
                <ul className="mt-[6px] flex flex-col gap-2">
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
              )}
            </div>
          </div>
        ))}
      </section>

      {conRegistros === 0 ? (
        <p className="mt-3 text-center text-[14px] text-tinta-2">
          {esHoy
            ? 'Todavía no hay registros hoy. Usa Foto, Grabar o Escribir.'
            : v.dia > v.hoy
              ? 'Ese día todavía no llega.'
              : 'Ese día no hubo registros.'}
        </p>
      ) : null}
    </>
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
      <Miniatura formato={r.formato} foto={r.foto} tamano={56} />
      <span className="min-w-0 flex-1">
        <span className="block text-[14px]">
          <b>{procesando ? 'Leyendo tu nota…' : nombres || 'Nota'}</b>
          <span className="text-tinta-2"> · {r.hora} · {autora}</span>
        </span>
        {r.texto ? (
          <span
            className="mt-[1px] block overflow-hidden text-[13px] text-tinta-2"
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
            <span className="rounded-[3px] bg-cuadricula px-[6px] py-[1px] text-[12px] text-tinta-2">
              Nota de la sala
            </span>
          ) : null}
          {pendiente && !procesando ? (
            <span className="rounded-[3px] border border-aviso-borde bg-aviso-fondo px-[6px] py-[1px] text-[12px] text-[#6B4A00]">
              Por revisar
            </span>
          ) : null}
        </span>
      </span>
    </button>
  );
}
