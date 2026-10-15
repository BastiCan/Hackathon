import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { ProveedorAviso } from './aviso';
import { BarraInferior } from './BarraInferior';
import { ProveedorCaptura } from './captura';
import { Dock } from './Dock';
import { Encabezado } from './Encabezado';
import { useNombreNino, useSesion } from './hooks';

/**
 * Marco de las pantallas: encabezado institucional arriba, contenido centrado a
 * 480 px (la vista directora usa hasta 1100 px), barra de captura en la agenda
 * y en la ficha, y la barra inferior de navegación.
 */
export function Layout() {
  const { pathname } = useLocation();
  const sesion = useSesion();

  const enFicha = pathname.startsWith('/nino/');
  const enDirectora = pathname.startsWith('/directora');
  const conDock = pathname === '/' || enFicha;
  const ninoId = enFicha ? pathname.split('/')[2] : undefined;
  const nombreNino = useNombreNino(ninoId);

  if (sesion.cargando) {
    return <Cargando />;
  }

  // Demo sin usuaria elegida: primero la pantalla de entrada (tarea 5).
  if (sesion.valor && !sesion.valor.elegida) {
    return <Navigate to="/entrada" replace />;
  }

  const pendientes = sesion.valor?.pendientes ?? 0;
  const esDirectora = sesion.valor?.usuaria.rol === 'directora';

  // Acceso por rol: la vista directora no es para las tías (privacidad.md 6).
  if (enDirectora && sesion.valor && !esDirectora) {
    return <Navigate to="/" replace />;
  }

  const ancho = enDirectora ? 'max-w-contenido' : 'max-w-tia';

  return (
    <ProveedorAviso conDock={conDock}>
      <ProveedorCaptura nino={ninoId && nombreNino ? { id: ninoId, nombre: nombreNino } : null}>
        <div className={`mx-auto flex min-h-dvh w-full flex-col bg-fondo ${ancho}`}>
          <Encabezado
            usuaria={sesion.valor?.usuaria}
            salas={sesion.valor?.salas}
            salaActual={sesion.valor?.sala}
          />
          <main
            className="flex-1 px-4 pt-[14px]"
            style={{ paddingBottom: conDock ? (nombreNino ? 156 : 132) : 84 }}
          >
            {sesion.error ? (
              <p className="rounded-tarjeta border border-linea bg-papel p-4 text-tinta-2">
                {sesion.error}
              </p>
            ) : (
              <Outlet />
            )}
          </main>
        </div>
        {conDock ? <Dock nombreNino={nombreNino ?? undefined} /> : null}
        <BarraInferior pendientes={pendientes} esDirectora={esDirectora} ancho={ancho} />
      </ProveedorCaptura>
    </ProveedorAviso>
  );
}

function Cargando() {
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-tia items-center justify-center bg-fondo">
      <p role="status" className="text-tinta-2">
        Cargando tu agenda…
      </p>
    </div>
  );
}
