import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
// Tipografía autoalojada para que la PWA funcione sin conexión. El manual de
// imagen corporativa de Integra pide Calibri; en web usamos Carlito, su
// equivalente libre y métricamente idéntico, que solo trae 400 y 700
// (ver `.kiro/steering/diseno-visual.md`).
import '@fontsource/carlito/latin-400.css';
import '@fontsource/carlito/latin-700.css';
import { App } from './app/App';
import './estilos.css';

const raiz = document.getElementById('raiz');
if (!raiz) throw new Error('No se encontró el contenedor raíz.');

createRoot(raiz).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
