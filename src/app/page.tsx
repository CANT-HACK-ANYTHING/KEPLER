"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { SignInPage } from "@/components/SignInPage";
import { IntroTransition } from "@/components/IntroTransition";
import { ClassroomDashboard } from "@/components/ClassroomDashboard";
import { StudentDashboard } from "@/components/StudentDashboard";

export default function Home() {
  const router = useRouter();
  const [currentView, setCurrentView] = React.useState<"signin" | "intro" | "dashboard" | "learningModule">("signin");
  const [isFadingOut, setIsFadingOut] = React.useState(false);
  const [isCrossfadingIntro, setIsCrossfadingIntro] = React.useState(false);

  const handleStartTransition = () => {
    // 1. Immediately mount intro video behind login form for a seamless crossfade
    setIsCrossfadingIntro(true);
    // 2. Trigger smooth 0.75s opacity fade-out on the login form
    setIsFadingOut(true);

    // 3. Cleanly transition after 750ms: unmount sign-in and preserve intro
    setTimeout(() => {
      setCurrentView("intro");
      setIsFadingOut(false);
      setIsCrossfadingIntro(false);
    }, 750);
  };

  const handleTransitionComplete = () => {
    setCurrentView("dashboard");
    router.push("/dashboard");
  };

  const handleSignOut = () => {
    setCurrentView("signin");
  };

  return (
    <main className="min-h-screen w-full relative bg-[#0F172A] overflow-hidden">
      {/* 1. Cinematic Intro Transition Overlay (Mounted during active intro or during login crossfade) */}
      {(currentView === "intro" || isCrossfadingIntro) && (
        <div className={`fixed inset-0 z-10 transition-opacity duration-700 ease-out ${isCrossfadingIntro ? "animate-in fade-in duration-700" : ""}`}>
          <IntroTransition
            onComplete={handleTransitionComplete}
            redirectTo="/dashboard"
          />
        </div>
      )}

      {/* 2. Sign In Page View with Crossfade transition support (0.7s smooth fade out) */}
      {currentView === "signin" && (
        <div className={`relative z-20 transition-opacity duration-700 ease-in-out ${isFadingOut ? "opacity-0 pointer-events-none" : "opacity-100"}`}>
          <SignInPage
            onSignIn={handleStartTransition}
            isFadingOut={isFadingOut}
          />
        </div>
      )}

      {/* 3. Main Classroom Dashboard View (After Login) */}
      {currentView === "dashboard" && (
        <ClassroomDashboard
          studentName="Alex Chen"
          studentId="10034455542"
          onSignOut={handleSignOut}
          onOpenLearningModule={() => setCurrentView("learningModule")}
          onOpenDoubtSolver={() => router.push("/ask")}
        />
      )}

      {/* 4. Optional AI Learning Module & Allie Chat */}
      {currentView === "learningModule" && (
        <StudentDashboard
          onReplayIntro={() => setCurrentView("dashboard")}
          onSignOut={handleSignOut}
        />
      )}
    </main>
  );
}
