/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg0: "#0a0a1a",
        bg1: "#10102a",
        card: "rgba(20,20,50,0.65)",
        surface: "rgba(20, 20, 50, 0.4)",
        primary: "#6366f1",
        secondary: "#818cf8",
      }
    },
  },
  plugins: [],
}
