# Diseño: Huellita

## Visión general
La app es una PWA en React. Todas las pantallas consumen dos interfaces: `DataService` (datos) e `IAService` (procesamiento de evidencias). En la Fase 1 ambas son locales o simuladas, y la demo funciona sin AWS ni internet. En las Fases 2–3 se cambian por implementaciones con AWS Amplify y Bedrock, sin tocar las pantallas.

```
[Mi sala]   [Revisar]   [Ficha]   [Directora]
      \         |          |          /
       ---- hooks (useSala, usePendientes, useNino) ----
                |                     |
         DataService            IAService
         ├ Local (F1)           ├ Simulado (F1)
         └ Amplify (F2)         └ Bedrock (F3)
```

## Modelo de datos (`src/lib/tipos.ts`)
```ts
type NucleoId = 'IA'|'CC'|'CM'|'LV'|'LA'|'EN'|'ES'|'PM';
type Nivel = 1|2|3|4|5|6|7|8;
type Rol = 'tia'|'directora';
type Formato = 'foto'|'audio'|'texto';
type Certeza = 'alta'|'media'|'baja';
type EstadoSugerencia = 'pendiente'|'aceptada'|'cambiada'|'descartada';

interface Jardin { id: string; nombre: string; comuna: string; region: string }
interface Sala   { id: string; jardinId: string; nombre: string; nivelEducativo: 'Sala Cuna Menor'|'Sala Cuna Mayor'|'Medio Menor'|'Medio Mayor'|'Transición 1'|'Transición 2' }
interface Usuaria { id: string; nombre: string; rol: Rol; jardinId: string; salaIds: string[] }
interface Nino   { id: string; nombre: string; apellidoInicial: string; fechaNacimiento: string; salaId: string; activo: boolean }

interface Evidencia {
  id: string; salaId: string; autorId: string; creadaEn: string;
  formato: Formato; ninoIdSugerido?: string;
  textoExtraido?: string;
  estado: 'procesando'|'lista'|'error';
}

interface Sugerencia {
  id: string; evidenciaId: string; salaId: string;
  tipo: 'evaluacion'|'nota_sala';
  ninoId?: string;              // undefined si es nota de sala o nombre no reconocido
  nombreDetectado?: string;     // tal como aparece en la evidencia
  nucleo?: NucleoId; nivel?: Nivel;
  conducta?: string;            // texto de la rúbrica
  cita: string;                 // fragmento de la evidencia que la respalda
  certeza: Certeza;
  estado: EstadoSugerencia;
  validadaPor?: string; validadaEn?: string;
  original?: { ninoId?: string; nucleo?: NucleoId; nivel?: Nivel }; // si fue cambiada
}
```
Una **evaluación validada** es una `Sugerencia` con `tipo='evaluacion'` y estado `aceptada` o `cambiada`.

## Interfaces de servicio (`src/services`)
```ts
interface DataService {
  sesion(): Promise<Usuaria>; cambiarUsuaria(id: string): Promise<void>;
  jardin(): Promise<Jardin>; salas(): Promise<Sala[]>;
  ninos(salaId: string): Promise<Nino[]>; nino(id: string): Promise<Nino>;
  sugerencias(filtro: { salaId?: string; ninoId?: string; estado?: EstadoSugerencia[] }): Promise<Sugerencia[]>;
  guardarEvidencia(e: Omit<Evidencia,'id'|'creadaEn'|'estado'>, archivo?: Blob): Promise<Evidencia>;
  guardarSugerencias(s: Sugerencia[]): Promise<void>;
  validar(id: string, cambios?: Partial<Pick<Sugerencia,'ninoId'|'nucleo'|'nivel'>>): Promise<void>;
  descartar(id: string): Promise<void>;
  moverNino(ninoId: string, salaId: string): Promise<void>; darDeBaja(ninoId: string): Promise<void>;
  suscribir(cb: () => void): () => void;   // para refrescar la interfaz
  reiniciarDemo(): Promise<void>;
}
interface IAService {
  procesar(evidencia: Evidencia, archivo: Blob | undefined, contexto: { ninos: {id:string; nombre:string}[] }): Promise<Sugerencia[]>;
}
```
- Las pantallas llaman a `capturar()` (en `src/services/captura.ts`), que guarda la evidencia y llama a `IAService.procesar` **en segundo plano**. Al terminar, guarda las sugerencias y notifica a los suscriptores.

