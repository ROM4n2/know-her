/** 站点级常量（RSS、Schema、页面共用） */
export const SITE_TITLE = 'know-her · 每日性健康科普与愉悦分享';
export const SITE_DESCRIPTION =
  '每日精选两性健康、安全避孕、愉悦探索与亲密关系优质科普，权威来源，一键直达。';

export const CATEGORIES = {
  contraception: { label: '安全避孕', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  pleasure: { label: '愉悦探索', cls: 'bg-rose-50 text-rose-700 border-rose-200' },
  body: { label: '身体机制', cls: 'bg-blue-50 text-blue-700 border-blue-200' },
  intimacy: { label: '亲密沟通', cls: 'bg-purple-50 text-purple-700 border-purple-200' },
} as const;

export type CategoryKey = keyof typeof CATEGORIES;
