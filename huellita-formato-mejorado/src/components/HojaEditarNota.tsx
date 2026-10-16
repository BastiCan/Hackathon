import { useState } from 'react';
import { Boton } from './Boton';
import { HojaInferior } from './HojaInferior';

/**
 * Hoja "Editar nota de la sala": la tía corrige el texto de una observación
 * general (nota de sala) ya guardada. Solo texto libre; no hay núcleo ni nivel
 * porque no es una evaluación de un niño o niña.
 */
export function HojaEditarNota({
  textoInicial,
  onGuardar,
  onCerrar,
}: {
  textoInicial: string;
  onGuardar: (texto: string) => void;
  onCerrar: () => void;
}) {
  const [texto, setTexto] = useState(textoInicial);
  const limpio = texto.trim();

  return (
    <HojaInferior titulo="Editar nota de la sala" onCerrar={onCerrar}>
      <label className="mt-[10px] block text-[15px] text-tinta-2">
        Observación general
        <textarea
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          rows={5}
          autoFocus
          className="mt-1 w-full rounded-campo border border-linea bg-papel px-[10px] py-2 text-base text-tinta"
          placeholder="Lo que pasó en la sala (asistencia, clima del grupo, acuerdos del equipo…)"
        />
      </label>
      <p className="mb-3 mt-1 text-[13px] text-tinta-2">
        No es una evaluación de un niño o niña. Se guarda en el diario de la sala.
      </p>
      <Boton
        ancho
        variante="pri"
        disabled={limpio.length === 0 || limpio === textoInicial.trim()}
        onClick={() => onGuardar(limpio)}
      >
        Guardar cambios
      </Boton>
    </HojaInferior>
  );
}