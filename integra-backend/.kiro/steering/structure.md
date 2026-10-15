---
inclusion: always
---
# Estructura (carpeta `integra-backend/` dentro del repo `BastiCan/Hackathon`)

Todo archivo nuevo va dentro de `integra-backend/`. No tocar nada fuera de esta carpeta.

```
integra-backend/
├── .kiro/                      # steering, spec y MCP de Kiro
├── data/
│   ├── raw/                    # dataset E-1 original (solo lectura)
│   └── processed/              # rubrica.json y fewshot.json (YA generados), embeddings_rubrica.json (lo genera Kiro)
├── src/
│   ├── core/
│   │   ├── config.py           # env vars; carga la rúbrica desde S3 o desde data/processed (FUENTE_DATOS)
│   │   ├── modelos.py          # pydantic: Entrada, Fragmento, Observacion, Conducta, Sugerencia, Candidato
│   │   ├── rubrica.py          # cruce código → nivel, dominio, texto (sin IA)
│   │   ├── edad.py             # edad en meses y niveles esperados (solo código, después de evaluar)
│   │   ├── nombres.py          # normalización y resolución contra la nómina
│   │   ├── validaciones.py
│   │   ├── postproceso.py      # consolidación de corridas: nivel, certeza, comentario
│   │   ├── llm.py              # call_json (Bedrock Converse)
│   │   ├── retriever.py        # búsqueda por embeddings sobre la rúbrica
│   │   ├── datos.py            # leer nómina/educadora y guardar observaciones (DynamoDB o local)
│   │   └── pipeline.py         # procesar_nota(entrada) -> Resultado
│   ├── prompts/                # separar_identificar.md, extraer_conductas.md, clasificar.md
│   ├── schemas/                # JSON Schema de salida de cada prompt
│   └── handler.py              # Lambda: evento -> pipeline -> respuesta
├── scripts/                    # embeber_rubrica.py, cargar_aws.py, pipeline_local.py, medir.py
├── events/                     # eventos de prueba para invocar la Lambda
├── tests/{unit,llm,fixtures}/
├── docs/                       # AWS_SETUP.md, DECISIONES.md
├── template.yaml               # AWS SAM
└── samconfig.toml
```

## Convenciones
- Identificadores en español sin tildes ni ñ (`nino`, `anio`).
- `handler.py` es delgado: valida el evento, llama a `pipeline.procesar_nota`, devuelve el resultado.
- Lógica sin AWS en `core/` con test unitario. IDs con prefijo: `CAP-<ulid>`, `OBS-<ulid>`.
