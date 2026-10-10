import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        "space-grotesk": ["var(--font-space-grotesk)", "'Space Grotesk'", "sans-serif"],
      },
      colors: {
        space: {
          950: "#070B14",
          900: "#0F172A",
          850: "#131C33",
          800: "#1E293B",
          700: "#334155",
        },
        bioluminescent: {
          teal: "#2DD4BF",
          tealGlow: "rgba(45, 212, 191, 0.4)",
        },
        softPurple: {
          DEFAULT: "#A78BFA",
          glow: "rgba(167, 139, 250, 0.4)",
        },
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        "float-delayed": "float 7s ease-in-out 1s infinite",
        "pulse-slow": "pulseSlow 5s ease-in-out infinite",
        twinkle: "twinkle 3s ease-in-out infinite",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px) rotate(0deg)" },
          "50%": { transform: "translateY(-16px) rotate(1.5deg)" },
        },
        pulseSlow: {
          "0%, 100%": { opacity: "0.3" },
          "50%": { opacity: "0.7" },
        },
        twinkle: {
          "0%, 100%": { opacity: "0.2", transform: "scale(0.8)" },
          "50%": { opacity: "0.9", transform: "scale(1.2)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
