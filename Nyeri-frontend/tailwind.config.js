/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#F7F7F4',
        surface: '#FFFFFF',
        ink: {
          DEFAULT: '#1C1F1D',
          muted: '#5B6560',
          faint: '#8A928C',
        },
        line: '#E2E5E1',
        forest: {
          50: '#EAF2ED',
          100: '#CFE1D6',
          300: '#6E9E7C',
          500: '#2E6B44',
          600: '#1F5535',
          700: '#14532D',
          800: '#0B3B1F',
          900: '#062615',
        },
        clay: {
          50: '#FBEEE8',
          100: '#F2D2C1',
          400: '#C15A31',
          500: '#A6431F',
          600: '#8A3618',
        },
        gold: {
          50: '#FAF1DE',
          100: '#F0DBA8',
          400: '#C08A28',
          500: '#A87620',
        },
      },
      fontFamily: {
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      borderRadius: {
        sm: '4px',
        DEFAULT: '6px',
        md: '8px',
        lg: '10px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(28, 31, 29, 0.06)',
        raised: '0 2px 8px rgba(28, 31, 29, 0.08)',
      },
      maxWidth: {
        content: '1180px',
      },
    },
  },
  plugins: [],
}
