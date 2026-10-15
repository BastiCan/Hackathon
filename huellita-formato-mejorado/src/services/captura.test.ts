/**
 * Captura en la versión AWS (tarea 5): si el servicio de datos procesa en el
 * servidor, la nota se guarda y nada más. La IA del dispositivo no se llama y
 * los estados de la evidencia los define el BFF.
 */
import semillaJson from '@data/semilla.json';
import { describe, expect, it, vi } from 'vitest';
import type { Evidencia, Semilla, Sugerencia } from '../lib/tipos';
import { capturar } from './captura';
import { almacenMemoria, DataServiceLocal } from './datos';
import type { ContextoIA, IAService } from './ia';

const semilla = semillaJson as unknown as Semilla;

/** Como el servicio de AWS: el BFF lee la nota y devuelve las sugerencias. */
class DatosEnServidor extends DataServiceLocal {
  readonly procesaEnServidor = true;
}

function iaEspia(): IAService & { procesar: ReturnType<typeof vi.fn> } {
  const procesar = vi.fn(
    async (_e: Evidencia, _a: Blob | undefined, _c: ContextoIA): Promise<Sugerencia[]> => [],
  );
  return { procesar };
}

describe('capturar en modo servidor', () => {
  it('no llama a la IA del dispositivo y deja la nota en procesando', async () => {
    const datos = new DatosEnServidor({ semilla, almacen: almacenMemoria() });
    const ia = iaEspia();
    const antes = (await datos.sugerencias({ estado: ['pendiente'] })).length;

    const { evidencia, procesada } = await capturar(
      'texto',
      undefined,
      'Nayara apiló cinco cubos y dijo torre',
      undefined,
      { datos, ia },
    );

    expect(await procesada).toEqual([]);
    expect(ia.procesar).not.toHaveBeenCalled();
    const [guardada] = await datos.evidencias({ ids: [evidencia.id] });
    expect(guardada.estado).toBe('procesando');
    expect(guardada.textoExtraido).toBe('Nayara apiló cinco cubos y dijo torre');
    expect(await datos.sugerencias({ estado: ['pendiente'] })).toHaveLength(antes);
  });

  it('en modo local sigue procesando en el dispositivo', async () => {
    const datos = new DataServiceLocal({ semilla, almacen: almacenMemoria() });
    const ia = iaEspia();

    const { procesada } = await capturar('texto', undefined, 'Josefa pidió agua', undefined, {
      datos,
      ia,
    });

    await procesada;
    expect(ia.procesar).toHaveBeenCalledTimes(1);
  });
});
