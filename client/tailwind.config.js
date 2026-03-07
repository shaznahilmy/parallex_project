/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Streamlit dark theme palette
        primary: {
          bg:        '#0e1117',   // page background
          card:      '#1e2130',   // card / expander body
          surface:   '#262730',   // borders, expander headers, inputs
          border:    '#3d4166',   // upload zone borders, nested borders
          muted:     '#181b27',   // deselected row bg
          text:      '#fafafa',   // primary text
          body:      '#cfd1db',   // body text
          subtle:    '#8b8fa8',   // labels, hints
          dim:       '#4a4f6a',   // very dim text / icons
          cyan:      '#4fc3f7',   // accent / chevrons / progress
          green:     '#21c45d',   // fully covered
          yellow:    '#fbbf24',   // partially covered
          red:       '#f87171',   // not covered
          btnred:    '#ff4b4b',   // primary action button
          infobg:    '#1a3a5c',   // blue info banner bg
          infotext:  '#cfe8ff',   // blue info banner text
          greenbg:   '#14291f',   // green info banner bg
        },
      },
      fontFamily: {
        sans: ["'Source Sans Pro'", "'Segoe UI'", 'sans-serif'],
        mono: ["'Fira Code'", "'Courier New'", 'monospace'],
      },
      maxHeight: {
        70: '280px',
      },
    },
  },
  plugins: [],
};