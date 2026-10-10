/**
 * src/lib/ui/langConverter.ts — 纯静态客户端一键简繁转换核心模块
 *
 * 特性：
 * 1. 按需动态加载 opencc-js（动态 import('opencc-js')），简体中文读者首屏访问 0KB 额外体积开销；
 * 2. 转换器函数内存级单例缓存（cn2tw / tw2cn 实例仅初始化一次）；
 * 3. 递归安全遍历 DOM 文本节点（Node.TEXT_NODE === 3），严格跳过 SCRIPT, STYLE, CODE, PRE 及排除元素；
 * 4. 同步更新 document.title 与 html lang 标签属性；
 * 5. 采用 safeGet / safeSet try...catch 防护封装，杜绝 Safari 隐身模式/私密浏览 localStorage 异常抛崩；
 * 6. 本地持久化储存偏好 ('know-her-lang')，历史偏好为繁体时页面自动平滑转换。
 */

export type SupportedLang = 'cn' | 'tw';

export const STORAGE_KEY = 'know-her-lang';

/** 遍历 DOM 时跳过的标签名称 */
const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'CODE', 'PRE']);

/** 转换器函数签名 */
type ConverterFn = (text: string) => string;

/** 单例转换器缓存 */
let cn2twConverter: ConverterFn | null = null;
let tw2cnConverter: ConverterFn | null = null;

/** 当前激活语言状态 */
let currentLang: SupportedLang = 'cn';

/** 正在转换中的防抖/互斥锁 */
let isConverting = false;

/**
 * 安全读取 localStorage（防范 Safari 隐身模式 SecurityError）
 */
export function safeGet(key: string): string | null {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return null;
    return window.localStorage.getItem(key);
  } catch (err) {
    console.warn('[langConverter] safeGet 异常:', err);
    return null;
  }
}

/**
 * 安全写入 localStorage（防范 Safari 隐身模式 SecurityError 及 QuotaExceededError）
 */
export function safeSet(key: string, value: string): void {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return;
    window.localStorage.setItem(key, value);
  } catch (err) {
    console.warn('[langConverter] safeSet 异常:', err);
  }
}

/**
 * 动态加载并缓存 OpenCC 转换器实例
 */
async function getConverters(): Promise<{ cn2tw: ConverterFn; tw2cn: ConverterFn }> {
  if (cn2twConverter && tw2cnConverter) {
    return { cn2tw: cn2twConverter, tw2cn: tw2cnConverter };
  }

  // 动态按需加载，简体中文访客首屏 0KB 额外负载
  const OpenCC = await import('opencc-js');
  cn2twConverter = OpenCC.Converter({ from: 'cn', to: 'tw' });
  tw2cnConverter = OpenCC.Converter({ from: 'tw', to: 'cn' });

  return { cn2tw: cn2twConverter, tw2cn: tw2cnConverter };
}

/**
 * 递归遍历 DOM 文本节点并执行批量转换
 * 跳过 SCRIPT、STYLE、CODE、PRE 以及语言切换按钮本身
 */
function walkTextNodes(node: Node, converter: ConverterFn): void {
  // Node.TEXT_NODE === 3
  if (node.nodeType === Node.TEXT_NODE || node.nodeType === 3) {
    if (node.nodeValue && node.nodeValue.trim().length > 0) {
      node.nodeValue = converter(node.nodeValue);
    }
    return;
  }

  if (node.nodeType === 1 /* Node.ELEMENT_NODE */) {
    const el = node as HTMLElement;
    const tagName = el.tagName ? el.tagName.toUpperCase() : '';

    // 跳过代码、脚本、样式及显式免转元素
    if (SKIP_TAGS.has(tagName) || el.id === 'lang-switch-btn' || el.hasAttribute('data-no-convert')) {
      return;
    }

    // 常用属性文本同步转换
    const title = el.getAttribute('title');
    if (title && title.trim()) {
      el.setAttribute('title', converter(title));
    }
    const placeholder = el.getAttribute('placeholder');
    if (placeholder && placeholder.trim()) {
      el.setAttribute('placeholder', converter(placeholder));
    }
    const ariaLabel = el.getAttribute('aria-label');
    if (ariaLabel && ariaLabel.trim()) {
      el.setAttribute('aria-label', converter(ariaLabel));
    }
  }

  const children = node.childNodes;
  for (let i = 0; i < children.length; i++) {
    walkTextNodes(children[i], converter);
  }
}

