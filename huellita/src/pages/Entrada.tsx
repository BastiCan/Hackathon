import { ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useConsulta } from '../app/hooks';
import { useServicios } from '../app/servicios';
import { inicialesUsuaria } from '../lib/vistas';

/**
 * Entrada de la demo (tarea 5): elegir con quién se entra. La elección queda
 * recordada en el `DataService`. En la Fase 2 la reemplaza el login de Cognito.
 */
export function Entrada() {
  const { datos } = useServicios();
  const navegar = useNavigate();

  const consulta = useConsulta(async (d) => {
    const [usuarias, salas, jardin] = await Promise.all([
      d.usuarias(),
      d.salasDelJardin(),
      d.jardin(),
    ]);
    return {
      jardin,
      opciones: usuarias.map((u) => ({
        id: u.id,
        nombre: u.nombre,
        iniciales: inicialesUsuaria(u.nombre),
        detalle:
          u.rol === 'directora'
            ? 'Todas las salas del jardín'
            : u.salaIds
                .map((id) => salas.find((s) => s.id === id)?.nombre ?? 'Sala')
                .join(' · '),
      })),
    };
  }, []);

  const entrar = async (id: string) => {
    await datos.cambiarUsuaria(id);
    navegar('/', { replace: true });
  };

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-tia flex-col bg-fondo px-4 pb-10 pt-12">
      <h1>Huellita</h1>
      <p className="mt-1 text-[15px] text-tinta-2">
        {consulta.valor?.jardin.nombre ?? 'Jardín de la demo'}
      </p>
      <h2 className="mb-2 mt-7">¿Quién entra hoy?</h2>

      {consulta.cargando ? <p className="text-tinta-2">Cargando…</p> : null}
      {consulta.error ? <p className="text-tinta-2">{consulta.error}</p> : null}

      <ul className="flex flex-col gap-[10px]">
        {(consulta.valor?.opciones ?? []).map((o) => (
          <li key={o.id}>
            <button
              type="button"
              onClick={() => void entrar(o.id)}
              className="flex w-full min-h-tactil items-center gap-3 rounded-tarjeta border border-linea bg-papel p-3 text-left"
            >
              <span
                aria-hidden="true"
                className="grid h-11 w-11 flex-none place-items-center rounded-full bg-integra font-display font-semibold text-white"
              >
                {o.iniciales}
              </span>
              <span className="flex-1">
                <span className="block font-bold">{o.nombre}</span>
                <span className="block text-[14px] text-tinta-2">{o.detalle}</span>
              </span>
              <ChevronRight aria-hidden="true" className="h-[22px] w-[22px] text-tinta-3" />
            </button>
          </li>
        ))}
      </ul>

      <p className="mt-6 text-[14px] text-tinta-2">
        Datos de demostración: los nombres de niños y niñas son ficticios.
      </p>
    </div>
  );
}
