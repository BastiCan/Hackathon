import { ChevronLeft, Eye, Flag } from 'lucide-react';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useFicha } from '../app/hooks';
import {
  ambitoDe,
  COLOR_AMBITO,
  NOMBRE_AMBITO,
  TEXTO_AMBITO,
  type AmbitoId,
} from '../components/ambitos';
import { Avatar } from '../components/Avatar';
import { NumeroNivel } from '../components/ChipNivel';
import { HojaNucleo } from '../components/HojaNucleo';
import { Mancha, type FormaMancha } from '../components/Mancha';
import { Miniatura } from '../components/Miniatura';
import type { NucleoId } from '../lib/tipos';
import type { NucleoVista } from '../lib/vistas';

const AMBITOS: AmbitoId[] = ['dps', 'com', 'ent'];

/** Fondo suave de cada ámbito para su tarjeta (texto oscuro del mismo color). */
const FONDO_AMBITO: Record<AmbitoId, string> = {
  dps: 'bg-ambito-dps',
  com: 'bg-ambito-com',
  ent: 'bg-ambito-ent',
};

/** Una mancha distinta por ámbito, siempre la misma. */
const FORMA_AMBITO: Record<AmbitoId, FormaMancha> = {
  dps: 'a',
  com: 'b',
  ent: 'c',
};

/**
 * Ficha del niño/a, como una página de su agenda: qué acompañar esta semana,
 * cómo va por ámbito (con los colores del logo de Integra) y sus registros con
 * la foto de cada post-it.
 */
