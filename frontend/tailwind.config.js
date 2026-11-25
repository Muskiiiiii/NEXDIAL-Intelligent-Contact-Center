/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#090D18',
        'background-secondary': '#101827',
        card: '#151F30',
        'card-border': '#1E2C44',
        accent: {
          DEFAULT: '#7C6CFF',
          hover: '#6854F5',
          subtle: '#7C6CFF1F',
        },
        success: {
          DEFAULT: '#20C997',
          subtle: '#20C99722',
        },
        warning: {
          DEFAULT: '#F5B942',
          subtle: '#F5B94222',
        },
        danger: {
          DEFAULT: '#FF5C70',
          subtle: '#FF5C7022',
        },
        text: {
          DEFAULT: '#F5F7FF',
          muted: '#8B96AA',
          subtle: '#55637D',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Menlo', 'monospace'],
      },
      boxShadow: {
        'glow-accent': '0 0 20px -3px rgba(124, 108, 255, 0.25)',
        'glow-success': '0 0 20px -3px rgba(32, 201, 151, 0.25)',
        'glow-danger': '0 0 20px -3px rgba(255, 92, 112, 0.25)',
        'card-subtle': '0 4px 20px -2px rgba(0, 0, 0, 0.4)',
      },
    },
  },
  plugins: [],
}
