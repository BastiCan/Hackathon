/**
 * Datos de la Fase 1: la interfaz `DataService` y su implementación local, que
 * parte de `data/semilla.json` y guarda los cambios en `localStorage`.
 * Las pantallas nunca leen el JSON ni AWS directamente: solo hablan con esta
 * interfaz, así la Fase 2 cambia la implementación y no las pantallas.
 */
import semillaJson from '@data/semilla.json';
import type {
  DemoCaptura,
  EstadoSugerencia,
  Evidencia,
  Jardin,
  Nino,
  Nivel,
  NucleoId,
  Sala,
  Semilla,
  Sugerencia,
  Usuaria,
} from '../lib/tipos';

export const CLAVE_ALMACEN = 'huellita:v1';

export interface FiltroSugerencias {
  salaId?: string;
  ninoId?: string;
  estado?: EstadoSugerencia[];
}

export interface FiltroEvidencias {
  salaId?: string;
  ids?: string[];
}

export interface CambiosValidacion {
  ninoId?: string;
  nucleo?: NucleoId;
  nivel?: Nivel;
}

export interface DataService {
  /** Fecha "hoy" de la demo, inyectable para que todo sea reproducible. */
  hoy(): string;
  sesion(): Promise<Usuaria>;
  usuarias(): Promise<Usuaria[]>;
  /**
   * `false` mientras la demo no tiene usuaria elegida: la app muestra la
   * pantalla de entrada. En la Fase 2 lo reemplaza la sesión de Cognito.
   */
  usuariaElegida(): Promise<boolean>;
  cambiarUsuaria(id: string): Promise<void>;
  jardin(): Promise<Jardin>;
  /** Salas visibles para la usuaria actual (su sala, o el jardín si es directora). */
  salas(): Promise<Sala[]>;
  /**
   * Catálogo de salas del jardín (solo nombres, sin datos de niños/as). Lo usan
   * la pantalla de entrada de la demo y, más adelante, la vista directora.
   */
  salasDelJardin(): Promise<Sala[]>;
  salaActual(): Promise<Sala>;
  cambiarSala(id: string): Promise<void>;
  ninos(salaId: string): Promise<Nino[]>;
  nino(id: string): Promise<Nino>;
  /** En el orden en que llegaron (la última capturada al final). Revisar usa ese orden. */
  evidencias(filtro: FiltroEvidencias): Promise<Evidencia[]>;
  sugerencias(filtro: FiltroSugerencias): Promise<Sugerencia[]>;
  /** Guiones de la demo, que usa la IA simulada para foto y audio. */
  demoCapturas(): Promise<DemoCaptura[]>;
  guardarEvidencia(
    e: Omit<Evidencia, 'id' | 'creadaEn' | 'estado'>,
    archivo?: Blob,
  ): Promise<Evidencia>;
  marcarEvidencia(
    id: string,
    estado: Evidencia['estado'],
    textoExtraido?: string,
    foto?: string,
  ): Promise<void>;
  guardarSugerencias(s: Sugerencia[]): Promise<void>;
  validar(id: string, cambios?: CambiosValidacion): Promise<void>;
  descartar(id: string): Promise<void>;
  moverNino(ninoId: string, salaId: string): Promise<void>;
  darDeBaja(ninoId: string): Promise<void>;
  /** Avisa a la interfaz que los datos cambiaron. Devuelve la baja. */
  suscribir(cb: () => void): () => void;
  reiniciarDemo(): Promise<void>;
}

/** Almacenamiento mínimo, para poder probar sin navegador. */
export interface Almacen {
  leer(clave: string): string | null;
  escribir(clave: string, valor: string): void;
  borrar(clave: string): void;
}

export const almacenMemoria = (): Almacen => {
  const mapa = new Map<string, string>();
  return {
    leer: (c) => mapa.get(c) ?? null,
    escribir: (c, v) => void mapa.set(c, v),
    borrar: (c) => void mapa.delete(c),
  };
};

const almacenNavegador = (): Almacen => ({
  leer: (c) => {
    try {
      return window.localStorage.getItem(c);
    } catch {
      return null;
    }
  },
  escribir: (c, v) => {
    try {
      window.localStorage.setItem(c, v);
    } catch {
      /* modo privado o sin espacio: la demo sigue en memoria */
    }
  },
  borrar: (c) => {
    try {
      window.localStorage.removeItem(c);
    } catch {
      /* sin efecto */
    }
  },
});

function almacenPorDefecto(): Almacen {
  const hayNavegador = typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
  return hayNavegador ? almacenNavegador() : almacenMemoria();
}

/** Parte mutable de la demo. Lo demás (jardín, salas, guiones) viene de la semilla. */
interface EstadoGuardado {
  version: number;
  usuariaId: string;
  /** La tía ya eligió usuaria en la pantalla de entrada de la demo. */
  usuariaElegida: boolean;
  salaId: string;
  ninos: Nino[];
  evidencias: Evidencia[];
  sugerencias: Sugerencia[];
  /** Correlativo para los IDs nuevos de la sesión. */
  contador: number;
}

const semillaBase = semillaJson as unknown as Semilla;

