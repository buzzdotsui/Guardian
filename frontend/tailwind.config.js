/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        hudBg: "#000000",
        hudCard: "rgba(0, 15, 20, 0.8)",
        hudBorder: "rgba(0, 221, 255, 0.4)",
        hudCyan: "#00ddff",
        hudRed: "#ff2a2a",
        hudAmber: "#ffb400",
        hudGreen: "#00ff88",
        hudText: "#c0f8ff",
      },
      fontFamily: {
        sans: ['Rajdhani', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      backgroundImage: {
        'scanlines': "repeating-linear-gradient(to bottom, transparent 0px, transparent 2px, rgba(0, 221, 255, 0.05) 3px, rgba(0, 221, 255, 0.05) 4px)",
      }
    },
  },
  plugins: [],
}
