/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.{html,js}"],
  safelist: [
    'kiwix-home-btn',
    'kiwix-home-btn-active',
    'kiwix-download-btn',
    'kiwix-download-btn-active',
    'kiwix-order-dir-btn',
    'kiwix-sort-btn',
    'kiwix-sort-btn-active',
    {pattern: /kiwix-.+/},
  ],
  theme: {
    extend: {
      screens: {
        'xxs': {'min': '376px', 'max': '439px'},
        'xs': {'min': '440px', 'max': '639px'},
      },
      colors: {
        kwwhite: '#eef2f6',
        kwbgwhitehover: '#f7f8fa',
        kwbggrey: '#eef2f6',
        kwfiltersgrey: {
          DEFAULT: '#dbe1e9',
          400: '#dae0e8',
          500: '#d6dce4',
          600: '#d3d9e1',
          700: '#cfd5dd',
          800: '#cbd1d9',
          900: '#ccd3da',
        },
        kwordergrey: {
          100: '#a6b2bd',
          500: '#6f8291',
          600: '#92a6b9',
        },
        kwtagbggrey: '#a8aba2',
        kwreaderbggrey: '#777777',
        kwreaderhover: '#4c4c4c',
        kwbordergrey: '#c3c5c6',
        kwtextblack: '#231f20',
        kwtextgrey: '#585b5d',
        kwtextgreyn: '#707272',
        'kworange': {
           DEFAULT: '#f39325',
           100: '#f79433',
           200: '#f39033',
           300: '#f08e33',
           400: '#ed8b33',
           500: '#cc6600',
           600: '#dc7d2c',
           700: '#da7c2c',
           800: '#d7711d',
           900: '#d77336',
        }
      },
      gridTemplateColumns: {
        '1m': 'repeat(1, max-content)',
        '1f': 'minmax(100%, 100%)',
        '2m': 'repeat(2, max-content)',
        '3m': 'repeat(3, max-content)',
        '4m': 'repeat(4, max-content)',
        '5m': 'repeat(5, max-content)',
      }
    }
  },
}
