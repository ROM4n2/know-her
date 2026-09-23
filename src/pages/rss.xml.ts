import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { getCollection, type CollectionEntry } from 'astro:content';
import { SITE_DESCRIPTION, SITE_TITLE } from '../consts';

export async function GET(context: APIContext) {
  const articles = await getCollection('articles');
  const published = articles.filter(
    (entry: CollectionEntry<'articles'>) =>
      entry.data.review_status === 'published',
  );

  return rss({
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    site: context.site ?? 'https://know-her.pages.dev',
    items: published.map((article: CollectionEntry<'articles'>) => ({
      // 标题取正文首个 H1（frontmatter 无 title 字段），此处回退到 slug
      title: article.id,
      link: `/articles/${article.id}/`,
      pubDate: article.data.review_date
        ? new Date(`${article.data.review_date}T00:00:00Z`)
        : undefined,
      description: `来源：${article.data.source_url}（快照 ${article.data.source_snapshot_date}）`,
      customData: `<dc:source><![CDATA[${article.data.source_url}]]></dc:source>`,
    })),
    customData: '<language>zh-CN</language>',
  });
}
