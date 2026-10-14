import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api";
import type { FichaNino } from "../types";

export default function FichaView() {
  const { id } = useParams();
  const nav = useNavigate();
  const [ficha, setFicha] = useState<FichaNino | null>(null);

  useEffect(() => {
    if (id) api.ficha(id).then(setFicha);
  }, [id]);

  if (!ficha) return <p className="muted">Cargando…</p>;

  const { estado, observaciones, alertas } = ficha;

  return (
    <>
      <span className="back" onClick={() => nav(-1)}>
        ← Volver a la sala
      </span>

      <div className="card">
        <h2>{estado.nino.id_nino}</h2>
        <p className="muted">
          {estado.edad_meses} meses · Sala {estado.nino.sala_grupo} ·
          {estado.nivel_actual != null
            ? ` Nivel actual ${estado.nivel_actual}`
            : " Sin nivel registrado"}
        </p>
        <p className="muted">
          Última observación: {estado.ultima_observacion ?? "—"}
        </p>
      </div>

      {alertas.length > 0 && (
        <div className="card">
          <h2>⚠️ Alertas</h2>
          {alertas.map((a, i) => (
            <div key={i} className={`alert-box ${a.severidad}`}>
              <strong>
                {a.tipo === "posible_rezago" ? "🔴" : "🟡"} {a.mensaje}
              </strong>
              <div className="muted" style={{ marginTop: 4 }}>
                {a.accion_sugerida}
                {a.confirmada ? " · confirmada" : " · por confirmar"}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <h2>📈 Trayectoria ({observaciones.length} observaciones)</h2>
        {observaciones.length === 0 ? (
          <p className="muted">Aún no hay observaciones registradas.</p>
        ) : (
          <div className="timeline">
            {[...observaciones]
              .reverse()
              .map((o) => (
                <div className="event" key={o.id_observacion}>
                  <div>
                    <strong>{o.fecha_observacion}</strong>{" "}
                    <span className="level-badge">N{o.nivel_estimado}</span>{" "}
                    <span className="muted">· {o.formato_captura}</span>
                  </div>
                  {o.nota_breve && (
                    <div className="muted" style={{ marginTop: 2 }}>
                      {o.nota_breve}
                    </div>
                  )}
                </div>
              ))}
          </div>
        )}
      </div>
    </>
  );
}
