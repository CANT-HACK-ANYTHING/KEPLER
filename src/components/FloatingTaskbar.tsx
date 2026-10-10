"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  BookOpen,
  Sparkles,
  ClipboardList,
  TrendingUp,
  FileText,
} from "lucide-react";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
}

const navItems: NavItem[] = [
  {
    name: "Learn",
    href: "/learn",
    icon: BookOpen,
    description: "Learning Materials",
  },
  {
    name: "Ask",
    href: "/ask",
    icon: Sparkles,
    description: "AI Assistant",
  },
  {
    name: "Test",
    href: "/test",
    icon: ClipboardList,
    description: "Practice & Mock Tests",
  },
  {
    name: "Improve",
    href: "/improve",
    icon: TrendingUp,
    description: "Improvement Book & Mistakes",
  },
  {
    name: "Papers",
    href: "/papers",
    icon: FileText,
    description: "Previous Years' Papers",
  },
];

export function FloatingTaskbar() {
  const pathname = usePathname();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  // Avoid hydration mismatch
  if (!mounted) {
    return null;
  }

  // Do not show on initial sign-in / intro page
  if (!pathname || pathname === "/") {
    return null;
  }

  const isHomeActive = pathname === "/dashboard";

  return (
    <aside
      aria-label="Floating Navigation Taskbar"
      className="fixed left-3 sm:left-5 top-1/2 -translate-y-1/2 z-50 flex flex-col items-center bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl border border-slate-200/90 dark:border-slate-800 shadow-[0_8px_32px_rgba(0,0,0,0.14)] rounded-2xl p-1.5 sm:p-2 gap-1.5 select-none transition-all duration-300"
    >
      {/* Home / Classroom Dashboard button */}
      <Link
        href="/dashboard"
        title="Classroom Dashboard"
        className={`group relative flex flex-col items-center justify-center w-14 sm:w-16 py-2 px-1 rounded-xl gap-1 transition-all duration-200 ${
          isHomeActive
            ? "bg-teal-50 text-teal-600 dark:bg-teal-500/20 dark:text-teal-300 font-semibold shadow-xs"
            : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/70 font-medium"
        }`}
      >
        {isHomeActive && (
          <span className="absolute -left-1 sm:-left-1.5 top-1/2 -translate-y-1/2 w-1 h-5 bg-teal-500 dark:bg-teal-400 rounded-r-full" />
        )}
        <Home
          className={`w-5 h-5 transition-transform duration-200 group-hover:scale-110 ${
            isHomeActive
              ? "text-teal-600 dark:text-teal-300"
              : "text-slate-500 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-slate-100"
          }`}
        />
        <span className="text-[11px] leading-none tracking-tight">Home</span>
      </Link>

      {/* Subtle Divider */}
      <div className="w-8 h-[1px] bg-slate-200 dark:bg-slate-800 my-0.5" />

      {/* 5 Items in exact order: Learn, Ask, Test, Improve, Papers */}
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive =
          pathname === item.href ||
          (item.href === "/ask" && pathname === "/doubt-solver");

        return (
          <Link
            key={item.name}
            href={item.href}
            title={`${item.name} — ${item.description}`}
            className={`group relative flex flex-col items-center justify-center w-14 sm:w-16 py-2 px-1 rounded-xl gap-1 transition-all duration-200 ${
              isActive
                ? "bg-blue-50 text-blue-600 dark:bg-blue-600/20 dark:text-blue-400 font-semibold shadow-xs"
                : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/70 font-medium"
            }`}
          >
            {/* Active left indicator pip */}
            {isActive && (
              <span className="absolute -left-1 sm:-left-1.5 top-1/2 -translate-y-1/2 w-1 h-5 bg-blue-600 dark:bg-blue-400 rounded-r-full" />
            )}

            <Icon
              className={`w-5 h-5 transition-transform duration-200 group-hover:scale-110 ${
                isActive
                  ? "text-blue-600 dark:text-blue-400"
                  : "text-slate-500 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-slate-100"
              }`}
            />
            <span className="text-[11px] leading-none tracking-tight">
              {item.name}
            </span>
          </Link>
        );
      })}
    </aside>
  );
}
