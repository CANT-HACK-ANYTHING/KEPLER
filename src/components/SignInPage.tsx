"use client";

import * as React from "react";
import { Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
      />
    </svg>
  );
}

function SparkleStar({
  className,
  glowColor = "rgba(254, 240, 138, 0.8)",
}: {
  className?: string;
  glowColor?: string;
}) {
  return (
    <div
      className={`absolute pointer-events-none select-none animate-sparkle ${className}`}
      style={{ filter: `drop-shadow(0 0 8px ${glowColor})` }}
    >
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-full h-full">
        <path d="M12 0C12 6.627 6.627 12 0 12C6.627 12 12 17.373 12 24C12 17.373 17.373 12 24 12C17.373 12 12 6.627 12 0Z" />
      </svg>
    </div>
  );
}

function PastelClouds() {
  return (
    <div className="absolute -bottom-1 inset-x-0 w-full h-[280px] pointer-events-none overflow-hidden z-0">
      <svg
        viewBox="0 0 1200 360"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full object-cover"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="cloudWarm1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFF1E2" stopOpacity="0.85" />
            <stop offset="50%" stopColor="#FED7AA" stopOpacity="0.7" />
            <stop offset="100%" stopColor="#FDE68A" stopOpacity="0.6" />
          </linearGradient>
          <linearGradient id="cloudWarm2" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.95" />
            <stop offset="50%" stopColor="#FFF3E6" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#FED7AA" stopOpacity="0.8" />
          </linearGradient>
          <linearGradient id="cloudLavender" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#E9D5FF" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#FFF5EB" stopOpacity="0.85" />
          </linearGradient>
          <filter id="softGlow" x="-15%" y="-15%" width="130%" height="130%">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        <circle cx="150" cy="280" r="190" fill="url(#cloudLavender)" filter="url(#softGlow)" />
        <circle cx="520" cy="270" r="210" fill="url(#cloudWarm1)" filter="url(#softGlow)" />
        <circle cx="950" cy="260" r="230" fill="url(#cloudWarm1)" filter="url(#softGlow)" />

        <circle cx="340" cy="290" r="180" fill="url(#cloudWarm2)" />
        <circle cx="750" cy="300" r="190" fill="url(#cloudWarm2)" />
        <circle cx="1120" cy="290" r="170" fill="url(#cloudWarm2)" />
        <circle cx="0" cy="320" r="160" fill="url(#cloudWarm2)" />

        <path
          d="M0 360L0 290C50 250 140 250 200 280C270 230 400 230 470 270C550 220 700 220 780 260C860 210 1020 210 1100 260C1150 240 1190 260 1200 280V360H0Z"
          fill="url(#cloudWarm2)"
        />
      </svg>
    </div>
  );
}

interface SignInPageProps {
  onSignIn: () => void;
  isFadingOut?: boolean;
}

