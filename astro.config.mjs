// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import pagefind from 'astro-pagefind';
import mdx from '@astrojs/mdx';

// https://astro.build/config
export default defineConfig({
  output: 'static',
  site: 'https://know-her.pages.dev',
  integrations: [pagefind(), mdx()],
  vite: {
    plugins: [tailwindcss()],
  },
});
