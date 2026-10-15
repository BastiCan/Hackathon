/**
 * Hooks de datos. Cada uno pide lo que necesita una pantalla al `DataService`,
 * lo combina con las reglas de `lib/evaluacion.ts` y vuelve a cargar solo cuando
 * el servicio avisa que algo cambió (`suscribir`).
 */
import { useCallback, useEffect, useState } from 'react';
import {
  edadAniosMeses,
  edadMeses,
  evaluacionesDe,
  evaluacionesValidadas,
  nivelActualPorNucleo,
  nivelEsperado,
  observarAhora,
  resumenSala,
} from '../lib/evaluacion';
import { agendaDelDia, proximoIEA, semanaDe, type DiaSemana, type PeriodoAgenda } from '../lib/agenda';
import { conductas, nivelSiguiente } from '../lib/rubrica';
import type {
  Evidencia,
  Jardin,
  Nino,
  Nivel,
  Sala,
  Sugerencia,
  SugerenciaObservacion,
  Usuaria,
} from '../lib/tipos';
import {
  conteosFiltro,
  cuando,
  etiquetaFormato,
  historialVista,
  iniciales,
  nucleosDeFicha,
  ordenarNucleosFicha,
  partesResumenSala,
  resumenFicha,
  tarjetaSala,
  tarjetasDeSala,
  textoResumenSala,
  type ConteosFiltro,
  type NucleoVista,
  type RegistroVista,
  type TarjetaNinoVista,
  type TarjetaSalaVista,
} from '../lib/vistas';
import type { DataService } from '../services/datos';
import { useServicios } from './servicios';

export interface Consulta<T> {
  valor: T | null;
  cargando: boolean;
  /** Mensaje para la tía, sin trazas técnicas. */
  error: string | null;
}

const SIN_CARGAR = { valor: null, cargando: true, error: null } as const;

/** Carga algo del servicio y lo refresca cuando los datos cambian. */
export function useConsulta<T>(
  cargar: (datos: DataService) => Promise<T>,
  deps: unknown[],
): Consulta<T> {
  const { datos } = useServicios();
  const [estado, setEstado] = useState<Consulta<T>>(SIN_CARGAR);
  // Las dependencias las decide cada pantalla.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const consulta = useCallback(cargar, deps);

  useEffect(() => {
    let vivo = true;
    const correr = () => {
      consulta(datos).then(
        (valor) => {
          if (vivo) setEstado({ valor, cargando: false, error: null });
        },
        () => {
          if (vivo) {
            setEstado({ valor: null, cargando: false, error: 'No pudimos cargar esta información.' });
          }
        },
      );
    };
    correr();
    const baja = datos.suscribir(correr);
    return () => {
      vivo = false;
      baja();
    };
  }, [consulta, datos]);

  return estado;
}

export interface Sesion {
  usuaria: Usuaria;
  elegida: boolean;
  sala: Sala;
  salas: Sala[];
  jardin: Jardin;
  usuarias: Usuaria[];
  /** Fecha "hoy" de la demo. */
  hoy: string;
  /** Sugerencias pendientes de la sala actual, para el contador de la barra. */
  pendientes: number;
}

export function useSesion(): Consulta<Sesion> {
  return useConsulta(async (datos) => {
    const [usuaria, elegida, sala, salas, jardin, usuarias] = await Promise.all([
      datos.sesion(),
      datos.usuariaElegida(),
      datos.salaActual(),
      datos.salas(),
      datos.jardin(),
      datos.usuarias(),
    ]);
    const [pendientes, conError] = await Promise.all([
      datos.sugerencias({ salaId: sala.id, estado: ['pendiente'] }),
      datos.evidencias({ salaId: sala.id }),
    ]);
    return {
      usuaria,
      elegida,
      sala,
      salas,
      jardin,
      usuarias,
      hoy: datos.hoy(),
      pendientes: pendientes.length + conError.filter((e) => e.estado === 'error').length,
    };
  }, []);
}

export interface VistaMiSala {
  sala: Sala;
  hoy: string;
  tarjetas: TarjetaNinoVista[];
  conteos: ConteosFiltro;
  /** Línea completa, para lectores de pantalla y pruebas. */
  resumen: string;
  /** Las dos partes que van en negrita (como en el prototipo). */
  partesResumen: { observados: string; menos: string };
  pendientes: number;
}

export function useMiSala(salaId: string | undefined): Consulta<VistaMiSala> {
  return useConsulta(
    async (datos) => {
      const sala = salaId
        ? (await datos.salas()).find((s) => s.id === salaId) ?? (await datos.salaActual())
        : await datos.salaActual();
      const hoy = datos.hoy();
      const [ninos, sugerencias, evidencias] = await Promise.all([
        datos.ninos(sala.id),
        datos.sugerencias({ salaId: sala.id }),
        datos.evidencias({ salaId: sala.id }),
      ]);
      const evaluaciones = evaluacionesValidadas(sugerencias, evidencias);
      const tarjetas = tarjetasDeSala(ninos, evaluaciones, hoy);
      const resumen = resumenSala(ninos, evaluaciones, hoy);
      return {
        sala,
        hoy,
        tarjetas,
        conteos: conteosFiltro(tarjetas),
        resumen: textoResumenSala(resumen),
        partesResumen: partesResumenSala(resumen),
        pendientes:
          sugerencias.filter((s) => s.estado === 'pendiente').length +
          evidencias.filter((e) => e.estado === 'error').length,
      };
    },
    [salaId],
  );
}

