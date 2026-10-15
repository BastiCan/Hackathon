import { ChevronLeft, Flag, HelpCircle } from 'lucide-react';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useMiSala } from '../app/hooks';
import { FilaNiveles, NumeroNivel } from '../components/ChipNivel';
import { COLOR_FRESCURA, PALETA } from '../components/colores';
import { HojaGestionNino } from '../components/HojaGestionNino';
import { HojaLeyenda } from '../components/HojaLeyenda';
import { Mancha } from '../components/Mancha';
import { codigosNucleos, nombreNucleo, siglaNucleo } from '../lib/rubrica';
import {
  etiquetaTarjeta,
  filtrarTarjetas,
  type FiltroSala,
  type TarjetaNinoVista,
} from '../lib/vistas';

/**
 * Sala: la planilla de la sala, como el registro que la tía ya conoce. Una fila
 * por niño/a, una columna por núcleo con su nivel actual (el número va en el
 * color de su nivel, del 1 al 9) y la fecha del último registro con un punto
 * de frescura.
 *
 * En `soloLectura` es la misma planilla vista por la directora (tarea 14): al
 * tocar un niño/a se ofrece ver su ficha, moverlo de sala o darlo de baja.
 */
export function MiSala({ soloLectura = false }: { soloLectura?: boolean }) {
  const navegar = useNavigate();
  const { salaId } = useParams();
  const sala = useMiSala(soloLectura ? salaId : undefined);
  const [filtro, setFiltro] = useState<FiltroSala>('todos');
  const [leyenda, setLeyenda] = useState(false);
  const [gestionando, setGestionando] = useState<TarjetaNinoVista | null>(null);

  if (sala.cargando && !sala.valor) {
    return (
      <p role="status" className="py-10 text-center text-tinta-2">
        Cargando tu sala…
      </p>
    );
  }
  if (!sala.valor) {
    return (
      <p className="rounded-tarjeta border border-linea bg-papel p-4 text-tinta-2">
        {sala.error ?? 'No pudimos cargar tu sala.'}
      </p>
    );
  }

  const { tarjetas, conteos, partesResumen } = sala.valor;
  const visibles = filtrarTarjetas(tarjetas, filtro);
  const nucleos = codigosNucleos();

  return (
    <>
      {soloLectura ? (
        <button
          type="button"
          onClick={() => navegar('/directora')}
          className="-ml-[6px] mb-1 inline-flex min-h-tactil items-center gap-1 px-[6px] font-bold text-integra"
        >
          <ChevronLeft aria-hidden="true" className="h-[22px] w-[22px]" />
          Salas
        </button>
      ) : null}

      <p className="rotulo">
        {soloLectura ? 'Vista de la directora · solo lectura' : 'Planilla de la sala'}
      </p>
      <h1 className="mb-3">{sala.valor.sala.nombre}</h1>

      <div
        role="toolbar"
        aria-label="Filtrar niños y niñas"
        className="sin-barra -mx-4 mb-3 flex gap-2 overflow-x-auto px-4 pb-[2px]"
      >
        <Chip
          texto={`Todos ${conteos.todos}`}
          activo={filtro === 'todos'}
          onClick={() => setFiltro('todos')}
        />
        <Chip
          texto={`Sin registro ${conteos.sinRegistro}`}
          activo={filtro === 'sin-registro'}
          onClick={() => setFiltro('sin-registro')}
        />
        <Chip
          texto={`Revisar avance ${conteos.revisarAvance}`}
          activo={filtro === 'revisar-avance'}
          onClick={() => setFiltro('revisar-avance')}
        />
        <button
          type="button"
          onClick={() => setLeyenda(true)}
          aria-label="Qué significan los colores"
          className="grid min-h-tactil min-w-tactil flex-none place-items-center rounded-chip border border-linea bg-papel text-tinta-2"
        >
          <HelpCircle aria-hidden="true" className="h-[20px] w-[20px]" />
        </button>
      </div>

      {visibles.length > 0 ? (
        <div className="-mx-4 overflow-x-auto border-y border-linea bg-papel sm:mx-0 sm:rounded-tarjeta sm:border sm:shadow-tarjeta lg:overflow-x-visible">
          <table
            aria-label="Niños y niñas de la sala"
            className="w-full border-collapse text-[13px] lg:text-[15px]"
          >
            <thead>
              <tr className="border-b border-linea text-[12px] font-bold uppercase tracking-[0.04em] text-tinta-2">
                <th scope="col" className="py-2 pl-3 text-left font-bold lg:py-3 lg:pl-5">
                  Niño/a
                </th>
                {nucleos.map((n) => (
                  <th
                    key={n}
                    scope="col"
                    title={nombreNucleo(n)}
                    className="px-[1px] py-2 font-bold lg:px-2 lg:py-3"
                  >
                    <abbr title={nombreNucleo(n)} className="no-underline">
                      {siglaNucleo(n)}
                    </abbr>
                  </th>
                ))}
                <th scope="col" className="py-2 pr-3 text-right font-bold lg:py-3 lg:pr-5">
                  Último
                </th>
              </tr>
            </thead>
            <tbody>
              {visibles.map((t) => (
                <tr
                  key={t.id}
                  className="cursor-pointer border-b border-cuadricula last:border-b-0 hover:bg-integra-claro"
                  onClick={() => (soloLectura ? setGestionando(t) : navegar(`/nino/${t.id}`))}
                >
                  <th scope="row" className="pl-3 text-left font-bold lg:pl-5">
                    <button
                      type="button"
                      aria-label={etiquetaTarjeta(t)}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (soloLectura) setGestionando(t);
                        else navegar(`/nino/${t.id}`);
                      }}
                      className="flex min-h-tactil items-center gap-1 text-left"
                    >
                      {/* En escritorio hay espacio: el nombre se ve completo. */}
                      <span className="max-w-[96px] truncate lg:max-w-none lg:overflow-visible">
                        {t.nombreCorto}
                      </span>
                      {t.revisarAvance ? (
                        <Flag
                          aria-hidden="true"
                          className="h-[13px] w-[13px] flex-none text-naranjo-texto"
                        />
                      ) : null}
                    </button>
                  </th>
                  {nucleos.map((n) => {
                    const nivel = t.niveles[n];
                    const revisar = t.marcados.includes(n);
                    return (
                      <td key={n} className="px-[1px] text-center lg:px-2">
                        {nivel ? (
                          <>
                            <NumeroNivel nivel={nivel} revisar={revisar} tamano={20} />
                            <span className="sr-only">
                              Nivel {nivel}
                              {revisar ? ', revisar avance' : ''}
                            </span>
                          </>
                        ) : (
                          <span className="text-tinta-3" aria-label="sin registros">
                            –
                          </span>
                        )}
                      </td>
                    );
                  })}
                  <td className="tabular whitespace-nowrap pr-3 text-right text-[13px] text-tinta-2 lg:pr-5 lg:text-[14px]">
                    <span
                      className="punto mr-1 align-middle"
                      style={{ ['--punto' as string]: COLOR_FRESCURA[t.frescura] }}
                    />
                    {t.dias === null ? 'nunca' : t.dias === 0 ? 'hoy' : `${t.dias} d`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="rounded-tarjeta border border-dashed border-linea bg-papel p-4 text-center text-tinta-2">
          {filtro === 'todos'
            ? 'Todavía no hay niños ni niñas en esta sala.'
            : 'Ninguno en este filtro. ¡Buena noticia!'}
        </p>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] leading-[1.5] text-tinta-2">
        <span>Nivel alcanzado, del 1 al 9:</span>
        <FilaNiveles />
        <span>
          · aro <span className="font-bold text-naranjo-texto">naranjo</span>: revisar avance
        </span>
      </div>

      <p className="relative mt-3 overflow-hidden rounded-tarjeta border border-linea bg-papel p-3 text-[15px] text-tinta-2 shadow-tarjeta">
        <Mancha
          color={PALETA.azul}
          forma="c"
          opacidad={0.1}
          className="-bottom-6 -right-5 h-20 w-20"
        />
        <span className="relative">
          Observados en 30 días: <strong className="text-tinta">{partesResumen.observados}</strong> ·
          Menos registrado: <strong className="text-tinta">{partesResumen.menos}</strong>
        </span>
      </p>

      {leyenda ? <HojaLeyenda onCerrar={() => setLeyenda(false)} /> : null}
      {gestionando ? (
        <HojaGestionNino
          tarjeta={gestionando}
          salaActual={sala.valor.sala}
          onCerrar={() => setGestionando(null)}
        />
      ) : null}
    </>
  );
}

function Chip({
  texto,
  activo,
  onClick,
}: {
  texto: string;
  activo: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={activo}
      onClick={onClick}
      className={`min-h-tactil flex-none rounded-chip border px-3 text-[15px] ${
        activo
          ? 'border-integra bg-integra font-bold text-white'
          : 'border-linea bg-papel text-tinta-2'
      }`}
    >
      {texto}
    </button>
  );
}
