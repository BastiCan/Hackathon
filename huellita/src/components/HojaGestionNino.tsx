import { ArrowRightLeft, Eye, UserMinus } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAviso } from '../app/aviso';
import { useConsulta } from '../app/hooks';
import { useServicios } from '../app/servicios';
import type { Sala } from '../lib/tipos';
import type { TarjetaNinoVista } from '../lib/vistas';
import { Avatar } from './Avatar';
import { Boton } from './Boton';
import { ChipNivel } from './ChipNivel';
import { HojaInferior } from './HojaInferior';

type Accion = 'mover' | 'baja' | null;

/**
 * Gestión de un niño/a desde la vista de la directora (tarea 14): ver su ficha,
 * moverlo de sala o darlo de baja. Las dos últimas piden confirmación y en la
 * Fase 1 solo cambian los datos de prueba.
 */
export function HojaGestionNino({
  tarjeta,
  salaActual,
  onCerrar,
}: {
  tarjeta: TarjetaNinoVista;
  salaActual: Sala;
  onCerrar: () => void;
}) {
  const { datos } = useServicios();
  const navegar = useNavigate();
  const aviso = useAviso();
  const [accion, setAccion] = useState<Accion>(null);
  const [destino, setDestino] = useState<string>('');

  const salas = useConsulta(async (d) => d.salasDelJardin(), []);
  const otras = (salas.valor ?? []).filter((s) => s.id !== salaActual.id);

  const mover = () => {
    const id = destino || otras[0]?.id;
    if (!id) return;
    const nombreSala = otras.find((s) => s.id === id)?.nombre ?? 'otra sala';
    void datos.moverNino(tarjeta.id, id).then(() => {
      onCerrar();
      aviso(`${tarjeta.nombre} ahora está en ${nombreSala}`);
    });
  };

  const darDeBaja = () => {
    void datos.darDeBaja(tarjeta.id).then(() => {
      onCerrar();
      aviso(`${tarjeta.nombre} quedó fuera de la lista de la sala`);
    });
  };

  return (
    <HojaInferior etiqueta={`Opciones de ${tarjeta.nombre}`} onCerrar={onCerrar}>
      <div className="mb-4 flex items-center gap-3">
        <Avatar iniciales={tarjeta.iniciales} frescura={tarjeta.frescura} tamano={54} />
        <div>
          <h2>{tarjeta.nombre}</h2>
          <p className="mt-1 flex items-center gap-2 text-[14px] text-tinta-2">
            <ChipNivel nivel={tarjeta.nivelGeneral} />
            {salaActual.nombre}
          </p>
        </div>
      </div>

      {accion === null ? (
        <div className="flex flex-col gap-2">
          <Opcion
            icono={<Eye aria-hidden="true" className="h-[22px] w-[22px] text-tinta-2" />}
            texto="Ver su ficha"
            onClick={() => navegar(`/nino/${tarjeta.id}`)}
          />
          {otras.length > 0 ? (
            <Opcion
              icono={
                <ArrowRightLeft aria-hidden="true" className="h-[22px] w-[22px] text-tinta-2" />
              }
              texto="Mover de sala"
              onClick={() => {
                setDestino(otras[0]?.id ?? '');
                setAccion('mover');
              }}
            />
          ) : null}
          <Opcion
            icono={<UserMinus aria-hidden="true" className="h-[22px] w-[22px] text-tinta-2" />}
            texto="Dar de baja"
            onClick={() => setAccion('baja')}
          />
        </div>
      ) : null}

      {accion === 'mover' ? (
        <div>
          <label className="block text-[14px] text-tinta-2">
            Nueva sala
            <select
              value={destino}
              onChange={(e) => setDestino(e.target.value)}
              className="mt-1 min-h-tactil w-full rounded-tarjeta border border-linea bg-papel px-[10px] py-2 text-base text-tinta"
            >
              {otras.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nombre}
                </option>
              ))}
            </select>
          </label>
          <p className="mt-3 text-[15px] text-tinta-2">
            Sus registros se van con {tarjeta.nombre}. Esto solo cambia los datos de la demo.
          </p>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <Boton variante="sec" onClick={() => setAccion(null)}>
              Volver
            </Boton>
            <Boton variante="pri" onClick={mover}>
              Mover
            </Boton>
          </div>
        </div>
      ) : null}

      {accion === 'baja' ? (
        <div>
          <p className="text-[15px] text-tinta-2">
            ¿Dar de baja a {tarjeta.nombre}? Deja de aparecer en la sala y sus registros quedan
            guardados. Esto solo cambia los datos de la demo.
          </p>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <Boton variante="sec" onClick={() => setAccion(null)}>
              Volver
            </Boton>
            <Boton variante="pri" onClick={darDeBaja}>
              Sí, dar de baja
            </Boton>
          </div>
        </div>
      ) : null}
    </HojaInferior>
  );
}

function Opcion({
  icono,
  texto,
  onClick,
}: {
  icono: ReactNode;
  texto: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-h-tactil items-center gap-3 rounded-tarjeta border border-linea px-3 py-2 text-left font-bold"
    >
      {icono}
      {texto}
    </button>
  );
}
