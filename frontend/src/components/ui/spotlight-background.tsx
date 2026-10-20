import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

// Adaptado de 21st.dev/@dhileepkumargm/spotlight-background: blobs de luz que flotan y rotan.
// `tint` permite que la escena reaccione al gesto (verde / ámbar / rojo según la dirección).

type SpotlightProps = {
  className: string;
  duration: number;
  delay?: number;
  x: string[];
  y: string[];
  rotate: string[];
  reduced: boolean;
};

function Spotlight({ className, duration, delay = 0, x, y, rotate, reduced }: SpotlightProps) {
  return (
    <motion.div
      aria-hidden
      className={cn("absolute rounded-full blur-[110px] will-change-transform", className)}
      initial={{ x: x[0], y: y[0], rotate: rotate[0] }}
      animate={reduced ? undefined : { x, y, rotate }}
      transition={{ duration, delay, ease: "easeInOut", repeat: Infinity, repeatType: "mirror" }}
    />
  );
}

export function SpotlightBackground({
  children,
  tint,
  intensity = 0,
}: {
  children: ReactNode;
  tint?: string;
  intensity?: number;
}) {
  const reduced = useReducedMotion() === true;
  return (
    <div className="grain relative min-h-full overflow-hidden bg-bg">
      <div className="pointer-events-none fixed inset-0 z-0">
        <Spotlight
          reduced={reduced}
          duration={12}
          x={["-10%", "5%", "-20%", "-10%"]}
          y={["-30%", "-15%", "-40%", "-30%"]}
          rotate={["0deg", "15deg", "-15deg", "0deg"]}
          className="left-[-10%] top-0 h-[60vh] w-[55vw] bg-[radial-gradient(closest-side,rgb(139_123_255/0.35),transparent)]"
        />
        <Spotlight
          reduced={reduced}
          duration={15}
          delay={3}
          x={["0%", "20%", "-20%", "0%"]}
          y={["0%", "15%", "5%", "0%"]}
          rotate={["-20deg", "0deg", "20deg", "-20deg"]}
          className="right-[-15%] top-[10%] h-[55vh] w-[50vw] bg-[radial-gradient(closest-side,rgb(255_93_115/0.22),transparent)]"
        />
        <Spotlight
          reduced={reduced}
          duration={18}
          delay={5}
          x={["0%", "-30%", "10%", "0%"]}
          y={["0%", "-20%", "20%", "0%"]}
          rotate={["10deg", "-10deg", "25deg", "10deg"]}
          className="bottom-[-25%] left-[20%] h-[60vh] w-[60vw] bg-[radial-gradient(closest-side,rgb(62_224_125/0.18),transparent)]"
        />
        {/* Luz que reacciona a la decisión en curso. */}
        <motion.div
          aria-hidden
          className="absolute left-1/2 top-1/2 h-[80vh] w-[80vw] -translate-x-1/2 -translate-y-1/2 rounded-full blur-[120px]"
          animate={{ opacity: tint ? 0.15 + intensity * 0.45 : 0 }}
          transition={{ duration: 0.25 }}
          style={{ background: tint ? `radial-gradient(closest-side, rgb(${tint} / 0.55), transparent)` : undefined }}
        />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgb(255_255_255/0.025)_1px,transparent_1px),linear-gradient(to_bottom,rgb(255_255_255/0.025)_1px,transparent_1px)] bg-[size:56px_56px] [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_75%)]" />
      </div>
      <div className="relative z-10 min-h-full">{children}</div>
    </div>
  );
}
