/**
 * Datos de la Fase 2: la misma interfaz `DataService`, pero contra el BFF de
 * AWS en `/api` (mismo origen que la app, ver `app/config.ts`). Las pantallas
 * no cambian: siguen pidiendo `useServicios()`.
 *
 * Lo que distingue esta versión de la local:
 * - el servidor procesa las notas (`procesaEnServidor`), así que la captura no
 *   llama a la IA del dispositivo;
 * - mientras haya notas en `procesando`, `suscribir` consulta los registros
 *   cada `INTERVALO_SONDEO_MS`; cuando no queda ninguna, el sondeo se detiene;
 * - las decisiones de Revisar se pisan primero en el caché (la tía ve el
 *   cambio de inmediato) y, si la llamada falla, se vuelven atrás.
 *
 * Contratos: `huellita-web/SPEC-OFICIAL.md` §1 (manda) y `CONTRATOS.md` §9.
 */
import { CONFIG, MAX_BYTES_AUDIO } from '../app/config';
import { reducirFoto } from '../lib/fotos';
import type {
  DemoCaptura,
  Evidencia,
  Jardin,
  Nino,
  Nivel,
  NucleoId,
  Sala,
  Sugerencia,
  Usuaria,
} from '../lib/tipos';
import {
  almacenMemoria,
  type Almacen,
  type CambiosValidacion,
  type DataService,
  type FiltroEvidencias,
  type FiltroSugerencias,
} from './datos';
import { ErrorParaTia } from './errores';

/** Mismo origen que la app: CloudFront manda `/api/*` al BFF. */
export const BASE = '/api';
/** La usuaria de la demo viaja en una cabecera, no en una cookie. */
export const CABECERA_USUARIA = 'X-Usuaria-Id';
/** Cada cuánto se consultan los registros mientras algo está procesando. */
export const INTERVALO_SONDEO_MS = 5000;
/** Clave de `localStorage` con la usuaria y la sala elegidas. */
export const CLAVE_SESION = 'huellita:aws:v1';
/** Bloque máximo para `String.fromCharCode`: más que esto desborda la pila. */
export const BLOQUE_BASE64 = 0x8000;
/** Tope de caracteres de una nota escrita (lo mismo valida el BFF). */
export const MAX_CARACTERES_TEXTO = 5000;
/**
 * Tope del base64 de la foto ya reducida. El BFF rechaza más de ~5.5 MiB de
 * imagen decodificada; con el margen del base64 (4/3) este tope deja la foto
 * holgadamente bajo ese límite y evita gastar el viaje con una imagen enorme.
 */
export const MAX_BASE64_FOTO = Math.floor(5.5 * 1024 * 1024);

/** Zona horaria de la demo, la misma que usa el BFF. */
const ZONA_HORARIA = 'America/Santiago';

/** Lo que se le dice a la tía cuando la respuesta no trae un error entendible. */
const MENSAJE_GENERICO = 'No pudimos guardar esto. Intenta de nuevo.';

// --- base64 ---------------------------------------------------------------

/**
 * Pasa los bytes a base64 **por bloques** de `BLOQUE_BASE64`: un audio de
 * minutos son millones de bytes y `String.fromCharCode(...todos)` desborda la
 * pila del navegador.
 */
export function aBase64(bytes: Uint8Array): string {
  const partes: string[] = [];
  for (let desde = 0; desde < bytes.length; desde += BLOQUE_BASE64) {
    partes.push(String.fromCharCode(...bytes.subarray(desde, desde + BLOQUE_BASE64)));
  }
  return btoa(partes.join(''));
}

/** El audio grabado, listo para viajar en el JSON de la captura. */
export async function blobABase64(blob: Blob): Promise<string> {
  return aBase64(new Uint8Array(await blob.arrayBuffer()));
}

// --- cuerpos de la API ----------------------------------------------------

