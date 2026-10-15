import { Building2, ClipboardCheck, House, Table2, type LucideIcon } from 'lucide-react';

/**
 * Los destinos de la navegación, en un solo lugar: los usan la barra inferior
 * del celular (`BarraInferior`) y la barra lateral del computador
 * (`NavegacionLateral`), así nunca se desordena una respecto de la otra.
 */
export interface Destino {
  a: string;
  texto: string;
  icono: LucideIcon;
  /** Rutas que dejan el destino marcado como actual. */
  esActivo: (ruta: string) => boolean;
  /** Muestra el contador de pendientes. */
  conContador?: boolean;
  /** Acceso por rol: solo la directora lo ve (privacidad.md 6). */
  soloDirectora?: boolean;
}

const TODOS: Destino[] = [
  { a: '/', texto: 'Inicio', icono: House, esActivo: (r) => r === '/' },
  {
    a: '/sala',
    texto: 'Sala',
    icono: Table2,
    esActivo: (r) => r === '/sala' || r.startsWith('/nino/'),
  },
  {
    a: '/revisar',
    texto: 'Revisar',
    icono: ClipboardCheck,
    esActivo: (r) => r === '/revisar',
    conContador: true,
  },
  {
    a: '/directora',
    texto: 'Directora',
    icono: Building2,
    esActivo: (r) => r.startsWith('/directora'),
    soloDirectora: true,
  },
];

/** Los destinos que corresponden al rol de quien entró. */
export function destinos(esDirectora: boolean): Destino[] {
  return TODOS.filter((d) => !d.soloDirectora || esDirectora);
}
