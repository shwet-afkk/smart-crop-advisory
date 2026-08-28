/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paddy: {
          50: '#F6F8F0',
          100: '#EEF3E4',
          200: '#DCE7C9',
        },
        forest: {
          400: '#3C7A5C',
          500: '#2A5D45',
          600: '#1F4D36',
          700: '#153A28',
          900: '#0C2318',
        },
        turmeric: {
          300: '#F4C866',
          400: '#EDB53F',
          500: '#E8A324',
          600: '#C6850F',
        },
        laterite: {
          400: '#C9622F',
          500: '#B8461E',
          600: '#963816',
        },
        sky: {
          400: '#5FA0C7',
          500: '#3D7EA6',
          600: '#2E6488',
        },
        severity: {
          healthy: '#2F9E52',
          moderate: '#E8A324',
          critical: '#C23B22',
        },
      },
      fontFamily: {
        display: ['"Inter"', '"Noto Sans Kannada"', '"Noto Sans Devanagari"', 'system-ui', 'sans-serif'],
        body: ['"Inter"', '"Noto Sans Kannada"', '"Noto Sans Devanagari"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        leaf: '0 8px 24px -8px rgba(31, 77, 54, 0.35)',
        card: '0 2px 12px rgba(31, 77, 54, 0.10)',
      },
      keyframes: {
        pulseRing: {
          '0%': { transform: 'scale(0.9)', opacity: '0.6' },
          '80%': { transform: 'scale(1.6)', opacity: '0' },
          '100%': { transform: 'scale(1.6)', opacity: '0' },
        },
        riseIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        pulseRing: 'pulseRing 2.2s cubic-bezier(0.4,0,0.6,1) infinite',
        riseIn: 'riseIn 0.5s ease-out both',
      },
    },
  },
  plugins: [],
}
