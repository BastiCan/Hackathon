import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { PALETA } from '../components/colores';
import { Mancha } from '../components/Mancha';
import { ProveedorAviso } from './aviso';
import { BarraInferior } from './BarraInferior';
import { ProveedorCaptura } from './captura';
import { Dock } from './Dock';
import { Encabezado } from './Encabezado';
import { useNombreNino, useSesion } from './hooks';
import { NavegacionLateral } from './NavegacionLateral';
import { rutaInicio } from './opciones';

/**
 * Marco de las pantallas, adaptable (`.kiro/steering/diseno-visual.md`):
 *
 * - **Celular** (< 1024 px): columna de 480 px (640 px en tablet) con el
 *   encabezado institucional arriba, la barra de captura y la barra inferior
 *   de navegación fijas abajo.
 * - **Computador** (desde 1024 px, `lg:`): encabezado a todo el ancho con su
 *   contenido hasta 1280 px, barra lateral de 232 px con la navegación y el
 *   bloque "Registrar", y el contenido a la derecha hasta 1000 px. No hay
 *   barras fijas abajo.
 */
export function Layout() {
  const { pathname } = useLocation();
  const sesion = useSesion();
  // Redirecciones por rol vuelven al inicio (Inicio).
  const inicio = rutaInicio();

  const enFicha = pathname.startsWith('/nino/');
  const enDirectora = pathname.startsWith('/directora');
  // Inicio lleva los botones de captura en la pantalla misma; la ficha, en el
  // dock (celular) o en la barra lateral (computador).
  const conDock = enFicha;
  const ninoId = enFicha ? pathname.split('/')[2] : undefined;
  const nombreNino = useNombreNino(ninoId);

  if (sesion.cargando) {
    return <Cargando texto="Cargando Huellita…" />;
  }

  // Demo sin usuaria elegida: primero la pantalla de entrada (tarea 5).
  if (sesion.valor && !sesion.valor.elegida) {
    return <Navigate to="/entrada" replace />;
  }

  const pendientes = sesion.valor?.pendientes ?? 0;
  const esDirectora = sesion.valor?.usuaria.rol === 'directora';

  // Acceso por rol: la vista directora no es para las tías (privacidad.md 6).
  if (enDirectora && sesion.valor && !esDirectora) {
    return <Navigate to={inicio} replace />;
  }

  // Ancho de la columna del celular; en escritorio manda la grilla de abajo.
  const ancho = enDirectora ? 'max-w-contenido' : 'max-w-tia md:max-w-[640px]';
  const hueco = conDock ? (nombreNino ? 'hueco-dock-nino' : 'hueco-dock') : 'hueco-barra';

  return (
    <ProveedorAviso conDock={conDock}>
      <ProveedorCaptura nino={ninoId && nombreNino ? { id: ninoId, nombre: nombreNino } : null}>
        <div
          className={`alto-pantalla relative isolate mx-auto flex w-full flex-col bg-fondo lg:max-w-none ${ancho}`}
        >
          <FondoManchas />
          <Encabezado
            usuaria={sesion.valor?.usuaria}
            salas={sesion.valor?.salas}
            salaActual={sesion.valor?.sala}
          />
          <div className="flex w-full flex-1 lg:mx-auto lg:max-w-[1280px]">
            <NavegacionLateral
              pendientes={pendientes}
              esDirectora={esDirectora}
              conDock={conDock}
              nombreNino={nombreNino ?? undefined}
            />
            <main className={`min-w-0 flex-1 px-4 pt-[14px] lg:max-w-[1000px] lg:px-7 lg:pt-6 ${hueco}`}>
              {sesion.error ? (
                <p className="rounded-tarjeta border border-linea bg-papel p-4 text-tinta-2">
                  {sesion.error}
                </p>
              ) : (
                <Outlet />
              )}
            </main>
          </div>
          {/* Las barras fijas van dentro de la columna (`isolate`), igual que las
              hojas que abren las pantallas: así una hoja (z-20) siempre queda
              sobre la barra (z-10) y su último botón nunca se esconde detrás. */}
          {conDock ? <Dock nombreNino={nombreNino ?? undefined} /> : null}
          <BarraInferior pendientes={pendientes} esDirectora={esDirectora} ancho={ancho} />
        </div>
      </ProveedorCaptura>
    </ProveedorAviso>
  );
}

/**
 * Manchas gigantes de la gráfica institucional, muy tenues (6 % o menos) y
 * detrás de todo el contenido (`-z-10` dentro del `isolate` de la columna).
 * Puro adorno: no estorban la lectura ni capturan toques.
 */
export function FondoManchas() {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <Mancha color={PALETA.azul} forma="a" opacidad={0.05} className="-left-24 top-20 h-72 w-72" />
      <Mancha
        color={PALETA.amarillo}
        forma="b"
        opacidad={0.06}
        className="-right-28 top-1/3 h-80 w-80"
      />
      <Mancha
        color={PALETA.rosado}
        forma="c"
        opacidad={0.04}
        className="-left-20 bottom-8 h-64 w-64"
      />
    </div>
  );
}

function Cargando({ texto }: { texto: string }) {
  return (
    <div className="alto-pantalla mx-auto flex w-full max-w-tia items-center justify-center bg-fondo md:max-w-[640px] lg:max-w-none">
      <p role="status" className="text-tinta-2">
        {texto}
      </p>
    </div>
  );
}
