// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import pagefind from 'astro-pagefind';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
  output: 'static',
  site: 'https://rom4n2.github.io',
  base: '/know-her',
  integrations: [pagefind(), mdx(), sitemap()],
  vite: {
    plugins: [tailwindcss()],
  },
});
