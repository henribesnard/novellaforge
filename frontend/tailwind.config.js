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
        ink: '#1b1a17',
        canvas: '#f7f2ea',
        shell: '#fffbf4',
        stone: {
          50: '#fbf8f2',
          100: '#f2ece4',
          200: '#e3d8c9',
          300: '#d2c4b2',
          400: '#bca993',
          500: '#a38d74',
          600: '#86715c',
          700: '#6a5746',
          800: '#4f3f32',
          900: '#362a22',
        },
        brand: {
          50: '#edf7f6',
          100: '#d5ebe8',
          200: '#acd7d1',
          300: '#7fbcb3',
          400: '#53a094',
          500: '#2f8578',
          600: '#23695f',
          700: '#1c5149',
          800: '#143b33',
          900: '#0d2621',
        },
        accent: {
          50: '#fff5ea',
          100: '#fee6ce',
          200: '#fccb9a',
          300: '#f7a86a',
          400: '#ef823f',
          500: '#d76323',
          600: '#b24e1b',
          700: '#8d3c16',
          800: '#6b2d12',
          900: '#4a1f0c',
        },
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'sans-serif'],
        serif: ['var(--font-serif)', 'serif'],
        mono: ['Fira Code', 'monospace'],
      },
      boxShadow: {
        soft: '0 18px 45px -30px rgba(27, 26, 23, 0.5)',
        lift: '0 30px 60px -45px rgba(27, 26, 23, 0.6)',
      },
    },
  },
  plugins: [],
}
