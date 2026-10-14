export type AlertState =
  | "al_dia"
  | "sin_evidencia"
  | "posible_rezago"
  | "ingreso_reciente";

export interface Jardin {
  id_jardin: string;
  nombre_fantasia: string;
  comuna: string;
  region: string;
  numero_salas: number;
  numero_educadoras: number;
}

export interface Nino {
  id_nino: string;
  fecha_nacimiento: string;
  sexo_registrado: string;
  id_jardin: string;
  sala_grupo: string;
  fecha_ingreso: string;
}

export interface NinoEstado {
  nino: Nino;
  edad_meses: number;
  ultima_observacion: string | null;
  nivel_actual: number | null;
  estado: AlertState;
  dias_sin_evidencia: number | null;
}

export interface Observacion {
  id_observacion: string;
  id_nino: string;
  id_educadora: string;
  fecha_observacion: string;
  formato_captura: string;
  nivel_estimado: number;
  nota_breve: string | null;
}

export interface Alerta {
  id_nino: string;
  tipo: "sin_evidencia" | "posible_rezago";
  severidad: "media" | "alta";
  mensaje: string;
  accion_sugerida: string;
  nucleos_afectados: string[];
  confirmada: boolean;
}

export interface MisionItem {
  id_nino: string;
  motivo: string;
  dominio_sugerido: string | null;
  que_observar: string | null;
}

export interface NivelRuta {
  nivel: number;
  nombre_nivel: string;
  edad_min_meses: number;
  edad_max_meses: number;
  dominios: string[];
  descripcion: string;
}

export interface SugerenciaIA {
  id_nino_sugerido: string | null;
  nombre_detectado: string | null;
  es_evaluable: boolean;
  dominio: string | null;
  nivel_sugerido: number | null;
  manifestacion_sugerida: string | null;
  certeza: "alta" | "media" | "baja";
  evidencia: string;
}

export interface FichaNino {
  estado: NinoEstado;
  observaciones: Observacion[];
  alertas: Alerta[];
}
