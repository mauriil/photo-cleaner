import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ArrowUp, CornerDownLeft, HardDrive, Images, Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import { backend, CATEGORIAS, type DirEntry, type Exploracion } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { FolderTree, type TreeNode } from "@/components/ui/folder-tree";
import { Kbd } from "@/components/ui/kbd";
import { cn } from "@/lib/utils";

type Props = {
  open: boolean;
  modo: "origen" | "destino";
  inicial?: string | null;
  onClose: () => void;
  onPick: (path: string) => void;
};

function Chip({ rgb, children }: { rgb: string; children: React.ReactNode }) {
  return (
    <span
      style={{ color: `rgb(${rgb})`, background: `rgb(${rgb} / 0.12)`, boxShadow: `inset 0 0 0 1px rgb(${rgb} / 0.3)` }}
      className="shrink-0 rounded-full px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide"
    >
      {children}
    </span>
  );
}

function aNodo(d: DirEntry): TreeNode {
  let badge: React.ReactNode = null;
  if (d.categoria) badge = <Chip rgb={CATEGORIAS[d.categoria].rgb}>{CATEGORIAS[d.categoria].corto}</Chip>;
  else if (d.es_resultado_consola)
    badge = (
      <Chip rgb="245 193 74">
        <span className="inline-flex items-center gap-1">
          <Sparkles className="size-3" /> lote
        </span>
      </Chip>
    );
  return { id: d.path, label: d.nombre, badge, highlight: d.es_resultado_consola, leaf: Boolean(d.categoria) };
}

export function FolderPicker({ open, modo, inicial, onClose, onPick }: Props) {
  const [data, setData] = useState<Exploracion | null>(null);
  const [input, setInput] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  const ir = useCallback(async (path?: string | null) => {
    setCargando(true);
    try {
      const res = await backend.explorar(path || undefined);
      setData(res);
      setInput(res.path);
      setSelected(null);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    if (open) ir(inicial);
  }, [open, inicial, ir]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const load = async (id: string) => (await backend.explorar(id)).dirs.map(aNodo);
  const elegida = selected ?? data?.path ?? "";

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50 grid place-items-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div className="absolute inset-0 bg-black/70 backdrop-blur-md" onClick={onClose} />
          <motion.div
            role="dialog"
            aria-modal
            aria-label={modo === "destino" ? "Elegir carpeta destino" : "Elegir carpeta con fotos"}
            initial={{ opacity: 0, y: 24, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 320, damping: 30 }}
            className="relative flex max-h-[min(760px,92vh)] w-full max-w-2xl flex-col overflow-hidden rounded-3xl border border-line-strong bg-bg-2/95 shadow-[0_0_0_1px_rgb(255_255_255/0.04),0_50px_120px_-20px_rgb(0_0_0/0.9),0_0_120px_-40px_rgb(139_123_255/0.5)]"
          >
            <header className="flex items-start justify-between gap-4 border-b border-line px-6 pb-4 pt-5">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
                  {modo === "destino" ? "Cúmulo final" : "Tus fotos"}
                </p>
                <h2 className="mt-1 text-lg font-semibold tracking-tight">
                  {modo === "destino" ? "¿Dónde junto las fotos decididas?" : "¿Dónde están tus imágenes?"}
                </h2>
                <p className="mt-1 text-sm text-ink-3">
                  {modo === "destino"
                    ? "Se crean normales/, explicitas_guardar/ y explicitas_borrar/ adentro."
                    : "Elegí un *_clasificado o una carpeta madre: detecto todos los lotes adentro (explicito / no_explicito / revisar_manual, también en inglés)."}
                </p>
              </div>
              <Button variant="ghost" size="icon" aria-label="Cerrar" onClick={onClose}>
                <X />
              </Button>
            </header>

            <div className="space-y-3 px-6 pt-4">
              <form
                className="flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (input.trim()) ir(input.trim());
                }}
              >
                <Button
                  variant="secondary"
                  size="icon"
                  aria-label="Subir un nivel"
                  disabled={!data?.parent}
                  onClick={() => ir(data?.parent)}
                >
                  <ArrowUp />
                </Button>
                <div className="relative flex-1">
                  <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    spellCheck={false}
                    placeholder="Pegá una ruta completa y Enter"
                    className="h-10 w-full rounded-xl border border-line-strong bg-black/30 pl-3 pr-10 font-mono text-[13px] text-ink outline-none transition-colors placeholder:text-ink-3 focus:border-accent/60 focus:ring-2 focus:ring-accent/25"
                  />
                  <CornerDownLeft className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-ink-3" />
                </div>
              </form>
              <div className="flex flex-wrap gap-1.5">
                {data?.shortcuts.map((s) => (
                  <button
                    key={s.path}
                    type="button"
                    onClick={() => ir(s.path)}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition-colors",
                      data.path === s.path
                        ? "border-accent/50 bg-accent/15 text-ink"
                        : "border-line bg-white/[0.03] text-ink-2 hover:bg-white/[0.08] hover:text-ink",
                    )}
                  >
                    <HardDrive className="size-3" />
                    {s.nombre}
                  </button>
                ))}
              </div>
            </div>

            <div className="relative mx-6 mt-3 min-h-[220px] flex-1 overflow-y-auto rounded-2xl border border-line bg-black/25 p-1.5">
              {cargando && !data ? (
                <div className="space-y-2 p-2">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="h-8 animate-pulse rounded-xl bg-white/[0.04]" />
                  ))}
                </div>
              ) : data && data.dirs.length ? (
                <FolderTree
                  key={data.path}
                  nodes={data.dirs.map(aNodo)}
                  load={load}
                  selected={selected}
                  onSelect={(n) => setSelected((cur) => (cur === n.id ? null : n.id))}
                  onOpen={(n) => ir(n.id)}
                />
              ) : (
                <p className="p-6 text-center text-sm text-ink-3">No hay subcarpetas acá.</p>
              )}
            </div>

            <div className="mx-6 mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-3">
              {data?.consola ? (
                <span className="inline-flex items-center gap-1.5 text-apart">
                  <Sparkles className="size-3.5" />
                  Resultado de consola · {data.consola.pendientes} por decidir
                </span>
              ) : data && data.lotes_hijos > 0 ? (
                <span className="inline-flex items-center gap-1.5 text-apart">
                  <Sparkles className="size-3.5" />
                  {data.lotes_hijos} {data.lotes_hijos === 1 ? "lote" : "lotes"} acá adentro
                </span>
              ) : null}
              {data ? (
                <span className="inline-flex items-center gap-1.5">
                  <Images className="size-3.5" />
                  {data.fotos_aqui === 1 ? "1 foto suelta" : `${data.fotos_aqui} fotos sueltas`}
                </span>
              ) : null}
              <span className="ml-auto hidden items-center gap-1 sm:inline-flex">
                <Kbd>clic</Kbd> elegir · <Kbd>doble clic</Kbd> entrar
              </span>
            </div>

            <footer className="mt-4 flex items-center gap-3 border-t border-line bg-black/20 px-6 py-4">
              <div className="min-w-0 flex-1">
                <p className="text-[11px] uppercase tracking-wider text-ink-3">Vas a usar</p>
                <p className="truncate font-mono text-[13px] text-ink" title={elegida}>
                  {elegida}
                </p>
              </div>
              <Button variant="ghost" onClick={onClose}>
                Cancelar
              </Button>
              <Button variant="primary" disabled={!elegida} onClick={() => onPick(elegida)}>
                Usar esta carpeta
              </Button>
            </footer>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
