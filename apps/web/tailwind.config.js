/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: {
          base: '#0b1220',
          panel: '#101a2e',
          card: '#172238',
          line: '#1f2c47',
        },
        accent: {
          DEFAULT: '#4f9cff',
          muted: '#2d6cb6',
        },
        warn: '#f0a500',
        crit: '#e25c5c',
        ok: '#3ec28f',
      },
      fontFamily: {
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
};
