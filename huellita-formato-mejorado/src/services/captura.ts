/**
 * Captura de evidencias. Guarda la evidencia y manda a procesarla en segundo
 * plano: la tía vuelve de inmediato a lo que estaba haciendo y nunca espera a
 * la IA (requisito 1.5 e `interfaz.md`).
 */
import { evaluacionesDe, evaluacionesValidadas, nivelActualPorNucleo, nivelEsperado, edadMeses } from '../lib/evaluacion';
import { reducirFoto } from '../lib/fotos';
import type { Evidencia, Formato, Sugerencia } from '../lib/tipos';
import { servicioDatos, type DataService } from './datos';
import { servicioIA, type ContextoIA, type IAService } from './ia';

export interface ServiciosCaptura {
  datos: DataService;
  ia: IAService;
}

export interface ResultadoCaptura {
  /** Evidencia ya guardada, en estado `procesando`. */
  evidencia: Evidencia;
  /** Se cumple cuando la IA terminó. La interfaz no necesita esperarla. */
  procesada: Promise<Sugerencia[]>;
}

/**
 * Arma el contexto que recibe la IA: solo ID, nombre de pila y los niveles ya
 * calculados en el dispositivo. Nada de fecha de nacimiento ni datos de familia.
 */
async function contextoDeSala(datos: DataService, salaId: string): Promise<ContextoIA> {
  const hoy = datos.hoy();
  const [ninos, sugerencias, evidencias] = await Promise.all([
    datos.ninos(salaId),
    datos.sugerencias({ salaId }),
    datos.evidencias({ salaId }),
  ]);
  const evaluaciones = evaluacionesValidadas(sugerencias, evidencias);

  return {
    ninos: ninos.map((nino) => ({
      id: nino.id,
      nombre: nino.nombre,
      nivelesActuales: nivelActualPorNucleo(evaluacionesDe(evaluaciones, nino.id)),
      nivelEsperado: nivelEsperado(edadMeses(nino.fechaNacimiento, hoy)),
    })),
  };
}

/**
 * Captura una evidencia en la sala actual.
 * @param formato foto, audio o texto.
 * @param archivo foto o audio. El audio queda solo en memoria; la foto del
 *   post-it se guarda reducida en la evidencia para que la tía la vea.
 * @param texto lo que escribió la tía (solo en formato texto).
 * @param ninoId niño/a asociado si la captura empezó en su ficha.
 */
export async function capturar(
  formato: Formato,
  archivo?: Blob,
  texto?: string,
  ninoId?: string,
  servicios: ServiciosCaptura = { datos: servicioDatos, ia: servicioIA },
): Promise<ResultadoCaptura> {
  const { datos, ia } = servicios;
  const [usuaria, sala] = await Promise.all([datos.sesion(), datos.salaActual()]);

  const foto = formato === 'foto' && archivo ? await reducirFoto(archivo) : undefined;
  const evidencia = await datos.guardarEvidencia(
    {
      salaId: sala.id,
      autorId: usuaria.id,
      formato,
      ninoIdSugerido: ninoId,
      textoExtraido: texto?.trim() ? texto.trim() : undefined,
      ...(foto ? { foto } : {}),
    },
    archivo,
  );

  const procesada = (async () => {
    try {
      const contexto = await contextoDeSala(datos, sala.id);
      const sugerencias = await ia.procesar(evidencia, archivo, contexto);
      // Si la captura venía de una ficha, se respeta ese niño/a.
      const ajustadas = sugerencias.map((s) =>
        ninoId && s.tipo === 'evaluacion' && !s.ninoId ? { ...s, ninoId } : s,
      );
      await datos.guardarSugerencias(ajustadas);
      // Se guarda lo que se leyó. En la demo, si la nota venía de un guion con
      // foto de ejemplo, se usa esa foto para que calce con el texto leído.
      const lectura = ia.lecturaDe?.(evidencia.id);
      await datos.marcarEvidencia(evidencia.id, 'lista', lectura?.texto, lectura?.foto);
      return ajustadas;
    } catch {
      // Sin trazas técnicas ni datos de niños: la evidencia queda en error y
      // Revisar ofrece "Escribirla" o "Descartar".
      await datos.marcarEvidencia(evidencia.id, 'error');
      return [];
    }
  })();

  return { evidencia, procesada };
}
