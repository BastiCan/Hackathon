import { useState } from "react";
import { api } from "../api";
import type { SugerenciaIA } from "../types";

const DOMINIO_LABEL: Record<string, string> = {
  motor_grueso: "Motor grueso",
  motor_fino: "Motor fino",
  lenguaje_comunicacion: "Lenguaje y comunicación",
  socioemocional: "Socioemocional",
  cognitivo: "Cognitivo",
};

export default function CaptureBox() {
  const [texto, setTexto] = useState("");
  const [sugerencias, setSugerencias] = useState<SugerenciaIA[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [aceptadas, setAceptadas] = useState<Set<number>>(new Set());

  async function procesar() {
    if (!texto.trim()) return;
    setLoading(true);
    try {
      const res = await api.procesarCaptura(texto);
      setSugerencias(res);
      setAceptadas(new Set());
    } catch (e) {
      alert("No se pudo procesar la captura. ¿Está corriendo el backend?");
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  function aceptar(i: number) {
    setAceptadas((prev) => new Set(prev).add(i));
  }

  return (
    <div className="card">
      <h2>🎙️ Captura rápida</h2>
      <div className="capture-buttons">
        <button type="button" title="Grabar audio (demo: usa texto)">
          <span className="ico">🎙️</span> Audio
        </button>
        <button type="button" title="Tomar foto del cuaderno (demo: usa texto)">
          <span className="ico">📷</span> Foto
        </button>
        <button type="button" title="Escribir">
          <span className="ico">✏️</span> Texto
        </button>
      </div>

      <textarea
        placeholder='Ej: "8 recogió los individuales y me los pasó. 51 clasificó las piezas por color."'
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
      />
      <div style={{ marginTop: 10 }}>
        <button className="btn" onClick={procesar} disabled={loading}>
          {loading ? "Procesando…" : "Procesar con IA"}
        </button>
      </div>

      {sugerencias && (
        <div style={{ marginTop: 16 }}>
          <h2>Por revisar ({sugerencias.filter((s) => s.es_evaluable).length})</h2>
          {sugerencias.length === 0 && (
            <p className="muted">No se detectaron observaciones.</p>
          )}
          {sugerencias.map((s, i) => (
            <div
              key={i}
              className={`suggestion ${s.es_evaluable ? "" : "not-eval"}`}
            >
              {!s.es_evaluable ? (
                <p className="muted">
                  ⚪ Descartada: no parece una observación evaluable (p. ej. nota
                  grupal).
                </p>
              ) : aceptadas.has(i) ? (
                <p style={{ color: "var(--green)", fontWeight: 600 }}>
                  ✓ Guardada
                </p>
              ) : (
                <>
                  <div>
                    <span className="child-id">
                      {s.id_nino_sugerido ?? "Niño no identificado"}
                    </span>{" "}
                    {s.dominio && (
                      <span className="chip dom">{DOMINIO_LABEL[s.dominio]}</span>
                    )}
                    {s.nivel_sugerido != null && (
                      <span className="chip media">Nivel {s.nivel_sugerido}</span>
                    )}
                    <span className={`chip ${s.certeza}`}>
                      certeza {s.certeza}
                    </span>
                  </div>
                  <p className="evidence">"{s.evidencia}"</p>
                  {s.manifestacion_sugerida && (
                    <p className="muted">→ {s.manifestacion_sugerida}</p>
                  )}
                  <div className="actions">
                    <button
                      className="btn small"
                      disabled={!s.id_nino_sugerido}
                      onClick={() => aceptar(i)}
                    >
                      ✓ Aceptar
                    </button>
                    <button className="btn small ghost" onClick={() => aceptar(i)}>
                      ✎ Cambiar
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
