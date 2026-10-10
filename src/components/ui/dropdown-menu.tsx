"use client";

import * as React from "react";
import { ChevronDown, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface DropdownMenuProps {
  options?: string[];
  defaultValue?: string;
  onSelect?: (value: string) => void;
  className?: string;
}

export function DropdownMenu({
  options = ["Enterprise", "DemoOne", "DemoTwo", "LocalTutor AI"],
  defaultValue = "Enterprise",
  onSelect,
  className,
}: DropdownMenuProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [selected, setSelected] = React.useState(defaultValue);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (option: string) => {
    setSelected(option);
    setIsOpen(false);
    onSelect?.(option);
  };

  return (
    <div className={cn("relative inline-block text-left", className)} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-2 rounded-full border border-slate-700/80 bg-[#0d1424] px-4 py-1.5 text-sm font-medium text-slate-100 shadow-sm transition-all duration-200 hover:border-slate-500 hover:bg-slate-800/80 hover:text-white focus:outline-none focus:ring-1 focus:ring-slate-400"
      >
        <span>{selected}</span>
        <ChevronDown
          className={cn(
            "h-4 w-4 text-slate-400 transition-transform duration-200",
            isOpen && "rotate-180 text-slate-200"
          )}
        />
      </button>

      {isOpen && (
        <div className="absolute left-0 mt-2 w-48 origin-top-left rounded-xl border border-slate-800 bg-[#0b101f] p-1.5 shadow-2xl backdrop-blur-md ring-1 ring-black/50 z-50 animate-in fade-in zoom-in-95 duration-150">
          <div className="space-y-0.5">
            {options.map((option) => {
              const isSelected = option === selected;
              return (
                <button
                  key={option}
                  type="button"
                  onClick={() => handleSelect(option)}
                  className={cn(
                    "flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs text-left transition-colors",
                    isSelected
                      ? "bg-slate-800 text-[#2DD4BF] font-medium"
                      : "text-slate-300 hover:bg-slate-800/60 hover:text-slate-100"
                  )}
                >
                  <span>{option}</span>
                  {isSelected && <Check className="h-3.5 w-3.5 text-[#2DD4BF]" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
