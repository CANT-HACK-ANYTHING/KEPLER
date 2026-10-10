import { Metadata } from "next";
import { BookOpen } from "lucide-react";

export const metadata: Metadata = {
  title: "Learning Materials",
  description: "Curated learning materials, course notes, and study modules.",
};

export default function LearnPage() {
  return (
    <div className="min-h-screen w-full bg-[#FFFFFF] text-slate-800 flex flex-col items-center justify-center p-6 pl-20 sm:pl-24 antialiased">
      <div className="w-full max-w-2xl flex flex-col items-center text-center">
        {/* Header Icon */}
        <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center mb-5 text-blue-600 shadow-sm">
          <BookOpen className="w-7 h-7" />
        </div>

        {/* Title */}
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 mb-2">
          Learning Materials
        </h1>

        {/* Subtitle */}
        <p className="text-slate-500 text-sm sm:text-base max-w-md mb-8">
          Course syllabus, concept notes, and interactive modules will be connected to your database here.
        </p>

        {/* Minimal Placeholder State */}
        <div className="w-full rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 p-10 flex flex-col items-center justify-center text-slate-400">
          <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center mb-3 text-slate-400">
            <BookOpen className="w-5 h-5" />
          </div>
          <span className="text-sm font-medium text-slate-600 mb-1">
            No materials loaded yet
          </span>
          <span className="text-xs text-slate-400">
            Database connection pending
          </span>
        </div>
      </div>
    </div>
  );
}
