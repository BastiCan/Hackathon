# Plan de implementación: Huellita

Ejecutar en orden. Al terminar cada tarea: `npm run build` sin errores, `npm test` en verde, y marcar `[x]`.

> **Actualización (15-10-2026):** la app pasó a la rúbrica E-1 del backend (5 núcleos × 9 niveles, `data/rubrica_e1.json`) y la Agenda se reemplazó por Inicio. Donde este plan diga 8 núcleos, nivel 1–8 o `rubrica_8_niveles.json`, mandan `.kiro/steering/rubrica.md` e `interfaz.md`. Detalle en `PROGRESO.md`.

## Fase 1: Interfaz completa con datos de prueba (sin AWS)

- [x] 1. Crear el proyecto base
  - Vite + React 18 + TypeScript en la raíz de `huellita/` (sin borrar `.kiro/` ni `data/`).
  - Tailwind CSS, React Router, `lucide-react`, Vitest y `vite-plugin-pwa` (manifest: nombre "Huellita", color de tema `#1F4E9A`, ícono simple generado en SVG).
  - Permitir importar los JSON de `data/` (alias `@data`).
  - Scripts: `dev`, `build`, `test`, `preview`.
  - _Requisitos: 9.1, 9.2_

- [x] 2. Tipos de dominio y carga de la rúbrica
  - `src/lib/tipos.ts` según el diseño.
  - `src/lib/rubrica.ts`: cargar `data/rubrica_8_niveles.json`; funciones `niveles()`, `nucleos()`, `descriptor(nucleo, nivel)`, `conductas(nucleo, nivel)` y `colorNivel(nivel)` (colores de `interfaz.md`).
  - _Requisitos: 2.6, 5.5_

- [x] 3. Lógica de evaluación con pruebas
  - `src/lib/evaluacion.ts` con todas las funciones del diseño y las reglas de `rubrica.md`.
  - `src/lib/evaluacion.test.ts`: casos de frescura (13, 14, 30 y 31 días, sin evidencia), nivel esperado en los bordes de cada rango, bandera de revisar avance (1 evidencia → no; 2 evidencias bajas en fechas distintas → sí; 2 en la misma fecha → no; evidencias bajas solo respecto de la edad actual pero normales para la edad en su fecha → no). Con `data/semilla.json` y `fechaDemo`, solo Josefa (núcleo LV) debe quedar marcada, mediana del nivel general y núcleo menos cubierto.
  - _Requisitos: 4.4, 5.2, 5.3_

- [x] 4. Servicios locales
  - `src/services/datos.ts`: interfaz `DataService` + `DataServiceLocal` (lee `data/semilla.json`, persiste en `localStorage` con la clave `huellita:v1`, `suscribir` con un emisor simple, `reiniciarDemo`).
  - `src/services/ia.ts`: interfaz `IAService` + `IAServiceSimulado` según el diseño (guiones `demoCapturas`, búsqueda de nombres, nota de sala, latencia de 1,5 s).
  - `src/services/captura.ts`: `capturar(formato, blob?, texto?, ninoId?)`, que guarda la evidencia y procesa en segundo plano.
  - Pruebas de `IAServiceSimulado`: nombre exacto → certeza alta; dos niños → 2 sugerencias; texto grupal → nota_sala; nombre desconocido → certeza baja sin `ninoId`.
  - _Requisitos: 1.5, 2.3, 2.4, 2.5_

- [x] 5. Layout, navegación y sesión de demo
  - Barra inferior con Mi sala, Revisar (con contador de pendientes) y Directora (solo para el rol directora).
  - Pantalla de entrada simple para la demo: elegir usuaria (tarjetas "Tía Ana · Medio Menor A", "Tía Rosa · Medio Menor A", "Directora Carmen"). Recordar la elección.
  - Menú de usuaria: cambiar usuaria, cambiar sala y "Reiniciar demo".
  - _Requisitos: 6.1, 6.2, 6.3_

- [x] 6. Pantalla Mi sala
  - Aviso de pendientes, chips de filtro con conteo, grilla de `TarjetaNino` (iniciales, nombre, punto de frescura, chip de nivel general y bandera) y resumen de la sala.
  - Leyenda del semáforo y la bandera (botón "?").
  - Estados de carga y vacío.
  - _Requisitos: 4.1–4.6_