interface RespuestaContexto {
  jardin: Jardin;
  salas: Sala[];
  usuarias: Usuaria[];
}

interface RespuestaRegistros {
  evidencias: Evidencia[];
  sugerencias: Sugerencia[];
}

interface CambiosCompletos {
  ninoId: string;
  nucleo: NucleoId;
  nivel: Nivel;
}

interface ItemDecision {
  idSugerencia: string;
  estado: 'aceptada' | 'descartada' | 'pendiente';
  cambios?: CambiosCompletos;
}

interface SesionLocal {
  usuariaId: string;
  salaId: string;
  elegida: boolean;
}

const SESION_VACIA: SesionLocal = { usuariaId: '', salaId: '', elegida: false };

// --- utilidades -----------------------------------------------------------

function almacenNavegador(): Almacen {
  return {
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
        /* modo privado o sin espacio: la sesión queda en memoria */
      }
    },
    borrar: (c) => {
      try {
        window.localStorage.removeItem(c);
      } catch {
        /* sin efecto */
      }
    },
  };
}

function almacenPorDefecto(): Almacen {
  const hayNavegador = typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
  return hayNavegador ? almacenNavegador() : almacenMemoria();
}

/** Fecha de hoy en Chile (`AAAA-MM-DD`), como la calcula el BFF con `zoneinfo`. */
function hoyEnChile(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: ZONA_HORARIA }).format(new Date());
}

/** El error del BFF viene como `{"error": {"codigo", "mensaje"}}`. */
function errorDeRespuesta(cuerpo: unknown, estado: number): ErrorParaTia {
  const detalle = (cuerpo as { error?: { codigo?: unknown; mensaje?: unknown } } | null)?.error;
  const mensaje =
    typeof detalle?.mensaje === 'string' && detalle.mensaje.trim() !== ''
      ? detalle.mensaje
      : MENSAJE_GENERICO;
  const codigo = typeof detalle?.codigo === 'string' ? detalle.codigo : undefined;
  return new ErrorParaTia(mensaje, codigo, estado);
}

/**
 * Misma regla que `DataServiceLocal.validar` (regla 7): si algo cambió respecto
 * de lo que propuso la IA, la sugerencia queda `cambiada` y se guarda el
 * `original`. Se usa para pintar el cambio antes de que conteste el servidor.
 */
function validadaLocal(
  s: Sugerencia,
  cambios: CambiosValidacion | undefined,
  usuariaId: string,
  cuando: string,
): Sugerencia {
  const huboCambio =
    !!cambios &&
    ((cambios.ninoId !== undefined && cambios.ninoId !== s.ninoId) ||
      (cambios.nucleo !== undefined && cambios.nucleo !== s.nucleo) ||
      (cambios.nivel !== undefined && cambios.nivel !== s.nivel));

  const nueva: Sugerencia = { ...s };
  if (huboCambio && cambios) {
    nueva.original = { ninoId: s.ninoId, nucleo: s.nucleo, nivel: s.nivel };
    if (cambios.ninoId !== undefined) nueva.ninoId = cambios.ninoId;
    if (cambios.nucleo !== undefined) nueva.nucleo = cambios.nucleo;
    if (cambios.nivel !== undefined) nueva.nivel = cambios.nivel;
  }
  nueva.estado = huboCambio ? 'cambiada' : 'aceptada';
  nueva.validadaPor = usuariaId;
  nueva.validadaEn = cuando;
  return nueva;
}

/**
 * `cambios` completo para el BFF: necesita los tres campos. Lo que no venga en
 * la corrección se toma de la sugerencia; si falta alguno, no se manda nada y
 * la decisión queda como una aceptación simple.
 */
function cambiosCompletos(
  s: Sugerencia | undefined,
  cambios: CambiosValidacion | undefined,
): CambiosCompletos | undefined {
  if (!cambios) return undefined;
  const ninoId = cambios.ninoId ?? s?.ninoId;
  const nucleo = cambios.nucleo ?? s?.nucleo;
  const nivel = cambios.nivel ?? s?.nivel;
  if (!ninoId || !nucleo || !nivel) return undefined;
  return { ninoId, nucleo, nivel };
}

