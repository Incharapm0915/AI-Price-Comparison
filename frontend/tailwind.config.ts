import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          500: "#3f6fee",
          600: "#2f57d6",
          700: "#2544ab",
        },
      },
    },
  },
  plugins: [],
};

export default config;
