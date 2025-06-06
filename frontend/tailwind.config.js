/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html", // Main HTML file
    "./src/**/*.{js,ts,jsx,tsx}", // All JavaScript/TypeScript files in src
  ],
  theme: {
    extend: {
      // You can extend your Tailwind theme here with custom colors, fonts, spacing, etc.
      // Example:
      // colors: {
      //   'brand-primary': '#007bff',
      //   'brand-secondary': '#6c757d',
      // },
      // fontFamily: {
      //   sans: ['Inter', 'sans-serif'], // Add custom fonts
      // },
    },
  },
  plugins: [
    require('@tailwindcss/forms'), // Official plugin for better default form styling
    // require('@tailwindcss/typography'), // Official plugin for prose styling (Markdown)
  ],
}