/** Un ítem de `PUT /api/decisiones` por cada estado de sugerencia. */
function itemDeSugerencia(s: Sugerencia): ItemDecision {
  if (s.estado === 'descartada') return { idSugerencia: s.id, estado: 'descartada' };
  // `pendiente` borra la decisión guardada: es el camino de Deshacer.
  if (s.estado === 'pendiente') return { idSugerencia: s.id, estado: 'pendiente' };
  const cambios =
    s.estado === 'cambiada'
      ? cambiosCompletos(s, { ninoId: s.ninoId, nucleo: s.nucleo, nivel: s.nivel })
      : undefined;
  return { idSugerencia: s.id, estado: 'aceptada', ...(cambios ? { cambios } : {}) };
}

export interface OpcionesDataServiceHttp {
  /** Dónde se recuerda la usuaria elegida; en memoria en las pruebas. */
  almacen?: Almacen;
  /** Raíz de la API; por omisión `/api`. */
  base?: string;
}

// --- el servicio ----------------------------------------------------------

export class DataServiceHttp implements DataService {
  /** El BFF procesa la nota: la captura no llama a la IA del dispositivo. */
  readonly procesaEnServidor = true;
  /** La versión AWS ya recibe fotos de post-it: el BFF las lee con el OCR. */
  readonly admiteFoto = true;

  private readonly almacen: Almacen;
  private readonly base: string;
  private readonly suscriptores = new Set<() => void>();

  private sesionLocal: SesionLocal;
  private contextoGuardado: RespuestaContexto | null = null;
  private contextoEnVuelo: Promise<RespuestaContexto> | null = null;
  private readonly registrosPorSala = new Map<string, RespuestaRegistros>();
  private readonly registrosEnVuelo = new Map<string, Promise<RespuestaRegistros>>();
  private readonly ninosPorSala = new Map<string, Nino[]>();
  private readonly ninosEnVuelo = new Map<string, Promise<Nino[]>>();
  private readonly ninosPorId = new Map<string, Nino>();
  private sondeo: ReturnType<typeof setInterval> | null = null;

  constructor(opciones: OpcionesDataServiceHttp = {}) {
    this.almacen = opciones.almacen ?? almacenPorDefecto();
    this.base = opciones.base ?? BASE;
    this.sesionLocal = this.leerSesion();
  }

  // --- sesión local -------------------------------------------------------

  private leerSesion(): SesionLocal {
    const guardado = this.almacen.leer(CLAVE_SESION);
    if (guardado) {
      try {
        const leida = JSON.parse(guardado) as Partial<SesionLocal>;
        return {
          usuariaId: typeof leida.usuariaId === 'string' ? leida.usuariaId : '',
          salaId: typeof leida.salaId === 'string' ? leida.salaId : '',
          elegida: leida.elegida === true,
        };
      } catch {
        /* dato corrupto: se parte de cero */
      }
    }
    return { ...SESION_VACIA };
  }

  private escribirSesion(sesion: SesionLocal): void {
    this.sesionLocal = sesion;
    this.almacen.escribir(CLAVE_SESION, JSON.stringify(sesion));
  }

  /** Sin usuaria elegida todavía, se parte de la primera tía del jardín. */
  private asegurarSesion(contexto: RespuestaContexto): void {
    if (this.sesionLocal.usuariaId && this.sesionLocal.salaId) return;
    const tia =
      contexto.usuarias.find((u) => u.id === this.sesionLocal.usuariaId) ??
      contexto.usuarias.find((u) => u.rol === 'tia') ??
      contexto.usuarias[0];
    if (!tia) return;
    this.sesionLocal = {
      usuariaId: this.sesionLocal.usuariaId || tia.id,
      salaId: this.sesionLocal.salaId || tia.salaIds[0] || contexto.salas[0]?.id || '',
      elegida: this.sesionLocal.elegida,
    };
  }

