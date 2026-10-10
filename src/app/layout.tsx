import type { Metadata } from "next";
import { Space_Grotesk } from "next/font/google";
import "./globals.css";
import { FloatingTaskbar } from "@/components/FloatingTaskbar";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Kepler | Learning Platform",
  description: "AI-powered learning platform with smart doubt solving and practice testing",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${spaceGrotesk.variable}`}>
      <body className="min-h-screen bg-[#0F172A] text-slate-50 antialiased selection:bg-[#2DD4BF]/30 selection:text-white">
        <FloatingTaskbar />
        {children}
      </body>
    </html>
  );
}
