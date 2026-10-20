import { motion } from "motion/react";
import { ArrowLeft, ArrowRight, ArrowUp, FolderInput, FolderOutput, Layers, Loader2, Sparkles } from "lucide-react";
import { ACCIONES, CATEGORIAS, type Accion, type Estado, type ResumenConsola } from "@/lib/api";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { SpotlightCard } from "@/components/ui/spotlight-card";
import { cn } from "@/lib/utils";

const ORDEN: Accion[] = ["explicitas_borrar", "explicitas_guardar", "normales"];
const ICONO = { left: ArrowLeft, up: ArrowUp, right: ArrowRight } as const;
const TECLA = { left: "A", up: "W", right: "D" } as const;
const DESCRIPCION: Record<Accion, string> = {
  explicitas_borrar: "Explícitas para eliminar después. Nada se borra solo.",
  explicitas_guardar: "Explícitas que sí querés conservar, apartadas.",
  normales: "En realidad es normal, o una dudosa que se queda.",
};

const fadeUp = (i: number) => ({
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
  transition: { delay: 0.05 + i * 0.07, type: "spring" as const, stiffness: 200, damping: 26 },
});

type Props = {
  estado: Estado | null;
  inspeccion: ResumenConsola | null;
  inspeccionando: boolean;
  pasarNormales: boolean;
  setPasarNormales: (v: boolean) => void;
  error: string | null;
  empezando: boolean;
  onElegirDestino: () => void;
  onElegirOrigen: () => void;
  onEmpezar: () => void;
};

