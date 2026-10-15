import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Agenda } from '../pages/Agenda';
import { Directora } from '../pages/Directora';
import { Entrada } from '../pages/Entrada';
import { FichaNino } from '../pages/FichaNino';
import { MiSala } from '../pages/MiSala';
import { Revisar } from '../pages/Revisar';
import { Layout } from './Layout';
import { rutaInicio, useOpciones } from './opciones';
import { ProveedorServicios } from './servicios';

/**
 * Rutas de Huellita. Nada de datos de niños/as en las URLs: solo IDs
 * (privacidad.md 8). Sin agenda (versión AWS), "/" lleva a Mi sala.
 */
export function Rutas() {
  const opciones = useOpciones();
  const inicio = rutaInicio(opciones);
  return (
    <Routes>
      <Route path="/entrada" element={<Entrada />} />
      <Route element={<Layout />}>
        <Route path="/" element={opciones.agenda ? <Agenda /> : <Navigate to="/sala" replace />} />
        <Route path="/sala" element={<MiSala />} />
        <Route path="/revisar" element={<Revisar />} />
        <Route path="/nino/:id" element={<FichaNino />} />
        <Route path="/directora" element={<Directora />} />
        <Route path="/directora/sala/:salaId" element={<MiSala soloLectura />} />
      </Route>
      <Route path="*" element={<Navigate to={inicio} replace />} />
    </Routes>
  );
}

/**
 * `basename` sale de la base con la que se compiló (`BASE_URL`): así la app
 * también funciona servida desde una subcarpeta. Una base relativa (`./`, la
 * del HTML de un solo archivo) no sirve como `basename`: ahí va `/`.
 */
const BASE_RUTAS = import.meta.env.BASE_URL.startsWith('/') ? import.meta.env.BASE_URL : '/';

export function App() {
  return (
    <ProveedorServicios>
      <BrowserRouter basename={BASE_RUTAS}>
        <Rutas />
      </BrowserRouter>
    </ProveedorServicios>
  );
}
