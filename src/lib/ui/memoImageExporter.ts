/**
 * memoImageExporter.ts — 纯前端零依赖纸墨质感便签长图导出器
 *
 * 解决移动端（微信内置浏览器等）无法调用 window.print()、长文本复制格式碎裂的问题：
 * 使用原生 Canvas 2D API 在本地浏览器内存中完成排版与绘制，导出 Academic Modern Editorial
 * 纸墨风格的整张便签长图。全程零网络请求、零第三方依赖、零个人数据外发。
 */

export interface MemoExportSection {
  /** 栏目名称（渲染为 [ 01 // 栏目名 ] 结构化标题） */
  heading: string;
  /** 栏目正文行（逐行渲染为项目符号列表） */
  lines: string[];
}

export interface MemoExportOptions {
  /** 便签主标题 */
  title: string;
  /** 顶部双线印章徽标文案 */
  badge?: string;
  /** 主标题下方的说明性副标题 */
  subtitle?: string;
  /** 结构化栏目标题与正文内容 */
  sections: MemoExportSection[];
  /** 底部免责声明 */
  disclaimer?: string;
  /** 导出文件名（无需扩展名） */
  fileName?: string;
}

/** 纸墨调色板（严格对齐站内 Design Tokens） */
const PAPER = '#FAF8F5';
const INK = '#15140F';
const INK_SOFT = '#2A2620';
const ACCENT = '#E11D48';
const MUTED = '#8B8676';
const HAIRLINE = 'rgba(21, 20, 15, 0.25)';

const FONT_STACK =
  '"Noto Sans SC", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", system-ui, -apple-system, sans-serif';
const MONO_STACK = '"SFMono-Regular", Menlo, Consolas, "Liberation Mono", monospace';

const LOGICAL_WIDTH = 900;
const PADDING_X = 64;
const CONTENT_WIDTH = LOGICAL_WIDTH - PADDING_X * 2;
const PADDING_TOP = 64;
const PADDING_BOTTOM = 72;
const DEFAULT_BADGE = '[ know-her · 离线健康决策便签 ]';
const DEFAULT_DISCLAIMER =
  '本便签由 know-her 在你的浏览器本地离线生成：全部排版与绘制均在内存中完成，绝不上传任何个人数据，也不替代执业医师面对面面诊意见。';

type FontWeight = 400 | 600 | 700 | 800;

interface RenderTextOp {
  lines: string[];
  x: number;
  y: number;
  font: string;
  color: string;
  lineHeight: number;
  align: CanvasTextAlign;
}

interface RenderRuleOp {
  x1: number;
  x2: number;
  y: number;
  thickness: number;
  color: string;
}

function buildFont(weight: FontWeight, size: number, mono = false): string {
  return `${weight} ${size}px ${mono ? MONO_STACK : FONT_STACK}`;
}

/** 按画布实测字宽做逐字折行，兼容中英文混排与显式换行符 */
function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = [];
  let current = '';

  for (const char of Array.from(text)) {
    if (char === '\n') {
      lines.push(current);
      current = '';
      continue;
    }

    const next = current + char;
    if (current !== '' && ctx.measureText(next).width > maxWidth) {
      lines.push(current);
      current = char;
    } else {
      current = next;
    }
  }

  lines.push(current);
  return lines;
}

/**
 * 将结构化便签内容导出为纸墨风格 PNG 长图。
 * 生成的图片通过触发浏览器下载保存；微信等会忽略 download 属性的内置浏览器会自动新开标签页，
 * 便于用户长按图片保存到相册。
 */