export function SignInPage({ onSignIn, isFadingOut = false }: SignInPageProps) {
  const [studentId, setStudentId] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const [useVideoAnimation] = React.useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isFadingOut) return;
    onSignIn();
  };

  const handleGoogleClick = () => {
    if (isFadingOut) return;
    onSignIn();
  };

  return (
    <div
      className={`min-h-screen w-full flex flex-col lg:flex-row relative overflow-hidden select-none transition-opacity duration-700 ease-in-out ${
        isFadingOut ? "opacity-0 pointer-events-none" : "opacity-100"
      }`}
    >
      {/* LEFT COLUMN: The Form */}
      <section
        className="w-full lg:w-1/2 min-h-screen flex flex-col justify-center items-center px-6 sm:px-12 lg:px-16 py-16 z-10 relative overflow-hidden"
        style={{
          background:
            "radial-gradient(circle at 10% 12%, #FFF4E2 0%, #FFF9F2 45%, #FFFFFF 90%)",
        }}
      >
        <div className="w-full max-w-[420px] mx-auto pt-6">
          <div className="text-center mb-9 sm:mb-10">
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-slate-900">
              Sign In
            </h1>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5 sm:space-y-6">
            <div className="space-y-2 text-left">
              <label
                htmlFor="studentId"
                className="block text-sm font-medium text-slate-800"
              >
                Student ID
              </label>
              <Input
                id="studentId"
                name="studentId"
                type="text"
                placeholder="1003445542"
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                autoComplete="username"
                required
              />
            </div>

            <div className="space-y-2 text-left">
              <label
                htmlFor="password"
                className="block text-sm font-medium text-slate-800"
              >
                Password
              </label>
              <div className="relative">
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  className="pr-12"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 transition-colors focus:outline-none"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>

              <div className="pt-1 text-left">
                <a
                  href="#forgot-password"
                  className="text-xs sm:text-sm text-slate-500 hover:text-slate-900 transition-colors inline-block"
                >
                  Forgot password?
                </a>
              </div>
            </div>

            <div className="pt-2">
              <Button
                type="submit"
                variant="gradient"
                className="w-full h-12 sm:h-13 text-sm sm:text-base font-semibold"
              >
                Sign In
              </Button>
            </div>

            <div className="pt-1 text-center text-sm text-slate-500">
              Don&apos;t have an account?{" "}
              <a
                href="#signup"
                className="text-slate-900 font-bold hover:underline transition-all inline-block ml-0.5"
              >
                Sign up
              </a>
            </div>

            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200/90" />
              </div>
              <div className="relative flex justify-center text-xs sm:text-sm">
                <span className="bg-[#FFF9F3] px-4 text-slate-400">
                  Or continue with
                </span>
              </div>
            </div>

            <Button
              type="button"
              variant="outline"
              className="w-full h-12 sm:h-13 text-sm sm:text-base font-medium flex items-center justify-center gap-3"
              onClick={handleGoogleClick}
            >
              <GoogleIcon className="h-5 w-5 flex-shrink-0" />
              <span className="text-slate-800 font-medium">
                Continue with Google
              </span>
            </Button>
          </form>
        </div>

        {/* Soft edge blend toward dividing seam */}
        <div
          className="absolute inset-x-0 bottom-0 h-16 lg:h-full lg:w-32 lg:inset-y-0 lg:right-0 lg:left-auto pointer-events-none bg-gradient-to-b lg:bg-gradient-to-r from-transparent to-white"
          aria-hidden="true"
        />
      </section>

      {/* RIGHT COLUMN: The Visual */}
      <section className="w-full lg:w-1/2 min-h-[520px] lg:min-h-screen relative flex h-full w-full items-center justify-center overflow-hidden bg-gradient-to-b from-[#DDD3F8] via-[#DBEAFE] to-[#FEE8D4]">
        {/* Seamless Dividing Edge Gradient Transition (Melts background into form) */}
        <div
          className="absolute inset-x-0 top-0 h-28 lg:h-full lg:w-48 xl:w-72 lg:inset-y-0 lg:left-0 lg:right-auto z-20 pointer-events-none bg-gradient-to-b lg:bg-gradient-to-r from-white via-white/70 to-white/0"
          aria-hidden="true"
        />
        {useVideoAnimation ? (
          <div className="flex h-full w-full items-center justify-center overflow-hidden">
            <video
              autoPlay
              loop
              muted
              playsInline
              poster="/video_frame.png"
              className="w-full h-full max-w-full max-h-full object-contain select-none pointer-events-none"
            >
              <source src="/localtutor_active_scene.mp4" type="video/mp4" />
            </video>
          </div>
        ) : (
          <>
            <SparkleStar
              className="top-12 left-1/4 w-5 h-5 text-[#FEF08A]"
              glowColor="rgba(254, 240, 138, 0.9)"
            />
            <SparkleStar
              className="top-24 right-1/4 w-4 h-4 text-white"
              glowColor="rgba(255, 255, 255, 0.9)"
            />
            <SparkleStar
              className="top-1/3 left-12 w-3.5 h-3.5 text-white/90"
              glowColor="rgba(255, 255, 255, 0.8)"
            />
            <SparkleStar
              className="top-2/5 right-12 w-4 h-4 text-[#FED7AA]"
              glowColor="rgba(254, 215, 170, 0.8)"
            />
            <SparkleStar
              className="bottom-1/3 left-1/5 w-3 h-3 text-[#E9D5FF]"
              glowColor="rgba(233, 213, 255, 0.8)"
            />

            <PastelClouds />
            <div className="w-full h-4 z-10" />

            <div className="relative z-10 my-auto flex h-full w-full items-center justify-center overflow-hidden py-6 sm:py-10">
              <div className="absolute -inset-10 bg-radial from-white/40 via-purple-200/20 to-transparent rounded-full blur-2xl pointer-events-none" />
              <img
                src="/astronaut.png"
                alt="Floating 3D Astronaut"
                className="w-full h-full max-w-full max-h-full object-contain select-none animate-float filter drop-shadow-[0_22px_40px_rgba(147,112,219,0.22)] pointer-events-none"
              />
            </div>

            <div className="relative z-10 text-center max-w-md mx-auto pt-6 pb-2">
              <blockquote className="text-lg sm:text-xl font-normal text-slate-800 tracking-tight leading-relaxed">
                &ldquo;Welcome back. A new chapter awaits.&rdquo;
              </blockquote>
              <p className="mt-1.5 text-xs sm:text-sm text-slate-500 font-normal">
                &mdash; Kepler
              </p>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
