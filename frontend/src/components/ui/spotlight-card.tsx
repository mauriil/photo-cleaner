import type { CSSProperties, HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

// Patrón Spotlight de 21st (luz radial que sigue al cursor + borde iluminado).
export function SpotlightCard({
  className,
  glow = "255 255 255",
  style,
  ...props
}: HTMLAttributes<HTMLDivElement> & { glow?: string }) {
  return (
    <div
      onPointerMove={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`);
        e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
      }}
      style={{ "--glow": glow, ...style } as CSSProperties}
      className={cn(
        "spotlight-card rounded-3xl border border-line bg-surface/70 backdrop-blur-xl shadow-[0_1px_0_rgb(255_255_255/0.05)_inset,0_30px_60px_-30px_rgb(0_0_0/0.8)]",
        className,
      )}
      {...props}
    />
  );
}
