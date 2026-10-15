/**
 * Fotos de post-its. Las de ejemplo son recortes de las fotos reales que
 * Fundación Integra mostró en la presentación del desafío, sin nombres de
 * niños/as. Las que captura la tía se guardan como URL de datos reducida.
 */
import postitHojas from '../assets/demo/postit-hojas.jpg';
import postitIndividuales from '../assets/demo/postit-individuales.jpg';
import postitTortugas from '../assets/demo/postit-tortugas.jpg';

const FOTOS_DEMO: Record<string, string> = {
  'postit-hojas': postitHojas,
  'postit-individuales': postitIndividuales,
  'postit-tortugas': postitTortugas,
};

/** URL lista para `<img src>`, o `undefined` si la evidencia no tiene foto. */
export function urlFoto(foto: string | undefined): string | undefined {
  if (!foto) return undefined;
  if (foto.startsWith('data:') || foto.startsWith('blob:')) return foto;
  return FOTOS_DEMO[foto];
}

/**
 * Reduce una foto en el dispositivo antes de guardarla (lado mayor de 1000 px,
 * JPEG). Si el navegador no puede (por ejemplo, en las pruebas), no guarda foto.
 */
export async function reducirFoto(archivo: Blob, ladoMax = 1000): Promise<string | undefined> {
  try {
    if (typeof createImageBitmap !== 'function' || typeof document === 'undefined') return undefined;
    const imagen = await createImageBitmap(archivo);
    const escala = Math.min(1, ladoMax / Math.max(imagen.width, imagen.height));
    const lienzo = document.createElement('canvas');
    lienzo.width = Math.round(imagen.width * escala);
    lienzo.height = Math.round(imagen.height * escala);
    const ctx = lienzo.getContext('2d');
    if (!ctx) return undefined;
    ctx.drawImage(imagen, 0, 0, lienzo.width, lienzo.height);
    return lienzo.toDataURL('image/jpeg', 0.72);
  } catch {
    return undefined;
  }
}