- [x] 7. Captura (Foto, Audio y Texto)
  - Barra de captura con 3 botones grandes (Audio destacado) sobre la navegación, en Mi sala y en la ficha.
  - Foto: input con `capture="environment"`, vista previa y Enviar.
  - Audio: MediaRecorder, contador y máximo de 60 s; si no hay permiso de micrófono, mensaje claro y ofrecer Texto.
  - Texto: hoja inferior con área de texto con foco y Enviar.
  - Aviso "Listo, lo verás en Revisar" y retorno inmediato. Si se captura desde la ficha, asociar el niño/a.
  - _Requisitos: 1.1–1.6, 1.8_

- [x] 8. Pantalla Revisar
  - Lista de `TarjetaSugerencia` según `interfaz.md` (origen, cita, chip del niño/a, núcleo, nivel con nombre, conducta, certeza y 3 botones).
  - Hoja "Cambiar": selector de niño/a, núcleo y nivel 1–8 con descriptor y conductas de cada nivel.
  - Tarjeta de nota de sala (Guardar como nota o Descartar).
  - Tarjeta de error ("No pudimos leer esta nota").
  - "Aceptar las de certeza alta" con opción de deshacer durante 5 s.
  - Estado vacío "Todo al día. Buen trabajo, tía."
  - _Requisitos: 3.1–3.7_

- [x] 9. Pantalla Ficha del niño/a
  - Encabezado, resumen por plantilla (por ejemplo: "Avanza bien en X; conviene observar más Y."), barras de los 8 núcleos con color de nivel y bandera (4 visibles + "Ver los 8").
  - Tarjeta "Observar ahora".
  - Hoja de detalle por núcleo: descriptor y conductas del nivel actual y del siguiente.
  - Historial con filtro por núcleo y botón "Registrar para [nombre]".
  - _Requisitos: 5.1–5.5_

- [x] 10. Pulido visual y accesibilidad
  - Revisar en 360 px, 390 px y 1280 px: sin desplazamiento horizontal y áreas táctiles de ≥ 44 px.
  - `aria-label` en los botones con solo ícono, foco visible y contraste AA.
  - Microinteracciones simples (transición al aceptar una tarjeta). Sin sombras pesadas.
  - _Requisitos: 9.1, 9.3_

- [x] 11. PWA y sin conexión
  - Service worker que cachea la app y los datos de demo; probar con `npm run build && npm run preview` y abrir sin red.
  - _Requisitos: 9.2_

- [x] 12. Revisión de privacidad de la Fase 1
  - Confirmar: ninguna foto de niño en la interfaz, nada de datos de niños en URLs (solo IDs), sin `console.log` con datos y las fotos o audios capturados quedan solo en memoria local.
  - _Requisitos: 8.1, 8.2, 8.5_

- [x] 13. Guion de demo
  - Crear `DEMO.md` con el recorrido de 3 minutos:
    1. Entrar como tía Ana y ver Mi sala (semáforo, Josefa con bandera).
    2. Tocar Foto, sacar foto a cualquier cosa y ver que llega a Revisar el guion del post-it de Josefa.
    3. Aceptarlo y ver que se actualiza su ficha.
    4. Grabar un audio (guion de Emilio) y usar "Cambiar" para corregir el nivel.
    5. Mostrar una nota grupal como nota de sala.
    6. Entrar como directora.
  - Verificar que el recorrido funciona de principio a fin después de "Reiniciar demo".

- [x] 14. Pantalla Directora (solo visual)
  - Ruta `/directora`, visible solo para el rol directora: una tarjeta por sala con nº de niños, % observados en 30 días, nº con "revisar avance" y núcleo menos cubierto (calculado con `evaluacion.ts` sobre los datos de prueba).
  - Al tocar una sala, se abre su vista Mi sala en modo lectura.
  - Botones "Mover de sala" y "Dar de baja" con confirmación que solo cambian los datos de prueba en memoria.
  - _Requisitos: 7.1, 7.2_

## Fuera de alcance de este repositorio (lo hace el equipo de backend)
No implementar nada de lo siguiente: Amplify, Cognito, DynamoDB, S3, Lambda, Bedrock, Transcribe, Rekognition ni hosting. El frontend se queda con `DataServiceLocal` e `IAServiceSimulado`. El equipo de backend conectará sus servicios implementando las interfaces `DataService` e `IAService` de `src/services/`, así que esas interfaces deben quedar claras, tipadas y documentadas con comentarios JSDoc breves.
