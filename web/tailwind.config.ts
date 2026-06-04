import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0a0a0a",
          900: "#111111",
          800: "#1a1a1a",
          700: "#262626",
          600: "#3a3a3a",
          500: "#5c5c5c",
          400: "#8a8a8a",
          300: "#b5b5b5",
          200: "#d6d6d6",
          100: "#ededed",
        },
        accent: {
          DEFAULT: "#c4f25e",
          dim: "#9bc041",
        },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo"],
      },
    },
  },
  plugins: [],
};

export default config;
