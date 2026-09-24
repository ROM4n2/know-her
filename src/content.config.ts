import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'zod';

const articles = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/articles' }),
  schema: z.object({
    /** 词条标题 */
    title: z.string(),
    /** 发布/收录日期 */
    pubDate: z.coerce.date(),
    /** 核心看点 / 一句话推荐理由 */
    summary: z.string(),
    /** 主题分类：安全避孕、愉悦探索、身体机制、亲密沟通 */
    category: z.enum(['contraception', 'pleasure', 'body', 'intimacy']),
    /** 标签列表 */
    tags: z.array(z.string()).default([]),
    /** 权威来源原文链接（直达外链） */
    source_url: z.string().url(),
    /** 来源平台或媒体机构名称（如“果壳”、“谈性说爱”、“WHO”、“丁香医生”） */
    source_name: z.string(),
    /** 原文作者（可选） */
    author: z.string().optional(),
    /** 是否为开放授权全文收录（默认为 false：策展导读与看点速览） */
    is_full_text: z.boolean().default(false),
  }),
});

export const collections = { articles };
