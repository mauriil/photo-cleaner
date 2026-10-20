import { motion } from "motion/react";
import { Check, FolderOpen, RotateCcw } from "lucide-react";
import { ACCIONES, type Accion, type Estado } from "@/lib/api";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { Button } from "@/components/ui/button";
import { SpotlightCard } from "@/components/ui/spotlight-card";

const ORDEN: Accion[] = ["normales", "explicitas_guardar", "explicitas_borrar"];

export function Done({ estado, onOtra }: { estado: Estado; onOtra: () => void }) {
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-3xl flex-col items-center justify-center px-5 py-16 text-center">
      <motion.div
        initial={{ scale: 0.4, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 220, damping: 16 }}
        className="relative grid size-24 place-items-center rounded-full bg-keep/15 text-keep shadow-[0_0_0_1px_rgb(62_224_125/0.4),0_0_80px_-10px_rgb(62_224_125/0.8)]"
      >
        <motion.span
          aria-hidden
          className="absolute inset-0 rounded-full border border-keep/40"
          animate={{ scale: [1, 1.6], opacity: [0.6, 0] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }}
        />
        <Check className="size-11" strokeWidth={2.6} />
      </motion.div>
      <motion.h1
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="mt-8 text-4xl font-semibold tracking-[-0.04em] sm:text-5xl"
      >
        <span className="text-gradient animate-shimmer">Listo. No queda nada por decidir.</span>
      </motion.h1>
      <p className="mt-3 max-w-lg text-ink-2">
        Elegí otra carpeta para seguir sumando al mismo cúmulo. Nada se borró: <code className="text-no">explicitas_borrar/</code> espera a
        que la vacíes vos.
      </p>
      <div className="mt-10 grid w-full gap-3 sm:grid-cols-3">
        {ORDEN.map((k, i) => (
          <motion.div key={k} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 + i * 0.08 }}>
            <SpotlightCard glow={ACCIONES[k].rgb} className="p-5 text-left">
              <p className="text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: ACCIONES[k].color }}>
                {ACCIONES[k].corto}
              </p>
              <AnimatedNumber value={estado.conteos[k]} className="mt-2 block text-4xl font-semibold tabular-nums tracking-tight" />
              <code className="mt-1 block text-xs text-ink-3">{ACCIONES[k].carpeta}</code>
            </SpotlightCard>
          </motion.div>
        ))}
      </div>
      <p className="mt-6 flex w-full max-w-full items-center justify-center gap-2 font-mono text-xs text-ink-3" title={estado.destino}>
        <FolderOpen className="size-3.5 shrink-0" /> <span className="min-w-0 truncate">{estado.destino}</span>
      </p>
      <Button variant="primary" size="lg" className="mt-8" onClick={onOtra}>
        <RotateCcw /> Elegir otra carpeta
      </Button>
    </div>
  );
}
