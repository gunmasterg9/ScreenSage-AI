/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sage: {
          bg: '#fbfbfa',
          card: '#ffffff',
          subtle: '#f4f3ee',
          border: '#e6e4dc',
          muted: '#717568',
        },
        forest: {
          50: '#f0f7f3',
          100: '#dceee3',
          200: '#bbdec9',
          500: '#2d6a4f',
          700: '#1b4332',
          800: '#143526',
          900: '#102a1e',
          950: '#081710',
        },
        coral: {
          50: '#fff5f3',
          100: '#ffe8e4',
          500: '#e06d53',
          600: '#cc5439',
          700: '#ab4027',
        },
        ochre: {
          100: '#fef3c7',
          300: '#fcd34d',
          500: '#e9c46a',
          600: '#d4a337',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