  private notificar(): void {
    for (const cb of this.suscriptores) cb();
  }

  // --- llamadas -----------------------------------------------------------

  private async pedir<T>(
    ruta: string,
    opciones: { metodo?: string; cuerpo?: unknown } = {},
  ): Promise<T> {
    const cabeceras: Record<string, string> = {};
    if (this.sesionLocal.usuariaId) cabeceras[CABECERA_USUARIA] = this.sesionLocal.usuariaId;
    if (opciones.cuerpo !== undefined) cabeceras['Content-Type'] = 'application/json';

    let respuesta: Response;
    try {
      respuesta = await fetch(`${this.base}${ruta}`, {
        method: opciones.metodo ?? 'GET',
        headers: cabeceras,
        ...(opciones.cuerpo !== undefined ? { body: JSON.stringify(opciones.cuerpo) } : {}),
      });
    } catch {
      // Sin conexión o servidor caído: nada técnico para la tía.
      throw new ErrorParaTia(MENSAJE_GENERICO);
    }

    let crudo = '';
    if (respuesta.status !== 204) {
      try {
        crudo = await respuesta.text();
      } catch {
        crudo = '';
      }
    }
    let cuerpo: unknown = null;
    if (crudo !== '') {
      try {
        cuerpo = JSON.parse(crudo);
      } catch {
        cuerpo = null;
      }
    }

    if (!respuesta.ok) throw errorDeRespuesta(cuerpo, respuesta.status);
    return cuerpo as T;
  }

  private contexto(): Promise<RespuestaContexto> {
    if (this.contextoGuardado) return Promise.resolve(this.contextoGuardado);
    if (!this.contextoEnVuelo) {
      const enVuelo = this.pedir<RespuestaContexto>('/contexto').then((contexto) => {
        this.contextoGuardado = contexto;
        this.asegurarSesion(contexto);
        return contexto;
      });
      enVuelo.catch(() => {
        if (this.contextoEnVuelo === enVuelo) this.contextoEnVuelo = null;
      });
      this.contextoEnVuelo = enVuelo;
    }
    return this.contextoEnVuelo;
  }

  /** Último `GET /api/salas/{salaId}/registros`; se pide una sola vez por sala. */
  private registros(salaId: string, forzar = false): Promise<RespuestaRegistros> {
    if (!salaId) return Promise.resolve({ evidencias: [], sugerencias: [] });
    if (!forzar) {
      const guardados = this.registrosPorSala.get(salaId);
      if (guardados) return Promise.resolve(guardados);
      const enCurso = this.registrosEnVuelo.get(salaId);
      if (enCurso) return enCurso;
    }
    const enVuelo = this.pedir<RespuestaRegistros>(`/salas/${salaId}/registros`).then(
      (respuesta) => {
        const registros: RespuestaRegistros = {
          evidencias: respuesta.evidencias ?? [],
          sugerencias: respuesta.sugerencias ?? [],
        };
        this.registrosPorSala.set(salaId, registros);
        return registros;
      },
    );
    const limpiar = () => {
      if (this.registrosEnVuelo.get(salaId) === enVuelo) this.registrosEnVuelo.delete(salaId);
    };
    enVuelo.then(limpiar, limpiar);
    this.registrosEnVuelo.set(salaId, enVuelo);
    return enVuelo;
  }

  private salaDeSugerencia(id: string): string {
    for (const [salaId, registros] of this.registrosPorSala) {
      if (registros.sugerencias.some((s) => s.id === id)) return salaId;
    }
    return this.sesionLocal.salaId;
  }

  private sugerenciaGuardada(id: string): Sugerencia | undefined {
    for (const registros of this.registrosPorSala.values()) {
      const encontrada = registros.sugerencias.find((s) => s.id === id);
      if (encontrada) return encontrada;
    }
    return undefined;
  }