## Lógica de evaluación (`src/lib/evaluacion.ts`, funciones puras con pruebas)
- `edadMeses(fechaNacimiento, hoy)`
- `nivelEsperado(edadMeses, rubrica)`
- `nivelActualPorNucleo(evaluaciones)` → `Record<NucleoId, Nivel | null>`
- `nivelGeneral(nivelesPorNucleo)` → mediana redondeada hacia abajo
- `revisarAvance(evaluaciones, nivelEsperado)` → `NucleoId[]`
- `frescura(evaluaciones, hoy)` → `'verde'|'amarillo'|'rojo'`
- `observarAhora(evaluaciones, nivelesActuales, nivelEsperado, rubrica)` → 1–2 conductas con su núcleo
- `resumenSala(ninos, evaluaciones, hoy)` → `{ observadosMes, total, nucleoMenosCubierto }`
Las reglas exactas están en `.kiro/steering/rubrica.md`. Usar una fecha "hoy" inyectable para las pruebas y la demo (`data/semilla.json` → `fechaDemo`).

## IA simulada (Fase 1, `IAServiceSimulado`)
1. Si la evidencia es de **texto** o trae `textoExtraido`, se usa ese texto. Si es una **foto o audio** en la demo, se toma el siguiente "guion" pendiente de `semilla.demoCapturas` (texto preparado que simula lo leído). Así la demo es reproducible.
2. Si el texto coincide exactamente con un `demoCapturas[].texto`, se devuelven sus `sugerencias` predefinidas.
3. Si no: buscar nombres de pila de la sala en el texto (sin tildes ni mayúsculas); por cada niño/a encontrado, elegir el núcleo y la conducta de la rúbrica con más palabras en común con el texto, y el nivel = nivel actual de ese núcleo para el niño/a (o el esperado por edad). Calcular la certeza según `rubrica.md`.
4. Si no hay nombres y el texto habla del grupo ("los niños", "el grupo", "la sala", "asistencia"), devolver una `nota_sala`.
5. Simular una latencia de 1,5 s.

## IA real (Fase 3)
```
App → Amplify Storage (S3 privado: evidencias/{salaId}/{evidenciaId}.{ext}, cifrado, ciclo de vida de 1 día)
   → evento S3 → Lambda procesarEvidencia:
       foto  → Bedrock Claude (visión): "Transcribe literalmente el texto manuscrito…"
       audio → Transcribe (es-US o es-ES) → texto
       texto → Bedrock Claude (clasificación) con:
               - system: rol, reglas de privacidad, rúbrica (data/rubrica_8_niveles.json resumida)
               - user: texto + lista [{id, nombre}] de la sala
               - salida: JSON validado con esquema (tool use / structured output)
       → guarda Sugerencias en DynamoDB → la app se actualiza (suscripción de Amplify Data)
```
**Esquema de salida del clasificador**
```json
{ "items": [ { "tipo": "evaluacion|nota_sala", "ninoId": "NINO-… | null", "nombreDetectado": "…",
  "nucleo": "IA|CC|CM|LV|LA|EN|ES|PM", "nivel": 1, "conducta": "texto exacto de la rúbrica",
  "cita": "fragmento literal de la evidencia", "certeza": "alta|media|baja" } ] }
```
**Reglas del prompt**: usar solo conductas y niveles de la rúbrica; la cita debe ser un fragmento literal; si duda entre dos niveles, elegir el menor y certeza media; nunca inventar nombres; grupo o asistencia → `nota_sala`; responder solo JSON. Validar el JSON en la Lambda y descartar los ítems inválidos.
- Modelo: Claude Sonnet en Bedrock (perfil de inferencia entre regiones si la región no lo tiene). Configurable por variable de entorno.

## Backend Amplify (Fase 2)
- `amplify/auth`: Cognito con email; grupos `tia` y `directora`; atributo personalizado `custom:jardinId`.
- `amplify/data`: modelos `Jardin`, `Sala`, `Usuaria`, `Nino`, `Evidencia` y `Sugerencia`, con reglas de autorización por grupo (una tía lee y escribe solo en sus salas; la directora, en todo su jardín).
- `amplify/storage`: bucket `evidencias` con acceso solo para usuarios autenticados en su ruta de sala, y ciclo de vida de 1 día.
- Script `scripts/cargar-semilla.ts` para poblar DynamoDB desde `data/semilla.json`.

## Manejo de errores
- Si el procesamiento falla: la evidencia queda en estado `error` y aparece en Revisar como "No pudimos leer esta nota" con las opciones "Escribirla" (abre texto con la foto como referencia) o "Descartar".
- Sin cámara o micrófono: mensaje claro y ofrecer Texto.
- Nunca mostrar trazas técnicas a la tía.

## Pruebas
- Unitarias (Vitest) para todas las funciones de `evaluacion.ts` y para `IAServiceSimulado` (casos: nombre exacto, dos niños, nota grupal, nombre desconocido).
- Prueba manual de la demo (guion en `tasks.md`, tarea 13).
