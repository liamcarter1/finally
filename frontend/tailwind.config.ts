import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Dark terminal backgrounds (no pure black)
        bg: {
          DEFAULT: '#0d1117',
          alt: '#1a1a2e',
          panel: '#11151c',
          elevated: '#161b22',
        },
        border: {
          DEFAULT: '#2a2f3a',
          muted: '#21262d',
        },
        // Brand accents
        accent: '#ecad0a', // yellow
        brand: '#209dd7', // blue
        purple: '#753991', // purple submit
        up: '#16c784', // gain green
        down: '#ea3943', // loss red
        flat: '#8b949e',
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      keyframes: {
        'flash-up': {
          '0%': { backgroundColor: 'rgba(22, 199, 132, 0.45)' },
          '100%': { backgroundColor: 'transparent' },
        },
        'flash-down': {
          '0%': { backgroundColor: 'rgba(234, 57, 67, 0.45)' },
          '100%': { backgroundColor: 'transparent' },
        },
      },
      animation: {
        'flash-up': 'flash-up 500ms ease-out',
        'flash-down': 'flash-down 500ms ease-out',
      },
    },
  },
  plugins: [],
};

export default config;
