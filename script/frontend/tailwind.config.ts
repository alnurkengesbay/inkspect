import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        accent: "#2563eb",
        danger: "#ef4444",
        success: "#22c55e"
      }
    }
  },
  plugins: []
} satisfies Config;
