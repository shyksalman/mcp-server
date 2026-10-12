import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        mist: "#f6f8fb",
        line: "#dce3ec",
        brand: "#2563eb",
        success: "#16825d",
        danger: "#c2410c"
      },
      boxShadow: {
        soft: "0 14px 34px rgba(23, 32, 51, 0.08)"
      }
    }
  },
  plugins: [require("@tailwindcss/typography")]
};

export default config;
