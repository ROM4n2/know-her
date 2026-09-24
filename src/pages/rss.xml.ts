import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { getCollection, type CollectionEntry } from 'astro:content';
import { SITE_DESCRIPTION, SITE_TITLE } from '../consts';

export async function GET(context: APIContext) {
  const articles = await getCollection('articles');
  const valid = articles
    .filter((entry: CollectionEntry<'articles'>) => !entry.id.startsWith('_'))
    .sort(
      (a: CollectionEntry<'articles'>, b: CollectionEntry<'articles'>) =>
        b.data.pubDate.getTime() - a.data.pubDate.getTime(),
    );

  const base = import.meta.env.BASE_URL.endsWith('/')
    ? import.meta.env.BASE_URL
    : `${import.meta.env.BASE_URL}/`;

  return rss({
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    site: context.site ?? 'https://rom4n2.github.io',
    items: valid.map((article: CollectionEntry<'articles'>) => ({
      title: article.data.title,
      link: `${base}articles/${article.id}/`,
      pubDate: article.data.pubDate,
      description: article.data.summary,
      customData: `<dc:source><![CDATA[${article.data.source_url}]]></dc:source>`,
    })),
    customData: '<language>zh-CN</language>',
  });
}
