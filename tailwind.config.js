/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./main.py"],
  theme: {
    extend: {
      fontFamily: { sans: ["Inter", "sans-serif"] },
      animation: { "fade-in-up": "fadeInUp 0.8s ease-out forwards" },
      keyframes: {
        fadeInUp: {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
