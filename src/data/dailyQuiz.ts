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
  'body-dysmenorrhea': {
    articleId: 'body-dysmenorrhea',
    question: '对于原发性痛经，服用布洛芬等非甾体抗炎药的最佳时机是？',
    options: [
      '等到下腹绞痛极其剧烈、实在忍无可忍时再吃',
      '在月经刚见红或出现隐痛前提前服用，以阻止前列腺素大量合成',
      '只要痛经就必须连续大剂量吃一周',
    ],
    correctIndex: 1,
    explanation:
      '布洛芬的药理机制是抑制前列腺素合成酶。等到剧痛难忍时，前列腺素已大量与受体结合导致平滑肌强直痉挛。提前 6~12 小时预防性服用效果最好且用药量更少。',
  },
  'body-bacterial-vaginosis': {
    articleId: 'body-bacterial-vaginosis',
    question: '为了预防阴道炎，经常使用所谓的‘妇科专用洗液’深入阴道内部冲洗是否更健康？',
    options: [
      '是的，能彻底消灭内部有害细菌',
      '否，阴道内部具有自我菌群自洁能力，冲洗会杀死有益的乳酸杆菌，击穿保护屏障导致反复感染',
      '只有性生活后才需要每天冲洗深处',
    ],
    correctIndex: 1,
    explanation:
      '健康阴道内部 90% 以上由保护性的乳酸杆菌维持弱酸性自洁环境。阴道冲洗会彻底破坏微生态平衡，使厌氧菌乘虚而入诱发细菌性阴道病。日常只需温水清洁外阴表面即可。',
  },
  'body-vaginal-yeast-infection': {
    articleId: 'body-vaginal-yeast-infection',
    question: '出现剧烈外阴瘙痒与‘豆腐渣样’白带时，自行口服头孢或阿莫西林消炎管用吗？',
    options: [
      '管用，头孢是广谱消炎药能快速见效',
      '完全无效，且滥用抗生素杀死乳酸杆菌会使真菌感染进一步火上浇油',
      '只要多喝热水配合抗生素即可',
    ],
    correctIndex: 1,
    explanation:
      '霉菌性阴道炎是由念珠菌（真菌）引起，头孢、阿莫西林等抗生素只针对细菌，对真菌毫无杀伤力，反而会杀死共生的乳酸杆菌，失去竞争抑制使真菌爆发更严重。必须遵医嘱使用抗真菌药物（如克霉唑栓等）。',
  },
  'contraception-iud-guide': {
    articleId: 'contraception-iud-guide',
    question: '现代临床医学指南认为，从未生育过孩子的年轻未婚女性可以放置宫内节育器（IUD）吗？',
    options: [
      '绝对不可以，节育环只属于已生育女性',
      '可以，国际妇产指南明确确认未生育女性放置长效可逆避孕器（IUD）安全高效且可逆',
      '必须结扎后才能放置',
    ],
    correctIndex: 1,
    explanation:
      '世界卫生组织（WHO）与美国 ACOG 临床指南早已明确指出，宫内节育器（包括含铜 IUD 和曼月乐）是一线推荐的高效长效可逆避孕方式，未生育女性只要无解剖畸形与急性感染均可安全放置，取出后生育力立刻恢复。',
  },
  'intimacy-sti-prevention': {
    articleId: 'intimacy-sti-prevention',
    question: '性伴侣的外生殖器看起来完全干爽正常、没有任何红肿溃疡，是否意味着肯定没有性传播感染？',
    options: [
      '是的，健康肉眼一看便知',
      '不能，超过 70% 的衣原体、HPV 等性传播感染呈‘无症状隐匿状态’，没有症状不等于没有病原体',
      '只要洗个热水澡就能完全消除风险',
    ],
    correctIndex: 1,
    explanation:
      '性传播感染（STIs）极具隐蔽性，绝大多数感染者（尤其是衣原体、淋病、HPV 早期）没有任何自觉不适和肉眼可见皮损，但同样具有完全的传染性。全程正确使用安全套是阻断隐匿传播最有效的双重屏障。',
  },
  'pleasure-dyspareunia-pain': {
    articleId: 'pleasure-dyspareunia-pain',
    question: '同房时感到外阴剧烈刺痛或肌肉不受控制地紧紧闭合，正确的应对做法是？',
    options: [
      '“忍一忍就过去了”，咬牙用力强行进入',
      '立即停止插入尝试，排查器质性炎症，转向非插入式亲密与盆底物理脱敏训练',
      '大量饮用高度白酒麻痹神经再尝试',
    ],
    correctIndex: 1,
    explanation:
      '生殖器-骨盆疼痛与阴道痉挛是神经与肌肉的条件反射。强行插入不仅会造成黏膜撕裂损伤，更会强化大脑的恐惧反射使下一次痉挛更严重。必须停止强行尝试，寻求专业盆底物理康复与渐进式脱敏。',
  },
  'intimacy-healthy-boundaries': {
    articleId: 'intimacy-healthy-boundaries',
    question: '伴侣每天严格翻查手机聊天记录、强迫你删掉所有异性朋友并切断闺蜜社交，这属于？',
    options: [
      '“因为太爱我、在乎我”，是爱意深沉的表现',
      '典型的亲密关系控制与精神情感虐待（心理控制红线）',
      '情侣之间的正常情趣互动',
    ],
    correctIndex: 1,
    explanation:
      '世界卫生组织（WHO）将隔离社交圈、剥夺独立自主权与侵犯隐私明确界定为亲密伴侣暴力中的“控制与情感虐待”行为。健康的关系建立在相互尊重信任和平等边界之上，控制绝不是爱。',
  },
  'body-endometriosis': {
    articleId: 'body-endometriosis',
    question: '痛经一年比一年剧烈（进行性加重），并伴随深部同房刺痛和经期肛门坠胀，可能提示什么疾病？',
    options: [
      '单纯体质虚寒，喝红糖姜茶即可根治',
      '子宫内膜异位症或子宫腺肌病，需到妇科门诊做专业超声排查',
      '只要生完孩子自然就会完全痊愈',
    ],
    correctIndex: 1,
    explanation:
      '进行性加剧的痛经是子宫内膜异位症与腺肌病的典型标志性信号。异位内膜随月经反复出血导致盆腔严重粘连，延误诊治可能导致输卵管梗阻与不孕。应及时前往公立妇科做超声与妇科内诊。',
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
