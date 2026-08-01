import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0d12",
        panel: "#11151c",
        panelBorder: "#1f2530",
        bull: "#089981",
        bullBright: "#00ff88",
        bear: "#f23645",
        muted: "#7d8494",
        accentGold: "#e8b84b",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "monospace"],
        sans: ["'IBM Plex Sans Arabic'", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
