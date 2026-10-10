"use client";

import * as React from "react";
import { Send, Sparkles, BookOpen, Clock, ChevronRight, User, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Message {
  id: string;
  sender: "allie" | "user";
  text: string;
  timestamp: string;
}

interface StudentDashboardProps {
  onReplayIntro?: () => void;
  onSignOut?: () => void;
}

export function StudentDashboard({ onReplayIntro, onSignOut }: StudentDashboardProps) {
  const [messages, setMessages] = React.useState<Message[]>([
    {
      id: "1",
      sender: "allie",
      text: "Welcome to your Kepler Dashboard! I'm Allie, your AI tutor. We're currently exploring orbital dynamics and zero-gravity celestial mechanics. How can I assist you today?",
      timestamp: "10:14 AM",
    },
    {
      id: "2",
      sender: "user",
      text: "Can you explain why the astronaut floats in zero gravity instead of falling down?",
      timestamp: "10:15 AM",
    },
    {
      id: "3",
      sender: "allie",
      text: "Great question! The astronaut is actually in continuous free fall around the Earth at roughly 17,500 mph. Gravity is pulling them downward, but their forward orbital velocity matches the Earth's curvature, resulting in apparent weightlessness!",
      timestamp: "10:15 AM",
    },
  ]);

  const [inputMessage, setInputMessage] = React.useState("");
  const [isTyping, setIsTyping] = React.useState(false);
  const chatScrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSendMessage = (textToSend?: string) => {
    const text = textToSend || inputMessage;
    if (!text.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: "user",
      text: text.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputMessage("");
    setIsTyping(true);

    setTimeout(() => {
      let replyText = "That's a key insight in celestial mechanics! Gravitational pull precisely balances centrifugal force in stable planetary orbits.";
      const lower = text.toLowerCase();
      if (lower.includes("kepler") || lower.includes("law")) {
        replyText = "Kepler's First Law states orbits are ellipses with the Sun at one focus. His Second Law explains that a radius vector sweeps out equal areas in equal times!";
      } else if (lower.includes("quiz") || lower.includes("test")) {
        replyText = "Quick quiz: If an orbital radius quadruples, what happens to the orbital period T under Kepler's 3rd Law? (Hint: T² ∝ a³)";
      } else if (lower.includes("summarize") || lower.includes("summary")) {
        replyText = "Summary: This module demonstrates orbital mechanics, zero-gravity trajectories, and how Keplerian parameters govern spacecraft flight paths.";
      }

      const allieMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: "allie",
        text: replyText,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, allieMsg]);
      setIsTyping(false);
    }, 1000);
  };

  const quickPrompts = [
    "Explain Kepler's 2nd Law",
    "Summarize this lesson",
    "Quiz me on orbital velocity",
  ];

  return (
    <div className="min-h-screen w-full bg-[#0F172A] text-slate-50 flex flex-col selection:bg-[#2DD4BF]/30 selection:text-white animate-in fade-in duration-500">
      {/* MAIN NAVBAR: Kepler Logo in Top-Left with Space Grotesk & Wide Tracking */}
      <header className="w-full border-b border-slate-800/80 bg-[#0B1120]/90 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Top-Left: Kepler Logo */}
          <div className="flex items-center gap-4">
            <a
              href="/"
              className="group inline-flex items-center gap-2.5 transition-all duration-300"
              title="Kepler Learning Architecture"
            >
              <span className="h-2.5 w-2.5 rounded-full bg-[#2DD4BF] shadow-[0_0_10px_#2DD4BF] transition-transform duration-300 group-hover:scale-125" />
              <span className="font-space-grotesk font-medium text-lg tracking-[0.15em] text-slate-50 transition-colors duration-300 group-hover:text-[#2DD4BF]">
                Kepler
              </span>
            </a>

            <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400 pl-4 border-l border-slate-800">
              <span className="text-slate-500">Module 3</span>
              <ChevronRight className="h-3 w-3 text-slate-600" />
              <span className="text-slate-300 font-medium">Orbital Mechanics</span>
            </div>
          </div>

          {/* Right Header Controls */}
          <div className="flex items-center gap-3">
            {onReplayIntro && (
              <button
                type="button"
                onClick={onReplayIntro}
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:text-[#2DD4BF] hover:border-[#2DD4BF]/40 transition-colors"
                title="Replay cinematic intro transition"
              >
                <RotateCcw className="h-3 w-3" />
                <span>Replay Intro</span>
              </button>
            )}
            <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/80 border border-slate-800 text-xs text-slate-300">
              <Clock className="h-3.5 w-3.5 text-[#2DD4BF]" />
              <span>Session: 24m active</span>
            </div>
            <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-full pl-3 pr-2 py-1 text-xs text-slate-200">
              <span>Student ID: <span className="text-slate-400 font-mono">1003445542</span></span>
              <div className="h-6 w-6 rounded-full bg-slate-800 flex items-center justify-center text-slate-300">
                <User className="h-3.5 w-3.5" />
              </div>
            </div>
            {onSignOut && (
              <button
                type="button"
                onClick={onSignOut}
                className="text-xs text-slate-400 hover:text-slate-200 transition-colors px-2 py-1"
              >
                Sign Out
              </button>
            )}
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER: Strict CSS Grid Wrapper below the navbar */}
      <main className="flex-1 w-full px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <div className="grid grid-cols-1 lg:grid-cols-10 gap-8 w-full max-w-7xl mx-auto">
          {/* LEFT COLUMN: The Video (70% width) */}
          <section className="col-span-1 lg:col-span-7 w-full overflow-hidden flex flex-col space-y-4">
            <div className="w-full overflow-hidden rounded-xl bg-black/40 border border-slate-800 shadow-xl">
              <video
                src="/localtutor_active_scene.mp4"
                poster="/video_frame.png"
                controls
                autoPlay
                loop
                muted
                playsInline
                className="w-full max-w-full h-auto rounded-xl shadow-lg aspect-video object-cover block"
              >
                Your browser does not support the video tag.
              </video>
            </div>

            {/* Video Metadata & Chapter Details */}
            <div className="rounded-xl border border-slate-800/80 bg-[#0B1120] p-5 shadow-sm space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#2DD4BF]/10 text-[#2DD4BF] border border-[#2DD4BF]/20">
                    Live Lesson
                  </span>
                  <span className="text-xs text-slate-400">Physics 101 • Section 4</span>
                </div>
                <span className="text-xs text-slate-500 font-mono">4:00 Looped Simulation</span>
              </div>

              <div>
                <h1 className="text-xl sm:text-2xl font-semibold text-slate-50 tracking-tight">
                  Orbital Mechanics & Zero-Gravity Dynamics
                </h1>
                <p className="mt-1 text-sm text-slate-300 leading-relaxed">
                  Observe how gravitational attraction and orbital velocity interact to create stable elliptical trajectories in space.
                </p>
              </div>

              <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center gap-4 text-xs text-slate-400">
                <span className="flex items-center gap-1.5">
                  <BookOpen className="h-3.5 w-3.5 text-purple-400" />
                  Key Formula: <code className="text-slate-200 bg-slate-900 px-1.5 py-0.5 rounded font-mono">v = √(GM / r)</code>
                </span>
                <span className="flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-[#2DD4BF]" />
                  Kepler AI Co-Pilot Active
                </span>
              </div>
            </div>
          </section>

          {/* RIGHT COLUMN: The Chat Box - Allie (30% width) */}
          <section className="col-span-1 lg:col-span-3 h-full w-full">
            <div className="flex flex-col h-full min-h-[540px] lg:min-h-[600px] rounded-xl border border-slate-800 bg-[#0B1120] shadow-xl overflow-hidden">
              {/* Allie Chat Header */}
              <div className="px-4 py-3.5 border-b border-slate-800 bg-[#0d1424] flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="relative">
                    <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-purple-600 via-indigo-600 to-[#2DD4BF] p-0.5 shadow-sm">
                      <div className="h-full w-full rounded-full bg-[#0B1120] flex items-center justify-center text-xs font-semibold text-slate-100">
                        AL
                      </div>
                    </div>
                    <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-[#2DD4BF] ring-2 ring-[#0B1120] shadow-[0_0_8px_#2DD4BF]" />
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-1.5">
                      Allie
                      <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.2 rounded bg-[#2DD4BF]/15 text-[#2DD4BF]">
                        AI Tutor
                      </span>
                    </h2>
                    <p className="text-[11px] text-slate-400">Kepler Learning Assistant</p>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-[11px] text-slate-400 font-medium">Online</span>
                </div>
              </div>

              {/* Chat Messages */}
              <div
                ref={chatScrollRef}
                className="flex-1 overflow-y-auto p-4 space-y-3.5"
              >
                {messages.map((msg) => {
                  const isAllie = msg.sender === "allie";
                  return (
                    <div
                      key={msg.id}
                      className={`flex flex-col ${isAllie ? "items-start" : "items-end"}`}
                    >
                      <div
                        className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 text-xs sm:text-sm leading-relaxed shadow-sm ${
                          isAllie
                            ? "bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-sm"
                            : "bg-[#2DD4BF] text-slate-950 font-medium rounded-tr-sm shadow-[0_2px_12px_rgba(45,212,191,0.25)]"
                        }`}
                      >
                        {msg.text}
                      </div>
                      <span className="text-[10px] text-slate-500 mt-1 px-1">
                        {msg.timestamp}
                      </span>
                    </div>
                  );
                })}

                {isTyping && (
                  <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-sm px-3.5 py-2 w-16 text-slate-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#2DD4BF] animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="h-1.5 w-1.5 rounded-full bg-[#2DD4BF] animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="h-1.5 w-1.5 rounded-full bg-[#2DD4BF] animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                )}
              </div>

              {/* Quick Prompts */}
              <div className="px-3 py-2 border-t border-slate-800/60 bg-[#070c18]/60 overflow-x-auto flex gap-1.5 no-scrollbar">
                {quickPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => handleSendMessage(prompt)}
                    className="whitespace-nowrap rounded-full border border-slate-800 bg-slate-900/80 px-2.5 py-1 text-[11px] text-slate-300 hover:border-[#2DD4BF]/50 hover:text-[#2DD4BF] hover:bg-slate-800 transition-colors"
                  >
                    {prompt}
                  </button>
                ))}
              </div>

              {/* Input Form */}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="p-3 border-t border-slate-800 bg-[#0d1424] flex items-center gap-2"
              >
                <div className="relative flex-1">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder="Ask Allie about this lesson..."
                    className="w-full rounded-lg border border-slate-700 bg-[#070c18] px-3.5 py-2 text-xs sm:text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-[#2DD4BF]/50 transition-all"
                  />
                </div>
                <Button
                  type="submit"
                  disabled={!inputMessage.trim()}
                  className="h-9 w-9 p-0 rounded-lg bg-[#2DD4BF] text-slate-950 font-semibold hover:bg-[#20b8a5] transition-all disabled:opacity-40 disabled:pointer-events-none flex items-center justify-center flex-shrink-0 shadow-[0_0_12px_rgba(45,212,191,0.3)]"
                  title="Send message to Allie"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </form>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
