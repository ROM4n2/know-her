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

  return rss({
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    site: context.site ?? 'https://know-her.pages.dev',
    items: valid.map((article: CollectionEntry<'articles'>) => ({
      title: article.data.title,
      link: `/articles/${article.id}/`,
      pubDate: article.data.pubDate,
      description: article.data.summary,
      customData: `<dc:source><![CDATA[${article.data.source_url}]]></dc:source>`,
    })),
    customData: '<language>zh-CN</language>',
  });
}