export async function exportMemoAsImage(options: MemoExportOptions): Promise<void> {
  if (typeof document === 'undefined' || typeof window === 'undefined') {
    throw new Error('便签长图导出仅支持在浏览器环境中运行。');
  }
  if (!options.sections || options.sections.length === 0) {
    throw new Error('便签内容为空，暂无可导出的长图。');
  }

  // 视网膜高清渲染：至少 2 倍像素密度
  const scale = Math.max(2, Math.min(window.devicePixelRatio || 1, 3));

  const measureCanvas = document.createElement('canvas');
  const ctx = measureCanvas.getContext('2d');
  if (!ctx) {
    throw new Error('当前浏览器不支持 Canvas 2D，无法导出便签长图，请改用复制或打印。');
  }

  const textOps: RenderTextOp[] = [];
  const ruleOps: RenderRuleOp[] = [];
  let cursorY = PADDING_TOP;

  const pushText = (
    content: string,
    font: string,
    color: string,
    lineHeight: number,
    opts: { indent?: number; align?: CanvasTextAlign } = {}
  ): void => {
    ctx.font = font;
    const indent = opts.indent ?? 0;
    const maxWidth = CONTENT_WIDTH - indent;
    const lines = wrapText(ctx, content, maxWidth);
    const isCentered = opts.align === 'center';

    textOps.push({
      lines,
      x: isCentered ? LOGICAL_WIDTH / 2 : PADDING_X + indent,
      y: cursorY,
      font,
      color,
      lineHeight,
      align: isCentered ? 'center' : 'left',
    });

    cursorY += lines.length * lineHeight;
  };

  // ---- 顶部双线印章 ----
  ruleOps.push({ x1: PADDING_X, x2: LOGICAL_WIDTH - PADDING_X, y: cursorY, thickness: 2, color: INK });
  ruleOps.push({ x1: PADDING_X, x2: LOGICAL_WIDTH - PADDING_X, y: cursorY + 6, thickness: 1, color: INK });
  cursorY += 6 + 30;

  pushText(options.badge ?? DEFAULT_BADGE, buildFont(700, 18, true), ACCENT, 26);
  cursorY += 6;

  // ---- 主标题与副标题 ----
  pushText(options.title, buildFont(800, 34), INK, 48);
  cursorY += 12;

  if (options.subtitle) {
    pushText(options.subtitle, buildFont(400, 17), MUTED, 27);
    cursorY += 16;
  }

  ruleOps.push({ x1: PADDING_X, x2: LOGICAL_WIDTH - PADDING_X, y: cursorY, thickness: 1, color: HAIRLINE });
  cursorY += 30;

  // ---- 结构化栏目 ----
  options.sections.forEach((section, index) => {
    const order = String(index + 1).padStart(2, '0');
    pushText(`[ ${order} // ${section.heading} ]`, buildFont(700, 18, true), INK, 28);
    cursorY += 10;

    section.lines.forEach((rawLine) => {
      const line = rawLine.trim();
      if (!line) return;
      const text = line.startsWith('•') ? line : `• ${line}`;
      pushText(text, buildFont(400, 17), INK_SOFT, 30, { indent: 8 });
      cursorY += 6;
    });

    cursorY += 18;
  });

  // ---- 底部免责声明与生成时间戳 ----
  cursorY += 4;
  ruleOps.push({ x1: PADDING_X, x2: LOGICAL_WIDTH - PADDING_X, y: cursorY, thickness: 1, color: HAIRLINE });
  cursorY += 28;

  pushText(options.disclaimer ?? DEFAULT_DISCLAIMER, buildFont(400, 14), MUTED, 22);
  cursorY += 12;

  const timestamp = new Date().toLocaleString('zh-CN', { hour12: false });
  pushText(`生成时间：${timestamp}`, buildFont(400, 13, true), MUTED, 20);

  const totalHeight = Math.ceil(cursorY + PADDING_BOTTOM);

  // ---- 正式绘制 ----
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(LOGICAL_WIDTH * scale);
  canvas.height = Math.round(totalHeight * scale);

  const renderCtx = canvas.getContext('2d');
  if (!renderCtx) {
    throw new Error('Canvas 2D 上下文初始化失败，无法导出便签长图。');
  }
  renderCtx.scale(scale, scale);

  renderCtx.fillStyle = PAPER;
  renderCtx.fillRect(0, 0, LOGICAL_WIDTH, totalHeight);

  renderCtx.strokeStyle = INK;
  renderCtx.lineWidth = 2;
  renderCtx.strokeRect(1, 1, LOGICAL_WIDTH - 2, totalHeight - 2);

  ruleOps.forEach((rule) => {
    renderCtx.beginPath();
    renderCtx.moveTo(rule.x1, rule.y);
    renderCtx.lineTo(rule.x2, rule.y);
    renderCtx.lineWidth = rule.thickness;
    renderCtx.strokeStyle = rule.color;
    renderCtx.stroke();
  });

  renderCtx.textBaseline = 'alphabetic';
  textOps.forEach((op) => {
    renderCtx.font = op.font;
    renderCtx.fillStyle = op.color;
    renderCtx.textAlign = op.align;
    op.lines.forEach((lineText, lineIndex) => {
      const baseline = op.y + lineIndex * op.lineHeight + Math.round(op.lineHeight * 0.72);
      renderCtx.fillText(lineText, op.x, baseline);
    });
  });

  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob(resolve, 'image/png');
  });

  if (!blob) {
    throw new Error('便签长图生成失败，请改用复制或打印功能。');
  }

  const safeName = (options.fileName ?? 'know-her-便签').replace(/[\\/:*?"<>|\s]+/g, '-');
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = `${safeName}.png`;
  link.rel = 'noopener';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // 微信 / QQ 等内置浏览器会忽略 download 属性，新开标签页以支持长按保存到相册
  if (/MicroMessenger|QQ\/|Weibo/i.test(window.navigator.userAgent || '')) {
    window.open(objectUrl, '_blank');
  }

  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 10000);
}
