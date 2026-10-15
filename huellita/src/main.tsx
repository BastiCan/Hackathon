import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
// Tipografías autoalojadas para que la PWA funcione sin conexión
// (ver `.kiro/steering/diseno-visual.md`).
import '@fontsource-variable/bricolage-grotesque/wght.css';
import '@fontsource/atkinson-hyperlegible/latin-400.css';
import '@fontsource/atkinson-hyperlegible/latin-700.css';
import '@fontsource/kalam/latin-400.css';
import { App } from './app/App';
import './estilos.css';

const raiz = document.getElementById('raiz');
if (!raiz) throw new Error('No se encontró el contenedor raíz.');

createRoot(raiz).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
