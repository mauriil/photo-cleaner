import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  AnimatePresence,
  animate,
  motion,
  useMotionValue,
  useReducedMotion,
  useTransform,
} from "motion/react";
import { cn } from "@/lib/utils";

// Adaptado de 21st.dev/@ddoemonn/swipe-deck: misma física (springs, intent por pasos, flick)
// pero con 3 salidas (← ↑ →) y la cola controlada desde afuera (el servidor decide qué sigue).

const DISCLOSE = { type: "spring", stiffness: 150, damping: 27, mass: 1 } as const;
const CROSSFADE = { type: "spring", stiffness: 260, damping: 34, mass: 0.8 } as const;
const LEAVE = [0.4, 0, 1, 1] as const;

export type DeckDir = "left" | "right" | "up";
export type DeckIntent = { dir: DeckDir | null; amount: number };

export type DeckSide = { label: string; rgb: string };

const VECTOR: Record<DeckDir, { x: number; y: number; r: number }> = {
  left: { x: -1, y: 0, r: -18 },
  right: { x: 1, y: 0, r: 18 },
  up: { x: 0, y: -1, r: 0 },
};

function leer(dx: number, dy: number, reach: number): DeckIntent {
  const up = -dy;
  if (up > Math.abs(dx) && up > 12) return { dir: "up", amount: Math.min(1, up / reach) };
  if (Math.abs(dx) > 12) return { dir: dx > 0 ? "right" : "left", amount: Math.min(1, Math.abs(dx) / reach) };
  return { dir: null, amount: 0 };
}

type CardProps = {
  depth: number;
  active: boolean;
  entry: DeckDir | null;
  reduced: boolean;
  sides: Record<DeckDir, DeckSide>;
  intent: DeckIntent;
  threshold: number;
  flick: number;
  onIntent: (intent: DeckIntent) => void;
  onDecide: (dir: DeckDir) => void;
  children: ReactNode;
};

function DeckCard({ depth, active, entry, reduced, sides, intent, threshold, flick, onIntent, onDecide, children }: CardProps) {
  const x = useMotionValue(entry ? VECTOR[entry].x * 700 : 0);
  const y = useMotionValue(entry ? VECTOR[entry].y * 700 : 0);
  const rotate = useTransform(x, [-240, 0, 240], [-10, 0, 10], { clamp: false });

  const skip = useRef(reduced);
  skip.current = reduced;

  useEffect(() => {
    if (x.get() === 0 && y.get() === 0) return;
    const opts = skip.current ? { duration: 0 } : DISCLOSE;
    const a = animate(x, 0, opts);
    const b = animate(y, 0, opts);
    return () => {
      a.stop();
      b.stop();
    };
  }, [x, y]);

  // La carta de atrás se acomoda a medida que la de arriba se compromete.
  const commit = !active && depth === 1 ? intent.amount : 0;
  const offsetY = depth * 14 - commit * 14;
  const scale = 1 - depth * 0.05 + commit * 0.05;
  const lado = intent.dir ? sides[intent.dir] : null;
  const armed = intent.amount >= 1;

  return (
    <motion.div
      aria-hidden={!active}
      inert={!active}
      custom={intent.dir}
      variants={{
        exit: (dir: DeckDir | null) => {
          const v = VECTOR[dir ?? "right"];
          return {
            x: v.x * 900,
            y: v.y * 900,
            rotate: v.r,
            opacity: 0,
            zIndex: 30,
            transition: reduced ? { duration: 0 } : { duration: 0.32, ease: LEAVE },
          };
        },
      }}
      initial={{ y: offsetY, scale, opacity: depth > 1 ? 0 : 1 }}
      animate={{ y: active ? 0 : offsetY, scale, opacity: 1 - depth * 0.25 }}
      exit="exit"
      transition={reduced ? { duration: 0 } : active ? { ...CROSSFADE, delay: 0.04 } : CROSSFADE}
      drag={active}
      dragMomentum={false}
      dragElastic={1}
      dragConstraints={{ left: 0, right: 0, top: 0, bottom: 0 }}
      dragTransition={{ bounceStiffness: 260, bounceDamping: 30 }}
      whileDrag={reduced ? undefined : { scale: 1.02, cursor: "grabbing" }}
      onDrag={(_e, info) => onIntent(leer(info.offset.x, info.offset.y, threshold))}
      onDragEnd={(_e, info) => {
        const actual = leer(info.offset.x, info.offset.y, threshold);
        const fast = leer(info.velocity.x, info.velocity.y, flick);
        if (actual.dir && actual.amount >= 1) onDecide(actual.dir);
        else if (fast.dir && fast.amount >= 1 && actual.amount >= 0.35) onDecide(fast.dir);
        else onIntent({ dir: null, amount: 0 });
      }}
      style={{
        x: active ? x : 0,
        y: active ? y : undefined,
        rotate: active ? rotate : 0,
        zIndex: 20 - depth,
        transformOrigin: "50% 100%",
        touchAction: "none",
        boxShadow:
          active && lado
            ? `0 0 0 ${armed ? 2 : 1}px rgb(${lado.rgb} / ${0.25 + intent.amount * 0.6}), 0 0 ${40 + intent.amount * 80}px -10px rgb(${lado.rgb} / ${0.25 + intent.amount * 0.5}), 0 40px 90px -30px rgb(0 0 0 / 0.8)`
            : active
              ? "0 0 0 1px rgb(255 255 255 / 0.1), 0 40px 90px -30px rgb(0 0 0 / 0.8)"
              : "0 0 0 1px rgb(255 255 255 / 0.06), 0 20px 50px -30px rgb(0 0 0 / 0.7)",
      }}
      className={cn(
        "absolute inset-0 select-none overflow-hidden rounded-[28px] bg-surface",
        active ? "cursor-grab" : "pointer-events-none",
      )}
    >
      {children}
      {active
        ? (Object.keys(sides) as DeckDir[]).map((dir) => {
            const on = intent.dir === dir;
            const pos =
              dir === "left"
                ? "right-6 top-8 rotate-[14deg]"
                : dir === "right"
                  ? "left-6 top-8 -rotate-[14deg]"
                  : "bottom-24 left-1/2 -translate-x-1/2";
            return (
              <motion.span
                key={dir}
                aria-hidden
                initial={false}
                animate={{ opacity: on ? Math.min(1, intent.amount * 1.4) : 0, scale: on ? (armed ? 1.06 : 1) : 0.9 }}
                transition={reduced ? { duration: 0 } : { type: "spring", stiffness: 520, damping: 34, mass: 0.45 }}
                style={{
                  color: `rgb(${sides[dir].rgb})`,
                  borderColor: `rgb(${sides[dir].rgb})`,
                  textShadow: `0 0 24px rgb(${sides[dir].rgb} / 0.8)`,
                  boxShadow: `0 0 30px -4px rgb(${sides[dir].rgb} / 0.6), inset 0 0 20px -6px rgb(${sides[dir].rgb} / 0.6)`,
                }}
                className={cn(
                  "pointer-events-none absolute z-10 rounded-2xl border-[3px] bg-black/45 px-4 py-1.5 text-2xl font-black uppercase tracking-[0.12em] backdrop-blur-md",
                  pos,
                )}
              >
                {sides[dir].label}
              </motion.span>
            );
          })
        : null}
    </motion.div>
  );
}