  // --- sesión y catálogos -------------------------------------------------

  hoy(): string {
    return CONFIG.fechaHoy ?? hoyEnChile();
  }

  async sesion(): Promise<Usuaria> {
    const contexto = await this.contexto();
    const usuaria =
      contexto.usuarias.find((u) => u.id === this.sesionLocal.usuariaId) ??
      contexto.usuarias.find((u) => u.rol === 'tia') ??
      contexto.usuarias[0];
    if (!usuaria) throw new ErrorParaTia('No pudimos cargar tu sesión.');
    return usuaria;
  }

  async usuarias(): Promise<Usuaria[]> {
    return (await this.contexto()).usuarias;
  }

  async usuariaElegida(): Promise<boolean> {
    return this.sesionLocal.elegida === true;
  }

  async cambiarUsuaria(id: string): Promise<void> {
    const contexto = await this.contexto();
    const usuaria = contexto.usuarias.find((u) => u.id === id);
    if (!usuaria) throw new ErrorParaTia('Esa usuaria no existe.');
    const salaId = usuaria.salaIds.includes(this.sesionLocal.salaId)
      ? this.sesionLocal.salaId
      : usuaria.salaIds[0] ?? contexto.salas[0]?.id ?? '';
    this.escribirSesion({ usuariaId: usuaria.id, salaId, elegida: true });
    // Lo cacheado es de la usuaria anterior.
    this.registrosPorSala.clear();
    this.ninosPorSala.clear();
    this.notificar();
  }

  async jardin(): Promise<Jardin> {
    return (await this.contexto()).jardin;
  }

  async salas(): Promise<Sala[]> {
    const contexto = await this.contexto();
    const usuaria = await this.sesion();
    const permitidas = new Set(usuaria.salaIds);
    return contexto.salas.filter((s) => permitidas.has(s.id));
  }

  async salasDelJardin(): Promise<Sala[]> {
    return (await this.contexto()).salas;
  }

  async salaActual(): Promise<Sala> {
    const contexto = await this.contexto();
    const sala =
      contexto.salas.find((s) => s.id === this.sesionLocal.salaId) ?? contexto.salas[0];
    if (!sala) throw new ErrorParaTia('No pudimos cargar tu sala.');
    return sala;
  }

  async cambiarSala(id: string): Promise<void> {
    const usuaria = await this.sesion();
    if (!usuaria.salaIds.includes(id)) {
      throw new ErrorParaTia('Esa sala no corresponde a la usuaria.');
    }
    this.escribirSesion({ ...this.sesionLocal, salaId: id });
    this.notificar();
  }

  async ninos(salaId: string): Promise<Nino[]> {
    const guardados = this.ninosPorSala.get(salaId);
    if (guardados) return guardados;
    const enCurso = this.ninosEnVuelo.get(salaId);
    if (enCurso) return enCurso;
    const enVuelo = this.pedir<Nino[]>(`/salas/${salaId}/ninos`).then((lista) => {
      const ninos = lista ?? [];
      this.ninosPorSala.set(salaId, ninos);
      for (const nino of ninos) this.ninosPorId.set(nino.id, nino);
      return ninos;
    });
    const limpiar = () => {
      if (this.ninosEnVuelo.get(salaId) === enVuelo) this.ninosEnVuelo.delete(salaId);
    };
    enVuelo.then(limpiar, limpiar);
    this.ninosEnVuelo.set(salaId, enVuelo);
    return enVuelo;
  }

  async nino(id: string): Promise<Nino> {
    const guardado = this.ninosPorId.get(id);
    if (guardado) return guardado;
    const nino = await this.pedir<Nino>(`/ninos/${id}`);
    if (!nino) throw new ErrorParaTia('No encontramos a ese niño o niña.');
    this.ninosPorId.set(nino.id, nino);
    return nino;
  }

