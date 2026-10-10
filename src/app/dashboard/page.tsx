"use client";

import * as React from "react";
import { ClassroomDashboard } from "@/components/ClassroomDashboard";
import { StudentDashboard } from "@/components/StudentDashboard";
import { useRouter } from "next/navigation";

export default function DashboardRoute() {
  const router = useRouter();
  const [currentView, setCurrentView] = React.useState<"dashboard" | "learningModule">("dashboard");

  if (currentView === "learningModule") {
    return (
      <StudentDashboard
        onReplayIntro={() => setCurrentView("dashboard")}
        onSignOut={() => router.push("/")}
      />
    );
  }

  return (
    <ClassroomDashboard
      studentName="Alex Chen"
      studentId="10034455542"
      onSignOut={() => router.push("/")}
      onOpenLearningModule={() => setCurrentView("learningModule")}
      onOpenDoubtSolver={() => router.push("/ask")}
    />
  );
}
