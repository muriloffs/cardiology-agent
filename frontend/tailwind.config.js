/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          light: '#667eea',
          dark: '#764ba2'
        },
        classe: {
          a: '#FF6B6B',
          b: '#FFA500',
          c: '#4CAF50'
        },
        featured: {
          red: '#FF6B6B',
          teal: '#20B2AA',
          orange: '#FF9800'
        }
      },
      borderRadius: {
        DEFAULT: '6px',
        lg: '8px'
      },
      boxShadow: {
        elevation: '0 2px 8px rgba(0, 0, 0, 0.1)',
        'elevation-lg': '0 4px 16px rgba(0, 0, 0, 0.15)'
      }
    }
  },
  plugins: []
}
