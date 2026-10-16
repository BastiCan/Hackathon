import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Directora } from '../pages/Directora';
import { Entrada } from '../pages/Entrada';
import { FichaNino } from '../pages/FichaNino';
import { Inicio } from '../pages/Inicio';
import { MiSala } from '../pages/MiSala';
import { Revisar } from '../pages/Revisar';
import { Layout } from './Layout';
import { rutaInicio } from './opciones';
import { ProveedorServicios } from './servicios';

/**
 * Rutas de Huellita. Nada de datos de niños/as en las URLs: solo IDs
 * (privacidad.md 8). "/" es Inicio, que reemplazó a la antigua agenda.
 */
export function Rutas() {
  const inicio = rutaInicio();
  return (
    <Routes>
      <Route path="/entrada" element={<Entrada />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Inicio />} />
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
