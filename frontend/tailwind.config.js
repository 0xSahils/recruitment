/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: "#2563eb", 50: "#eff6ff", 100: "#dbeafe", 200: "#bfdbfe", 500: "#3b82f6", 600: "#2563eb", 700: "#1d4ed8", 800: "#1e40af" },
        success: { DEFAULT: "#16a34a", 50: "#f0fdf4" },
        warning: { DEFAULT: "#d97706", 50: "#fffbeb" },
        danger: { DEFAULT: "#dc2626", 50: "#fef2f2" },
      },
    },
  },
  plugins: [],
};
