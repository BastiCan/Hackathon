import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { Jardin, MisionItem, NinoEstado } from "../types";
import CaptureBox from "../components/CaptureBox";
import MissionCard from "../components/MissionCard";

const ESTADO_LABEL: Record<string, string> = {
  al_dia: "Al día",
  sin_evidencia: "Sin evidencia",
  posible_rezago: "Posible rezago",
  ingreso_reciente: "Ingreso reciente",
};

export default function SalaView() {
  const nav = useNavigate();
  const [jardines, setJardines] = useState<Jardin[]>([]);
  const [idJardin, setIdJardin] = useState<string>("");
  const [salas, setSalas] = useState<string[]>([]);
  const [sala, setSala] = useState<string>("");
  const [ninos, setNinos] = useState<NinoEstado[]>([]);
  const [mision, setMision] = useState<MisionItem[]>([]);

  useEffect(() => {
    api.jardines().then((js) => {
      setJardines(js);
      if (js.length) setIdJardin(js[0].id_jardin);
    });
  }, []);

  useEffect(() => {
    if (!idJardin) return;
    api.salas(idJardin).then((ss) => {
      setSalas(ss);
      setSala(ss[0] ?? "");
    });
  }, [idJardin]);

  useEffect(() => {
    if (!idJardin || !sala) return;
    api.ninosDeSala(idJardin, sala).then(setNinos);
    api.mision(idJardin, sala).then(setMision);
  }, [idJardin, sala]);

  return (
    <>
      <div className="card">
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <select value={idJardin} onChange={(e) => setIdJardin(e.target.value)}>
            {jardines.map((j) => (
              <option key={j.id_jardin} value={j.id_jardin}>
                {j.nombre_fantasia} ({j.comuna})
              </option>
            ))}
          </select>
          <select value={sala} onChange={(e) => setSala(e.target.value)}>
            {salas.map((s) => (
              <option key={s} value={s}>
                Sala {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      <MissionCard items={mision} />

      <CaptureBox />

      <div className="card">
        <h2>Mi sala ({ninos.length})</h2>
        <div className="room-grid">
          {ninos.map((n) => (
            <div
              key={n.nino.id_nino}
              className="child"
              onClick={() => nav(`/nino/${n.nino.id_nino}`)}
            >
              <div className="row">
                <span className="child-id">{n.nino.id_nino}</span>
                <span className={`dot ${n.estado}`} title={ESTADO_LABEL[n.estado]} />
              </div>
              <div className="row" style={{ marginTop: 6 }}>
                <span className="muted">{n.edad_meses} meses</span>
                {n.nivel_actual != null && (
                  <span className="level-badge">N{n.nivel_actual}</span>
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="legend">
          <span>
            <i className="dot al_dia" /> Al día
          </span>
          <span>
            <i className="dot sin_evidencia" /> Sin evidencia
          </span>
          <span>
            <i className="dot posible_rezago" /> Posible rezago
          </span>
          <span>
            <i className="dot ingreso_reciente" /> Ingreso reciente
          </span>
        </div>
      </div>
    </>
  );
}
