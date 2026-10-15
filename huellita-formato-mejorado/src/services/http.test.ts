/**
 * Pruebas del servicio contra el BFF (tareas 5, 6 y 7 del lado cliente): el
 * cuerpo que viaja en cada llamada, la conversión del audio a base64, el
 * sondeo que se detiene cuando no queda nada procesando y las decisiones de
 * Revisar con su vuelta atrás.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MAX_BYTES_AUDIO } from '../app/config';
import type { Evidencia, Nino, Sugerencia, Usuaria } from '../lib/tipos';
import { almacenMemoria } from './datos';
import { ErrorParaTia } from './errores';
import { aBase64, BLOQUE_BASE64, DataServiceHttp, INTERVALO_SONDEO_MS } from './http';

const USUARIAS: Usuaria[] = [
  { id: 'EDU-0001', nombre: 'Tía Ana', rol: 'tia', jardinId: 'JAR-0001', salaIds: ['SG-A'] },
  { id: 'EDU-0002', nombre: 'Tía Rosa', rol: 'tia', jardinId: 'JAR-0001', salaIds: ['SG-B'] },
];

const CONTEXTO = {
  jardin: { id: 'JAR-0001', nombre: 'Jardín de la demo', comuna: 'Maipú', region: 'Metropolitana' },
  salas: [
    { id: 'SG-A', jardinId: 'JAR-0001', nombre: 'Sala A', nivelEducativo: 'Sala Cuna Menor' },
    { id: 'SG-B', jardinId: 'JAR-0001', nombre: 'Sala B', nivelEducativo: 'Sala Cuna Mayor' },
  ],
  usuarias: USUARIAS,
};

const NINOS: Nino[] = [
  {
    id: 'NINO-00001',
    nombre: 'Nayara',
    apellidoInicial: '',
    fechaNacimiento: '2025-01-10',
    salaId: 'SG-A',
    activo: true,
  },
];

function unaEvidencia(id: string, estado: Evidencia['estado']): Evidencia {
  return {
    id,
    salaId: 'SG-A',
    autorId: 'EDU-0001',
    creadaEn: '2026-10-15T09:10:00-03:00',
    formato: 'texto',
    estado,
  };
}

function unaSugerencia(id: string, estado: Sugerencia['estado'] = 'pendiente'): Sugerencia {
  return {
    id,
    evidenciaId: 'CAP-01',
    salaId: 'SG-A',
    tipo: 'evaluacion',
    ninoId: 'NINO-00001',
    nucleo: 'cognitivo',
    nivel: 3,
    cita: 'Nayara apiló cinco cubos y dijo torre',
    certeza: 'alta',
    estado,
  };
}

interface Llamada {
  metodo: string;
  ruta: string;
  usuaria: string | undefined;
  cuerpo: Record<string, unknown> | undefined;
}

interface ItemEnviado {
  idSugerencia: string;
  estado: string;
  cambios?: { ninoId: string; nucleo: string; nivel: number };
}

interface EstadoServidor {
  registros: { evidencias: Evidencia[]; sugerencias: Sugerencia[] };
  ninos: Nino[];
  evidenciaCreada: Evidencia;
  sugerenciasTrasDecision: Sugerencia[] | null;
  /** Si está, el servidor no contesta hasta que la prueba lo suelte. */
  freno: Promise<void> | null;
}

