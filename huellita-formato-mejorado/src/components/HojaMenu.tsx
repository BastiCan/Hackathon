import { DoorOpen, RotateCcw, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useServicios } from '../app/servicios';
import type { Sala, Usuaria } from '../lib/tipos';
import { HojaInferior } from './HojaInferior';

/**
 * Menú de la tía: cambiar de sala, cambiar de usuaria y reiniciar la demo.
 * Al reiniciar se vuelve a la pantalla de entrada.
 */
export function HojaMenu({
  usuaria,
  salas,
  salaActual,
  onCerrar,
}: {
  usuaria: Usuaria;
  salas: Sala[];
  salaActual: Sala;
  onCerrar: () => void;
}) {
  const { datos } = useServicios();
  const navegar = useNavigate();

  return (
    <HojaInferior titulo={usuaria.nombre} onCerrar={onCerrar}>
      <p className="mt-1 text-[15px] text-tinta-2">Sala {salaActual.nombre}</p>

      {salas.length > 1 ? (
        <div className="mt-4">
          <h3 className="mb-2 text-[13px] font-bold uppercase tracking-[0.06em] text-tinta-2">
            Cambiar de sala
          </h3>
          <div className="flex flex-col gap-2">
            {salas.map((s) => (
              <button
                key={s.id}
                type="button"
                aria-pressed={s.id === salaActual.id}
                onClick={() => {
                  void datos.cambiarSala(s.id).then(onCerrar);
                }}
                className={`flex min-h-tactil items-center rounded-tarjeta border px-3 py-2 text-left font-bold ${
                  s.id === salaActual.id ? 'border-integra bg-integra-claro' : 'border-linea'
                }`}
              >
                {s.nombre}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-5 flex flex-col gap-2">
        <button
          type="button"
          onClick={() => navegar('/entrada')}
          className="flex min-h-tactil items-center gap-3 rounded-tarjeta border border-linea px-3 py-2 text-left font-bold"
        >
          <Users aria-hidden="true" className="h-[22px] w-[22px] text-tinta-2" />
          Cambiar de usuaria
        </button>
        <button
          type="button"
          onClick={() => {
            void datos.reiniciarDemo().then(() => {
              onCerrar();
              navegar('/entrada', { replace: true });
            });
          }}
          className="flex min-h-tactil items-center gap-3 rounded-tarjeta border border-linea px-3 py-2 text-left font-bold"
        >
          <RotateCcw aria-hidden="true" className="h-[22px] w-[22px] text-tinta-2" />
          Reiniciar demo
        </button>
        <button
          type="button"
          onClick={onCerrar}
          className="flex min-h-tactil items-center gap-3 rounded-tarjeta px-3 py-2 text-left font-bold text-tinta-2"
        >
          <DoorOpen aria-hidden="true" className="h-[22px] w-[22px]" />
          Seguir en mi sala
        </button>
      </div>
    </HojaInferior>
  );
}
