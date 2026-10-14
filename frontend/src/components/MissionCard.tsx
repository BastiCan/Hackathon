import type { MisionItem } from "../types";
import { Link } from "react-router-dom";

export default function MissionCard({ items }: { items: MisionItem[] }) {
  return (
    <div className="card">
      <h2>🎯 Misión de hoy</h2>
      {items.length === 0 ? (
        <p className="muted">Sin pendientes urgentes. Buen trabajo.</p>
      ) : (
        items.map((m) => (
          <div className="mission-item" key={m.id_nino}>
            <Link to={`/nino/${m.id_nino}`}>
              <strong>{m.id_nino}</strong>
            </Link>{" "}
            <span className="muted">· {m.motivo}</span>
            {m.que_observar && (
              <div className="muted" style={{ marginTop: 4 }}>
                👀 Fíjate si: {m.que_observar}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}
