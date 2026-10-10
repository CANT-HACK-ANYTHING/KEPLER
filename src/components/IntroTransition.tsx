"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

interface IntroTransitionProps {
  onComplete?: () => void;
  redirectTo?: string;
}

export function IntroTransition({
  onComplete,
  redirectTo = "/dashboard",
}: IntroTransitionProps) {
  const router = useRouter();
  const videoRef = React.useRef<HTMLVideoElement>(null);
  const hasProceeded = React.useRef(false);

  // Proceed handler to automatically navigate to the main dashboard
  const handleProceed = React.useCallback(() => {
    if (hasProceeded.current) return;
    hasProceeded.current = true;

    if (onComplete) {
      onComplete();
    } else if (redirectTo) {
      router.push(redirectTo);
    }
  }, [onComplete, redirectTo, router]);

  // When video naturally ends: hold briefly on the final classroom frame, then auto-navigate
  const handleVideoEnded = React.useCallback(() => {
    if (videoRef.current) {
      videoRef.current.pause();
    }
    // Short transition pause (500ms) on the classroom frame before automatic navigation
    setTimeout(() => {
      handleProceed();
    }, 500);
  }, [handleProceed]);

  // Safety fallback: auto-proceed after 12s if video encounters autoplay or playback delays
  React.useEffect(() => {
    const safetyTimer = setTimeout(() => {
      handleProceed();
    }, 12000);

    return () => clearTimeout(safetyTimer);
  }, [handleProceed]);

  return (
    <div
      className="fixed inset-0 z-10 flex items-center justify-center bg-[#0F172A] overflow-hidden select-none"
    >
      {/* 
        ASSET MANAGEMENT NOTE:
        The raw video file originates from:
        C:\Users\OJUS\Desktop\PYSUSTAIN\FPV_drone_entering_school_classroom_20261010012134.mp4
        It must be physically moved into the Next.js /public directory as:
        /public/FPV_drone_entering_school_classroom_20261010012134.mp4
        so that the frontend path resolves correctly at runtime.
      */}
      {/* Cinematic Native HTML5 Video Player */}
      <video
        ref={videoRef}
        src="/FPV_drone_entering_school_classroom_20261010012134.mp4"
        autoPlay
        muted
        playsInline
        onEnded={handleVideoEnded}
        className="w-full h-full object-cover block"
      >
        Your browser does not support the video tag.
      </video>

      {/* Subtle Vignette Overlay for cinematic atmosphere */}
      <div className="absolute inset-0 pointer-events-none bg-gradient-to-t from-[#0F172A]/70 via-transparent to-[#0F172A]/50" />
    </div>
  );
}
