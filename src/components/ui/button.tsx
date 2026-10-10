import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "gradient" | "outline" | "ghost";
  size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap rounded-2xl text-sm sm:text-base font-semibold transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-300 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 select-none",
          // Dreamy pastel left-to-right gradient (Pale Pink to Light Blue)
          variant === "gradient" &&
            "bg-gradient-to-r from-[#FCE2D5] via-[#EDE0F5] to-[#D0E6F8] text-slate-900 border border-white/80 shadow-[0_4px_18px_rgba(200,215,250,0.55)] hover:shadow-[0_6px_24px_rgba(185,205,250,0.75)] hover:brightness-[1.02] active:scale-[0.99]",
          // Default
          variant === "default" &&
            "bg-slate-900 text-white hover:bg-slate-800 shadow-sm active:scale-[0.99]",
          // Light rounded outline (Continue with Google)
          variant === "outline" &&
            "border border-slate-200/90 bg-white/70 text-slate-800 font-medium shadow-[0_2px_8px_rgba(0,0,0,0.03)] hover:bg-white hover:border-slate-300/90 hover:shadow-md active:scale-[0.99]",
          // Ghost variant
          variant === "ghost" &&
            "hover:bg-slate-100 hover:text-slate-900 text-slate-600",
          size === "default" && "h-12 px-5 py-2.5",
          size === "sm" && "h-9 rounded-xl px-3.5 text-xs",
          size === "lg" && "h-14 rounded-2xl px-8 text-base",
          size === "icon" && "h-10 w-10",
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
