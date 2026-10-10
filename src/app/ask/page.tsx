import { Metadata } from "next";
import { DoubtSolvingInterface } from "@/components/DoubtSolvingInterface";

export const metadata: Metadata = {
  title: "AI Assistant — Doubt Solver",
  description: "AI-powered doubt solving interface with Socratic Method, Detailed Explanation, and Exam Ready modes.",
};

export default function AskPage() {
  return <DoubtSolvingInterface />;
}
