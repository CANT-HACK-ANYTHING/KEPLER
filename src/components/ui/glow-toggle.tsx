"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface GlowToggleProps {
  active?: boolean;
  onToggle?: (active: boolean) => void;
  className?: string;
}

export function GlowToggle({
  active = true,
  onToggle,
  className,
}: GlowToggleProps) {
  const [isActive, setIsActive] = React.useState(active);

  const handleToggle = () => {
    const nextState = !isActive;
    setIsActive(nextState);
    onToggle?.(nextState);
  };

  return (
    <button
      type="button"
      onClick={handleToggle}
      className={cn(
        "inline-flex items-center gap-2.5 rounded-full border border-slate-700/80 bg-[#0d1424] px-3.5 py-1.5 text-xs shadow-sm transition-all duration-200 hover:border-slate-500 hover:bg-slate-800/80 focus:outline-none focus:ring-1 focus:ring-slate-400 select-none cursor-pointer",
        className
      )}
      title={isActive ? "Bioluminescent glow active (Click to disable)" : "Glow disabled (Click to activate)"}
    >
      <span className="text-[11px] font-semibold tracking-wider text-slate-400">
        GLOW:
      </span>
      <div className="flex items-center gap-1.5">
        {/* Active Teal indicator matching reference image */}
        <span
          className={cn(
            "h-3 w-3 rounded-full transition-all duration-300",
            isActive
              ? "bg-[#2DD4BF] ring-4 ring-[#2DD4BF]/25 shadow-[0_0_10px_#2DD4BF] scale-105"
              : "bg-[#2DD4BF]/30 hover:bg-[#2DD4BF]/50"
          )}
        />
        {/* Inactive slate dot indicator */}
        <span
          className={cn(
            "h-3 w-3 rounded-full transition-all duration-300",
            !isActive
              ? "bg-slate-500 ring-2 ring-slate-400/40"
              : "bg-[#475569]"
          )}
        />
      </div>
    </button>
  );
}
