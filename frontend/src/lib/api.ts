export type Accion = "normales" | "explicitas_guardar" | "explicitas_borrar";
export type CategoriaConsola = "explicito" | "no_explicito" | "revisar_manual";
export type Direccion = "left" | "right" | "up";

export type Conteos = Record<Accion, number>;
export type ConteosConsola = Record<CategoriaConsola, number>;

export type LoteResumen = {
  etiqueta: string;
  path: string;
  conteos: ConteosConsola;
  pendientes: number;
};

export type ResumenConsola = {
  root: string;
  es_resultado_consola: boolean;
  conteos_consola: ConteosConsola;
  pendientes: number;
  lotes: LoteResumen[];
  filtro: CategoriaConsola | null;
  elegida?: string;
};

export type FotoMeta = {
  id: number;
  nombre: string;
  relativo: string;
  lote: string;
  subcarpeta: string;
  preview: string;
  categoria_consola: CategoriaConsola;
  /** Por qué la marcó el pulido (NudeNet / CLIP); null si vino de la consola. */
  motivo?: string | null;
};

export type Estado = {
  destino: string;
  origen: string | null;
  fase: "setup" | "review" | "done";
  foto: FotoMeta | null;
  siguientes: FotoMeta[];
  indice: number;
  total: number;
  restantes: number;
  conteos: Conteos;
  puede_deshacer: boolean;
  ultima_accion: Accion | null;
  resumen_consola: ResumenConsola | null;
  filtro: CategoriaConsola | null;
  movidas_normales?: number;
};

export type DirEntry = {
  nombre: string;
  path: string;
  es_resultado_consola?: boolean;
  categoria?: CategoriaConsola;
};

export type Exploracion = {
  path: string;
  parent: string | null;
  dirs: DirEntry[];
  fotos_aqui: number;
  shortcuts: { nombre: string; path: string }[];
  consola: ResumenConsola | null;
  lotes_hijos: number;
};

export const ACCIONES: Record<Accion, { label: string; corto: string; dir: Direccion; carpeta: string; color: string; rgb: string }> = {
  explicitas_borrar: { label: "Explícitas a borrar", corto: "Se va", dir: "left", carpeta: "explicitas_borrar/", color: "var(--color-no)", rgb: "255 93 115" },
  explicitas_guardar: { label: "Explícitas a guardar", corto: "Aparte", dir: "up", carpeta: "explicitas_guardar/", color: "var(--color-apart)", rgb: "245 193 74" },
  normales: { label: "Normales", corto: "Se queda", dir: "right", carpeta: "normales/", color: "var(--color-keep)", rgb: "62 224 125" },
};

export const ACCION_POR_DIR: Record<Direccion, Accion> = {
  left: "explicitas_borrar",
  up: "explicitas_guardar",
  right: "normales",
};

export const CATEGORIAS: Record<CategoriaConsola, { label: string; corto: string; rgb: string }> = {
  explicito: { label: "Explícito (IA)", corto: "explícito", rgb: "255 93 115" },
  revisar_manual: { label: "Revisar manual (IA dudosa)", corto: "revisar", rgb: "139 123 255" },
  no_explicito: { label: "No explícito (IA)", corto: "no explícito", rgb: "62 224 125" },
};

async function api<T>(url: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json().catch(() => ({ ok: false, error: "Respuesta inválida del servidor" }));
  if (!res.ok || data.ok === false) throw new Error(data.error || "Error de red");
  return data as T;
}

const post = <T,>(url: string, body: unknown = {}) => api<T>(url, { method: "POST", body: JSON.stringify(body) });

export const backend = {
  estado: () => api<Estado>("/api/estado"),
  destino: (path: string) => post<Estado>("/api/destino", { path }),
  inspeccionar: (path: string) => api<ResumenConsola>(`/api/inspeccionar?path=${encodeURIComponent(path)}`),
  origen: (path: string, pasar_normales: boolean) => post<Estado>("/api/origen", { path, pasar_normales }),
  accion: (accion: Accion) => post<Estado>("/api/accion", { accion }),
  deshacer: () => post<Estado>("/api/deshacer"),
  cerrar: () => post<Estado>("/api/cerrar"),
  explorar: (path?: string) => api<Exploracion>(`/api/explorar${path ? `?path=${encodeURIComponent(path)}` : ""}`),
};
