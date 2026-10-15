/**
 * Tipos de dominio de Huellita (ver `.kiro/specs/app-tias/design.md`).
 * Los nombres de dominio van en español: niño, sala, núcleo, evidencia.
 */

/** Códigos de los 8 núcleos de las BCEP 2018. La lista viva se carga de la rúbrica. */
export type NucleoId = 'IA' | 'CC' | 'CM' | 'LV' | 'LA' | 'EN' | 'ES' | 'PM';

/** Niveles de la rúbrica de Integra (1 Comenzando … 8 Profundizando). */
export type Nivel = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

export type Rol = 'tia' | 'directora';
export type Formato = 'foto' | 'audio' | 'texto';
export type Certeza = 'alta' | 'media' | 'baja';
export type EstadoSugerencia = 'pendiente' | 'aceptada' | 'cambiada' | 'descartada';
export type EstadoEvidencia = 'procesando' | 'lista' | 'error';

export type NivelEducativo =
  | 'Sala Cuna Menor'
  | 'Sala Cuna Mayor'
  | 'Medio Menor'
  | 'Medio Mayor'
  | 'Transición 1'
  | 'Transición 2';

export interface Jardin {
  id: string;
  nombre: string;
  comuna: string;
  region: string;
}

export interface Sala {
  id: string;
  jardinId: string;
  nombre: string;
  nivelEducativo: NivelEducativo;
}

export interface Usuaria {
  id: string;
  nombre: string;
  rol: Rol;
  jardinId: string;
  salaIds: string[];
}

export interface Nino {
  id: string;
  nombre: string;
  apellidoInicial: string;
  /** ISO `YYYY-MM-DD`. Nunca se envía a la IA (ver privacidad.md). */
  fechaNacimiento: string;
  salaId: string;
  activo: boolean;
}

export interface Evidencia {
  id: string;
  salaId: string;
  autorId: string;
  /** ISO. Fecha en que la tía observó y registró. */
  creadaEn: string;
  formato: Formato;
  ninoIdSugerido?: string;
  /** Texto leído del post-it, transcrito del audio o escrito por la tía. */
  textoExtraido?: string;
  /**
   * Foto del post-it o de la nota: URL de datos (JPEG reducido en el
   * dispositivo) o la clave de una foto de ejemplo de la demo. Solo fotos de
   * notas; las fotos con caras de niños/as se difuminan antes de guardarse
   * (privacidad.md 2).
   */
  foto?: string;
  estado: EstadoEvidencia;
}

export interface Sugerencia {
  id: string;
  evidenciaId: string;
  salaId: string;
  tipo: 'evaluacion' | 'nota_sala';
  /** `undefined` si es nota de sala o si el nombre no se reconoció. */
  ninoId?: string;
  /** Nombre tal como aparece en la evidencia. */
  nombreDetectado?: string;
  nucleo?: NucleoId;
  nivel?: Nivel;
  /** Conducta observable copiada de la rúbrica. */
  conducta?: string;
  /** Fragmento literal de la evidencia que respalda la sugerencia. */
  cita: string;
  certeza: Certeza;
  estado: EstadoSugerencia;
  validadaPor?: string;
  validadaEn?: string;
  /** Valores propuestos por la IA, si la tía los cambió. */
  original?: { ninoId?: string; nucleo?: NucleoId; nivel?: Nivel };
}

/**
 * Evaluación validada: sugerencia de tipo `evaluacion` aceptada o cambiada por
 * una tía, con la fecha de la evidencia que la originó. Solo estas cuentan para
 * niveles, frescura y banderas.
 */
export interface EvaluacionValidada {
  sugerenciaId: string;
  evidenciaId: string;
  ninoId: string;
  salaId: string;
  nucleo: NucleoId;
  nivel: Nivel;
  /** ISO. Fecha de la evidencia (no la de validación). */
  fecha: string;
  conducta?: string;
  cita: string;
  validadaPor?: string;
}

/** Un nivel de la rúbrica con su rango de edad orientativa en meses. */
export interface NivelInfo {
  nivel: Nivel;
  nombre: string;
  tramo: string;
  grupoOrientativo: string;
  /** Inclusivo. */
  edadDesdeMeses: number;
  /** Exclusivo (el último nivel no tiene techo efectivo). */
  edadHastaMeses: number;
  edadOrientativa: string;
}

/** Un núcleo de la rúbrica (configuración cargada desde datos). */
export interface NucleoInfo {
  codigo: NucleoId;
  nombre: string;
  ambito: string;
}

/** Contenido de un núcleo en un nivel. */
export interface CeldaRubrica {
  nucleo: NucleoId;
  nivel: Nivel;
  nombreNivel: string;
  descriptor: string;
  conductas: string[];
  oaReferencia: string[];
}

export type ColorFrescura = 'verde' | 'amarillo' | 'rojo';

export interface SugerenciaObservacion {
  nucleo: NucleoId;
  nivel: Nivel;
  conductas: string[];
}

export interface ResumenSala {
  observadosMes: number;
  total: number;
  nucleoMenosCubierto: NucleoId | null;
}

/** Sugerencia predefinida de un guion de demo (`semilla.demoCapturas`). */
export interface SugerenciaDemo {
  tipo: 'evaluacion' | 'nota_sala';
  ninoId?: string;
  nombreDetectado?: string;
  nucleo?: NucleoId;
  nivel?: Nivel;
  conducta?: string;
  cita: string;
  certeza: Certeza;
}

/** Guion de captura para que la demo sea reproducible. */
export interface DemoCaptura {
  formato: Formato;
  texto: string;
  /** Clave de la foto de ejemplo del post-it (ver `lib/fotos.ts`). */
  foto?: string;
  sugerencias: SugerenciaDemo[];
}

/** Contenido de `data/semilla.json`. */
export interface Semilla {
  version: number;
  nota: string;
  /** Fecha "hoy" de la demo (ISO `YYYY-MM-DD`). */
  fechaDemo: string;
  jardin: Jardin;
  salas: Sala[];
  usuarias: Usuaria[];
  ninos: Nino[];
  evidencias: Evidencia[];
  sugerencias: Sugerencia[];
  demoCapturas: DemoCaptura[];
}
