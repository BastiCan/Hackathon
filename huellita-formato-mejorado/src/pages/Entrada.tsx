import { ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useConsulta } from '../app/hooks';
import { FranjaLogo, LogoOficial } from '../app/Encabezado';
import { FondoManchas } from '../app/Layout';
import { rutaInicio } from '../app/opciones';
import { useServicios } from '../app/servicios';
import { inicialesUsuaria } from '../lib/vistas';

/**
 * Entrada de la demo (tarea 5): elegir con quién se entra. La elección queda
 * recordada en el `DataService`. En la Fase 2 la reemplaza el login de Cognito.
 */
export function Entrada() {
  const { datos } = useServicios();
  const navegar = useNavigate();
  const inicio = rutaInicio();

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
        rol: u.rol,
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
    // La directora parte en el resumen de todas las salas; la tía, en Inicio.
    const rol = consulta.valor?.opciones.find((u) => u.id === id)?.rol;
    navegar(rol === 'directora' ? '/directora' : inicio, { replace: true });
  };

  return (
    /*
     * En escritorio la entrada es una tarjeta centrada de 560 px sobre el fondo
     * con manchas; en celular sigue siendo la columna de siempre.
     */
    <div className="alto-pantalla-escritorio relative isolate lg:flex lg:items-center lg:justify-center lg:py-10">
      <FondoManchas />
      <div className="alto-pantalla mx-auto flex w-full max-w-tia flex-col bg-fondo md:max-w-[640px] lg:w-[560px] lg:min-h-0 lg:max-w-none lg:overflow-hidden lg:rounded-tarjeta lg:border lg:border-linea lg:shadow-tarjeta">
      <div className="flex min-h-[80px] items-center justify-center border-b border-linea bg-papel px-4 py-3">
        <LogoOficial className="h-14 sm:h-16" />
      </div>
      <FranjaLogo />
      <div className="px-4 pb-10 pt-8">
      <p className="rotulo">{consulta.valor?.jardin.nombre ?? 'Jardín de la demo'}</p>
      <h1 className="text-[26px]">Huellita</h1>
      <p className="mt-1 text-[15px] text-tinta-2">
        Registro de observaciones de la sala para educadoras y técnicas de párvulos.
      </p>
      <h2 className="mb-2 mt-7">¿Quién entra hoy?</h2>

      {consulta.cargando ? <p className="text-tinta-2">Cargando…</p> : null}
      {consulta.error ? <p className="text-tinta-2">{consulta.error}</p> : null}

      <ul className="flex flex-col gap-[10px] lg:grid lg:grid-cols-2">
        {(consulta.valor?.opciones ?? []).map((o) => (
          <li key={o.id}>
            <button
              type="button"
              onClick={() => void entrar(o.id)}
              className="flex w-full min-h-tactil items-center gap-3 rounded-tarjeta border border-linea bg-papel p-3 text-left"
            >
              <span
                aria-hidden="true"
                className="grid h-11 w-11 flex-none place-items-center rounded-full bg-integra font-bold text-white"
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
      </div>
    </div>
  );
}
