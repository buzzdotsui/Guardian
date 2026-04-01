/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        slate: {
          950: "#0b0f19",
          900: "#111827",
          800: "#1f2937",
          700: "#374151",
          400: "#94a3b8",
          100: "#f8fafc",
        },
        indigo: {
          500: "#6366f1",
          600: "#4f46e5",
          400: "#818cf8",
        },
        emerald: {
          500: "#10b981",
          400: "#34d399",
        },
        rose: {
          500: "#f43f5e",
          600: "#e11d48",
        }
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      backgroundImage: {
        'grid-slate': "linear-gradient(to right, #1e293b 1px, transparent 1px), linear-gradient(to bottom, #1e293b 1px, transparent 1px)",
      }
    },
  },
  plugins: [],
}
