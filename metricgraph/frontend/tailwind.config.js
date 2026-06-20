/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        margin: {
          bg: "#0b0f17",
          surface: "#121826",
          border: "#1e293b",
          primary: "#3b82f6",
          accent: "#6366f1",
          muted: "#94a3b8",
        },
      },
    },
  },
  plugins: [],
};
