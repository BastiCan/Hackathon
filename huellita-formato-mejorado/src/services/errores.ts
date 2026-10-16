/**
 * Errores que se pueden mostrar tal cual a la tía: en sus palabras, sin trazas
 * técnicas ni detalles de AWS (privacidad.md). Cualquier otro error se muestra
 * con un mensaje genérico de la pantalla.
 */
export class ErrorParaTia extends Error {
  constructor(
    mensaje: string,
    /** Código del servicio (por ejemplo `tope_diario`), para las pruebas y la interfaz. */
    readonly codigo?: string,
    /** Estado HTTP de la respuesta, si vino del servidor. */
    readonly estado?: number,
  ) {
    super(mensaje);
    this.name = 'ErrorParaTia';
  }
}

/** El mensaje del error si es para la tía; si no, el de la pantalla. */
export function mensajeParaTia(error: unknown, porDefecto: string): string {
  return error instanceof ErrorParaTia ? error.message : porDefecto;
}
