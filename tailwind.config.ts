import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: "#0F172A",
        "surface-container": "#111C33",
        "surface-container-high": "#1A2847",
        "surface-container-low": "#0B1326",
        "tertiary-container": "#173249",
        primary: "#52D7FF",
        secondary: "#2CD4B6",
        "on-surface": "#DDE8FF",
        "on-surface-variant": "#8FA8C7",
        "outline-variant": "#2A3A59",
        success: "#31D0AA",
        warning: "#F4B74A",
        danger: "#FF7A9B",
      },
      fontSize: {
        "headline-md-mobile": ["1.375rem", { lineHeight: "1.75rem", fontWeight: "700" }],
        "headline-md": ["1.75rem", { lineHeight: "2.125rem", fontWeight: "700" }],
        "title-sm": ["0.875rem", { lineHeight: "1.25rem", fontWeight: "600" }],
        "body-md": ["0.9375rem", { lineHeight: "1.5rem", fontWeight: "400" }],
        "code-md": ["0.8125rem", { lineHeight: "1.25rem", fontWeight: "500" }],
      },
      spacing: {
        4.5: "1.125rem",
        5.5: "1.375rem",
        18: "4.5rem",
        22: "5.5rem",
        30: "7.5rem",
      },
      boxShadow: {
        panel: "0 24px 48px -24px rgba(0, 0, 0, 0.55)",
        inner: "inset 0 1px 0 rgba(255, 255, 255, 0.08)",
      },
      animation: {
        "pulse-soft": "pulseSoft 1.8s ease-in-out infinite",
        "slide-up": "slideUp 0.45s cubic-bezier(0.16, 1, 0.3, 1)",
      },
      keyframes: {
        pulseSoft: {
          "0%, 100%": { opacity: "0.45", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.08)" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(10px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