function clonar<T>(valor: T): T {
  return JSON.parse(JSON.stringify(valor)) as T;
}

export interface OpcionesDataServiceLocal {
  semilla?: Semilla;
  almacen?: Almacen;
  /** Fecha "hoy"; por omisión, la `fechaDemo` de la semilla. */
  hoy?: string;
}

export class DataServiceLocal implements DataService {
  private readonly semilla: Semilla;
  private readonly almacen: Almacen;
  private readonly fechaHoy: string;
  private estado: EstadoGuardado;
  private readonly suscriptores = new Set<() => void>();
  /** Los archivos de foto y audio no salen del dispositivo ni se persisten. */
  private readonly archivos = new Map<string, Blob>();

  constructor(opciones: OpcionesDataServiceLocal = {}) {
    this.semilla = opciones.semilla ?? semillaBase;
    this.almacen = opciones.almacen ?? almacenPorDefecto();
    this.fechaHoy = opciones.hoy ?? this.semilla.fechaDemo;
    this.estado = this.leerEstado();
  }

  // --- estado -------------------------------------------------------------

  private estadoInicial(): EstadoGuardado {
    const primeraTia = this.semilla.usuarias.find((u) => u.rol === 'tia') ?? this.semilla.usuarias[0];
    return {
      version: this.semilla.version,
      usuariaId: primeraTia.id,
      usuariaElegida: false,
      salaId: primeraTia.salaIds[0] ?? this.semilla.salas[0].id,
      ninos: clonar(this.semilla.ninos),
      evidencias: clonar(this.semilla.evidencias),
      sugerencias: clonar(this.semilla.sugerencias),
      contador: 0,
    };
  }

  private leerEstado(): EstadoGuardado {
    const guardado = this.almacen.leer(CLAVE_ALMACEN);
    if (guardado) {
      try {
        const estado = JSON.parse(guardado) as EstadoGuardado;
        if (estado.version === this.semilla.version && Array.isArray(estado.sugerencias)) {
          return estado;
        }
      } catch {
        /* dato corrupto: se vuelve a la semilla */
      }
    }
    const inicial = this.estadoInicial();
    this.almacen.escribir(CLAVE_ALMACEN, JSON.stringify(inicial));
    return inicial;
  }

  private guardar(): void {
    this.almacen.escribir(CLAVE_ALMACEN, JSON.stringify(this.estado));
    for (const cb of this.suscriptores) cb();
  }

  private nuevoId(prefijo: string): string {
    this.estado.contador += 1;
    return `${prefijo}-L${String(this.estado.contador).padStart(5, '0')}`;
  }

  private usuariaActual(): Usuaria {
    const u = this.semilla.usuarias.find((x) => x.id === this.estado.usuariaId);
    if (!u) throw new Error('La usuaria de la demo no existe.');
    return u;
  }

  // --- sesión y catálogos -------------------------------------------------

  hoy(): string {
    return this.fechaHoy;
  }

  async sesion(): Promise<Usuaria> {
    return this.usuariaActual();
  }

  async usuarias(): Promise<Usuaria[]> {
    return this.semilla.usuarias;
  }

  async usuariaElegida(): Promise<boolean> {
    return this.estado.usuariaElegida === true;
  }

  async cambiarUsuaria(id: string): Promise<void> {
    const u = this.semilla.usuarias.find((x) => x.id === id);
    if (!u) throw new Error('Esa usuaria no existe.');
    this.estado.usuariaId = u.id;
    this.estado.usuariaElegida = true;
    if (!u.salaIds.includes(this.estado.salaId)) {
      this.estado.salaId = u.salaIds[0] ?? this.semilla.salas[0].id;
    }
    this.guardar();
  }

  async jardin(): Promise<Jardin> {
    return this.semilla.jardin;
  }

  async salas(): Promise<Sala[]> {
    const permitidas = new Set(this.usuariaActual().salaIds);
    return this.semilla.salas.filter((s) => permitidas.has(s.id));
  }

  async salasDelJardin(): Promise<Sala[]> {
    return clonar(this.semilla.salas);
  }

  async salaActual(): Promise<Sala> {
    const sala = this.semilla.salas.find((s) => s.id === this.estado.salaId);
    if (!sala) throw new Error('La sala de la demo no existe.');
    return sala;
  }

  async cambiarSala(id: string): Promise<void> {
    if (!this.usuariaActual().salaIds.includes(id)) {
      throw new Error('Esa sala no corresponde a la usuaria.');
    }
    this.estado.salaId = id;
    this.guardar();
  }

  async ninos(salaId: string): Promise<Nino[]> {
    return clonar(this.estado.ninos.filter((n) => n.salaId === salaId && n.activo));
  }

  async nino(id: string): Promise<Nino> {
    const n = this.estado.ninos.find((x) => x.id === id);
    if (!n) throw new Error('No encontramos a ese niño o niña.');
    return clonar(n);
  }

  async evidencias(filtro: FiltroEvidencias): Promise<Evidencia[]> {
    const ids = filtro.ids ? new Set(filtro.ids) : null;
    return clonar(
      this.estado.evidencias.filter(
        (e) => (!filtro.salaId || e.salaId === filtro.salaId) && (!ids || ids.has(e.id)),
      ),
    );
  }

