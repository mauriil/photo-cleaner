import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { ArrowLeft, ArrowRight, ArrowUp, ChevronLeft, FolderTree, ImageOff, Undo2 } from "lucide-react";
import { toast } from "sonner";
import {
  ACCION_POR_DIR,
  ACCIONES,
  backend,
  CATEGORIAS,
  type Accion,
  type Direccion,
  type Estado,
  type FotoMeta,
} from "@/lib/api";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { SwipeDeck, type DeckDir, type DeckIntent } from "@/components/ui/swipe-deck";
import { cn } from "@/lib/utils";

const SIDES = {
  left: { label: "Se va", rgb: ACCIONES.explicitas_borrar.rgb },
  up: { label: "Aparte", rgb: ACCIONES.explicitas_guardar.rgb },
  right: { label: "Se queda", rgb: ACCIONES.normales.rgb },
};

const ATAJOS: Record<string, Direccion> = {
  ArrowLeft: "left",
  KeyA: "left",
  ArrowUp: "up",
  KeyW: "up",
  ArrowRight: "right",
  KeyD: "right",
};

function enCampo(el: EventTarget | null) {
  if (!(el instanceof HTMLElement)) return false;
  return ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) || el.isContentEditable;
}

function Foto({ foto, active }: { foto: FotoMeta; active: boolean }) {
  const [error, setError] = useState(false);
  const cat = CATEGORIAS[foto.categoria_consola];
  return (
    <div className="relative h-full w-full bg-black">
      {error ? (
        <div className="grid h-full place-items-center text-ink-3">
          <div className="text-center">
            <ImageOff className="mx-auto size-8" />
            <p className="mt-2 text-sm">No pude abrir la vista previa</p>
            <p className="font-mono text-xs">{foto.nombre}</p>
          </div>
        </div>
      ) : (
        <>
          {/* Ambiente: la misma foto, desenfocada, rellena los bordes. */}
          <img src={foto.preview} alt="" aria-hidden draggable={false} className="absolute inset-0 h-full w-full scale-125 object-cover opacity-50 blur-3xl saturate-150" />
          <img
            src={foto.preview}
            alt={foto.nombre}
            draggable={false}
            onError={() => setError(true)}
            className="relative h-full w-full object-contain"
          />
        </>
      )}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-black/60 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-black/85 via-black/40 to-transparent" />
      <span
        className="absolute left-4 top-4 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider backdrop-blur-md"
        style={{ color: `rgb(${cat.rgb})`, background: `rgb(${cat.rgb} / 0.14)`, boxShadow: `inset 0 0 0 1px rgb(${cat.rgb} / 0.4)` }}
      >
        <span className="size-1.5 rounded-full" style={{ background: `rgb(${cat.rgb})`, boxShadow: `0 0 8px rgb(${cat.rgb})` }} />
        IA: {cat.corto}
      </span>
      {active ? (
        <div className="absolute inset-x-0 bottom-0 p-5">
          <p className="truncate text-base font-semibold text-white">{foto.nombre}</p>
          <p className="mt-0.5 flex items-center gap-1.5 truncate text-xs text-white/60">
            <FolderTree className="size-3.5 shrink-0" />
            <span className="truncate">
              {foto.lote}
              {foto.subcarpeta ? ` / ${foto.subcarpeta}` : ""}
            </span>
          </p>
        </div>
      ) : null}
    </div>
  );
}

const ICONOS = { left: ArrowLeft, up: ArrowUp, right: ArrowRight } as const;
const TECLA = { left: "A", up: "W", right: "D" } as const;
const FLECHA = { left: "←", up: "↑", right: "→" } as const;

function Fab({ dir, onClick, flash, big }: { dir: Direccion; onClick: () => void; flash: boolean; big?: boolean }) {
  const a = ACCIONES[ACCION_POR_DIR[dir]];
  const Icon = ICONOS[dir];
  return (
    <motion.button
      type="button"
      onClick={onClick}
      whileHover={{ y: -3 }}
      whileTap={{ scale: 0.92 }}
      animate={flash ? { scale: [1, 1.12, 1] } : { scale: 1 }}
      transition={{ duration: 0.22 }}
      title={`${a.corto} · ${FLECHA[dir]} o ${TECLA[dir]}`}
      className="group flex flex-col items-center gap-2 outline-none"
    >
      <span
        className={cn(
          "grid place-items-center rounded-full border backdrop-blur-xl transition-shadow duration-200",
          big ? "size-[4.5rem]" : "size-16",
        )}
        style={{
          color: a.color,
          borderColor: `rgb(${a.rgb} / 0.45)`,
          background: `radial-gradient(circle at 50% 30%, rgb(${a.rgb} / ${flash ? 0.35 : 0.16}), rgb(10 10 14 / 0.7))`,
          boxShadow: flash
            ? `0 0 0 4px rgb(${a.rgb} / 0.25), 0 0 50px rgb(${a.rgb} / 0.7)`
            : `0 0 30px -8px rgb(${a.rgb} / 0.6), inset 0 1px 0 rgb(255 255 255 / 0.08)`,
        }}
      >
        <Icon className={big ? "size-7" : "size-6"} strokeWidth={2.4} />
      </span>
      <span className="text-xs font-medium text-ink-2 group-hover:text-ink">{a.corto}</span>
      <span className="hidden items-center gap-1 sm:flex">
        <Kbd>{FLECHA[dir]}</Kbd>
        <Kbd>{TECLA[dir]}</Kbd>
      </span>
    </motion.button>
  );
}

