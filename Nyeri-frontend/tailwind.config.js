/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#F7F7F4',
        surface: '#FFFFFF',
        ink: {
          DEFAULT: '#000000',
          muted: '#333333',
          faint: '#555555',
        },
        line: '#CCCCCC',
        forest: {
          50: '#EAF2ED',
          100: '#CFE1D6',
          300: '#6E9E7C',
          500: '#2E6B44',
          600: '#1F5535',
          700: '#0B3B1F',
          800: '#082510',
          900: '#030F05',
        },
        clay: {
          50: '#FBEEE8',
          100: '#F2D2C1',
          400: '#C15A31',
          500: '#A6431F',
          600: '#8A3618',
          700: '#6D2C12',
          800: '#51210E',
        },
        gold: {
          50: '#FAF1DE',
          100: '#F0DBA8',
          400: '#C08A28',
          500: '#A87620',
          600: '#8F5C16',
        },
      },
      fontFamily: {
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
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