  async sugerencias(filtro: FiltroSugerencias): Promise<Sugerencia[]> {
    const estados = filtro.estado ? new Set(filtro.estado) : null;
    return clonar(
      this.estado.sugerencias.filter(
        (s) =>
          (!filtro.salaId || s.salaId === filtro.salaId) &&
          (!filtro.ninoId || s.ninoId === filtro.ninoId) &&
          (!estados || estados.has(s.estado)),
      ),
    );
  }

  async demoCapturas(): Promise<DemoCaptura[]> {
    return this.semilla.demoCapturas;
  }

  // --- escritura ----------------------------------------------------------

  async guardarEvidencia(
    e: Omit<Evidencia, 'id' | 'creadaEn' | 'estado'>,
    archivo?: Blob,
  ): Promise<Evidencia> {
    const evidencia: Evidencia = {
      ...e,
      id: this.nuevoId('EVI'),
      creadaEn: this.ahoraISO(),
      estado: 'procesando',
    };
    this.estado.evidencias.push(evidencia);
    // El archivo queda solo en memoria: nunca se persiste (privacidad.md 3).
    if (archivo) this.archivos.set(evidencia.id, archivo);
    this.guardar();
    return clonar(evidencia);
  }

  async marcarEvidencia(
    id: string,
    estado: Evidencia['estado'],
    textoExtraido?: string,
    foto?: string,
  ): Promise<void> {
    const evidencia = this.estado.evidencias.find((x) => x.id === id);
    if (!evidencia) return;
    evidencia.estado = estado;
    if (textoExtraido !== undefined) evidencia.textoExtraido = textoExtraido;
    if (foto !== undefined) evidencia.foto = foto;
    if (estado !== 'procesando') this.archivos.delete(id);
    this.guardar();
  }

  async guardarSugerencias(s: Sugerencia[]): Promise<void> {
    for (const nueva of clonar(s)) {
      const i = this.estado.sugerencias.findIndex((x) => x.id === nueva.id);
      if (i >= 0) this.estado.sugerencias[i] = nueva;
      else this.estado.sugerencias.push(nueva);
    }
    this.guardar();
  }

  async validar(id: string, cambios?: CambiosValidacion): Promise<void> {
    const s = this.estado.sugerencias.find((x) => x.id === id);
    if (!s) throw new Error('Esa sugerencia ya no está.');

    const huboCambio =
      !!cambios &&
      ((cambios.ninoId !== undefined && cambios.ninoId !== s.ninoId) ||
        (cambios.nucleo !== undefined && cambios.nucleo !== s.nucleo) ||
        (cambios.nivel !== undefined && cambios.nivel !== s.nivel));

    if (huboCambio && cambios) {
      s.original = { ninoId: s.ninoId, nucleo: s.nucleo, nivel: s.nivel };
      if (cambios.ninoId !== undefined) s.ninoId = cambios.ninoId;
      if (cambios.nucleo !== undefined) s.nucleo = cambios.nucleo;
      if (cambios.nivel !== undefined) s.nivel = cambios.nivel;
    }

    s.estado = huboCambio ? 'cambiada' : 'aceptada';
    s.validadaPor = this.estado.usuariaId;
    s.validadaEn = this.ahoraISO();
    this.guardar();
  }

  async descartar(id: string): Promise<void> {
    const s = this.estado.sugerencias.find((x) => x.id === id);
    if (!s) return;
    s.estado = 'descartada';
    s.validadaPor = this.estado.usuariaId;
    s.validadaEn = this.ahoraISO();
    this.guardar();
  }

  async moverNino(ninoId: string, salaId: string): Promise<void> {
    const n = this.estado.ninos.find((x) => x.id === ninoId);
    if (!n) throw new Error('No encontramos a ese niño o niña.');
    n.salaId = salaId;
    this.guardar();
  }

  async darDeBaja(ninoId: string): Promise<void> {
    const n = this.estado.ninos.find((x) => x.id === ninoId);
    if (!n) throw new Error('No encontramos a ese niño o niña.');
    n.activo = false;
    this.guardar();
  }

  suscribir(cb: () => void): () => void {
    this.suscriptores.add(cb);
    return () => void this.suscriptores.delete(cb);
  }

  async reiniciarDemo(): Promise<void> {
    this.almacen.borrar(CLAVE_ALMACEN);
    this.archivos.clear();
    this.estado = this.estadoInicial();
    this.guardar();
  }

  /**
   * Marca de tiempo de la demo: el día de `fechaDemo` con la hora real, para que
   * las evidencias nuevas aparezcan como de hoy en el recorrido.
   */
  private ahoraISO(): string {
    const ahora = new Date();
    const hhmmss = [ahora.getHours(), ahora.getMinutes(), ahora.getSeconds()]
      .map((n) => String(n).padStart(2, '0'))
      .join(':');
    return `${this.fechaHoy}T${hhmmss}`;
  }
}

/** Instancia única que usan las pantallas en la Fase 1. */
export const servicioDatos: DataService = new DataServiceLocal();
