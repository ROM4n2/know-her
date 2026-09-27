/**
 * rotation.ts — 轮换数学的唯一真值源 (ADR-0002 / M1)
 *
 * 组合指纹唯一性：两个真实独立轮换维度 (articles, glossary) 的最小公倍数 lcm
 * 即「首页当日组合不重复」的天数（速测题与今日文章 1:1 绑定，非独立维度，见 Spec §3.1.3）。
 * 断言 lcm(articles, glossary) >= MIN_UNIQUE_CYCLE_DAYS，由 scripts/test_daily_loop.py 的 G3 组强制守护。
 *
 * 约束：零第三方依赖（无 import）；getDayOfYear 与 dailyQuiz.ts 原实现逐位等价
 * （含 getTimezoneOffset() 的 UTC+8 口径），保证打卡跨日判断不错位。
 */

/** 首页当日组合不重复天数下限（一季下限；周期随内容池增长），由 G3 门禁强制。 */
export const MIN_UNIQUE_CYCLE_DAYS = 90;

/**
 * 计算基于北京时间（UTC+8）的当年度积日（Day of Year）。
 * 与旧 dailyQuiz.ts 实现逐位等价：先按本地时区偏移还原 UTC，再叠加 UTC+8。
 */
export function getDayOfYear(date: Date = new Date()): number {
  const utc = date.getTime() + date.getTimezoneOffset() * 60000;
  const bjTime = new Date(utc + 3600000 * 8);
  const start = new Date(bjTime.getFullYear(), 0, 0);
  const diff = bjTime.getTime() - start.getTime();
  const oneDay = 1000 * 60 * 60 * 24;
  return Math.floor(diff / oneDay);
}

/**
 * 根据池规模与日期，确定性返回今日轮换索引。
 * 空池守卫：totalCount <= 0 时短路返回 0，避免取模除零。
 */
export function getTodayIndex(totalCount: number, date?: Date): number {
  if (totalCount <= 0) return 0;
  const day = getDayOfYear(date);
  return (day - 1) % totalCount;
}

/**
 * 根据总周数与日期，确定性返回本周轮换索引。
 */
export function getWeekIndex(totalWeeks: number, date?: Date): number {
  if (totalWeeks <= 0) return 0;
  const day = getDayOfYear(date);
  return Math.floor((day - 1) / 7) % totalWeeks;
}

/** 欧几里得算法求两数最大公约数（零依赖）。 */
function gcd(a: number, b: number): number {
  let x = Math.abs(a);
  let y = Math.abs(b);
  while (y !== 0) {
    const t = y;
    y = x % y;
    x = t;
  }
  return x;
}

/**
 * 计算一组正整数的最小公倍数（手写 a*b/gcd，零依赖）。
 * 空数组或含 0/负数时返回 0（该组合不构成有效轮换周期）。
 */
export function lcm(values: number[]): number {
  if (values.length === 0) return 0;
  let result = 1;
  for (const value of values) {
    if (value <= 0) return 0;
    result = (result / gcd(result, value)) * value;
  }
  return result;
}

/**
 * 计算给定日期在三池上的组合指纹，形如 "3-12-7"。
 * 空池守卫：不抛异常，直接返回空字符串。
 */
export function computeFingerprint(date: Date, poolSizes: number[]): string {
  if (poolSizes.length === 0) return '';
  return poolSizes.map((size) => getTodayIndex(size, date)).join('-');
}

/**
 * 计算基于北京时间（UTC+8）的整日序号（自 Unix 纪元起的天数）。
 * 与 getDayOfYear 同源：两者都要求「结果与构建机时区无关」。
 *
 * 实现契约：**不得**引入 getTimezoneOffset() 项 —— 传入的 date 已是绝对时间戳
 * （getTime() 返回自 Unix 纪元的毫秒数，不含本地时区语义），直接加 8 小时再取整
 * 即为北京日序号；若引入 date.getTimezoneOffset() * 60000 本地偏移项，该项在
 * Math.floor 前不会抵消，会使结果随构建机时区漂移（同一时刻在 TZ=UTC 机与 UTC+8 机
 * 可相差 1 天），进而令「今日上新」7 天窗口整体错位、第 7/8 天边界判定失准。
 * 该 TZ 无关约束由 scripts/test_daily_loop.py 的 G6 契约强制守护。
 * 用于 pickFreshArticle 的「日差」比较，禁止直接用毫秒相减（跨时区会漏判）。
 */
export function beijingDayNumber(date: Date): number {
  return Math.floor((date.getTime() + 8 * 3600000) / 86400000);
}

/**
 * 挑选「今日上新」文章：发布日距 today 的北京日差落在 [0, windowDays) 内的最新一篇。
 *
 * 纯函数，零依赖。仅用于 DailyCard 的附加「今日上新」条带，
 * **不参与轮换索引计算**（getTodayIndex(articles.length) 零扰动）。
 * - 空数组守卫：直接返回 null。
 * - 未来日期守卫：daysDiff < 0 时跳过（不命中）。
 * - 窗口上界开区间：daysDiff < windowDays（windowDays=7 ⇒ 第 1~7 天命中，第 8 天不命中）。
 * - 多篇命中：返回 getDate 最新的一篇。
 */
export function pickFreshArticle<T>(
  items: T[],
  getDate: (item: T) => Date,
  today: Date = new Date(),
  windowDays = 7,
): T | null {
  if (items.length === 0) return null;

  const todayNo = beijingDayNumber(today);
  let fresh: T | null = null;
  let freshNo = Number.NEGATIVE_INFINITY;

  for (const item of items) {
    const itemNo = beijingDayNumber(getDate(item));
    const daysDiff = todayNo - itemNo;
    if (daysDiff < 0) continue;
    if (daysDiff < windowDays && itemNo > freshNo) {
      fresh = item;
      freshNo = itemNo;
    }
  }
  return fresh;
}
