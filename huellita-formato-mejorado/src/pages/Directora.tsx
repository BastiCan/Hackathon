import { ChevronRight, Flag } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useDirectora } from '../app/hooks';
import { PALETA } from '../components/colores';
import { Mancha, type FormaMancha } from '../components/Mancha';
import type { TarjetaSalaVista } from '../lib/vistas';

/**
 * Pantalla 4: Directora (tarea 14, solo visual). Una tarjeta por sala con
 * cuántos niños/as tiene, cuántos se observaron en los últimos 30 días,
 * cuántos están en "revisar avance" y el núcleo menos registrado.
 *
 * Todo se calcula con `lib/evaluacion.ts` sobre los datos de prueba; al tocar
 * una sala se abre su vista Mi sala en modo lectura.
 */
export function Directora() {
  const navegar = useNavigate();
  const vista = useDirectora();

  if (vista.cargando) {
    return (
      <p role="status" className="py-10 text-center text-tinta-2">
        Cargando las salas…
      </p>
    );
  }
  if (!vista.valor) {
    return (
      <p className="rounded-tarjeta border border-linea bg-papel p-4 text-tinta-2">
        {vista.error ?? 'No pudimos cargar las salas.'}
      </p>
    );
  }

  const { jardin, salas } = vista.valor;

  return (
    <>
      <p className="rotulo">{jardin.nombre}</p>
      <h1 className="mb-3">Salas del jardín</h1>

      <section aria-label="Salas del jardín" className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {salas.map((s, i) => (
          <TarjetaSala
            key={s.id}
            sala={s}
            indice={i}
            onAbrir={() => navegar(`/directora/sala/${s.id}`)}
          />
        ))}
      </section>

      <p className="mt-4 rounded-tarjeta border border-dashed border-linea bg-papel p-[14px] text-[15px] text-tinta-2">
        "Observados" quiere decir que tienen un registro guardado en los últimos 30 días. No mide
        cómo le va al niño o niña.
      </p>
    </>
  );
}

/** Un color fijo de la paleta por sala, en el mismo orden de la lista. */
const COLORES_SALA = [PALETA.azul, PALETA.verde, PALETA.rosado, PALETA.naranjo, PALETA.amarillo];
const FORMAS_SALA: FormaMancha[] = ['a', 'b', 'c'];

function TarjetaSala({
  sala,
  indice,
  onAbrir,
}: {
  sala: TarjetaSalaVista;
  indice: number;
  onAbrir: () => void;
}) {
  const etiqueta = [
    sala.nombre,
    `${sala.total} niños y niñas`,
    `${sala.observados30} observados en 30 días`,
    sala.revisarAvance > 0 ? `${sala.revisarAvance} por revisar avance` : 'ninguno por revisar',
  ].join(', ');

  return (
    <button
      type="button"
      onClick={onAbrir}
      aria-label={etiqueta}
      className="relative block w-full overflow-hidden rounded-tarjeta border border-linea bg-papel p-[14px] text-left shadow-tarjeta"
    >
      <Mancha
        color={COLORES_SALA[indice % COLORES_SALA.length]}
        forma={FORMAS_SALA[indice % FORMAS_SALA.length]}
        opacidad={0.16}
        className="-right-6 -top-7 h-28 w-28"
      />
      <div className="relative flex items-center justify-between gap-2">
        <h2>{sala.nombre}</h2>
        <ChevronRight aria-hidden="true" className="h-[22px] w-[22px] flex-none text-tinta-2" />
      </div>
      <div
        aria-hidden="true"
        className="relative my-2 h-2 overflow-hidden rounded-full bg-cuadricula"
      >
        <span className="block h-full rounded-full bg-integra" style={{ width: `${sala.porcentaje}%` }} />
      </div>
      <p className="relative text-[15px] text-tinta-2">
        {sala.observados30} de {sala.total} observados en 30 días ·{' '}
        {sala.revisarAvance > 0 ? (
          <span className="inline-flex items-center gap-1 font-bold text-tinta">
            <Flag aria-hidden="true" className="h-4 w-4 text-naranjo-texto" />
            {sala.revisarAvance} por revisar avance
          </span>
        ) : (
          'Ninguno por revisar'
        )}
      </p>
      <p className="relative text-[15px] text-tinta-2">
        Menos registrado: {sala.nombreNucleoMenosCubierto ?? '—'}
      </p>
    </button>
  );
}