export interface VistaDirectora {
  jardin: Jardin;
  salas: TarjetaSalaVista[];
}

/**
 * Vista directora (tarea 14): una tarjeta por sala del jardín, calculada con
 * las mismas reglas de `lib/evaluacion.ts` que usa la tía.
 */
export function useDirectora(): Consulta<VistaDirectora> {
  return useConsulta(async (datos) => {
    const hoy = datos.hoy();
    const [jardin, salas] = await Promise.all([datos.jardin(), datos.salas()]);
    const tarjetas = await Promise.all(
      salas.map(async (sala) => {
        const [ninos, sugerencias, evidencias] = await Promise.all([
          datos.ninos(sala.id),
          datos.sugerencias({ salaId: sala.id }),
          datos.evidencias({ salaId: sala.id }),
        ]);
        const evaluaciones = evaluacionesValidadas(sugerencias, evidencias);
        const { nucleoMenosCubierto } = resumenSala(ninos, evaluaciones, hoy);
        return tarjetaSala(sala, ninos, evaluaciones, hoy, nucleoMenosCubierto);
      }),
    );
    return { jardin, salas: tarjetas };
  }, []);
}

/** Una nota pendiente: la evidencia original más lo que Huellita leyó. */
export interface NotaPendiente {
  sugerencia: Sugerencia;
  evidencia?: Evidencia;
  /** "Foto de post-it · Hoy, 09:12 · Tía Ana". */
  origen: string;
  nombreNino?: string;
  inicialesNino?: string;
}

/** Evidencia que no se pudo leer; en Revisar se ofrece escribirla o descartarla. */
export interface NotaConError {
  evidencia: Evidencia;
  origen: string;
}

export interface VistaRevisar {
  sala: Sala;
  hoy: string;
  notas: NotaPendiente[];
  conError: NotaConError[];
  /** Cuántas pendientes son de certeza alta ("Aceptar las seguras"). */
  seguras: number;
  ninos: Nino[];
}

export function useRevisar(): Consulta<VistaRevisar> {
  return useConsulta(async (datos) => {
    const sala = await datos.salaActual();
    const hoy = datos.hoy();
    const [ninos, pendientes, evidencias, usuarias] = await Promise.all([
      datos.ninos(sala.id),
      datos.sugerencias({ salaId: sala.id, estado: ['pendiente'] }),
      datos.evidencias({ salaId: sala.id }),
      datos.usuarias(),
    ]);

    const porId = new Map(evidencias.map((e) => [e.id, e]));
    const nombreUsuaria = (id?: string) => usuarias.find((u) => u.id === id)?.nombre ?? 'Tía';
    const nombreNino = (id?: string) => ninos.find((n) => n.id === id)?.nombre;

    const etiquetaOrigen = (e: Evidencia | undefined): string => {
      if (!e) return 'Nota registrada';
      return `${etiquetaFormato(e.formato)} · ${cuando(e.creadaEn, hoy)} · ${nombreUsuaria(e.autorId)}`;
    };

    const notas: NotaPendiente[] = pendientes
      .map((sugerencia) => {
        const evidencia = porId.get(sugerencia.evidenciaId);
        const nombre = nombreNino(sugerencia.ninoId);
        return {
          sugerencia,
          evidencia,
          origen: etiquetaOrigen(evidencia),
          nombreNino: nombre,
          inicialesNino: nombre ? iniciales(nombre) : undefined,
        };
      })
      // De la más reciente a la más antigua (requisito 3.1). Las sugerencias de
      // una misma nota mantienen su orden (`sort` es estable si el empate da 0).
      .sort((a, b) =>
        (b.evidencia?.creadaEn ?? '').localeCompare(a.evidencia?.creadaEn ?? ''),
      );

    const conError: NotaConError[] = evidencias
      .filter((e) => e.estado === 'error')
      .map((evidencia) => ({ evidencia, origen: etiquetaOrigen(evidencia) }));

    return {
      sala,
      hoy,
      notas,
      conError,
      seguras: notas.filter(
        (n) => n.sugerencia.tipo === 'evaluacion' && n.sugerencia.certeza === 'alta',
      ).length,
      ninos,
    };
  }, []);
}

