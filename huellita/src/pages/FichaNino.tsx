import { ChevronLeft, Eye, Flag } from 'lucide-react';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useFicha } from '../app/hooks';
import { Avatar } from '../components/Avatar';
import { Escalera } from '../components/Escalera';
import { HojaNucleo } from '../components/HojaNucleo';
import type { NucleoId } from '../lib/tipos';
import type { NucleoVista } from '../lib/vistas';

/**
 * Pantalla 3: ficha del niño/a. Resumen, qué observar esta semana, cómo va por
 * núcleo (escalera de 8 escalones) y los registros validados.
 */
export function FichaNino() {
  const { id } = useParams();
  const navegar = useNavigate();
  const vista = useFicha(id);
  const [verTodos, setVerTodos] = useState(false);
  const [detalle, setDetalle] = useState<NucleoVista | null>(null);
  const [filtro, setFiltro] = useState<NucleoId | 'todos'>('todos');

  if (vista.cargando) {
    return (
      <p role="status" className="py-10 text-center text-tinta-2">
        Cargando la ficha…
      </p>
    );
  }
  if (!vista.valor) {
    return (
      <>
        <Volver onClick={() => navegar('/')} />
        <p className="rounded-tarjeta border border-linea bg-papel p-4 text-tinta-2">
          {vista.error ?? 'No encontramos a ese niño o niña.'}
        </p>
      </>
    );
  }

  const f = vista.valor;
  const nucleosVisibles = verTodos ? f.nucleos : f.nucleos.slice(0, 4);
  const historial =
    filtro === 'todos' ? f.historial : f.historial.filter((r) => r.nucleo === filtro);

  return (
    <>
      <Volver onClick={() => navegar('/')} />

      <header className="mb-[14px] flex items-center gap-[14px]">
        <Avatar iniciales={f.iniciales} frescura={f.frescura} tamano={64} />
        <div>
          <h1>{f.nino.nombre}</h1>
          <p className="text-[14px] text-tinta-2">
            {f.edad.anios} años {f.edad.meses} meses · {f.sala.nombre}
          </p>
        </div>
      </header>

      <section className="mb-3 rounded-tarjeta border border-linea bg-papel p-[14px]">
        <p className="text-[15px] text-tinta-2">{f.resumen}</p>
      </section>

      {f.conductasObservar.length > 0 ? (
        <section
          className="mb-3 rounded-tarjeta bg-postit-lima p-[14px]"
          style={{ transform: 'rotate(0.4deg)' }}
        >
          <h2 className="mb-[6px] flex items-center gap-[6px] text-[16px]">
            <Eye aria-hidden="true" className="h-[22px] w-[22px]" />
            Para observar esta semana
          </h2>
          <ul className="list-disc pl-5">
            {f.conductasObservar.map((conducta) => (
              <li key={conducta} className="font-mano text-[19px] leading-[1.3]">
                {conducta}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section
        aria-label="Nivel por núcleo"
        className="mb-3 rounded-tarjeta border border-linea bg-papel p-[14px]"
      >
        <h2 className="mb-1">Cómo va</h2>
        {nucleosVisibles.map((n) => (
          <button
            key={n.nucleo}
            type="button"
            onClick={() => setDetalle(n)}
            className="grid w-full min-h-tactil grid-cols-[1fr_auto] items-end gap-x-[10px] gap-y-1 border-b border-linea py-[10px] text-left last:border-b-0"
          >
            <span className="flex items-center gap-[6px] text-[15px] font-bold">
              {n.nombre}
              {n.revisarAvance ? (
                <Flag aria-hidden="true" className="h-[18px] w-[18px] flex-none text-ambar" />
              ) : null}
            </span>
            <Escalera nivel={n.nivel} />
            <span className="col-start-1 text-[13px] text-tinta-2">
              {n.nivel ? `Nivel ${n.nivel} · ${n.nombreNivel}` : 'Sin registros aún'}
              {n.revisarAvance ? ' · revisar avance' : ''}
            </span>
          </button>
        ))}
        {!verTodos && f.nucleos.length > 4 ? (
          <button
            type="button"
            onClick={() => setVerTodos(true)}
            className="mt-2 min-h-tactil font-bold text-integra"
          >
            Ver los {f.nucleos.length}
          </button>
        ) : null}
      </section>

      <section className="mb-3 rounded-tarjeta border border-linea bg-papel p-[14px]">
        <div className="mb-[10px] flex items-center justify-between gap-2">
          <h2>Registros</h2>
          <label className="min-w-0 flex-none text-[13px] text-tinta-2">
            <span className="sr-only">Filtrar por núcleo</span>
            <select
              value={filtro}
              onChange={(e) => setFiltro(e.target.value as NucleoId | 'todos')}
              className="min-h-tactil max-w-[180px] truncate rounded-[12px] border-[1.5px] border-linea bg-papel px-2 text-[14px] text-tinta"
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
          <p className="text-[15px] text-tinta-2">
            Todavía no hay registros guardados con este filtro.
          </p>
        ) : (
          <ol className="linea-tiempo">
            {historial.map((r) => (
              <li key={r.id} className="pb-[14px]" style={{ ['--punto' as string]: r.color }}>
                <p className="text-[13px] text-tinta-2">
                  {r.fechaCorta} · {r.nombreNucleo} · Nivel {r.nivel} · {r.autora}
                </p>
                <q className="font-mano text-[17px]">{r.cita}</q>
              </li>
            ))}
          </ol>
        )}
      </section>

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
      className="-ml-[6px] mb-1 inline-flex min-h-tactil items-center gap-1 px-[6px] font-bold text-tinta-2"
    >
      <ChevronLeft aria-hidden="true" className="h-[22px] w-[22px]" />
      Mi sala
    </button>
  );
}