/**
 * 更新语言切换按钮视觉排版与无障碍属性
 */
export function updateSwitcherButton(lang: SupportedLang): void {
  if (typeof document === 'undefined') return;
  const btn = document.getElementById('lang-switch-btn');
  if (!btn) return;

  const textNode = btn.querySelector('.lang-btn-text') || btn;
  if (lang === 'tw') {
    textNode.textContent = '[ 简体 ]';
    btn.setAttribute('title', '切换为简体中文');
    btn.setAttribute('aria-label', '切换为简体中文');
  } else {
    textNode.textContent = '[ 繁體 ]';
    btn.setAttribute('title', '切換為繁體中文');
    btn.setAttribute('aria-label', '切換為繁體中文');
  }
}

/**
 * 将整页内容转换为目标语言
 */
export async function convertPage(targetLang: SupportedLang): Promise<void> {
  if (typeof document === 'undefined' || isConverting || targetLang === currentLang) {
    return;
  }

  isConverting = true;
  try {
    const converters = await getConverters();
    const converter = targetLang === 'tw' ? converters.cn2tw : converters.tw2cn;

    // 1. 递归转换 document.body 文本节点
    if (document.body) {
      walkTextNodes(document.body, converter);
    }

    // 2. 转换 document.title
    if (document.title) {
      document.title = converter(document.title);
    }

    // 3. 更新 HTML lang 标记
    document.documentElement.lang = targetLang === 'tw' ? 'zh-TW' : 'zh-CN';

    // 4. 更新内部状态与本地存储持久化
    currentLang = targetLang;
    safeSet(STORAGE_KEY, targetLang);

    // 5. 更新按钮外观
    updateSwitcherButton(targetLang);
  } catch (err) {
    console.error('[langConverter] 页面语言转换执行失败:', err);
  } finally {
    isConverting = false;
  }
}

/**
 * 切换简繁语言状态
 */
export async function toggleLanguage(): Promise<void> {
  const nextLang: SupportedLang = currentLang === 'cn' ? 'tw' : 'cn';
  await convertPage(nextLang);
}

/**
 * 获取当前语言
 */
export function getCurrentLang(): SupportedLang {
  return currentLang;
}

/**
 * 客户端语言转换初始化器
 */
export function initLangConverter(): void {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;

  // 绑定切换按钮点击事件
  const btn = document.getElementById('lang-switch-btn');
  if (btn && !btn.dataset.langBound) {
    btn.dataset.langBound = 'true';
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      toggleLanguage();
    });
  }

  // 读取已保存的偏好设置
  const stored = safeGet(STORAGE_KEY);
  if (stored === 'tw') {
    // 立即更新按钮文案避免瞬态错位
    updateSwitcherButton('tw');

    const runConversion = () => {
      convertPage('tw');
    };

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', runConversion, { once: true });
    } else {
      runConversion();
    }
  }
}

// 注入全局 window 供调试及内联调用
declare global {
  interface Window {
    initLangConverter?: typeof initLangConverter;
    toggleLanguage?: typeof toggleLanguage;
    convertPage?: typeof convertPage;
    getCurrentLang?: typeof getCurrentLang;
  }
}

if (typeof window !== 'undefined') {
  window.initLangConverter = initLangConverter;
  window.toggleLanguage = toggleLanguage;
  window.convertPage = convertPage;
  window.getCurrentLang = getCurrentLang;
}
