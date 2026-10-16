import { ChevronLeft, Flag, HelpCircle, Pencil } from 'lucide-react';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAviso } from '../app/aviso';
import { useMiSala } from '../app/hooks';
import { useServicios } from '../app/servicios';
import { FilaNiveles, NumeroNivel } from '../components/ChipNivel';
import { COLOR_FRESCURA, PALETA } from '../components/colores';
import { HojaEditarNota } from '../components/HojaEditarNota';
import { HojaGestionNino } from '../components/HojaGestionNino';
import { HojaLeyenda } from '../components/HojaLeyenda';
import { Mancha } from '../components/Mancha';
import { codigosNucleos, nombreNucleo, nucleos, siglaNucleo } from '../lib/rubrica';
import {
  etiquetaTarjeta,
  filtrarTarjetas,
  type FiltroSala,
  type NotaSalaVista,
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
  const { datos } = useServicios();
  const aviso = useAviso();
  const { salaId } = useParams();
  const sala = useMiSala(soloLectura ? salaId : undefined);
  const [filtro, setFiltro] = useState<FiltroSala>('todos');
  const [leyenda, setLeyenda] = useState(false);
  const [gestionando, setGestionando] = useState<TarjetaNinoVista | null>(null);
  const [editandoNota, setEditandoNota] = useState<NotaSalaVista | null>(null);

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

  const { tarjetas, conteos, partesResumen, notas } = sala.valor;

  const guardarNota = (texto: string) => {
    if (!editandoNota) return;
    const id = editandoNota.sugerenciaId;
    setEditandoNota(null);
    void datos.editarNotaSala(id, texto).then(
      () => aviso('Nota actualizada'),
      () => aviso('No pudimos guardar la nota. Intentalo de nuevo.'),
    );
  };
  const visibles = filtrarTarjetas(tarjetas, filtro);
  const nucleosCodigos = codigosNucleos();

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

      {/* Leyenda de siglas de los núcleos, siempre a la vista. */}
      <ul className="mb-3 flex flex-wrap gap-x-3 gap-y-1 text-[13px] text-tinta-2">
        {nucleos().map((n) => (
          <li key={n.codigo} className="flex items-center gap-[6px]">
            <span className="grid h-5 min-w-[26px] place-items-center rounded-chip border border-linea bg-papel px-1 text-[11px] font-bold text-tinta">
              {n.sigla}
            </span>
            {n.nombre}
          </li>
        ))}
      </ul>

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
                {nucleosCodigos.map((n) => (
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
                  {nucleosCodigos.map((n) => {
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

      <section aria-labelledby="titulo-notas-sala" className="mt-4">
        <h2 id="titulo-notas-sala" className="rotulo mb-2">
          Notas de la sala{notas.length > 0 ? ` (${notas.length})` : ''}
        </h2>
        {notas.length === 0 ? (
          <p className="rounded-tarjeta border border-dashed border-linea bg-papel p-4 text-center text-[15px] text-tinta-2">
            Aqui quedan las observaciones generales de la sala (asistencia, clima del grupo,
            acuerdos del equipo). Registra una nota y confirmala en Revisar.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {notas.map((n) => (
              <li
                key={n.sugerenciaId}
                className="flex items-start justify-between gap-2 rounded-tarjeta border border-linea bg-papel p-3 shadow-tarjeta"
              >
                <div className="min-w-0">
                  <p className="text-[15px] text-tinta">{n.texto}</p>
                  <p className="mt-1 text-[13px] text-tinta-2">
                    {n.fechaCorta ? n.fechaCorta + ' | ' : ''}
                    {n.autora}
                  </p>
                </div>
                {!soloLectura ? (
                  <button
                    type="button"
                    onClick={() => setEditandoNota(n)}
                    aria-label="Editar esta nota de la sala"
                    className="grid min-h-tactil min-w-tactil flex-none place-items-center rounded-chip border border-linea bg-papel text-tinta-2"
                  >
                    <Pencil aria-hidden="true" className="h-[18px] w-[18px]" />
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      {leyenda ? <HojaLeyenda onCerrar={() => setLeyenda(false)} /> : null}
      {gestionando ? (
        <HojaGestionNino
          tarjeta={gestionando}
          salaActual={sala.valor.sala}
          onCerrar={() => setGestionando(null)}
        />
      ) : null}
      {editandoNota ? (
        <HojaEditarNota
          textoInicial={editandoNota.texto}
          onGuardar={guardarNota}
          onCerrar={() => setEditandoNota(null)}
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