export function Setup({
  estado,
  inspeccion,
  inspeccionando,
  pasarNormales,
  setPasarNormales,
  error,
  empezando,
  onElegirDestino,
  onElegirOrigen,
  onEmpezar,
}: Props) {
  const c = inspeccion?.conteos_consola;
  const pendientes = inspeccion?.pendientes ?? 0;

  return (
    <div className="mx-auto w-full max-w-6xl px-5 pb-16 pt-10 sm:px-8 sm:pt-16">
      <motion.header {...fadeUp(0)} className="max-w-3xl">
        <span className="inline-flex items-center gap-2 rounded-full border border-line-strong bg-white/[0.04] px-3 py-1 text-xs text-ink-2 backdrop-blur">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-keep opacity-60" />
            <span className="relative inline-flex size-2 rounded-full bg-keep" />
          </span>
          Post-consola · todo corre en tu compu
        </span>
        <h1 className="mt-5 text-4xl font-semibold leading-[1.05] tracking-[-0.04em] sm:text-6xl">
          La IA ya hizo lo suyo.
          <br />
          <span className="text-gradient animate-shimmer">El veredicto final es tuyo.</span>
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-relaxed text-ink-2 sm:text-lg">
          Apuntá a la carpeta con todas tus imágenes. Encuentro cada lote con <code className="text-ink">explicito</code>,{" "}
          <code className="text-ink">no_explicito</code> o <code className="text-ink">revisar_manual</code> (o en inglés:{" "}
          <code className="text-ink">explicit</code>, <code className="text-ink">non-explicit</code>,{" "}
          <code className="text-ink">force-revisit</code>) y te los paso uno por uno.
        </p>
      </motion.header>

      <div className="mt-10 grid gap-3 md:grid-cols-3">
        {ORDEN.map((key, i) => {
          const a = ACCIONES[key];
          const Icon = ICONO[a.dir];
          return (
            <motion.div key={key} {...fadeUp(i + 1)} className="min-w-0">
              <SpotlightCard glow={a.rgb} className="h-full p-5">
                <div className="flex items-center justify-between">
                  <span
                    className="grid size-11 place-items-center rounded-2xl"
                    style={{
                      color: a.color,
                      background: `rgb(${a.rgb} / 0.12)`,
                      boxShadow: `inset 0 0 0 1px rgb(${a.rgb} / 0.35), 0 0 30px -6px rgb(${a.rgb} / 0.6)`,
                    }}
                  >
                    <Icon className="size-5" />
                  </span>
                  <span className="flex items-center gap-1">
                    <Kbd>{a.dir === "left" ? "←" : a.dir === "up" ? "↑" : "→"}</Kbd>
                    <Kbd>{TECLA[a.dir]}</Kbd>
                  </span>
                </div>
                <p className="mt-4 text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: a.color }}>
                  {a.corto}
                </p>
                <h3 className="mt-1 text-lg font-semibold tracking-tight">{a.label}</h3>
                <p className="mt-1 text-sm leading-relaxed text-ink-3">{DESCRIPCION[key]}</p>
                <div className="mt-4 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 border-t border-line pt-3 text-xs text-ink-3">
                  <code className="truncate">{a.carpeta}</code>
                  <span className="whitespace-nowrap">
                    <AnimatedNumber value={estado?.conteos[key] ?? 0} className="text-base font-semibold tabular-nums text-ink" />{" "}
                    en el cúmulo
                  </span>
                </div>
              </SpotlightCard>
            </motion.div>
          );
        })}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_1.35fr]">
        <motion.div {...fadeUp(4)} className="min-w-0">
          <SpotlightCard className="h-full p-6">
            <div className="flex items-center gap-3">
              <span className="grid size-9 place-items-center rounded-xl bg-white/[0.06] text-ink-2">
                <FolderOutput className="size-4" />
              </span>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-3">Paso 1</p>
                <h2 className="font-semibold tracking-tight">Carpeta destino (el cúmulo)</h2>
              </div>
            </div>
            <p className="mt-3 text-sm text-ink-3">
              Acá se juntan las fotos de todos los lotes, respetando sus subcarpetas: <code className="text-ink-2">normales/&lt;lote&gt;/Camara/2024/…</code>
            </p>
            <div className="mt-4 flex items-center gap-2 rounded-2xl border border-line bg-black/30 p-1.5 pl-3">
              <code className="min-w-0 flex-1 truncate text-[13px] text-ink" title={estado?.destino}>
                {estado?.destino ?? "…"}
              </code>
              <Button size="sm" onClick={onElegirDestino}>
                Cambiar
              </Button>
            </div>
          </SpotlightCard>
        </motion.div>

        <motion.div {...fadeUp(5)} className="min-w-0">
          <SpotlightCard glow="139 123 255" className="h-full p-6">
            <div className="flex items-center gap-3">
              <span className="grid size-9 place-items-center rounded-xl bg-accent/15 text-accent">
                <FolderInput className="size-4" />
              </span>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-3">Paso 2</p>
                <h2 className="font-semibold tracking-tight">Tus imágenes</h2>
              </div>
            </div>

            <button
              type="button"
              onClick={onElegirOrigen}
              className={cn(
                "group mt-4 flex w-full items-center gap-3 rounded-2xl border border-dashed p-4 text-left transition-colors",
                inspeccion
                  ? "border-accent/40 bg-accent/[0.06] hover:bg-accent/[0.1]"
                  : "border-line-strong bg-black/20 hover:border-accent/50 hover:bg-accent/[0.05]",
              )}
            >
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-white/[0.06] text-ink-2 transition-colors group-hover:text-accent">
                {inspeccionando ? <Loader2 className="size-4 animate-spin" /> : <Layers className="size-4" />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium">{inspeccion ? "Carpeta elegida" : "Elegir carpeta con fotos"}</span>
                <span className="block truncate font-mono text-xs text-ink-3" title={inspeccion?.root}>
                  {inspeccion?.root ?? "Un *_clasificado, o la carpeta madre con varios adentro"}
                </span>
              </span>
              <span className="text-xs text-ink-3 group-hover:text-ink">{inspeccion ? "Cambiar" : "Explorar"}</span>
            </button>

            {inspeccion && c ? (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-4 space-y-4">
                <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
                  <div>
                    <p className="text-xs text-ink-3">Por decidir</p>
                    <AnimatedNumber value={pendientes} className="text-5xl font-semibold tabular-nums tracking-tight" />
                  </div>
                  <div className="flex flex-wrap gap-2 pb-1.5">
                    {(Object.keys(CATEGORIAS) as (keyof typeof CATEGORIAS)[]).map((k) => (
                      <span
                        key={k}
                        className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs"
                        style={{ background: `rgb(${CATEGORIAS[k].rgb} / 0.1)`, boxShadow: `inset 0 0 0 1px rgb(${CATEGORIAS[k].rgb} / 0.28)` }}
                      >
                        <span className="size-1.5 rounded-full" style={{ background: `rgb(${CATEGORIAS[k].rgb})` }} />
                        <span className="text-ink-2">{CATEGORIAS[k].corto}</span>
                        <strong className="tabular-nums">{c[k]}</strong>
                      </span>
                    ))}
                  </div>
                </div>

                {inspeccion.lotes.length > 1 ? (
                  <div className="rounded-2xl border border-line bg-black/20">
                    <p className="flex items-center gap-1.5 border-b border-line px-3 py-2 text-xs text-apart">
                      <Sparkles className="size-3.5" /> {inspeccion.lotes.length} lotes detectados
                    </p>
                    <ul className="max-h-40 divide-y divide-line overflow-y-auto">
                      {inspeccion.lotes.map((l) => (
                        <li key={l.path} className="flex items-center gap-3 px-3 py-2 text-sm">
                          <span className="min-w-0 flex-1 truncate" title={l.path}>
                            {l.etiqueta}
                          </span>
                          <span className="text-xs tabular-nums text-ink-3">{l.conteos.no_explicito} ok</span>
                          <span className="w-16 text-right text-xs font-medium tabular-nums">{l.pendientes} pend.</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {inspeccion.filtro ? (
                  <p className="text-xs text-ink-3">
                    Solo voy a revisar <strong className="text-ink">{CATEGORIAS[inspeccion.filtro].label}</strong>.
                  </p>
                ) : c.no_explicito > 0 ? (
                  <label className="flex cursor-pointer items-start gap-3 rounded-2xl border border-line bg-black/20 p-3 text-sm">
                    <input
                      type="checkbox"
                      checked={pasarNormales}
                      onChange={(e) => setPasarNormales(e.target.checked)}
                      className="mt-0.5 size-4 accent-[var(--color-keep)]"
                    />
                    <span>
                      Sumar las <strong>{c.no_explicito}</strong> no explícitas directo al cúmulo de{" "}
                      <code className="text-keep">normales/</code>
                      <span className="block text-xs text-ink-3">La IA ya las dio por seguras; no pasan por el swipe.</span>
                    </span>
                  </label>
                ) : null}
              </motion.div>
            ) : null}

            {error ? (
              <p className="mt-4 rounded-xl border border-no/30 bg-no/10 px-3 py-2 text-sm text-[#ffb3bf]">{error}</p>
            ) : null}

            <Button
              variant="primary"
              size="lg"
              className="mt-5 w-full"
              disabled={!inspeccion || empezando || (pendientes === 0 && !(pasarNormales && (c?.no_explicito ?? 0) > 0))}
              onClick={onEmpezar}
            >
              {empezando ? <Loader2 className="animate-spin" /> : null}
              {inspeccion && pendientes === 0 ? "Mover no explícitas y listo" : `Revisar ${pendientes || ""} fotos`.replace("  ", " ")}
              <ArrowRight />
            </Button>
          </SpotlightCard>
        </motion.div>
      </div>
    </div>
  );
}
