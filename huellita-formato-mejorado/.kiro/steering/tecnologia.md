---
inclusion: always
---

# Tecnología y forma de trabajar

## Stack
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS + React Router. PWA con `vite-plugin-pwa` (instalable en el celular y funciona sin conexión).
- **Íconos**: `lucide-react`. Sin otras librerías de UI pesadas.
- **Pruebas**: Vitest para la lógica (`src/lib`), con al menos los casos de las reglas de `rubrica.md`.
- **Este repositorio es SOLO FRONTEND.** El backend (AWS: base de datos, login, IA real) lo construye otro equipo. Aquí **no** se instala ni se configura nada de AWS (ni Amplify, ni Cognito, ni SDKs de AWS) ni ninguna base de datos. Todos los datos salen de `data/semilla.json` y viven en memoria o `localStorage`; la IA es simulada.
- El punto de conexión con el backend son las interfaces `DataService` e `IAService` de `src/services/`. Deben quedar limpias y documentadas para que el otro equipo las implemente sin tocar las pantallas.
- Windows 11 con PowerShell. Usar comandos compatibles (`npm.cmd` funciona si `npm` falla por la política de ejecución de scripts).

## Arquitectura del frontend
```
src/
  app/            rutas y layout (barra inferior, barra de captura, captura)
  pages/          Inicio, MiSala, Revisar, FichaNino, Directora, Entrada
  components/     TarjetaSugerencia, Captura (hojas de foto, audio, texto y subir audio), ChipNivel...
  lib/
    evaluacion.ts reglas de cálculo (puras, con pruebas)
    rubrica.ts    carga y consulta de data/rubrica_e1.json (la rúbrica del backend)
    inicio.ts     semana y próximo IEA de la pantalla de inicio
    audio.ts      revisión de audios subidos (mismas reglas del transcriptor)
    tipos.ts      tipos de dominio
  services/
    datos.ts      interfaz DataService + implementación local (Fase 1) y Amplify (Fase 2)
    ia.ts         interfaz IAService + implementación simulada (Fase 1) y Bedrock (Fase 3)
```
- **Toda la interfaz habla con `DataService` e `IAService`**, nunca directo con JSON ni con AWS. Así, pasar de la Fase 1 a la 2 o 3 es cambiar la implementación, no las pantallas.
- Fase 1: `DataServiceLocal` carga `data/semilla.json` y guarda los cambios en `localStorage` (con un botón oculto "Reiniciar demo" en el menú). `IAServiceSimulado` devuelve sugerencias después de 1,5 s: si el texto coincide con una evidencia de la semilla, usa su sugerencia predefinida; si no, busca nombres de la sala y palabras clave de las conductas de la rúbrica.

## Forma de trabajar
- Seguir el spec `.kiro/specs/app-tias/` **tarea por tarea**, en orden, marcando `[x]` cada tarea completada en `tasks.md`.
- Al terminar cada tarea: `npm run build` sin errores y `npm test` en verde.
- No agregar funcionalidades fuera del spec (nada de chat, asistencia ni notificaciones). Si algo falta, anotarlo en `PENDIENTES.md`.
- Código y comentarios en español donde sean nombres de dominio (niño, sala, núcleo, evidencia); el resto, en inglés idiomático.
- Commits pequeños y descriptivos en español si hay git.
