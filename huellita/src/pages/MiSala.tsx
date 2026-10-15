import { ChevronLeft, ChevronRight, HelpCircle } from 'lucide-react';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useMiSala, useSesion } from '../app/hooks';
import { HojaGestionNino } from '../components/HojaGestionNino';
import { HojaLeyenda } from '../components/HojaLeyenda';
import { HojaMenu } from '../components/HojaMenu';
import { TarjetaNino } from '../components/TarjetaNino';
import {
  fechaLarga,
  filtrarTarjetas,
  inicialesUsuaria,
  type FiltroSala,
  type TarjetaNinoVista,
} from '../lib/vistas';

/**
 * Pantalla 1: Mi sala. Pila de notas por revisar, filtros, grilla de niños/as y
 * resumen de la sala. El dock de captura lo pone el layout.
 *
 * En `soloLectura` es la misma pantalla vista por la directora (tarea 14): sin
 * captura ni revisión, y al tocar un niño/a se ofrece ver su ficha, moverlo de
 * sala o darlo de baja.
 */
export function MiSala({ soloLectura = false }: { soloLectura?: boolean }) {
  const navegar = useNavigate();
  const { salaId } = useParams();
  const sesion = useSesion();
  const sala = useMiSala(soloLectura ? salaId : sesion.valor?.sala.id);
  const [filtro, setFiltro] = useState<FiltroSala>('todos');
  const [hoja, setHoja] = useState<'menu' | 'leyenda' | null>(null);
  const [gestionando, setGestionando] = useState<TarjetaNinoVista | null>(null);

  if (sala.cargando || sesion.cargando) {
    return (
      <p role="status" className="py-10 text-center text-tinta-2">
        Cargando tu sala…
      </p>
    );
  }
  if (!sala.valor || !sesion.valor) {
    return (
      <p className="rounded-tarjeta border border-linea bg-papel p-4 text-tinta-2">
        {sala.error ?? 'No pudimos cargar tu sala.'}
      </p>
    );
  }

  const { tarjetas, conteos, partesResumen, pendientes, hoy } = sala.valor;
  const { usuaria, salas } = sesion.valor;
  const visibles = filtrarTarjetas(tarjetas, filtro);

  return (
    <>
      {soloLectura ? (
        <button
          type="button"
          onClick={() => navegar('/directora')}
          className="-ml-[6px] mb-1 inline-flex min-h-tactil items-center gap-1 px-[6px] font-bold text-tinta-2"
        >
          <ChevronLeft aria-hidden="true" className="h-[22px] w-[22px]" />
          Salas
        </button>
      ) : null}

      <header className="mb-[14px] flex items-start justify-between">
        <div>
          <p className="text-[14px] text-tinta-2">
            {soloLectura ? 'Vista de la directora · solo lectura' : fechaLarga(hoy)}
          </p>
          <h1>{sala.valor.sala.nombre}</h1>
        </div>
        {soloLectura ? null : (
          <button
            type="button"
            onClick={() => setHoja('menu')}
            aria-label={`Menú de ${usuaria.nombre}`}
            className="grid h-11 w-11 flex-none place-items-center rounded-full bg-integra font-display font-semibold text-white"
          >
            {inicialesUsuaria(usuaria.nombre)}
          </button>
        )}
      </header>

      {pendientes > 0 && !soloLectura ? (
        <button
          type="button"
          onClick={() => navegar('/revisar')}
          className="pila mt-[6px] mb-[18px] flex w-full min-h-tactil items-center gap-[14px] bg-postit-amarillo px-4 py-[14px] text-left"
          style={{ transform: 'rotate(-0.6deg)' }}
        >
          <b className="font-mano text-[26px] leading-none">{pendientes}</b>
          <span>
            <strong>notas por revisar</strong>
            <br />
            <span className="text-[14px]">Huellita ya las ordenó</span>
          </span>
          <ChevronRight aria-hidden="true" className="ml-auto h-[22px] w-[22px]" />
        </button>
      ) : null}

      <div
        role="toolbar"
        aria-label="Filtrar niños y niñas"
        className="sin-barra -mx-4 mb-[14px] flex gap-2 overflow-x-auto px-4 pb-[2px]"
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
          onClick={() => setHoja('leyenda')}
          aria-label="Qué significan los colores"
          className="grid min-h-tactil min-w-tactil flex-none place-items-center rounded-full border border-linea bg-papel text-tinta-2"
        >
          <HelpCircle aria-hidden="true" className="h-[22px] w-[22px]" />
        </button>
      </div>

      {visibles.length > 0 ? (
        <section
          aria-label="Niños y niñas de la sala"
          // 3 columnas en celular; la vista de la directora (hasta 1100 px)
          // aprovecha el escritorio con 6.
          className={`grid gap-[10px] grid-cols-3 ${soloLectura ? 'md:grid-cols-6' : ''}`}
        >
          {visibles.map((t) => (
            <TarjetaNino
              key={t.id}
              tarjeta={t}
              onAbrir={(id) => (soloLectura ? setGestionando(t) : navegar(`/nino/${id}`))}
            />
          ))}
        </section>
      ) : (
        <p className="rounded-tarjeta border border-dashed border-linea bg-papel p-4 text-center text-tinta-2">
          {filtro === 'todos'
            ? 'Todavía no hay niños ni niñas en esta sala.'
            : 'Ninguno en este filtro. ¡Buena noticia!'}
        </p>
      )}

      <p className="mt-4 rounded-tarjeta border border-dashed border-linea bg-papel p-[14px] text-[15px] text-tinta-2">
        Observados este mes: <strong className="text-tinta">{partesResumen.observados}</strong> ·
        Menos registrado: <strong className="text-tinta">{partesResumen.menos}</strong>
      </p>

      {hoja === 'menu' ? (
        <HojaMenu
          usuaria={usuaria}
          salas={salas}
          salaActual={sala.valor.sala}
          onCerrar={() => setHoja(null)}
        />
      ) : null}
      {hoja === 'leyenda' ? <HojaLeyenda onCerrar={() => setHoja(null)} /> : null}
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
      className={`min-h-tactil flex-none rounded-full border px-[14px] py-2 text-[15px] ${
        activo ? 'border-tinta bg-tinta text-white' : 'border-linea bg-papel text-tinta-2'
      }`}
    >
      {texto}
    </button>
  );
}
