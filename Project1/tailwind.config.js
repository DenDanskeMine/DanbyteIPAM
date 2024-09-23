/** @type {import('tailwindcss').Config} */

const { data } = require('autoprefixer');

// tailwind.config.js
module.exports = {
  content: [
    './templates/**/*.html',
    './static/**/*.js',
    // Include any other paths to your templates and scripts
    './node_modules/flowbite/**/*.js'
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('flowbite/plugin')({
      charts: true,
      datatables: true,
    }),
  ],
};