export interface VistaFicha {
  nino: Nino;
  sala: Sala;
  edad: { anios: number; meses: number };
  iniciales: string;
  frescura: TarjetaNinoVista['frescura'];
  nivelGeneral: TarjetaNinoVista['nivelGeneral'];
  resumen: string;
  nucleos: NucleoVista[];
  observar: SugerenciaObservacion | null;
  /** Nivel esperado para su edad; se usa cuando un núcleo no tiene registros. */
  nivelEsperadoEdad: Nivel;
  /** Conductas observables del núcleo propuesto (vienen de la rúbrica). */
  conductasObservar: string[];
  historial: RegistroVista[];
}

export function useFicha(ninoId: string | undefined): Consulta<VistaFicha> {
  return useConsulta(
    async (datos) => {
      if (!ninoId) throw new Error('Falta el niño o niña.');
      const hoy = datos.hoy();
      const nino = await datos.nino(ninoId);
      const [salas, sugerencias, evidencias, usuarias] = await Promise.all([
        datos.salas(),
        datos.sugerencias({ salaId: nino.salaId }),
        datos.evidencias({ salaId: nino.salaId }),
        datos.usuarias(),
      ]);
      const sala = salas.find((s) => s.id === nino.salaId) ?? (await datos.salaActual());
      const suyas = evaluacionesDe(evaluacionesValidadas(sugerencias, evidencias), nino.id);
      const nucleos = nucleosDeFicha(suyas, nino.fechaNacimiento);
      const niveles = nivelActualPorNucleo(suyas);
      const esperado = nivelEsperado(edadMeses(nino.fechaNacimiento, hoy));
      // Si un núcleo está en "revisar avance", lo que hay que observar es el
      // siguiente paso en ese núcleo; si no, la regla general de la rúbrica.
      const marcado = nucleos.find((n) => n.revisarAvance && n.nivel !== null);
      const observar: SugerenciaObservacion | null = marcado?.nivel
        ? (() => {
            const nivel = nivelSiguiente(marcado.nivel);
            return { nucleo: marcado.nucleo, nivel, conductas: conductas(marcado.nucleo, nivel).slice(0, 2) };
          })()
        : observarAhora(suyas, niveles, esperado);
      const tarjeta = tarjetasDeSala([nino], suyas, hoy)[0];

      return {
        nino,
        sala,
        edad: edadAniosMeses(nino.fechaNacimiento, hoy),
        iniciales: iniciales(nino.nombre),
        frescura: tarjeta.frescura,
        nivelGeneral: tarjeta.nivelGeneral,
        resumen: resumenFicha(nino.nombre, nucleos, observar),
        nucleos: ordenarNucleosFicha(nucleos),
        observar,
        nivelEsperadoEdad: esperado,
        conductasObservar: observar ? conductas(observar.nucleo, observar.nivel).slice(0, 2) : [],
        historial: historialVista(
          suyas,
          (id) => usuarias.find((u) => u.id === id)?.nombre ?? 'Tía',
          (id) => evidencias.find((e) => e.id === id),
        ),
      };
    },
    [ninoId],
  );
}


/**
 * Solo el nombre de pila, para rotular la captura desde la ficha
 * ("Registrar para Josefa").
 */
export function useNombreNino(ninoId: string | undefined): string | null {
  const consulta = useConsulta(
    async (datos) => (ninoId ? (await datos.nino(ninoId)).nombre : null),
    [ninoId],
  );
  return consulta.valor;
}

export interface VistaAgenda {
  sala: Sala;
  hoy: string;
  dia: string;
  semana: DiaSemana[];
  periodos: PeriodoAgenda[];
  pendientes: number;
  partesResumen: { observados: string; menos: string };
  iea: { numero: 1 | 2 | 3; mes: string };
  nombreAutora: Record<string, string>;
}

/** Agenda de la sala para un día (por defecto, hoy). */
export function useAgenda(dia: string | null): Consulta<VistaAgenda> {
  return useConsulta(
    async (datos) => {
      const sala = await datos.salaActual();
      const hoy = datos.hoy();
      const elegido = dia ?? hoy;
      const [ninos, sugerencias, evidencias, usuarias] = await Promise.all([
        datos.ninos(sala.id),
        datos.sugerencias({ salaId: sala.id }),
        datos.evidencias({ salaId: sala.id }),
        datos.usuarias(),
      ]);
      const nombre = (id: string | undefined) => ninos.find((n) => n.id === id)?.nombre;
      const evaluaciones = evaluacionesValidadas(sugerencias, evidencias);
      return {
        sala,
        hoy,
        dia: elegido,
        semana: semanaDe(hoy, evidencias, sugerencias),
        periodos: agendaDelDia(elegido, evidencias, sugerencias, nombre),
        pendientes:
          sugerencias.filter((s) => s.estado === 'pendiente').length +
          evidencias.filter((e) => e.estado === 'error').length,
        partesResumen: partesResumenSala(resumenSala(ninos, evaluaciones, hoy)),
        iea: proximoIEA(hoy),
        nombreAutora: Object.fromEntries(usuarias.map((u) => [u.id, u.nombre])),
      };
    },
    [dia],
  );
}
