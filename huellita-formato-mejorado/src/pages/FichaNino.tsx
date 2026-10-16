import { ChevronLeft, Flag, PencilLine } from 'lucide-react';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAviso } from '../app/aviso';
import { useFicha } from '../app/hooks';
import { useServicios } from '../app/servicios';
import { Avatar } from '../components/Avatar';
import { NumeroNivel } from '../components/ChipNivel';
import { PALETA } from '../components/colores';
import { HojaCambiar } from '../components/HojaCambiar';
import { HojaNucleo } from '../components/HojaNucleo';
import { Mancha } from '../components/Mancha';
import { Miniatura } from '../components/Miniatura';
import type { NucleoId, Sugerencia } from '../lib/tipos';
import type { NucleoVista, RegistroVista } from '../lib/vistas';

/**
 * Ficha del niño/a: cómo va en cada núcleo (el número en el color de su nivel,
 * igual que en la planilla), su promedio de notas válidas comparado con la
 * sala y sus registros con la foto de cada post-it.
 */
export function FichaNino() {
  const { id } = useParams();
  const navegar = useNavigate();
  const { datos } = useServicios();
  const aviso = useAviso();
  const vista = useFicha(id);
  const [detalle, setDetalle] = useState<NucleoVista | null>(null);
  const [filtro, setFiltro] = useState<NucleoId | 'todos'>('todos');
  const [corrigiendo, setCorrigiendo] = useState<Sugerencia | null>(null);

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

  // Un registro de la ficha abre la misma hoja Corregir de Revisar, armada con
  // sus datos actuales. Al guardar se vuelve a validar la sugerencia, que deja
  // registro del cambio (campo original) y recalcula niveles y promedio.
  const abrirCorreccion = (r: RegistroVista) => {
    setCorrigiendo({
      id: r.id,
      evidenciaId: '',
      salaId: f.sala.id,
      tipo: 'evaluacion',
      ninoId: f.nino.id,
      nucleo: r.nucleo,
      nivel: r.nivel,
      cita: r.cita,
      certeza: 'alta',
      estado: 'aceptada',
    });
  };
  const guardarCorreccion = (cambios: { ninoId?: string; nucleo?: NucleoId; nivel?: number }) => {
    if (!corrigiendo) return;
    const id = corrigiendo.id;
    setCorrigiendo(null);
    void datos
      .validar(id, cambios as Parameters<typeof datos.validar>[1])
      .then(
        () => aviso('Registro actualizado'),
        () => aviso('No pudimos guardar el cambio. Intentalo de nuevo.'),
      );
  };
  const historial =
    filtro === 'todos' ? f.historial : f.historial.filter((r) => r.nucleo === filtro);
  const conFoto = f.historial.filter((r) => r.foto).slice(0, 6);
  const tira = conFoto.length > 0 ? conFoto : f.historial.slice(0, 3);
  const promedioTexto = f.promedio !== null ? f.promedio.toFixed(1) : null;
  const promedioSalaTexto =
    f.rezago.promedioSala !== null ? f.rezago.promedioSala.toFixed(1) : null;

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

      {/* Escritorio: a la izquierda cómo va; a la derecha sus fotos y los
          registros. En celular es la misma fila de siempre. */}
      <div className="lg:grid lg:grid-cols-2 lg:items-start lg:gap-6">
        <div className="min-w-0">
          <section
            aria-label="Nivel por núcleo"
            className="relative mb-3 overflow-hidden rounded-tarjeta border border-linea bg-papel px-3 py-[10px] shadow-tarjeta"
          >
            <Mancha
              color={PALETA.azul}
              forma="c"
              opacidad={0.08}
              className="-right-6 -top-7 h-24 w-24"
            />
            <div className="relative mb-2 flex items-end justify-between gap-2">
              <p className="rotulo mb-0">Cómo va · por núcleo</p>
              {promedioTexto ? (
                <p className="text-[13px] text-tinta-2">
                  Promedio{' '}
                  <strong className="text-[15px] text-tinta">{promedioTexto}</strong>
                  {promedioSalaTexto ? (
                    <span> · sala {promedioSalaTexto}</span>
                  ) : null}
                </p>
              ) : null}
            </div>

            {f.rezago.enRezago ? (
              <p
                role="status"
                className="relative mb-2 flex items-start gap-2 rounded-campo border border-naranjo-texto/40 bg-naranjo-suave px-3 py-2 text-[14px] text-naranjo-texto"
              >
                <Flag aria-hidden="true" className="mt-[2px] h-[16px] w-[16px] flex-none" />
                <span>
                  <b>Posible rezago.</b> Su promedio está una desviación estándar o más por
                  debajo del resto de la sala. Conviene acompañar de cerca y registrar seguido.
                </span>
              </p>
            ) : null}

            <ul className="relative">
              {f.nucleos.map((n) => (
                <li key={n.nucleo} className="border-b border-cuadricula last:border-b-0">
                  <button
                    type="button"
                    onClick={() => setDetalle(n)}
                    className="flex min-h-tactil w-full items-center justify-between gap-2 py-[6px] text-left"
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
                        {n.nivel ? `Nivel ${n.nivel} · ${n.nombreNivel}` : 'Sin registros aún'}
                        {n.revisarAvance ? ` · revisar avance (esperado ${f.nivelEsperadoEdad})` : ''}
                      </span>
                    </span>
                    {n.nivel ? (
                      <NumeroNivel nivel={n.nivel} revisar={n.revisarAvance} tamano={28} />
                    ) : (
                      <span className="text-tinta-3">–</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <div className="min-w-0">
          {tira.length > 0 ? (
            <section className="mb-3 rounded-tarjeta border border-linea bg-papel px-3 py-[10px] shadow-tarjeta">
              <p className="rotulo mb-2">Últimos registros</p>
              <ul className="sin-barra -mx-3 flex gap-3 overflow-x-auto px-3">
                {tira.map((r) => (
                  <li key={r.id} className="w-[84px] flex-none">
                    <Miniatura formato={r.formato ?? 'texto'} foto={r.foto} tamano={84} conMancha />
                    <p className="mt-1 text-[12px] text-tinta-2">
                      {r.fechaCorta} · {r.sigla} {r.nivel}
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
              <p className="text-[15px] text-tinta-2">
                Todavía no hay registros guardados con este filtro.
              </p>
            ) : (
              <ol className="linea-tiempo">
                {historial.map((r) => (
                  <li
                    key={r.id}
                    className="pb-3"
                    style={{ ['--punto' as string]: r.color }}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-[13px] text-tinta-2">
                          {r.fechaCorta} · {r.nombreNucleo} · Nivel {r.nivel} · {r.autora}
                        </p>
                        <q className="text-[15px] text-tinta">“{r.cita}”</q>
                      </div>
                      <button
                        type="button"
                        onClick={() => abrirCorreccion(r)}
                        aria-label={`Corregir el registro de ${r.nombreNucleo} del ${r.fechaCorta}`}
                        className="grid min-h-tactil min-w-tactil flex-none place-items-center rounded-chip border border-linea bg-papel text-tinta-2"
                      >
                        <PencilLine aria-hidden="true" className="h-[18px] w-[18px]" />
                      </button>
                    </div>
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

      {corrigiendo ? (
        <HojaCambiar
          sugerencia={corrigiendo}
          ninos={f.ninosSala}
          onGuardar={guardarCorreccion}
          onCerrar={() => setCorrigiendo(null)}
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