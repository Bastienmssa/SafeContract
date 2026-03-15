import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Palette officielle SafeContract – dégradé du logo #2cbe88 → #152d5b
        primary: {
          DEFAULT: "#2cbe88",
          50: "#e8f7f0",
          100: "#b8edd9",
          200: "#88e2c0",
          300: "#58d7a7",
          400: "#2cbe88",
          500: "#249e7a",
          600: "#1c7e6c",
          700: "#185e6a",
          800: "#163e58",
          900: "#152d5b",
        },
        // Alias pour cohérence
        dark: {
          DEFAULT: "#152d5b",
          600: "#1c7e6c",
          700: "#185e6a",
          800: "#163e58",
          900: "#152d5b",
        },
        light: {
          DEFAULT: "#f8fafc",
          50: "#ffffff",
          100: "#f8fafc",
          200: "#f1f5f9",
          300: "#e2e8f0",
          400: "#cbd5e1",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
