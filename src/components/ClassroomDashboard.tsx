"use client";

import * as React from "react";
import Link from "next/link";
import { CheckCircle2, Circle, Clock, Zap, LogOut, BookOpen, Sparkles, AlertCircle, X } from "lucide-react";

interface ClassroomDashboardProps {
  studentName?: string;
  studentId?: string;
  onSignOut?: () => void;
  onOpenLearningModule?: () => void;
  onOpenDoubtSolver?: () => void;
}

interface TodoItem {
  id: string;
  text: string;
  completed: boolean;
}

export function ClassroomDashboard({
  studentName = "Alex Chen",
  studentId = "10034455542",
  onSignOut,
  onOpenLearningModule,
  onOpenDoubtSolver,
}: ClassroomDashboardProps) {
  // To-do list interactive state
  const [todos, setTodos] = React.useState<TodoItem[]>([
    { id: "1", text: "Review Kepler's 3 Laws of Planetary Motion", completed: true },
    { id: "2", text: "Complete Orbital Velocity Lab Simulation", completed: false },
    { id: "3", text: "Solve 10 Practice Questions on Gravity", completed: false },
  ]);

  // Score Booster modal state
  const [showScoreBooster, setShowScoreBooster] = React.useState(false);

  const toggleTodo = (id: string) => {
    setTodos((prev) =>
      prev.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t))
    );
  };

  return (
    <div className="relative min-h-screen w-full bg-[#0F172A] overflow-hidden select-none flex flex-col justify-between">
      {/* Invisible SVG definition for real matte chalkboard texture filter (rough edges, micro-breaks, zero glow) */}
      <svg className="absolute w-0 h-0 pointer-events-none opacity-0 overflow-hidden" aria-hidden="true">
        <defs>
          <filter id="chalk-roughness" x="-10%" y="-10%" width="120%" height="120%">
            {/* High frequency grain for rough imperfect chalk strokes */}
            <feTurbulence type="fractalNoise" baseFrequency="0.22" numOctaves="4" result="noise" />
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.6" xChannelSelector="R" yChannelSelector="G" result="displaced" />
            {/* Subtle micro-texture breaks inside the stroke */}
            <feColorMatrix in="noise" type="matrix" values="
              1 0 0 0 0
              0 1 0 0 0
              0 0 1 0 0
              0 0 0 1.6 -0.15" result="grain_mask" />
            <feComposite in="displaced" in2="grain_mask" operator="in" />
          </filter>
        </defs>
      </svg>

      {/* 1. Full Classroom Background Image */}
      <img
        src="/classroom_dashboard.jpg"
        alt="Classroom Main Dashboard"
        className="absolute inset-0 w-full h-full object-cover object-center z-0 pointer-events-none"
      />

      {/* Subtle atmospheric vignette */}
      <div className="absolute inset-0 bg-gradient-to-t from-slate-950/60 via-transparent to-slate-950/40 pointer-events-none z-0" />

      {/* 2. Top Header Navigation (Clean: No "KEPLER ENGINE" text) */}
      <header className="relative z-30 w-full px-6 sm:px-10 py-5 flex items-center justify-between pointer-events-none fade-in-smooth">
        {/* Top-Left: Clean / Empty (Removed "KEPLER ENGINE") */}
        <div className="pointer-events-auto" />

        {/* Top-Right: Student Profile & Navigation Controls */}
        <div className="pointer-events-auto flex items-center gap-3">
          {/* AI Assistant (Doubt Solver) Button */}
          <Link
            href="/ask"
            onClick={
              onOpenDoubtSolver
                ? (e) => {
                    e.preventDefault();
                    onOpenDoubtSolver();
                  }
                : undefined
            }
            className="inline-flex items-center gap-2 rounded-full border border-blue-500/40 bg-blue-600/20 px-3.5 py-1.5 text-xs font-medium text-blue-200 shadow-md backdrop-blur-md transition-all duration-200 hover:bg-blue-600/35 hover:border-blue-400 hover:text-white active:scale-95 group"
          >
            <Sparkles className="h-3.5 w-3.5 text-blue-400 group-hover:text-blue-300" />
            <span>AI Assistant</span>
          </Link>

          {onOpenLearningModule && (
            <button
              type="button"
              onClick={onOpenLearningModule}
              className="hidden sm:inline-flex items-center gap-2 rounded-full border border-slate-700/80 bg-slate-900/80 px-4 py-1.5 text-xs font-medium text-slate-200 shadow-lg backdrop-blur-md transition-all duration-200 hover:border-[#2DD4BF]/60 hover:text-[#2DD4BF] hover:bg-slate-900 active:scale-95"
            >
              <BookOpen className="h-3.5 w-3.5" />
              <span>AI Learning Module</span>
            </button>
          )}

          <div className="flex items-center gap-2 rounded-full border border-slate-700/80 bg-slate-900/85 px-3.5 py-1.5 text-xs text-slate-200 shadow-md backdrop-blur-md">
            <span className="h-2 w-2 rounded-full bg-[#2DD4BF] shadow-[0_0_8px_#2DD4BF]" />
            <span className="font-medium">{studentName}</span>
            <span className="text-slate-400 font-mono text-[11px]">({studentId})</span>
          </div>

          {onSignOut && (
            <button
              type="button"
              onClick={onSignOut}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-700/80 bg-slate-900/80 px-3.5 py-1.5 text-xs text-slate-300 shadow-md backdrop-blur-md transition-all duration-200 hover:text-rose-300 hover:border-rose-400/40 active:scale-95 cursor-pointer"
              title="Sign Out"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Sign Out</span>
            </button>
          )}
        </div>
      </header>

      {/* 3. DESKTOP / TABLET BOARD OVERLAYS (Positioned over the physical classroom boards) */}
      <main className="relative z-20 flex-1 w-full flex items-center justify-center p-2 sm:p-4">
        {/* 16:9 Aspect ratio container mapped precisely to the classroom boards */}
        <div className="relative w-full max-w-[1720px] aspect-video max-h-[88vh] hidden md:block">
          {/* ========================================================================= */}
          {/* GREEN CHALKBOARD (Left Board: 11.5% to 49% X, 18.5% to 52.5% Y)            */}
          {/* Positioned in the vertical middle of the board, dry matte chalk, zero glow */}
          {/* ========================================================================= */}
          <section
            aria-label="Green Chalkboard Welcome Area"
            className="absolute left-[11.5%] top-[18.5%] w-[37.5%] h-[34%] flex flex-col justify-center items-center text-center p-3 sm:p-4 overflow-hidden fade-in-smooth"
          >
            <div className="chalk-matte-filter flex flex-col items-center justify-center text-center w-full max-w-lg mx-auto select-none">
              {/* "Welcome back," in rough, matte chalk */}
              <h1 className="chalk-welcome text-2xl lg:text-[2.2rem] font-medium leading-none">
                Welcome back,
              </h1>

              {/* Student Name in pure milky white rough cursive chalk */}
              <p className="chalk-name text-3xl lg:text-[2.9rem] font-bold leading-tight my-1 sm:my-1.5">
                {studentName}
              </p>

              {/* The short line below */}
              <p className="chalk-sub text-sm lg:text-[1.1rem] font-normal leading-snug">
                Let&apos;s get started with today&apos;s orbital exploration.
              </p>

              {/* Student ID and attendance line */}
              <p className="chalk-meta text-xs lg:text-[0.85rem] font-normal tracking-wide mt-1.5 sm:mt-2">
                Student ID: {studentId} &bull; Attendance Verified
              </p>
            </div>
          </section>

          {/* ======================================================== */}
          {/* WHITE BOARD (Right Board: 52% to 84% X, 20% to 52% Y) */}
          {/* Clean chalk-like white text with high readability */}
          {/* ======================================================== */}
          <section
            aria-label="Whiteboard Student Tasks and Reminders"
            className="absolute left-[52%] top-[20%] w-[32.5%] h-[32%] flex flex-col justify-between px-5 lg:px-8 py-3.5 overflow-hidden fade-in-smooth-delay"
          >
            {/* Header: Next Exam Countdown Badge */}
            <div className="flex items-center justify-between pb-1 border-b border-white/20">
              <div className="flex items-center gap-1.5 text-xs lg:text-sm font-semibold tracking-wide text-white drop-shadow-[0_1px_3px_rgba(15,23,42,0.95)]">
                <Clock className="h-4 w-4 text-amber-300 drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]" />
                <span>Next Exam in:</span>
              </div>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold text-white bg-slate-900/60 border border-white/40 shadow-sm backdrop-blur-sm">
                4 Days Left (Physics Midterm)
              </span>
            </div>

            {/* Two Column Layout on Whiteboard: To-do List (Left) & Reminders (Right) */}
            <div className="grid grid-cols-2 gap-3 py-1 flex-1 overflow-hidden">
              {/* • To-Do List */}
              <div className="space-y-1.5">
                <h2 className="text-xs font-bold uppercase tracking-wider text-white drop-shadow-[0_1px_3px_rgba(15,23,42,0.95)] border-b border-white/15 pb-0.5">
                  To-Do List
                </h2>
                <ul className="space-y-1">
                  {todos.map((todo) => (
                    <li
                      key={todo.id}
                      onClick={() => toggleTodo(todo.id)}
                      className="group flex items-start gap-1.5 text-[11px] lg:text-xs text-white drop-shadow-[0_1px_3px_rgba(15,23,42,0.95)] cursor-pointer hover:text-white transition-colors"
                    >
                      {todo.completed ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-300 flex-shrink-0 mt-0.5 drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]" />
                      ) : (
                        <Circle className="h-3.5 w-3.5 text-white/70 flex-shrink-0 mt-0.5 group-hover:text-white" />
                      )}
                      <span className={`leading-snug ${todo.completed ? "line-through text-white/60" : "font-medium"}`}>
                        {todo.text}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* • Reminders */}
              <div className="space-y-1.5 pl-2 border-l border-white/20">
                <h2 className="text-xs font-bold uppercase tracking-wider text-white drop-shadow-[0_1px_3px_rgba(15,23,42,0.95)] border-b border-white/15 pb-0.5">
                  Reminders
                </h2>
                <ul className="space-y-1.5 text-[11px] lg:text-xs text-white drop-shadow-[0_1px_3px_rgba(15,23,42,0.95)]">
                  <li className="flex items-start gap-1.5 leading-snug">
                    <span className="text-amber-300 font-bold drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]">•</span>
                    <span>Review session: Friday 2:00 PM in Room 304</span>
                  </li>
                  <li className="flex items-start gap-1.5 leading-snug">
                    <span className="text-emerald-300 font-bold drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]">•</span>
                    <span>Allie AI Tutor available 24/7 for doubt clearance</span>
                  </li>
                </ul>
              </div>
            </div>

            {/* • "Visit Score Booster" Button or Link */}
            <div className="pt-1.5 flex items-center justify-between border-t border-white/20">
              <span className="text-[11px] text-white/80 drop-shadow-[0_1px_2px_rgba(15,23,42,0.9)] hidden lg:inline">
                Target: 95% Score Boost
              </span>
              <button
                type="button"
                onClick={() => setShowScoreBooster(true)}
                className="w-full lg:w-auto inline-flex items-center justify-center gap-1.5 rounded-full border border-slate-900/80 bg-slate-900/90 px-3.5 py-1 text-xs font-semibold text-white shadow-md hover:bg-[#2DD4BF] hover:text-slate-950 hover:border-[#2DD4BF] transition-all duration-200 active:scale-95 cursor-pointer"
              >
                <Zap className="h-3 w-3 text-amber-300 group-hover:text-slate-950" />
                <span>Visit Score Booster</span>
                <span className="text-[10px] ml-0.5">&rarr;</span>
              </button>
            </div>
          </section>
        </div>

        {/* 4. MOBILE / COMPACT FALLBACK (Rendered nicely for smaller screens) */}
        <div className="w-full max-w-lg mx-auto md:hidden space-y-4 my-auto fade-in-smooth">
          {/* Green Chalkboard Card on Mobile */}
          <div className="rounded-2xl border border-emerald-950/80 bg-[#1c2925]/95 p-6 shadow-2xl backdrop-blur-md text-white flex flex-col items-center justify-center text-center">
            <div className="chalk-matte-filter flex flex-col items-center justify-center text-center w-full space-y-1">
              <h1 className="chalk-welcome text-2xl font-medium leading-none">
                Welcome back,
              </h1>
              <p className="chalk-name text-3xl font-bold leading-tight my-1">
                {studentName}
              </p>
              <p className="chalk-sub text-sm font-normal leading-snug">
                Let&apos;s get started with today&apos;s orbital exploration.
              </p>
              <p className="chalk-meta text-xs font-normal tracking-wide mt-1.5">
                Student ID: {studentId} &bull; Attendance Verified
              </p>
            </div>
          </div>

          {/* Whiteboard Tasks Card on Mobile */}
          <div className="rounded-2xl border border-slate-700/80 bg-slate-900/85 p-5 shadow-2xl backdrop-blur-md text-white space-y-4">
            <div className="flex items-center justify-between border-b border-slate-700 pb-2">
              <span className="text-xs font-semibold text-white">Next Exam:</span>
              <span className="text-xs font-bold text-amber-300">4 Days Left (Physics)</span>
            </div>

            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">To-Do List</h2>
              <ul className="space-y-2">
                {todos.map((todo) => (
                  <li
                    key={todo.id}
                    onClick={() => toggleTodo(todo.id)}
                    className="flex items-center gap-2 text-xs cursor-pointer"
                  >
                    {todo.completed ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <Circle className="h-4 w-4 text-slate-400" />
                    )}
                    <span className={todo.completed ? "line-through text-slate-400" : "text-white"}>
                      {todo.text}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-1">Reminders</h2>
              <p className="text-xs text-slate-300">• Review session: Friday 2:00 PM</p>
              <p className="text-xs text-slate-300">• Allie AI 24/7 tutor active</p>
            </div>

            <button
              type="button"
              onClick={() => setShowScoreBooster(true)}
              className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[#2DD4BF] py-2.5 text-xs font-bold text-slate-950 shadow-lg hover:bg-emerald-400 transition-colors"
            >
              <Zap className="h-4 w-4" />
              <span>Visit Score Booster</span>
            </button>
          </div>
        </div>
      </main>

      {/* 5. Bottom Status Strip */}
      <footer className="relative z-30 w-full px-6 py-3 flex items-center justify-between text-xs text-white/60 bg-slate-950/40 backdrop-blur-sm">
        <span>Kepler Learning Environment &bull; Classroom View</span>
        <span>Active Session: Physics Mechanics</span>
      </footer>

      {/* 6. SCORE BOOSTER MODAL */}
      {showScoreBooster && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
          <div className="relative w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl text-white">
            <button
              type="button"
              onClick={() => setShowScoreBooster(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-2 text-[#2DD4BF] mb-2">
              <Zap className="h-5 w-5" />
              <span className="text-xs font-bold uppercase tracking-wider">Score Booster Engine</span>
            </div>

            <h3 className="text-lg font-bold">Physics Midterm Readiness</h3>
            <p className="text-xs text-slate-300 mt-1 mb-4">
              AI analysis of your latest quiz scores indicates you are 4 days away from your exam.
            </p>

            <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-3">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400">Projected Score:</span>
                <span className="font-bold text-emerald-400 text-sm">88% &rarr; 96% (+8%)</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2">
                <div className="bg-[#2DD4BF] h-2 rounded-full w-[88%]" />
              </div>
              <div className="text-[11px] text-slate-400 pt-1">
                Top Priority: Revisit <strong>Kepler&apos;s Second Law (Equal Areas)</strong> to maximize performance on section B questions.
              </div>
            </div>

            <div className="mt-5 flex gap-2">
              <button
                type="button"
                onClick={() => {
                  setShowScoreBooster(false);
                  if (onOpenLearningModule) onOpenLearningModule();
                }}
                className="flex-1 rounded-xl bg-[#2DD4BF] py-2 text-xs font-bold text-slate-950 hover:bg-teal-300 transition-colors"
              >
                Launch Targeted Practice
              </button>
              <button
                type="button"
                onClick={() => setShowScoreBooster(false)}
                className="px-4 rounded-xl border border-slate-700 text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