function montarServidor() {
  const llamadas: Llamada[] = [];
  const fallas = new Map<string, { estado: number; cuerpo?: unknown; crudo?: string }>();
  const estado: EstadoServidor = {
    registros: { evidencias: [], sugerencias: [] },
    ninos: NINOS,
    evidenciaCreada: unaEvidencia('CAP-NUEVA', 'procesando'),
    sugerenciasTrasDecision: null,
    freno: null,
  };

  const responder = (estadoHttp: number, cuerpo?: unknown, crudo?: string): Response =>
    ({
      ok: estadoHttp >= 200 && estadoHttp < 300,
      status: estadoHttp,
      text: async () => crudo ?? (cuerpo === undefined ? '' : JSON.stringify(cuerpo)),
    }) as unknown as Response;

  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const metodo = init?.method ?? 'GET';
      const ruta = String(url);
      llamadas.push({
        metodo,
        ruta,
        usuaria: (init?.headers as Record<string, string> | undefined)?.['X-Usuaria-Id'],
        cuerpo: init?.body
          ? (JSON.parse(String(init.body)) as Record<string, unknown>)
          : undefined,
      });

      const falla = fallas.get(`${metodo} ${ruta}`);
      if (falla) return responder(falla.estado, falla.cuerpo, falla.crudo);
      if (estado.freno) await estado.freno;

      if (ruta === '/api/contexto') return responder(200, CONTEXTO);
      if (ruta.endsWith('/ninos')) return responder(200, estado.ninos);
      if (ruta.endsWith('/registros')) return responder(200, estado.registros);
      if (ruta === '/api/capturas') return responder(201, { evidencia: estado.evidenciaCreada });
      if (ruta.endsWith('/archivar')) return responder(204);
      if (ruta === '/api/decisiones') {
        return responder(200, {
          sugerencias: estado.sugerenciasTrasDecision ?? estado.registros.sugerencias,
        });
      }
      return responder(404, { error: { codigo: 'no_encontrado', mensaje: 'Eso no está.' } });
    }),
  );

  return { llamadas, fallas, estado };
}

let servidor: ReturnType<typeof montarServidor>;

/** Servicio con la tía Ana ya elegida y, si se pide, los registros cargados. */
async function servicio(cargarRegistros = true): Promise<DataServiceHttp> {
  const datos = new DataServiceHttp({ almacen: almacenMemoria() });
  await datos.cambiarUsuaria('EDU-0001');
  if (cargarRegistros) await datos.sugerencias({ salaId: 'SG-A' });
  return datos;
}

function soloRuta(metodo: string, ruta: string): Llamada[] {
  return servidor.llamadas.filter((l) => l.metodo === metodo && l.ruta === ruta);
}

