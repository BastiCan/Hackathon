# Orden: Fase 1, tareas 5 a 9 (pantallas)

Eres el desarrollador de Huellita. Antes de empezar, vuelve a leer `.kiro/steering/` (sobre todo `interfaz.md`, `privacidad.md` y `tecnologia.md`: **este repositorio es solo frontend**), el spec `.kiro/specs/app-tias/` y `PROGRESO.md`, que resume lo ya hecho en las tareas 1 a 4.

Ejecuta, en orden y completas, las **tareas 5, 6, 7, 8 y 9** de `tasks.md`.

Referencia visual (respétala):
- **Mi sala**: encabezado con el nombre de la sala; aviso amarillo suave "N registros por revisar"; chips de filtro; grilla de tarjetas de 3 columnas en el celular (círculo con iniciales, nombre, punto de frescura + chip "N4" y bandera ámbar si hay revisar avance); línea de resumen de la sala; abajo, sobre la barra de navegación, 3 botones grandes Foto · **Audio** (azul Integra `#1F4E9A`, relleno) · Texto.
- **Revisar**: tarjetas con origen (ícono, hora, tía), cita en cursiva o serif, chips de niño/a y núcleo, "Nivel sugerido 4 Afianzando", chip de certeza (Alta verde, Media amarilla, Baja gris), conducta, y 3 botones: **Sí** (verde, relleno) · Cambiar · X.
- **Ficha**: volver + avatar + nombre + edad; caja gris con el resumen; barras horizontales por núcleo con el color de su nivel y número; tarjeta con borde azul "Observar ahora" (ícono de ampolleta); historial como línea de tiempo con borde izquierdo; botón "Registrar para [nombre]".
- Estética: plana, fondo blanco, bordes finos grises, esquinas redondeadas de 12 px en tarjetas, sin sombras pesadas ni degradados. Tipografía del sistema. Todo en español de Chile.

Reglas:
- Las pantallas solo hablan con `DataService` e `IAService` (vía hooks); nunca leen JSON ni `localStorage` directo.
- Usa `fechaDemo` de la semilla como "hoy" en toda la interfaz.
- Áreas táctiles de ≥ 44 px, `aria-label` en botones con solo ícono y sin desplazamiento horizontal en 360 px.
- Al final de cada tarea, `npm run build` y `npm test` deben pasar; marca `[x]` en `tasks.md`. Agrega pruebas de componentes solo donde aporten (no es obligatorio).
- No avances a la tarea 10. Nada de AWS ni funcionalidades fuera del spec.
- Al terminar, **agrega** a `PROGRESO.md` una sección "Tareas 5 a 9" con lo hecho, decisiones, resultado de build y pruebas, y pendientes.
