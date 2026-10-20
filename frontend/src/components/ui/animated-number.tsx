import { useEffect } from "react";
import { animate, motion, useMotionValue, useTransform } from "motion/react";

export function AnimatedNumber({ value, className }: { value: number; className?: string }) {
  const mv = useMotionValue(value);
  const text = useTransform(mv, (v) => Math.round(v).toLocaleString("es-AR"));
  useEffect(() => {
    const c = animate(mv, value, { type: "spring", stiffness: 140, damping: 22 });
    return () => c.stop();
  }, [mv, value]);
  return <motion.span className={className}>{text}</motion.span>;
}
