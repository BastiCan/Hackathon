/**
 * Procesamiento de evidencias. En la Fase 1 todo es simulado y local: no sale
 * nada del dispositivo. En la Fase 3 esta misma interfaz la implementa Bedrock.
 *
 * Privacidad: al servicio solo se le pasa el texto de la evidencia y la lista de
 * nombres de pila con su ID. Nunca fecha de nacimiento, RUT ni datos de familia.
 */
import semillaJson from '@data/semilla.json';
import { celda, codigosNucleos, todasLasCeldas } from '../lib/rubrica';
import type {
  Certeza,
  DemoCaptura,
  Evidencia,
  Nivel,
  NucleoId,
  Semilla,
  Sugerencia,
} from '../lib/tipos';

/** Lo que la interfaz le cuenta a la IA de cada niño/a de la sala. */
export interface NinoContexto {
  id: string;
  /** Nombre de pila, para reconocerlo en la nota. */
  nombre: string;
  /** Nivel actual por núcleo, para proponer un nivel coherente (se calcula local). */
  nivelesActuales?: Partial<Record<NucleoId, Nivel | null>>;
  /** Nivel esperado por edad, por si el núcleo no tiene evidencia. */
  nivelEsperado?: Nivel;
}

export interface ContextoIA {
  ninos: NinoContexto[];
}

export interface IAService {
  procesar(
    evidencia: Evidencia,
    archivo: Blob | undefined,
    contexto: ContextoIA,
  ): Promise<Sugerencia[]>;
}

const LATENCIA_POR_DEFECTO_MS = 1500;

/** Palabras que no aportan para calzar una nota con la rúbrica. */
const VACIAS = new Set([
  'ante','anterior','antes','aqui','asi','aun','ayer','cada','casi','como','con','contra','cual','cuando',
  'cuanto','de','del','desde','donde','dos','durante','el','ella','ellas','ellos','en','entre','era','eran',
  'ese','eso','esa','esas','esos','esta','estaba','estan','este','esto','estos','fue','fueron','ha','hace',
  'hacia','han','hasta','hay','hoy','la','las','le','les','lo','los','mas','me','mi','mientras','muy','nos',
  'nuestra','nuestro','o','otra','otro','para','pero','por','porque','que','quien','se','segun','sin','sobre',
  'solo','son','su','sus','tambien','tan','tras','tu','un','una','uno','unos','unas','y','ya',
]);

/** Palabras que suelen abrir una oración y no son nombres propios. */
const INICIOS_COMUNES = new Set([
  'hoy','ayer','los','las','la','el','en','durante','se','cuando','despues','manana','al','un','una','esta',
  'este','estos','estas','todos','todas','tambien','ademas','hubo','para','por','mientras','luego','a',
]);

/** Señales de que la nota habla del grupo y no de un niño/a en particular. */
const SENALES_GRUPO = [
  'los ninos','las ninas','los ninos y ninas','el grupo','la sala','el curso','asistencia','todos',
  'todas','el equipo','como equipo','la jornada','la rutina del grupo',
];

