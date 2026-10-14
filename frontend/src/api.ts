import type {
  Alerta,
  FichaNino,
  Jardin,
  MisionItem,
  NinoEstado,
  NivelRuta,
  SugerenciaIA,
} from "./types";

async function get<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} en ${url}`);
  return res.json() as Promise<T>;
}

export const api = {
  jardines: () => get<Jardin[]>("/api/jardines"),
  salas: (idJardin: string) => get<string[]>(`/api/jardines/${idJardin}/salas`),
  ninosDeSala: (idJardin: string, sala: string) =>
    get<NinoEstado[]>(`/api/salas/${idJardin}/${sala}/ninos`),
  mision: (idJardin: string, sala: string) =>
    get<MisionItem[]>(`/api/salas/${idJardin}/${sala}/mision`),
  ficha: (idNino: string) => get<FichaNino>(`/api/ninos/${idNino}`),
  alertas: (idNino: string) => get<Alerta[]>(`/api/ninos/${idNino}/alertas`),
  ruta: () => get<NivelRuta[]>("/api/ruta"),
  procesarCaptura: async (texto: string): Promise<SugerenciaIA[]> => {
    const res = await fetch("/api/capturas/procesar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto }),
    });
    if (!res.ok) throw new Error(`Error al procesar: ${res.status}`);
    const data = (await res.json()) as { sugerencias: SugerenciaIA[] };
    return data.sugerencias;
  },
};