  async evidencias(filtro: FiltroEvidencias): Promise<Evidencia[]> {
    const registros = await this.registros(filtro.salaId ?? this.sesionLocal.salaId);
    const ids = filtro.ids ? new Set(filtro.ids) : null;
    return registros.evidencias.filter(
      (e) => (!filtro.salaId || e.salaId === filtro.salaId) && (!ids || ids.has(e.id)),
    );
  }

  async sugerencias(filtro: FiltroSugerencias): Promise<Sugerencia[]> {
    const registros = await this.registros(filtro.salaId ?? this.sesionLocal.salaId);
    const estados = filtro.estado ? new Set(filtro.estado) : null;
    return registros.sugerencias.filter(
      (s) =>
        (!filtro.salaId || s.salaId === filtro.salaId) &&
        (!filtro.ninoId || s.ninoId === filtro.ninoId) &&
        (!estados || estados.has(s.estado)),
    );
  }

  async demoCapturas(): Promise<DemoCaptura[]> {
    return [];
  }

  // --- captura ------------------------------------------------------------

  async guardarEvidencia(
    e: Omit<Evidencia, 'id' | 'creadaEn' | 'estado'>,
    archivo?: Blob,
  ): Promise<Evidencia> {
    const entrada: Record<string, unknown> = {
      salaId: e.salaId,
      autorId: e.autorId,
      formato: e.formato,
    };
    if (e.ninoIdSugerido) entrada.ninoIdSugerido = e.ninoIdSugerido;

    if (e.formato === 'foto') {
      if (!archivo) throw new ErrorParaTia('No llegó la foto. Inténtalo de nuevo.');
      // Siempre se reduce a JPEG antes de salir del dispositivo: nunca viaja el
      // original crudo (puede ser HEIC o pesar demasiado para el BFF).
      const dataUrl = await reducirFoto(archivo);
      if (!dataUrl) {
        throw new ErrorParaTia('No pudimos preparar la foto. Intenta con otra.', 'foto_invalida');
      }
      // `reducirFoto` entrega `data:image/jpeg;base64,...`; el BFF solo quiere
      // la parte base64, sin el prefijo.
      const base64 = dataUrl.slice(dataUrl.indexOf(',') + 1);
      if (base64.length > MAX_BASE64_FOTO) {
        throw new ErrorParaTia(
          'La foto es muy pesada para enviarla. Prueba con otra.',
          'foto_demasiado_grande',
        );
      }
      entrada.fotoBase64 = base64;
      entrada.mimeType = 'image/jpeg';
    } else if (e.formato === 'audio') {
      if (!archivo) throw new ErrorParaTia('No llegó la grabación. Inténtalo de nuevo.');
      // Se revisa acá para no gastar el viaje: el BFF responde 413.
      if (archivo.size > MAX_BYTES_AUDIO) {
        throw new ErrorParaTia(
          'La grabación es muy larga para enviarla. Graba una más corta.',
          'audio_demasiado_grande',
        );
      }
      entrada.audioBase64 = await blobABase64(archivo);
      entrada.mimeType = archivo.type;
    } else {
      const texto = e.textoExtraido?.trim() ?? '';
      if (texto === '') throw new ErrorParaTia('Escribe la nota antes de enviarla.', 'texto_invalido');
      if (texto.length > MAX_CARACTERES_TEXTO) {
        throw new ErrorParaTia('La nota es muy larga. Déjala más corta.', 'texto_invalido');
      }
      entrada.texto = texto;
    }

    const respuesta = await this.pedir<{ evidencia: Evidencia }>('/capturas', {
      metodo: 'POST',
      cuerpo: entrada,
    });
    const evidencia = respuesta.evidencia;

    // Aparece en Revisar como `procesando` sin esperar la próxima consulta.
    const registros = this.registrosPorSala.get(evidencia.salaId);
    if (registros) {
      this.registrosPorSala.set(evidencia.salaId, {
        evidencias: [...registros.evidencias.filter((x) => x.id !== evidencia.id), evidencia],
        sugerencias: registros.sugerencias,
      });
    }
    this.notificar();
    this.quizasSondear();
    return evidencia;
  }

