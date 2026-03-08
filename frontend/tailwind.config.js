/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        navy: '#0F172A',
        'warm-white': '#F8FAFC',
        amber: {
          DEFAULT: '#F59E0B',
          400: '#FBBF24',
          500: '#F59E0B',
          600: '#D97706',
          900: '#451a03',
        },
        emerald: {
          DEFAULT: '#10B981',
          400: '#34D399',
          500: '#10B981',
          600: '#059669',
          900: '#022c22',
        },
        rose: {
          DEFAULT: '#F43F5E',
          400: '#FB7185',
          500: '#F43F5E',
          600: '#E11D48',
          900: '#4c0519',
        },
      },
      fontFamily: {
        sans: ['"Atkinson Hyperlegible"', 'system-ui', 'sans-serif'],
        display: ['"Atkinson Hyperlegible"', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        // Minimum 16px everywhere, body default 18px
        xs:   ['1rem',    { lineHeight: '1.5' }],   // 16px
        sm:   ['1rem',    { lineHeight: '1.5' }],   // 16px
        base: ['1.125rem', { lineHeight: '1.6' }],  // 18px
        lg:   ['1.25rem', { lineHeight: '1.6' }],   // 20px
        xl:   ['1.5rem',  { lineHeight: '1.4' }],   // 24px
        '2xl': ['1.875rem', { lineHeight: '1.3' }], // 30px
        '3xl': ['2.25rem',  { lineHeight: '1.2' }], // 36px
        '4xl': ['3rem',     { lineHeight: '1.1' }], // 48px
      },
      animation: {
        'tile-in':        'tile-in 200ms ease-out forwards',
        'pulse-urgent':   'pulse-urgent 1.5s ease-in-out infinite',
        'slide-up':       'slide-up 300ms ease-out forwards',
        'shimmer':        'shimmer 1.5s ease-in-out infinite',
        'slide-down':     'slide-down 300ms ease-out both',
        'fade-in':        'fade-in 200ms ease-out both',
        'msg-left':       'msg-left 200ms ease-out both',
        'msg-right':      'msg-right 200ms ease-out both',
        'idle-pulse':     'idle-pulse 3s ease-in-out infinite',
        'ring-expand':    'ring-expand 1.2s ease-out infinite',
        'slide-in-right': 'slide-in-right 200ms ease-out both',
      },
      keyframes: {
        'tile-in': {
          from: { opacity: '0', transform: 'scale(0.95)' },
          to:   { opacity: '1', transform: 'scale(1)' },
        },
        'pulse-urgent': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(244, 63, 94, 0.45)' },
          '50%':       { boxShadow: '0 0 0 10px rgba(244, 63, 94, 0)' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'shimmer': {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'slide-down': {
          from: { opacity: '0', transform: 'translateY(-10px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        'msg-left': {
          from: { opacity: '0', transform: 'translateX(-16px)' },
          to:   { opacity: '1', transform: 'translateX(0)' },
        },
        'msg-right': {
          from: { opacity: '0', transform: 'translateX(16px)' },
          to:   { opacity: '1', transform: 'translateX(0)' },
        },
        'idle-pulse': {
          '0%, 100%': { transform: 'scale(1)' },
          '50%':       { transform: 'scale(1.04)' },
        },
        'ring-expand': {
          '0%':   { transform: 'scale(1)',   opacity: '0.7' },
          '100%': { transform: 'scale(1.8)', opacity: '0' },
        },
        'slide-in-right': {
          from: { opacity: '0', transform: 'translateX(8px)' },
          to:   { opacity: '1', transform: 'translateX(0)' },
        },
      },
      minHeight: {
        touch: '3rem', // 48px minimum touch target
      },
    },
  },
  plugins: [],
};