function sinTildes(texto: string): string {
  return texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function normalizar(texto: string): string {
  return sinTildes(texto)
    .toLowerCase()
    .replace(/[^a-z0-9ñ]+/g, ' ')
    .trim();
}

function palabrasUtiles(texto: string): Set<string> {
  return new Set(
    normalizar(texto)
      .split(' ')
      .filter((p) => p.length >= 3 && !VACIAS.has(p)),
  );
}

/** Cuántas palabras con contenido comparten dos textos. */
function coincidencias(palabrasTexto: Set<string>, frase: string): number {
  let total = 0;
  for (const palabra of palabrasUtiles(frase)) if (palabrasTexto.has(palabra)) total += 1;
  return total;
}

/** Nombre de pila encontrado tal cual aparece en el texto. */
function mencionaNombre(texto: string, nombre: string): boolean {
  const palabras = normalizar(texto).split(' ');
  return palabras.includes(normalizar(nombre));
}

/** Posibles nombres propios que no están en la lista de la sala. */
function nombresDesconocidos(texto: string, nombresSala: string[]): string[] {
  const conocidos = new Set(nombresSala.map((n) => normalizar(n)));
  const encontrados: string[] = [];
  for (const bruto of texto.split(/[^\p{L}]+/u)) {
    if (bruto.length < 3) continue;
    const primera = bruto[0];
    if (primera !== primera.toLocaleUpperCase('es-CL')) continue;
    const clave = normalizar(bruto);
    if (!clave || conocidos.has(clave) || INICIOS_COMUNES.has(clave)) continue;
    if (!encontrados.includes(bruto)) encontrados.push(bruto);
  }
  return encontrados;
}

function hablaDelGrupo(texto: string): boolean {
  const plano = ` ${normalizar(texto)} `;
  return SENALES_GRUPO.some((senal) => plano.includes(` ${normalizar(senal)} `));
}

/** Celda de la rúbrica con más palabras en común con el texto. */
function mejorCelda(texto: string): { nucleo: NucleoId; nivel: Nivel; puntaje: number } {
  const palabras = palabrasUtiles(texto);
  let mejor = { nucleo: codigosNucleos()[0], nivel: 1 as Nivel, puntaje: -1 };
  for (const c of todasLasCeldas()) {
    let puntaje = coincidencias(palabras, c.descriptor);
    for (const conducta of c.conductas) {
      puntaje = Math.max(puntaje, coincidencias(palabras, conducta) * 2);
    }
    if (puntaje > mejor.puntaje) mejor = { nucleo: c.nucleo, nivel: c.nivel, puntaje };
  }
  return mejor;
}

/** Conducta del núcleo y nivel elegidos que mejor calza con el texto. */
function mejorConducta(nucleo: NucleoId, nivel: Nivel, texto: string): string {
  const palabras = palabrasUtiles(texto);
  const lista = celda(nucleo, nivel).conductas;
  let elegida = lista[0];
  let mejor = -1;
  for (const conducta of lista) {
    const puntaje = coincidencias(palabras, conducta);
    if (puntaje > mejor) {
      mejor = puntaje;
      elegida = conducta;
    }
  }
  return elegida;
}

/** Fragmento literal del texto que respalda la sugerencia (la oración del nombre). */
function citaDe(texto: string, nombre?: string): string {
  const oraciones = texto.split(/(?<=[.!?])\s+/).filter((o) => o.trim().length > 0);
  if (nombre) {
    const conNombre = oraciones.find((o) => mencionaNombre(o, nombre));
    if (conNombre) return conNombre.trim();
  }
  return (oraciones[0] ?? texto).trim();
}

function esperar(ms: number): Promise<void> {
  return ms > 0 ? new Promise((listo) => setTimeout(listo, ms)) : Promise.resolve();
}

export interface OpcionesIASimulada {
  /** Guiones de la demo para foto y audio. */
  guiones?: DemoCaptura[];
  /** Latencia simulada; 0 en las pruebas. */
  latenciaMs?: number;
  /** Mínimo de palabras en común para considerar la conducta reconocible. */
  umbralConducta?: number;
}

/**
 * IA simulada de la Fase 1. Devuelve sugerencias usando los guiones de la demo
 * o, si la nota es libre, buscando nombres de la sala y conductas de la rúbrica.
 */
export class IAServiceSimulado implements IAService {
  private readonly guiones: DemoCaptura[];
  private readonly latenciaMs: number;
  private readonly umbral: number;
  private readonly guionesUsados = new Set<number>();

  constructor(opciones: OpcionesIASimulada = {}) {
    const semilla = semillaJson as unknown as Semilla;
    this.guiones = opciones.guiones ?? semilla.demoCapturas;
    this.latenciaMs = opciones.latenciaMs ?? LATENCIA_POR_DEFECTO_MS;
    this.umbral = opciones.umbralConducta ?? 2;
  }

  async procesar(
    evidencia: Evidencia,
    _archivo: Blob | undefined,
    contexto: ContextoIA,
  ): Promise<Sugerencia[]> {
    await esperar(this.latenciaMs);

    // 1. Foto o audio sin texto: se usa el siguiente guion pendiente de la demo.
    let texto = evidencia.textoExtraido?.trim() ?? '';
    if (!texto) {
      const guion = this.siguienteGuion(evidencia.formato);
      if (!guion) {
        return [this.notaDeSala(evidencia, 'No pudimos leer esta nota.', 'baja')];
      }
      texto = guion.texto;
    }

    // 2. Si el texto es un guion de la demo, se devuelven sus sugerencias.
    const guionCalzado = this.guiones.find((g) => normalizar(g.texto) === normalizar(texto));
    if (guionCalzado) return this.desdeGuion(evidencia, guionCalzado, texto);

    // 3. Nota libre: se buscan nombres de la sala.
    const mencionados = contexto.ninos.filter((n) => mencionaNombre(texto, n.nombre));
    if (mencionados.length > 0) {
      return mencionados.map((nino, i) => this.evaluacionDe(evidencia, texto, nino, i));
    }

    // 4. Nombre que no es de la sala: queda "por confirmar" con certeza baja.
    const desconocidos = nombresDesconocidos(
      texto,
      contexto.ninos.map((n) => n.nombre),
    );
    if (desconocidos.length > 0 && !hablaDelGrupo(texto)) {
      return desconocidos.map((nombre, i) => this.porConfirmar(evidencia, texto, nombre, i));
    }

    // 5. Grupo o nota no evaluativa.
    return [this.notaDeSala(evidencia, citaDe(texto), 'alta')];
  }

  private siguienteGuion(formato: Evidencia['formato']): DemoCaptura | null {
    const indices = this.guiones.map((_, i) => i);
    const libre =
      indices.find((i) => !this.guionesUsados.has(i) && this.guiones[i].formato === formato) ??
      indices.find((i) => !this.guionesUsados.has(i));
    if (libre === undefined) {
      // Se agotaron los guiones: la demo vuelve a empezar.
      this.guionesUsados.clear();
      const reinicio =
        indices.find((i) => this.guiones[i].formato === formato) ?? indices[0] ?? undefined;
      if (reinicio === undefined) return null;
      this.guionesUsados.add(reinicio);
      return this.guiones[reinicio];
    }
    this.guionesUsados.add(libre);
    return this.guiones[libre];
  }

  private id(evidencia: Evidencia, indice: number): string {
    return `SUG-${evidencia.id}-${indice + 1}`;
  }

  private desdeGuion(evidencia: Evidencia, guion: DemoCaptura, texto: string): Sugerencia[] {
    return guion.sugerencias.map((s, i) => ({
      id: this.id(evidencia, i),
      evidenciaId: evidencia.id,
      salaId: evidencia.salaId,
      tipo: s.tipo,
      ninoId: s.ninoId,
      nombreDetectado: s.nombreDetectado,
      nucleo: s.nucleo,
      nivel: s.nivel,
      conducta: s.conducta,
      cita: s.cita || citaDe(texto, s.nombreDetectado),
      certeza: s.certeza,
      estado: 'pendiente',
    }));
  }

  private evaluacionDe(
    evidencia: Evidencia,
    texto: string,
    nino: NinoContexto,
    indice: number,
  ): Sugerencia {
    const mejor = mejorCelda(texto);
    const nucleo = mejor.nucleo;
    const nivelActual = nino.nivelesActuales?.[nucleo] ?? null;
    const nivel: Nivel = nivelActual ?? nino.nivelEsperado ?? mejor.nivel;
    const conductaReconocible = mejor.puntaje >= this.umbral;
    // Certeza (rubrica.md): nombre exacto de la sala + conducta reconocible → alta.
    const certeza: Certeza = conductaReconocible ? 'alta' : 'media';

    return {
      id: this.id(evidencia, indice),
      evidenciaId: evidencia.id,
      salaId: evidencia.salaId,
      tipo: 'evaluacion',
      ninoId: nino.id,
      nombreDetectado: nino.nombre,
      nucleo,
      nivel,
      conducta: mejorConducta(nucleo, nivel, texto),
      cita: citaDe(texto, nino.nombre),
      certeza,
      estado: 'pendiente',
    };
  }

  private porConfirmar(
    evidencia: Evidencia,
    texto: string,
    nombre: string,
    indice: number,
  ): Sugerencia {
    const { nucleo, nivel } = mejorCelda(texto);
    return {
      id: this.id(evidencia, indice),
      evidenciaId: evidencia.id,
      salaId: evidencia.salaId,
      tipo: 'evaluacion',
      ninoId: undefined,
      nombreDetectado: nombre,
      nucleo,
      nivel,
      conducta: mejorConducta(nucleo, nivel, texto),
      cita: citaDe(texto, nombre),
      certeza: 'baja',
      estado: 'pendiente',
    };
  }

  private notaDeSala(evidencia: Evidencia, cita: string, certeza: Certeza): Sugerencia {
    return {
      id: this.id(evidencia, 0),
      evidenciaId: evidencia.id,
      salaId: evidencia.salaId,
      tipo: 'nota_sala',
      cita,
      certeza,
      estado: 'pendiente',
    };
  }
}

/** Instancia única que usan las pantallas en la Fase 1. */
export const servicioIA: IAService = new IAServiceSimulado();
