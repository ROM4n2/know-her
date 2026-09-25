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
    /** 循证证据等级：A (国际公立卫生机构/系统评价) | B (临床指南/专业学会共识) | C (权威机构专业科普) */
    evidence_tier: z.enum(['A', 'B', 'C']).default('B'),
    /** 复审人或复审团队（例如 "know-her 策展组"） */
    reviewed_by: z.string().optional(),
    /** 最后人工核验/外链探测日期 */
    last_verified_at: z.coerce.date().optional(),
    /** 是否为开放授权全文收录（默认为 false：策展导读与看点速览） */
    is_full_text: z.boolean().default(false),
  }),
});

const glossary = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/glossary' }),
  schema: z.object({
    /** 术语规范中文名称，如“左炔诺孕酮” */
    term: z.string(),
    /** 外文医学名称或专业缩写，如“Levonorgestrel (LNG)” */
    en_term: z.string().optional(),
    /** 别名或通俗称呼列表 */
    aliases: z.array(z.string()).default([]),
    /** 检索拼音/字母索引大写 (A-Z) */
    letter: z.string().length(1).toUpperCase(),
    /** 概念简明权威释义（80字以内，适合正文悬浮和卡片速览） */
    definition: z.string(),
    /** 所属分类 */
    category: z.enum(['contraception', 'pleasure', 'body', 'intimacy']),
    /** 权威依据或临床定义来源 */
    source: z.string(),
    /** 关联的本站深度科普文章 slug（可选） */
    related_article: z.string().optional(),
  }),
});

export const collections = { articles, glossary };
