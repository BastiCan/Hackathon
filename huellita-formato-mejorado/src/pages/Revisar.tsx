import { Check } from 'lucide-react';
import { useState } from 'react';
import { useAviso } from '../app/aviso';
import { useCaptura } from '../app/captura';
import { useRevisar, type NotaPendiente } from '../app/hooks';
import { useServicios } from '../app/servicios';
import { Boton } from '../components/Boton';
import { HojaCambiar } from '../components/HojaCambiar';
import { TarjetaError, TarjetaSugerencia } from '../components/TarjetaSugerencia';
import type { Sugerencia } from '../lib/tipos';
import type { CambiosValidacion } from '../services/datos';
import { mensajeParaTia } from '../services/errores';

/** Lo que dura la transición de salida de una nota resuelta. */
const DURACION_SALIDA_MS = 160;

/**
 * Pantalla 2: Revisar. Cada nota es un post-it con lo que Huellita leyó pegado
 * debajo. Nada se guarda como evaluación sin que la tía lo confirme.
 */
export function Revisar() {
  const { datos } = useServicios();
  const aviso = useAviso();
  const abrirCaptura = useCaptura();
  const vista = useRevisar();
  const [cambiando, setCambiando] = useState<Sugerencia | null>(null);
  /** Notas que se están despidiendo con la transición de salida (tarea 10). */
  const [saliendo, setSaliendo] = useState<string[]>([]);

  /** Deja ver la transición antes de guardar; dura menos que un pestañeo. */
  const conSalida = (ids: string[], accion: () => void) => {
    if (saliendo.length > 0) return;
    setSaliendo(ids);
    window.setTimeout(() => {
      accion();
      setSaliendo([]);
    }, DURACION_SALIDA_MS);
  };

  if (vista.cargando) {
    return (
      <p role="status" className="py-10 text-center text-tinta-2">
        Cargando tus notas…
      </p>
    );
  }
  if (!vista.valor) {
    return (
      <p className="rounded-tarjeta border border-linea bg-papel p-4 text-tinta-2">
        {vista.error ?? 'No pudimos cargar tus notas.'}
      </p>
    );
  }

  const { notas, conError, seguras, ninos } = vista.valor;

  /** Si el cambio no se guardó (por ejemplo, sin conexión), la nota vuelve y se avisa. */
  const fallo = (error: unknown) =>
    aviso(mensajeParaTia(error, 'No pudimos guardar el cambio. Inténtalo de nuevo.'));

  /** Deshacer = devolver las sugerencias tal como estaban antes. */
  const deshacerCon = (previas: Sugerencia[]) => () => {
    void datos.guardarSugerencias(previas).catch(fallo);
  };

  const guardar = (nota: NotaPendiente) => {
    const previa = [{ ...nota.sugerencia }];
    conSalida([nota.sugerencia.id], () => {
      void datos.validar(nota.sugerencia.id).then(() => {
        const mensaje =
          nota.sugerencia.tipo === 'nota_sala'
            ? 'Nota guardada'
            : `Guardado en la ficha de ${nota.nombreNino ?? nota.sugerencia.nombreDetectado ?? 'la sala'}`;
        aviso(mensaje, deshacerCon(previa));
      }, fallo);
    });
  };

  const descartar = (nota: NotaPendiente) => {
    const previa = [{ ...nota.sugerencia }];
    conSalida([nota.sugerencia.id], () => {
      void datos
        .descartar(nota.sugerencia.id)
        .then(() => aviso('Descartada', deshacerCon(previa)), fallo);
    });
  };

  const cambiar = (sugerencia: Sugerencia, cambios: CambiosValidacion) => {
    const previa = [{ ...sugerencia }];
    setCambiando(null);
    conSalida([sugerencia.id], () => {
      void datos
        .validar(sugerencia.id, cambios)
        .then(() => aviso('Corregido y guardado', deshacerCon(previa)), fallo);
    });
  };

  const aceptarSeguras = () => {
    const altas = notas.filter(
      (n) => n.sugerencia.tipo === 'evaluacion' && n.sugerencia.certeza === 'alta',
    );
    if (altas.length === 0) return;
    const previas = altas.map((n) => ({ ...n.sugerencia }));
    conSalida(
      altas.map((n) => n.sugerencia.id),
      () => {
        void Promise.all(altas.map((n) => datos.validar(n.sugerencia.id))).then(
          () =>
            aviso(
              `${altas.length} ${altas.length === 1 ? 'guardada' : 'guardadas'}`,
              deshacerCon(previas),
            ),
          fallo,
        );
      },
    );
  };

  const total = notas.length + conError.length;

  return (
    <>
      <p className="rotulo">Revisar</p>
      <h1>¿Está bien lo que leyó Huellita?</h1>
      <p className="text-[15px] text-tinta-2">
        Confirma cada registro. Ninguna evaluación se guarda sin tu revisión.
      </p>

      {total > 0 ? (
        <div className="mb-3 mt-2 flex flex-col gap-2">
          <span className="text-[15px] text-tinta-2">
            {total} {total === 1 ? 'registro pendiente' : 'registros pendientes'}
          </span>
          {seguras > 0 ? (
            <Boton variante="sec" ancho onClick={aceptarSeguras}>
              <Check aria-hidden="true" className="h-[18px] w-[18px]" />
              Confirmar los de confianza alta ({seguras})
            </Boton>
          ) : null}
        </div>
      ) : null}

      {total === 0 ? (
        <div className="px-5 py-14 text-center text-tinta-2">
          <span className="mb-[6px] block text-[18px] font-bold text-tinta">Todo revisado</span>
          Cuando registres algo nuevo, aparecerá aquí.
        </div>
      ) : null}

      {/* En escritorio las tarjetas se reparten en dos columnas. */}
      <div className="lg:grid lg:grid-cols-2 lg:items-start lg:gap-4">
        {notas.map((nota, i) => (
          <TarjetaSugerencia
            key={nota.sugerencia.id}
            nota={nota}
            indice={i}
            saliendo={saliendo.includes(nota.sugerencia.id)}
            onGuardar={() => guardar(nota)}
            onCambiar={() => setCambiando(nota.sugerencia)}
            onDescartar={() => descartar(nota)}
          />
        ))}

        {conError.map((nota, i) => (
          <TarjetaError
            key={nota.evidencia.id}
            nota={nota}
            indice={notas.length + i}
            onEscribir={() => abrirCaptura('texto')}
            onDescartar={() => {
              // La evidencia queda resuelta y sale de Revisar; su archivo ya se
              // borró de la memoria al marcarla.
              void datos
                .marcarEvidencia(nota.evidencia.id, 'lista')
                .then(() => aviso('Descartada'), fallo);
            }}
          />
        ))}
      </div>

      {cambiando ? (
        <HojaCambiar
          sugerencia={cambiando}
          ninos={ninos}
          onGuardar={(cambios) => cambiar(cambiando, cambios)}
          onCerrar={() => setCambiando(null)}
        />
      ) : null}
    </>
  );
}