beforeEach(() => {
  servidor = montarServidor();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('base64 por bloques', () => {
  it('convierte más de un bloque sin perder ni mover bytes', () => {
    const bytes = new Uint8Array(BLOQUE_BASE64 * 2 + 7);
    for (let i = 0; i < bytes.length; i += 1) bytes[i] = i % 251;

    const vuelta = atob(aBase64(bytes));
    expect(vuelta).toHaveLength(bytes.length);
    expect([...vuelta].map((c) => c.charCodeAt(0))).toEqual([...bytes]);
  });

  it('da lo mismo que btoa cuando cabe en un bloque', () => {
    const bytes = new Uint8Array([72, 111, 108, 97, 0, 255]);
    expect(aBase64(bytes)).toBe(btoa(String.fromCharCode(...bytes)));
  });
});

describe('POST /api/capturas', () => {
  it('manda el texto tal cual y devuelve la evidencia en procesando', async () => {
    const datos = await servicio(false);
    const evidencia = await datos.guardarEvidencia({
      salaId: 'SG-A',
      autorId: 'EDU-0001',
      formato: 'texto',
      textoExtraido: 'Nayara apiló cinco cubos y dijo torre',
      ninoIdSugerido: 'NINO-00001',
    });

    const [llamada] = soloRuta('POST', '/api/capturas');
    expect(llamada.cuerpo).toEqual({
      salaId: 'SG-A',
      autorId: 'EDU-0001',
      formato: 'texto',
      ninoIdSugerido: 'NINO-00001',
      texto: 'Nayara apiló cinco cubos y dijo torre',
    });
    expect(llamada.usuaria).toBe('EDU-0001');
    expect(evidencia.estado).toBe('procesando');
  });

  it('manda el audio en base64 y su mimeType', async () => {
    const datos = await servicio(false);
    const bytes = new Uint8Array(BLOQUE_BASE64 + 3);
    for (let i = 0; i < bytes.length; i += 1) bytes[i] = (i * 7) % 256;
    servidor.estado.evidenciaCreada = { ...unaEvidencia('CAP-AUDIO', 'procesando'), formato: 'audio' };

    await datos.guardarEvidencia(
      { salaId: 'SG-A', autorId: 'EDU-0001', formato: 'audio' },
      new Blob([bytes], { type: 'audio/webm;codecs=opus' }),
    );

    const [llamada] = soloRuta('POST', '/api/capturas');
    expect(llamada.cuerpo).toEqual({
      salaId: 'SG-A',
      autorId: 'EDU-0001',
      formato: 'audio',
      audioBase64: aBase64(bytes),
      mimeType: 'audio/webm;codecs=opus',
    });
  });

  it('no gasta el viaje con un audio de más de 4 MiB ni con un texto vacío', async () => {
    const datos = await servicio(false);
    const grande = new Blob([new Uint8Array(MAX_BYTES_AUDIO + 1)], { type: 'audio/webm' });

    await expect(
      datos.guardarEvidencia({ salaId: 'SG-A', autorId: 'EDU-0001', formato: 'audio' }, grande),
    ).rejects.toMatchObject({ codigo: 'audio_demasiado_grande' });
    await expect(
      datos.guardarEvidencia({ salaId: 'SG-A', autorId: 'EDU-0001', formato: 'texto', textoExtraido: '   ' }),
    ).rejects.toMatchObject({ codigo: 'texto_invalido' });
    await expect(
      datos.guardarEvidencia({
        salaId: 'SG-A',
        autorId: 'EDU-0001',
        formato: 'texto',
        textoExtraido: 'x'.repeat(5001),
      }),
    ).rejects.toMatchObject({ codigo: 'texto_invalido' });
    expect(soloRuta('POST', '/api/capturas')).toHaveLength(0);
  });

  it('el tope diario llega como error para la tía, con su código', async () => {
    const datos = await servicio(false);
    servidor.fallas.set('POST /api/capturas', {
      estado: 429,
      cuerpo: { error: { codigo: 'tope_diario', mensaje: 'Ya registramos muchas notas hoy.' } },
    });

    const error = await datos
      .guardarEvidencia({ salaId: 'SG-A', autorId: 'EDU-0001', formato: 'texto', textoExtraido: 'Hola' })
      .catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ErrorParaTia);
    expect(error).toMatchObject({
      codigo: 'tope_diario',
      estado: 429,
      message: 'Ya registramos muchas notas hoy.',
    });
  });

  it('si la respuesta no trae un error entendible, el mensaje es el genérico', async () => {
    const datos = await servicio(false);
    servidor.fallas.set('POST /api/capturas', { estado: 502, crudo: '<html>502</html>' });

    const error = await datos
      .guardarEvidencia({ salaId: 'SG-A', autorId: 'EDU-0001', formato: 'texto', textoExtraido: 'Hola' })
      .catch((e: unknown) => e);
    expect(error).toMatchObject({
      codigo: undefined,
      estado: 502,
      message: 'No pudimos guardar esto. Intenta de nuevo.',
    });
  });
});

describe('PUT /api/decisiones', () => {
  beforeEach(() => {
    servidor.estado.registros = {
      evidencias: [unaEvidencia('CAP-01', 'lista')],
      sugerencias: [unaSugerencia('SUG-1'), unaSugerencia('SUG-2'), unaSugerencia('SUG-3')],
    };
  });

  it('confirmar manda un solo ítem y guarda lo que responde el servidor', async () => {
    const datos = await servicio();
    servidor.estado.sugerenciasTrasDecision = [
      { ...unaSugerencia('SUG-1', 'aceptada'), validadaPor: 'EDU-0001' },
      unaSugerencia('SUG-2'),
      unaSugerencia('SUG-3'),
    ];

    await datos.validar('SUG-1');

    const [llamada] = soloRuta('PUT', '/api/decisiones');
    expect(llamada.cuerpo).toEqual({
      salaId: 'SG-A',
      usuariaId: 'EDU-0001',
      items: [{ idSugerencia: 'SUG-1', estado: 'aceptada' }],
    });
    const aceptadas = await datos.sugerencias({ salaId: 'SG-A', estado: ['aceptada'] });
    expect(aceptadas.map((s) => s.id)).toEqual(['SUG-1']);
  });

  it('corregir manda los tres campos y descartar manda su estado', async () => {
    const datos = await servicio();
    await datos.validar('SUG-2', { ninoId: 'NINO-00001', nucleo: 'motor_fino', nivel: 5 });
    await datos.descartar('SUG-3');

    const llamadas = soloRuta('PUT', '/api/decisiones');
    expect(llamadas[0].cuerpo?.items).toEqual([
      {
        idSugerencia: 'SUG-2',
        estado: 'aceptada',
        cambios: { ninoId: 'NINO-00001', nucleo: 'motor_fino', nivel: 5 },
      },
    ]);
    expect(llamadas[1].cuerpo?.items).toEqual([
      { idSugerencia: 'SUG-3', estado: 'descartada' },
    ]);
  });

  it('la tía ve el cambio antes de la respuesta (actualización optimista)', async () => {
    const datos = await servicio();
    let avisos = 0;
    datos.suscribir(() => void (avisos += 1));

    let soltar = (): void => {};
    servidor.estado.freno = new Promise<void>((listo) => {
      soltar = () => listo();
    });
    const guardando = datos.validar('SUG-1');

    expect((await datos.sugerencias({ salaId: 'SG-A', estado: ['pendiente'] })).map((s) => s.id)).toEqual([
      'SUG-2',
      'SUG-3',
    ]);
    expect(avisos).toBe(1);

    soltar();
    await guardando;
  });

  it('si la llamada falla, la nota vuelve a pendiente y se avisa', async () => {
    const datos = await servicio();
    let avisos = 0;
    datos.suscribir(() => void (avisos += 1));
    servidor.fallas.set('PUT /api/decisiones', {
      estado: 503,
      cuerpo: { error: { codigo: 'servicio_saturado', mensaje: 'Intenta de nuevo en un rato.' } },
    });

    await expect(datos.validar('SUG-1')).rejects.toBeInstanceOf(ErrorParaTia);

    const pendientes = await datos.sugerencias({ salaId: 'SG-A', estado: ['pendiente'] });
    expect(pendientes.map((s) => s.id)).toEqual(['SUG-1', 'SUG-2', 'SUG-3']);
    expect(avisos).toBe(2); // el cambio optimista y la vuelta atrás
  });

  it('confirmar los de confianza alta manda una llamada de un ítem por nota', async () => {
    const datos = await servicio();
    await Promise.all(['SUG-1', 'SUG-2', 'SUG-3'].map((id) => datos.validar(id)));

    const llamadas = soloRuta('PUT', '/api/decisiones');
    expect(llamadas).toHaveLength(3);
    expect(llamadas.map((l) => (l.cuerpo?.items as ItemEnviado[]).length)).toEqual([1, 1, 1]);
    expect(llamadas.map((l) => (l.cuerpo?.items as ItemEnviado[])[0].idSugerencia)).toEqual([
      'SUG-1',
      'SUG-2',
      'SUG-3',
    ]);
  });

  it('Deshacer manda una sola llamada con el estado de cada sugerencia', async () => {
    const datos = await servicio();
    const cambiada: Sugerencia = {
      ...unaSugerencia('SUG-3', 'cambiada'),
      ninoId: 'NINO-00001',
      nucleo: 'socioemocional',
      nivel: 6,
    };

    await datos.guardarSugerencias([
      unaSugerencia('SUG-1', 'pendiente'),
      unaSugerencia('SUG-2', 'aceptada'),
      cambiada,
    ]);

    const llamadas = soloRuta('PUT', '/api/decisiones');
    expect(llamadas).toHaveLength(1);
    expect(llamadas[0].cuerpo?.items).toEqual([
      { idSugerencia: 'SUG-1', estado: 'pendiente' },
      { idSugerencia: 'SUG-2', estado: 'aceptada' },
      {
        idSugerencia: 'SUG-3',
        estado: 'aceptada',
        cambios: { ninoId: 'NINO-00001', nucleo: 'socioemocional', nivel: 6 },
      },
    ]);
  });
});

describe('archivar una nota que no se pudo leer', () => {
  it('solo llama al servidor si la evidencia está en error', async () => {
    servidor.estado.registros = {
      evidencias: [unaEvidencia('CAP-ERROR', 'error'), unaEvidencia('CAP-OK', 'procesando')],
      sugerencias: [],
    };
    const datos = await servicio();

    await datos.marcarEvidencia('CAP-OK', 'lista');
    await datos.marcarEvidencia('CAP-ERROR', 'error');
    expect(servidor.llamadas.filter((l) => l.ruta.endsWith('/archivar'))).toHaveLength(0);

    await datos.marcarEvidencia('CAP-ERROR', 'lista');
    const [llamada] = soloRuta('POST', '/api/capturas/CAP-ERROR/archivar');
    expect(llamada.cuerpo).toEqual({ salaId: 'SG-A' });

    const evidencias = await datos.evidencias({ salaId: 'SG-A' });
    expect(evidencias.find((e) => e.id === 'CAP-ERROR')?.estado).toBe('lista');
  });
});

describe('seguimiento de las notas en proceso', () => {
  it('consulta cada 5 s y se detiene cuando no queda nada procesando', async () => {
    servidor.estado.registros = {
      evidencias: [unaEvidencia('CAP-01', 'procesando')],
      sugerencias: [],
    };
    const datos = await servicio();
    const consultas = () => soloRuta('GET', '/api/salas/SG-A/registros').length;
    expect(consultas()).toBe(1);

    vi.useFakeTimers();
    let avisos = 0;
    const baja = datos.suscribir(() => void (avisos += 1));

    // Sigue procesando: cada vuelta vuelve a preguntar.
    await vi.advanceTimersByTimeAsync(INTERVALO_SONDEO_MS);
    expect(consultas()).toBe(2);
    expect(avisos).toBe(1);

    // El servidor terminó: la última consulta apaga el seguimiento.
    servidor.estado.registros = { evidencias: [unaEvidencia('CAP-01', 'lista')], sugerencias: [] };
    await vi.advanceTimersByTimeAsync(INTERVALO_SONDEO_MS);
    expect(consultas()).toBe(3);

    await vi.advanceTimersByTimeAsync(INTERVALO_SONDEO_MS * 4);
    expect(consultas()).toBe(3);
    baja();
  });

  it('sin nada procesando no arranca, y una captura nueva lo vuelve a encender', async () => {
    const datos = await servicio();
    vi.useFakeTimers();
    const baja = datos.suscribir(() => {});

    await vi.advanceTimersByTimeAsync(INTERVALO_SONDEO_MS * 2);
    expect(soloRuta('GET', '/api/salas/SG-A/registros')).toHaveLength(1);

    servidor.estado.evidenciaCreada = unaEvidencia('CAP-NUEVA', 'procesando');
    await datos.guardarEvidencia({
      salaId: 'SG-A',
      autorId: 'EDU-0001',
      formato: 'texto',
      textoExtraido: 'Nayara apiló cinco cubos y dijo torre',
    });
    servidor.estado.registros = {
      evidencias: [unaEvidencia('CAP-NUEVA', 'procesando')],
      sugerencias: [],
    };

    await vi.advanceTimersByTimeAsync(INTERVALO_SONDEO_MS);
    expect(soloRuta('GET', '/api/salas/SG-A/registros')).toHaveLength(2);
    baja();
  });
});

describe('sesión y catálogos', () => {
  it('el servidor procesa las notas y todavía no recibe fotos', async () => {
    const datos = await servicio(false);
    expect(datos.procesaEnServidor).toBe(true);
    expect(datos.admiteFoto).toBe(false);
    await expect(
      datos.guardarEvidencia({ salaId: 'SG-A', autorId: 'EDU-0001', formato: 'foto' }),
    ).rejects.toMatchObject({ codigo: 'formato_no_soportado' });
  });

  it('la usuaria elegida queda en el dispositivo y la sala se consulta una vez', async () => {
    const datos = await servicio(false);
    expect(await datos.usuariaElegida()).toBe(true);
    expect((await datos.sesion()).id).toBe('EDU-0001');
    expect((await datos.salaActual()).id).toBe('SG-A');
    expect((await datos.salas()).map((s) => s.id)).toEqual(['SG-A']);

    await datos.ninos('SG-A');
    await datos.ninos('SG-A');
    expect(soloRuta('GET', '/api/salas/SG-A/ninos')).toHaveLength(1);
    expect((await datos.nino('NINO-00001')).nombre).toBe('Nayara');
    expect(soloRuta('GET', '/api/ninos/NINO-00001')).toHaveLength(0);
    expect(soloRuta('GET', '/api/contexto')).toHaveLength(1);
  });

  it('la fecha de hoy es la de Chile y no hay guiones de demo', async () => {
    const datos = await servicio(false);
    expect(datos.hoy()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(await datos.demoCapturas()).toEqual([]);
    await expect(datos.moverNino('NINO-00001', 'SG-B')).rejects.toMatchObject({
      codigo: 'no_disponible',
    });
  });
});