export type SwipeDeckProps<T> = {
  items: readonly T[];
  itemKey: (item: T) => string | number;
  sides: Record<DeckDir, DeckSide>;
  children: (item: T, active: boolean) => ReactNode;
  onDecide: (item: T, dir: DeckDir) => void;
  onIntent?: (intent: DeckIntent) => void;
  /** Dirección de la que entra la carta de arriba (al deshacer vuelve de donde salió). */
  entry?: DeckDir | null;
  /** Fuerza la salida en esta dirección (teclado / botones). */
  exitDir?: DeckDir | null;
  threshold?: number;
  flick?: number;
  peek?: number;
  className?: string;
  empty?: ReactNode;
};

export function SwipeDeck<T>({
  items,
  itemKey,
  sides,
  children,
  onDecide,
  onIntent,
  entry = null,
  exitDir = null,
  threshold = 130,
  flick = 650,
  peek = 3,
  className,
  empty,
}: SwipeDeckProps<T>) {
  const reduced = useReducedMotion() === true;
  const [intent, setIntent] = useState<DeckIntent>({ dir: null, amount: 0 });
  const stack = items.slice(0, Math.max(1, peek));
  const topKey = stack[0] !== undefined ? itemKey(stack[0]) : null;

  const report = (next: DeckIntent) => {
    setIntent((prev) => (prev.dir === next.dir && Math.abs(prev.amount - next.amount) < 0.02 ? prev : next));
    onIntent?.(next);
  };

  // Al cambiar la carta de arriba limpiamos el intent (si salió por botón no hubo drag).
  useEffect(() => {
    setIntent({ dir: null, amount: 0 });
    onIntent?.({ dir: null, amount: 0 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topKey]);

  const salida = exitDir ?? intent.dir;

  return (
    <div className={cn("relative", className)}>
      {stack.length === 0 ? empty : null}
      <AnimatePresence initial={false} custom={salida}>
        {stack
          .map((item, depth) => (
            <DeckCard
              key={itemKey(item)}
              depth={depth}
              active={depth === 0}
              entry={depth === 0 ? entry : null}
              reduced={reduced}
              sides={sides}
              intent={intent}
              threshold={threshold}
              flick={flick}
              onIntent={report}
              onDecide={(dir) => {
                setIntent({ dir, amount: 1 });
                onDecide(item, dir);
              }}
            >
              {children(item, depth === 0)}
            </DeckCard>
          ))
          .reverse()}
      </AnimatePresence>
    </div>
  );
}
