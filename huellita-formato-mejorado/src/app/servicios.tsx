/**
 * Único punto donde la interfaz toma los servicios. Las pantallas piden
 * `useServicios()` y hablan solo con `DataService` e `IAService`: nunca leen
 * `data/semilla.json` ni `localStorage` por su cuenta.
 */
import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { servicioDatos, type DataService } from '../services/datos';
import { servicioHttp } from '../services/http';
import { servicioIA, type IAService } from '../services/ia';
import { CONFIG } from './config';

export interface Servicios {
  datos: DataService;
  ia: IAService;
}

/** Con `VITE_DATOS=http` la app habla con el BFF en `/api`; si no, es local. */
const PREDETERMINADOS: Servicios = {
  datos: CONFIG.datos === 'http' ? servicioHttp : servicioDatos,
  ia: servicioIA,
};

const ContextoServicios = createContext<Servicios>(PREDETERMINADOS);

export function ProveedorServicios({
  children,
  datos,
  ia,
}: {
  children: ReactNode;
  datos?: DataService;
  ia?: IAService;
}) {
  const valor = useMemo<Servicios>(
    () => ({ datos: datos ?? PREDETERMINADOS.datos, ia: ia ?? PREDETERMINADOS.ia }),
    [datos, ia],
  );
  return <ContextoServicios.Provider value={valor}>{children}</ContextoServicios.Provider>;
}

export function useServicios(): Servicios {
  return useContext(ContextoServicios);
}
