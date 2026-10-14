import { Routes, Route } from "react-router-dom";
import SalaView from "./views/SalaView";
import FichaView from "./views/FichaView";

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>Sala Caracolitos · Tía Mercedes</h1>
          <div className="sub">Integra · Documentación asistida por IA</div>
        </div>
        <span>Hoy</span>
      </header>

      <Routes>
        <Route path="/" element={<SalaView />} />
        <Route path="/nino/:id" element={<FichaView />} />
      </Routes>
    </div>
  );
}
