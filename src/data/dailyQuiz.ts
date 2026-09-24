/**
 * dailyQuiz.ts — 每日科普精选与 30 秒知情速测数据契约 (ADR-0002)
 */

export interface QuizItem {
  /** 对应的词条 ID (slug) */
  articleId: string;
  /** 速测题干 */
  question: string;
  /** 选项列表 (通常 2~3 个) */
  options: string[];
  /** 正确选项下标 (0-indexed) */
  correctIndex: number;
  /** 简明权威原理解释 (答题后揭晓) */
  explanation: string;
}

export const DAILY_QUIZZES: Record<string, QuizItem> = {
  'contraception-condom-myths': {
    articleId: 'contraception-condom-myths',
    question: '为了加倍安全，在亲密过程中同时佩戴两层避孕套效果会更好吗？',
    options: [
      '会，双层物理防护不易破漏',
      '不会，两层避孕套相互摩擦极易磨损破裂导致意外怀孕',
      '只有在排卵期才需要戴两层',
    ],
    correctIndex: 1,
    explanation:
      '戴两只避孕套会在活塞运动中产生剧烈的相对摩擦，破坏乳胶弹性并迅速磨破，导致避孕失败率大幅上升。正确佩戴单只合格避孕套足矣。',
  },
  'contraception-emergency-pill': {
    articleId: 'contraception-emergency-pill',
    question: '无保护亲密接触后，服用单剂左炔诺孕酮（如毓婷等）的最佳抢救时间窗口是？',
    options: [
      '24 小时以内（最迟不超过 72 小时）',
      '无所谓，只要在一周以内即可',
      '只要在下一次预计月经来潮前吃即可',
    ],
    correctIndex: 0,
    explanation:
      '紧急避孕药主要通过阻止或延迟排卵起效，越早服用有效率越高。前 24 小时内服用效果最佳，超过 72 小时后阻止受精的成功率将大幅衰减。',
  },
  'contraception-oral-pills': {
    articleId: 'contraception-oral-pills',
    question: '如果服用复方短效口服避孕药（COC）不小心漏服了 1 天，次日应该如何处理？',
    options: [
      '这个月直接放弃停药，等下次月经',
      '次日发现后立即补服 1 片（即使当天吃 2 片），随后按原时间继续',
      '立即去药店买两粒紧急避孕药吃',
    ],
    correctIndex: 1,
    explanation:
      '复方短效避孕药在漏服 1 天时体内激素仍能维持基本抑制。发现后立即补服 1 片，随后继续正常规律服药，通常无需额外加用防护。',
  },
  'female-pleasure-clitoris': {
    articleId: 'female-pleasure-clitoris',
    question: '关于女性阴蒂的真实生理结构，以下哪项描述符合现代解剖学事实？',
    options: [
      '阴蒂只有表面露出的几毫米微小凸起',
      '绝大部分阴蒂（两支阴蒂脚与前庭球）埋在体内，长度可达 9~11 厘米',
      '女性性高潮主要完全依赖阴道内部深处神经',
    ],
    correctIndex: 1,
    explanation:
      '表面可见的阴蒂头仅占总体积的不到 10%。阴蒂是一座庞大的海绵体器官，日常绝大部分所谓的阴道高潮，本质都是间接刺激到了深部阴蒂脚。',
  },
  'pleasure-lubricant-guide': {
    articleId: 'pleasure-lubricant-guide',
    question: '使用天然乳胶避孕套时，为什么严禁搭配凡士林、婴儿油或椰子油等油基润滑剂？',
    options: [
      '单纯因为油基太滑容易导致脱落',
      '矿物油与植物油脂可在 60 秒内迅速溶解腐蚀乳胶，导致避孕套微孔破损',
      '油基润滑剂味道不好闻',
    ],
    correctIndex: 1,
    explanation:
      '天然乳胶是有机高分子聚合物，极易被油脂溶解破坏。搭配天然乳胶避孕套只能使用水基或硅基润滑剂。',
  },
  'pleasure-female-masturbation': {
    articleId: 'pleasure-female-masturbation',
    question: '关于女性自慰（自我愉悦探索），现代临床性医学的权威共识是什么？',
    options: [
      '自慰会导致肾虚、面色暗沉与内分泌失调',
      '自慰是人类一生中普遍正常的健康生理行为，不影响生育能力与身体机能',
      '经常自慰会造成不可逆的阴道松弛',
    ],
    correctIndex: 1,
    explanation:
      '现代医学早就证实，适度自慰是正常的生理行为，不影响生育机能与生理健康。自我探索有助于了解身体触感，高潮释放的催产素还可缓解痛经与压力。',
  },
  'normal-menstrual-cycle': {
    articleId: 'normal-menstrual-cycle',
    question: '根据国际妇产科联合会（FIGO）标准，正常月经周期的天数范围是多少？',
    options: [
      '必须严格整整 28 天，差一天都不行',
      '24 至 38 天之间均属健康规律的生理范畴',
      '只要在 10 天至 50 天之间都算正常',
    ],
    correctIndex: 1,
    explanation:
      '28 天只是大众统计均值而非铁律。FIGO 临床规范定义：周期在 24~38 天、出血持续 3~8 天、相邻周期间波动 ≤7~9 天均属健康规律的生理周期。',
  },
  'abnormal-uterine-bleeding': {
    articleId: 'abnormal-uterine-bleeding',
    question: '在月经刚结束几天后，内裤上出现少许咖啡色分泌物，通常是什么原因？',
    options: [
      '一定是发生了严重的妇科恶性病变',
      '经血排出缓慢，在阴道酸性环境中氧化变暗的正常陈旧血残留',
      '着凉引起的下腹血液循环坏死',
    ],
    correctIndex: 1,
    explanation:
      '血液中的血红蛋白流速缓慢时，与空气和阴道弱酸性环境接触氧化，就会呈现咖啡色或暗褐色。量少且 1~2 天自行干净通常属于陈旧血残留。',
  },
  'body-hpv-vaccine-screening': {
    articleId: 'body-hpv-vaccine-screening',
    question: '接种完九价 HPV 疫苗后，女性是否还需要定期做宫颈癌筛查（TCT+HPV）？',
    options: [
      '不需要，打完疫苗已经终身免疫所有宫颈癌病毒',
      '仍需规律定期筛查，因为现有疫苗未覆盖 100% 的致癌高危型别',
      '只有接种二价疫苗的人才需要额外筛查',
    ],
    correctIndex: 1,
    explanation:
      '现有疫苗无法覆盖所有导致宫颈癌的高危亚型。接种疫苗是一级预防，定期进行 TCT 与 HPV 筛查是二级预防，二者结合才能构筑完整的防护网。',
  },
  'intimacy-fries-consent': {
    articleId: 'intimacy-fries-consent',
    question: '亲密关系知情同意 FRIES 法则中，字母“R（Reversible，可撤回的）”代表什么？',
    options: [
      '一旦同意就不能再反悔',
      '同意是随时可撤回的，任何阶段只要一方喊停必须立即得到无条件尊重',
      '同意必须录音或留下书面协议',
    ],
    correctIndex: 1,
    explanation:
      '可撤回性（Reversible）是知情同意的基石。同意仅针对当下的具体动作，哪怕进行到任何一步，只要有任何一方感到犹豫或不适，都可以立即喊停。',
  },
};

/**
 * 计算基于北京时间（UTC+8）的当年度积日（Day of Year）
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
 * 根据文章数量与日期，确定性返回今日主推索引
 */
export function getTodayIndex(totalCount: number, date?: Date): number {
  if (totalCount <= 0) return 0;
  const day = getDayOfYear(date);
  return day % totalCount;
}
