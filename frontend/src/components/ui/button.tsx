import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium outline-none transition-[background-color,border-color,color,box-shadow,transform,opacity] duration-150 focus-visible:ring-2 focus-visible:ring-accent/60 disabled:pointer-events-none disabled:opacity-40 active:scale-[0.98] [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary:
          "relative bg-ink text-bg shadow-[0_0_0_1px_rgb(255_255_255/0.2),0_10px_40px_-10px_rgb(139_123_255/0.8)] hover:shadow-[0_0_0_1px_rgb(255_255_255/0.4),0_10px_50px_-6px_rgb(139_123_255/0.95)]",
        secondary: "border border-line-strong bg-white/[0.04] text-ink backdrop-blur hover:bg-white/[0.09]",
        ghost: "text-ink-2 hover:bg-white/[0.06] hover:text-ink",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-4",
        lg: "h-12 px-6 text-base",
        icon: "size-10",
      },
    },
    defaultVariants: { variant: "secondary", size: "md" },
  },
);

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>;

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, type = "button", ...props }, ref) => (
  <button ref={ref} type={type} className={cn(buttonVariants({ variant, size }), className)} {...props} />
));
Button.displayName = "Button";
