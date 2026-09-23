import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'zod';

const articles = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/articles' }),
  schema: z
    .object({
      /** Canonical URL of the original source article */
      source_url: z.string().url(),
      /** Date the source was snapshotted, YYYY-MM-DD */
      source_snapshot_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
      /** Optional hash of the snapshot for change detection */
      source_snapshot_hash: z.string().optional(),
      /** Lifecycle status of the review */
      review_status: z.enum(['draft', 'in_review', 'published', 'stale']),
      /** Date of last review, YYYY-MM-DD */
      review_date: z
        .string()
        .regex(/^\d{4}-\d{2}-\d{2}$/)
        .optional(),
      /** How many months between scheduled reviews */
      review_interval_months: z
        .number()
        .int()
        .min(6)
        .max(24)
        .default(12),
      /** Checklist flags */
      reviewed_source: z.boolean(),
      reviewed_copyright: z.boolean(),
      reviewed_medical: z.boolean(),
      reviewed_sensitivity: z.boolean(),
      /** List of red-flag notes raised during review */
      red_flags: z.array(z.string()),
      /** Must always be false — no individual medical advice */
      has_individual_advice: z.literal(false),
      /** Content language */
      lang: z.enum(['zh-CN', 'en']).default('zh-CN'),
      /** If this article is a translation, the slug of the source article */
      translation_of: z.string().optional(),
    })
    .strict()
    .superRefine((data, ctx) => {
      // Invariant 1: reviewed_medical===true requires review_date
      if (data.reviewed_medical && !data.review_date) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['review_date'],
          message:
            'review_date is required when reviewed_medical is true',
        });
      }

      // Invariant 2: translation_of present → lang must not be zh-CN
      if (data.translation_of && data.lang === 'zh-CN') {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['lang'],
          message:
            'lang must not be zh-CN when translation_of is set (translated content should carry the target language)',
        });
      }

      // Invariant 3: published requires reviewed_source, reviewed_copyright, reviewed_sensitivity all true
      if (data.review_status === 'published') {
        if (!data.reviewed_source) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ['reviewed_source'],
            message:
              'reviewed_source must be true when review_status is published',
          });
        }
        if (!data.reviewed_copyright) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ['reviewed_copyright'],
            message:
              'reviewed_copyright must be true when review_status is published',
          });
        }
        if (!data.reviewed_sensitivity) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ['reviewed_sensitivity'],
            message:
              'reviewed_sensitivity must be true when review_status is published',
          });
        }
      }
    }),
});

export const collections = { articles };