type Props = {
  estado: Estado;
  setEstado: (e: Estado) => void;
  onSalir: () => void;
  onIntent: (intent: DeckIntent) => void;
};

export function Review({ estado, setEstado, onSalir, onIntent }: Props) {
  const [cola, setCola] = useState<FotoMeta[]>(() => (estado.foto ? [estado.foto, ...estado.siguientes] : []));
  const [exitDir, setExitDir] = useState<DeckDir | null>(null);
  const [entry, setEntry] = useState<DeckDir | null>(null);
  const [flash, setFlash] = useState<Direccion | null>(null);
  const ocupado = useRef(false);

  useEffect(() => {
    setCola(estado.foto ? [estado.foto, ...estado.siguientes] : []);
  }, [estado]);

  const decidir = useCallback(
    async (dir: Direccion) => {
      if (ocupado.current || !cola.length) return;
      ocupado.current = true;
      const accion: Accion = ACCION_POR_DIR[dir];
      setEntry(null);
      setExitDir(dir);
      setFlash(dir);
      window.setTimeout(() => setFlash(null), 240);
      setCola((prev) => prev.slice(1));
      try {
        setEstado(await backend.accion(accion));
      } catch (err) {
        toast.error((err as Error).message);
        setEstado(await backend.estado());
      } finally {
        ocupado.current = false;
      }
    },
    [cola.length, setEstado],
  );

  const deshacer = useCallback(async () => {
    if (ocupado.current || !estado.puede_deshacer) return;
    ocupado.current = true;
    const vuelve = estado.ultima_accion ? ACCIONES[estado.ultima_accion].dir : null;
    setExitDir(null);
    setEntry(vuelve);
    try {
      setEstado(await backend.deshacer());
      toast("Deshecho", { description: "La última foto volvió a la pila." });
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      ocupado.current = false;
    }
  }, [estado.puede_deshacer, estado.ultima_accion, setEstado]);

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      if (ev.repeat || ev.metaKey || ev.ctrlKey || ev.altKey || enCampo(ev.target)) return;
      const dir = ATAJOS[ev.code] ?? ATAJOS[ev.key];
      if (dir) {
        ev.preventDefault();
        decidir(dir);
      } else if (ev.code === "KeyZ" || ev.key === "Backspace") {
        ev.preventDefault();
        deshacer();
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [decidir, deshacer]);

  const progreso = estado.total ? (estado.total - estado.restantes) / estado.total : 0;

  return (
    <div className="flex h-dvh flex-col">
      {/* Barra de progreso luminosa */}
      <div className="relative h-1 w-full bg-white/[0.04]">
        <motion.div
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-accent via-apart to-keep shadow-[0_0_16px_rgb(139_123_255/0.8)]"
          animate={{ width: `${progreso * 100}%` }}
          transition={{ type: "spring", stiffness: 120, damping: 24 }}
        />
      </div>

      <header className="flex items-center gap-3 px-4 py-3 sm:px-6">
        <Button variant="ghost" size="sm" onClick={onSalir}>
          <ChevronLeft /> Cambiar carpeta
        </Button>
        <div className="min-w-0 flex-1 text-center">
          <p className="text-sm font-semibold tabular-nums">
            <AnimatedNumber value={Math.min(estado.indice, estado.total)} /> <span className="text-ink-3">/ {estado.total}</span>
          </p>
          <p className="truncate font-mono text-[11px] text-ink-3" title={estado.origen ?? ""}>
            {estado.origen}
          </p>
        </div>
        <Button variant="secondary" size="sm" disabled={!estado.puede_deshacer} onClick={deshacer}>
          <Undo2 /> Deshacer <Kbd className="ml-1 hidden sm:inline-flex">Z</Kbd>
        </Button>
      </header>

      <main className="flex min-h-0 flex-1 flex-col items-center justify-center px-4 pb-2">
        <SwipeDeck
          className="aspect-[3/4] h-full max-h-[min(68dvh,720px)] w-auto max-w-full"
          items={cola}
          itemKey={(f) => f.id}
          sides={SIDES}
          exitDir={exitDir}
          entry={entry}
          onIntent={onIntent}
          onDecide={(_f, dir) => decidir(dir)}
          empty={
            <div className="grid h-full place-items-center rounded-[28px] border border-dashed border-line-strong text-sm text-ink-3">
              Cargando…
            </div>
          }
        >
          {(foto, active) => <Foto foto={foto} active={active} />}
        </SwipeDeck>
      </main>

      <div className="flex items-end justify-center gap-8 px-4 pb-3 pt-4 sm:gap-14">
        <Fab dir="left" flash={flash === "left"} onClick={() => decidir("left")} />
        <Fab dir="up" flash={flash === "up"} onClick={() => decidir("up")} big />
        <Fab dir="right" flash={flash === "right"} onClick={() => decidir("right")} />
      </div>

      <footer className="flex flex-wrap items-center justify-center gap-2 px-4 pb-5 pt-2">
        {(["explicitas_borrar", "explicitas_guardar", "normales"] as Accion[]).map((k) => (
          <span
            key={k}
            className="inline-flex items-center gap-2 rounded-full border border-line bg-white/[0.03] px-3 py-1 text-xs text-ink-3 backdrop-blur"
          >
            <span className="size-1.5 rounded-full" style={{ background: ACCIONES[k].color, boxShadow: `0 0 8px ${ACCIONES[k].color}` }} />
            {ACCIONES[k].label}
            <AnimatedNumber value={estado.conteos[k]} className="font-semibold tabular-nums text-ink" />
          </span>
        ))}
      </footer>
    </div>
  );
}
