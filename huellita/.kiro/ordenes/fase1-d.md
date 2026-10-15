# Orden: revisión final de calidad (solo frontend)

Eres el revisor final de Huellita antes de la demo ante el jurado de la hackathon. **Solo frontend**: nada de AWS ni bases de datos.

Lee `.kiro/steering/` completo, `.kiro/diseno/prototipo.html`, `DEMO.md`, `PROGRESO.md` y `PENDIENTES.md`. Luego levanta la app (`npm run build` y `npm run preview`) y **recórrela como si fueras una tía con el celular en la mano** (360 y 390 px), y también en escritorio (1280 px) como directora.

Busca y corrige, en este orden:
1. **Errores funcionales** del recorrido de `DEMO.md`: cualquier cosa que se rompa, se trabe, muestre datos incoherentes (contadores, niveles, frescura o bandera que no calzan con las reglas de `rubrica.md`) o no actualice la pantalla después de una acción.
2. **Fidelidad visual al prototipo**: diferencias de espaciado, tamaños, alineación, tipografía, colores o textos. Mantén el chip de nivel en pastel con número en tinta (decisión de accesibilidad ya tomada).
3. **Pulido UX**: transiciones suaves, estados de carga, vacío y error amables, textos claros en español de Chile, que ningún texto se corte o desborde con nombres largos ("Maximiliano") y que la primera impresión de Mi sala se vea impecable.
4. **Consistencia**: el mismo nombre para la misma acción en todo el flujo, y los mismos íconos y estilos de botones.

Reglas:
- Haz cambios pequeños y seguros. No reescribas pantallas que ya funcionan.
- Después de cada grupo de cambios: `npm run build` sin errores y `npm test` en verde (hoy son 110 pruebas; no las borres).
- Al final, agrega a `PROGRESO.md` una sección "Revisión final" con la lista de lo que encontraste y corregiste, y lo que dejaste sin tocar y por qué.
