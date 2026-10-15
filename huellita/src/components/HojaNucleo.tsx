import { celda, nivelSiguiente, nombreNucleo } from '../lib/rubrica';
import type { Nivel, NucleoId } from '../lib/tipos';
import { HojaInferior } from './HojaInferior';
import { NumeroNivel } from './ChipNivel';

/**
 * Detalle de un núcleo: descriptor y conductas del nivel actual y del
 * siguiente, como apoyo a la tía (requisito 5.5). Todo sale de la rúbrica.
 */
export function HojaNucleo({
  nucleo,
  nivel,
  conEvidencia,
  onCerrar,
}: {
  nucleo: NucleoId;
  /** Nivel actual; si no hay evidencia, el esperado para su edad. */
  nivel: Nivel;
  conEvidencia: boolean;
  onCerrar: () => void;
}) {
  const siguiente = nivelSiguiente(nivel);
  const pasos: { nivel: Nivel; rotulo: string }[] = [
    { nivel, rotulo: conEvidencia ? 'Ahora' : 'Para su edad' },
    ...(siguiente !== nivel ? [{ nivel: siguiente, rotulo: 'Siguiente' }] : []),
  ];

  return (
    <HojaInferior titulo={nombreNucleo(nucleo)} onCerrar={onCerrar}>
      <p className="mb-3 mt-1 text-[14px] text-tinta-2">
        {conEvidencia
          ? 'Lo que se espera en este nivel y en el siguiente.'
          : 'Todavía no hay registros. Esto es lo que se espera a su edad.'}
      </p>
      {pasos.map((paso) => {
        const c = celda(nucleo, paso.nivel);
        return (
          <section
            key={paso.rotulo}
            className="mb-3 rounded-tarjeta border border-linea bg-papel p-[14px]"
          >
            <div className="flex items-center gap-[10px]">
              <NumeroNivel nivel={paso.nivel} />
              <strong>
                {paso.rotulo}: {c.nombreNivel}
              </strong>
            </div>
            <p className="mt-2 text-[15px] text-tinta-2">{c.descriptor}</p>
            <ul className="mt-2 list-disc pl-5 text-[15px]">
              {c.conductas.map((conducta) => (
                <li key={conducta} className="mb-1">
                  {conducta}
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </HojaInferior>
  );
}