  /**
   * Los estados de proceso los define el servidor: lo único que la tía decide
   * es archivar una nota que quedó en `error` ("Descartar" en Revisar).
   */
  async marcarEvidencia(
    id: string,
    estado: Evidencia['estado'],
    _textoExtraido?: string,
    _foto?: string,
  ): Promise<void> {
    if (estado !== 'lista') return;
    const salaId = this.salaDeEvidencia(id);
    const registros = salaId ? this.registrosPorSala.get(salaId) : undefined;
    const evidencia = registros?.evidencias.find((x) => x.id === id);
    if (!registros || !evidencia || evidencia.estado !== 'error') return;

    await this.pedir<void>(`/capturas/${id}/archivar`, {
      metodo: 'POST',
      cuerpo: { salaId: evidencia.salaId },
    });
    // El archivar responde 204: el estado nuevo lo sabemos sin volver a leer.
    this.registrosPorSala.set(salaId, {
      evidencias: registros.evidencias.map((x) =>
        x.id === id ? { ...x, estado: 'lista' as const } : x,
      ),
      sugerencias: registros.sugerencias,
    });
    this.notificar();
  }

  private salaDeEvidencia(id: string): string {
    for (const [salaId, registros] of this.registrosPorSala) {
      if (registros.evidencias.some((e) => e.id === id)) return salaId;
    }
    return '';
  }

  // --- decisiones ---------------------------------------------------------

  /**
   * Manda las decisiones y deja en el caché lo que responde el servidor. La
   * actualización optimista la hace quien llama (`pisar`), para que la tía vea
   * el cambio antes del viaje; si falla, se vuelve atrás.
   */
  private async enviarDecisiones(
    salaId: string,
    items: ItemDecision[],
    pisar: (registros: RespuestaRegistros) => RespuestaRegistros,
  ): Promise<void> {
    if (items.length === 0) return;
    const previos = this.registrosPorSala.get(salaId);
    if (previos) {
      this.registrosPorSala.set(salaId, pisar(previos));
      this.notificar();
    }

    try {
      const respuesta = await this.pedir<{ sugerencias: Sugerencia[] }>('/decisiones', {
        metodo: 'PUT',
        cuerpo: { salaId, usuariaId: this.sesionLocal.usuariaId, items },
      });
      const actuales = this.registrosPorSala.get(salaId);
      if (actuales && respuesta?.sugerencias) {
        this.registrosPorSala.set(salaId, {
          evidencias: actuales.evidencias,
          sugerencias: respuesta.sugerencias,
        });
      }
      this.notificar();
    } catch (error) {
      // Vuelta atrás: la nota reaparece como estaba y se avisa a la tía.
      if (previos) {
        this.registrosPorSala.set(salaId, previos);
        this.notificar();
      }
      throw error;
    }
  }

  async validar(id: string, cambios?: CambiosValidacion): Promise<void> {
    const salaId = this.salaDeSugerencia(id);
    const guardada = this.sugerenciaGuardada(id);
    const item: ItemDecision = { idSugerencia: id, estado: 'aceptada' };
    const completos = cambiosCompletos(guardada, cambios);
    if (completos) item.cambios = completos;

    const cuando = new Date().toISOString();
    const usuariaId = this.sesionLocal.usuariaId;
    await this.enviarDecisiones(salaId, [item], (registros) => ({
      evidencias: registros.evidencias,
      sugerencias: registros.sugerencias.map((s) =>
        s.id === id ? validadaLocal(s, cambios, usuariaId, cuando) : s,
      ),
    }));
  }

