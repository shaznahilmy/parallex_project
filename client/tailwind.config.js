/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["'Source Sans Pro'", "'Segoe UI'", "sans-serif"],
        mono: ["'Fira Code'", "'Courier New'", "monospace"],
      },
      maxHeight: {
        70: "280px",
      },
    },
  },
  plugins: [],
};
