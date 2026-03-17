import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        shell: "#f4f1ea",
        ink: "#1f2937",
        moss: "#1f5134",
        clay: "#b35c44",
        pine: "#0e3a2d",
      },
      boxShadow: {
        card: "0 12px 28px rgba(17, 24, 39, 0.14)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        rise: "rise 420ms ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;