  async descartar(id: string): Promise<void> {
    const salaId = this.salaDeSugerencia(id);
    const cuando = new Date().toISOString();
    const usuariaId = this.sesionLocal.usuariaId;
    await this.enviarDecisiones(
      salaId,
      [{ idSugerencia: id, estado: 'descartada' }],
      (registros) => ({
        evidencias: registros.evidencias,
        sugerencias: registros.sugerencias.map((s) =>
          s.id === id
            ? { ...s, estado: 'descartada', validadaPor: usuariaId, validadaEn: cuando }
            : s,
        ),
      }),
    );
  }

  /**
   * Una sola llamada con el estado de cada sugerencia. Es lo que usa Deshacer:
   * las que vuelven a `pendiente` borran su decisión en el servidor.
   */
  async guardarSugerencias(s: Sugerencia[]): Promise<void> {
    if (s.length === 0) return;
    const salaId = s[0].salaId || this.salaDeSugerencia(s[0].id);
    const items = s.map(itemDeSugerencia);
    const porId = new Map(s.map((x) => [x.id, x]));
    await this.enviarDecisiones(salaId, items, (registros) => ({
      evidencias: registros.evidencias,
      sugerencias: registros.sugerencias.map((x) => porId.get(x.id) ?? x),
    }));
  }

  async editarNotaSala(_sugerenciaId: string, _texto: string): Promise<void> {
    throw new ErrorParaTia('Esto todavía no se puede hacer desde aquí.', 'no_disponible');
  }

  async moverNino(_ninoId: string, _salaId: string): Promise<void> {
    throw new ErrorParaTia('Esto todavía no se puede hacer desde aquí.', 'no_disponible');
  }

  async darDeBaja(_ninoId: string): Promise<void> {
    throw new ErrorParaTia('Esto todavía no se puede hacer desde aquí.', 'no_disponible');
  }

  // --- sondeo -------------------------------------------------------------

  suscribir(cb: () => void): () => void {
    this.suscriptores.add(cb);
    this.quizasSondear();
    return () => {
      this.suscriptores.delete(cb);
      if (this.suscriptores.size === 0) this.detenerSondeo();
    };
  }

  /** `true` si alguna nota ya leída sigue en el servidor. */
  private hayProcesando(): boolean {
    for (const registros of this.registrosPorSala.values()) {
      if (registros.evidencias.some((e) => e.estado === 'procesando')) return true;
    }
    return false;
  }

  /** El sondeo existe solo mientras queda algo en `procesando`. */
  private quizasSondear(): void {
    if (this.sondeo !== null) {
      if (!this.hayProcesando()) this.detenerSondeo();
      return;
    }
    if (this.suscriptores.size === 0 || !this.hayProcesando()) return;
    this.sondeo = setInterval(() => void this.sondear(), INTERVALO_SONDEO_MS);
  }

  private detenerSondeo(): void {
    if (this.sondeo === null) return;
    clearInterval(this.sondeo);
    this.sondeo = null;
  }

  private async sondear(): Promise<void> {
    const salaId = this.sesionLocal.salaId;
    if (!salaId) return;
    try {
      await this.registros(salaId, true);
      this.notificar();
    } catch {
      /* sin conexión: se vuelve a intentar en la próxima vuelta */
    }
    this.quizasSondear();
  }

  async reiniciarDemo(): Promise<void> {
    this.detenerSondeo();
    this.almacen.borrar(CLAVE_SESION);
    this.sesionLocal = { ...SESION_VACIA };
    this.contextoGuardado = null;
    this.contextoEnVuelo = null;
    this.registrosPorSala.clear();
    this.registrosEnVuelo.clear();
    this.ninosPorSala.clear();
    this.ninosEnVuelo.clear();
    this.ninosPorId.clear();
    this.notificar();
  }
}

/** Instancia única que usa la app cuando se compiló con `VITE_DATOS=http`. */
export const servicioHttp: DataService = new DataServiceHttp();