export function FichaNino() {
  const { id } = useParams();
  const navegar = useNavigate();
  const vista = useFicha(id);
  const [detalle, setDetalle] = useState<NucleoVista | null>(null);
  const [filtro, setFiltro] = useState<NucleoId | 'todos'>('todos');

  if (vista.cargando && !vista.valor) {
    return (
      <p role="status" className="py-10 text-center text-tinta-2">
        Cargando la ficha…
      </p>
    );
  }
  if (!vista.valor) {
    return (
      <>
        <Volver onClick={() => navegar('/sala')} />
        <p className="rounded-tarjeta border border-linea bg-papel p-4 text-tinta-2">
          {vista.error ?? 'No encontramos a ese niño o niña.'}
        </p>
      </>
    );
  }

  const f = vista.valor;
  const historial =
    filtro === 'todos' ? f.historial : f.historial.filter((r) => r.nucleo === filtro);
  const conFoto = f.historial.filter((r) => r.foto).slice(0, 6);
  const tira = conFoto.length > 0 ? conFoto : f.historial.slice(0, 3);

  return (
    <>
      <Volver onClick={() => navegar('/sala')} />

      <header className="mb-3 flex items-center gap-3">
        <Avatar iniciales={f.iniciales} frescura={f.frescura} tamano={48} />
        <div className="min-w-0">
          <h1>
            {f.nino.nombre} {f.nino.apellidoInicial}
          </h1>
          <p className="text-[14px] text-tinta-2">
            {f.edad.anios} años {f.edad.meses} meses · {f.sala.nombre}
            {f.historial[0] ? ` · último registro ${f.historial[0].fechaCorta}` : ''}
          </p>
        </div>
      </header>

      {/* Escritorio: a la izquierda el resumen y cómo va; a la derecha sus
          fotos y los registros. En celular es la misma fila de siempre. */}
      <div className="lg:grid lg:grid-cols-2 lg:items-start lg:gap-6">
        <div className="min-w-0">
          <section className="aviso mb-3 px-3 py-[10px]">
        <p className="text-[15px]">{f.resumen}</p>
        {f.conductasObservar.length > 0 ? (
          <>
            <h2 className="mt-2 flex items-center gap-[6px] text-[15px]">
              <Eye aria-hidden="true" className="h-[18px] w-[18px]" />
              Para observar esta semana
            </h2>
            <ul className="mt-1 list-disc pl-5 text-[15px] text-tinta">
              {f.conductasObservar.map((conducta) => (
                <li key={conducta}>{conducta}</li>
              ))}
            </ul>
          </>
        ) : null}
      </section>

      <section
        aria-label="Nivel por núcleo"
        className="mb-3 rounded-tarjeta border border-linea bg-papel px-3 py-[10px] shadow-tarjeta"
      >
        <p className="rotulo mb-1">Cómo va · por ámbito</p>
        {AMBITOS.map((a) => {
          const nucleos = f.nucleos.filter((n) => ambitoDe(n.nucleo) === a);
          if (nucleos.length === 0) return null;
          return (
            <div
              key={a}
              className={`relative mt-2 overflow-hidden rounded-chip px-[10px] py-2 ${FONDO_AMBITO[a]}`}
            >
              <Mancha
                color={COLOR_AMBITO[a]}
                forma={FORMA_AMBITO[a]}
                opacidad={0.22}
                className="-right-5 -top-6 h-20 w-20"
              />
              <h2
                className="relative mb-1 flex items-center gap-2 text-[13px] font-bold"
                style={{ color: TEXTO_AMBITO[a] }}
              >
                <i
                  className="block h-[10px] w-[10px] rounded-full"
                  style={{ background: COLOR_AMBITO[a] }}
                />
                {NOMBRE_AMBITO[a]}
              </h2>
              {nucleos.map((n) => (
                <button
                  key={n.nucleo}
                  type="button"
                  onClick={() => setDetalle(n)}
                  className="relative flex min-h-tactil w-full items-center justify-between gap-2 border-b border-papel py-1 text-left last:border-b-0"
                >
                  <span className="min-w-0">
                    <span className="flex items-center gap-[6px] text-[15px]">
                      {n.nombre}
                      {n.revisarAvance ? (
                        <Flag
                          aria-hidden="true"
                          className="h-[15px] w-[15px] flex-none text-naranjo-texto"
                        />
                      ) : null}
                    </span>
                    <span className="block text-[13px] text-tinta-2">
                      {n.nivel ? n.nombreNivel : 'Sin registros aún'}
                      {n.revisarAvance ? ` · revisar avance (esperado ${f.nivelEsperadoEdad})` : ''}
                    </span>
                  </span>
                  {n.nivel ? (
                    <NumeroNivel
                      nivel={n.nivel}
                      nucleo={n.nucleo}
                      revisar={n.revisarAvance}
                      tamano={28}
                    />
                  ) : (
                    <span className="text-tinta-3">–</span>
                  )}
                </button>
              ))}
            </div>
          );
        })}
      </section>
        </div>

        <div className="min-w-0">
      {tira.length > 0 ? (
        <section className="mb-3 rounded-tarjeta border border-linea bg-papel px-3 py-[10px] shadow-tarjeta">
          <p className="rotulo mb-2">Su agenda · últimos registros</p>
          <ul className="sin-barra -mx-3 flex gap-3 overflow-x-auto px-3">
            {tira.map((r) => (
              <li key={r.id} className="w-[84px] flex-none">
                <Miniatura formato={r.formato ?? 'texto'} foto={r.foto} tamano={84} conMancha />
                <p className="mt-1 text-[12px] text-tinta-2">
                  {r.fechaCorta} · {r.nucleo} {r.nivel}
                </p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="mb-3 rounded-tarjeta border border-linea bg-papel px-3 py-[10px] shadow-tarjeta">
        <div className="mb-2 flex items-center justify-between gap-2">
          <h2>Registros</h2>
          <label className="min-w-0 flex-none text-[14px] text-tinta-2">
            <span className="sr-only">Filtrar por núcleo</span>
            <select
              value={filtro}
              onChange={(e) => setFiltro(e.target.value as NucleoId | 'todos')}
              className="min-h-tactil max-w-[180px] truncate rounded-campo border border-linea bg-papel px-2 text-[15px] text-tinta"
            >
              <option value="todos">Todos los núcleos</option>
              {f.nucleos.map((n) => (
                <option key={n.nucleo} value={n.nucleo}>
                  {n.nombre}
                </option>
              ))}
            </select>
          </label>
        </div>

        {historial.length === 0 ? (
          <p className="text-[15px] text-tinta-2">Todavía no hay registros guardados con este filtro.</p>
        ) : (
          <ol className="linea-tiempo">
            {historial.map((r) => (
              <li
                key={r.id}
                className="pb-3"
                style={{ ['--punto' as string]: COLOR_AMBITO[ambitoDe(r.nucleo)] }}
              >
                <p className="text-[13px] text-tinta-2">
                  {r.fechaCorta} · {r.nombreNucleo} · Nivel {r.nivel} · {r.autora}
                </p>
                <q className="text-[15px] text-tinta">“{r.cita}”</q>
              </li>
            ))}
          </ol>
        )}
      </section>
        </div>
      </div>

      {detalle ? (
        <HojaNucleo
          nucleo={detalle.nucleo}
          nivel={detalle.nivel ?? f.nivelEsperadoEdad}
          conEvidencia={detalle.nivel !== null}
          onCerrar={() => setDetalle(null)}
        />
      ) : null}
    </>
  );
}

function Volver({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="-ml-[6px] mb-1 inline-flex min-h-tactil items-center gap-1 px-[6px] font-bold text-integra"
    >
      <ChevronLeft aria-hidden="true" className="h-[22px] w-[22px]" />
      Sala
    </button>
  );
}
