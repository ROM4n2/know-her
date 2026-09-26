/**
 * clinicQuestions.ts — 妇科门诊就诊沟通主诉配置与急腹症红旗预警知识库
 * 遵循临床 SOAP (Subjective, Objective, Assessment, Plan) 问诊逻辑规范。
 */

export interface ClinicContext {
  /** 细分主诉具体表现 (如 "两次月经间突破性出血") */
  symptomDetail?: string;
  /** 症状持续时间或发作频次 (如 "持续3天"、"近2个月反复出现") */
  onsetDuration?: string;
  /** 疼痛视觉模拟评分 NRS (0 - 10) */
  painLevel?: number | string;
  /** 末次月经日期 LMP (YYYY-MM-DD 或文本描述) */
  lmp?: string;
  /** 平常月经周期天数 (如 28) */
  cycleLength?: number | string;
  /** 近期避孕方式与激素药具使用史 */
  contraceptiveHistory?: string;
  /** 自测早孕试纸情况 */
  pregnancyTestStatus?: string;
  /** 勾选的急腹症红旗预警标签列表 */
  emergencyRedFlags?: string[];
  /** 患者补充备忘说明 */
  additionalNotes?: string;
}

export interface SymptomConfig {
  id: string;
  title: string;
  badge: string;
  description: string;
  subCategories: string[];
  chiefComplaintTemplate: (ctx: ClinicContext) => string;
  recommendedQuestions: string[];
  relatedArticle: string;
}

export interface RedFlagItem {
  id: string;
  label: string;
  description: string;
  emergencyAlert: string;
}

export const RED_FLAG_SYMPTOMS: RedFlagItem[] = [
  {
    id: 'acute_severe_pain',
    label: '剧烈撕裂样剧痛',
    description: '下腹单侧或全腹突发刀割样、撕裂样剧烈锐痛，呈持续性并可能向肩部或肛门放射',
    emergencyAlert:
      '⚠️ 急诊红旗预警：可能提示宫外孕破裂、黄体破裂、急性盆腔脓肿破裂或卵巢囊肿蒂扭转，属于危急妇科急腹症，不可等待常规预约门诊，请立即前往最近公立医院急诊！',
  },
  {
    id: 'syncope_shock',
    label: '突发面色苍白/冷汗或晕厥',
    description: '突发站立不稳、眼前发黑、冷汗淋漓、意识模糊或晕厥跌倒，常伴肢端湿冷与脉搏细速',
    emergencyAlert:
      '⚠️ 急诊红旗预警：高度提示腹腔内大出血或失血性休克！请立即平卧保持呼吸道通畅，并由同伴呼叫 120 急救！',
  },
  {
    id: 'heavy_hemorrhage',
    label: '阴道大量出血（1小时浸透2片卫生巾连续2小时）',
    description: '阴道出血呈喷涌或持续股状流出，伴有鸡蛋大小暗红血块，大流量卫生巾在 1 小时内完全吸饱透湿且连续持续 2 小时以上',
    emergencyAlert:
      '⚠️ 急诊红旗预警：属于急性活动性重度大出血，极易在短时间内导致失血性贫血与循环衰竭，必须即刻送往医院急诊科止血！',
  },
  {
    id: 'high_fever_chills',
    label: '伴随高热（体温≥38.5℃）与寒战',
    description: '体温骤升达到或超过 38.5℃，全身发冷颤抖，伴下腹明显拒按压痛或异常恶臭阴道分泌物',
    emergencyAlert:
      '⚠️ 急诊红旗预警：警惕急性盆腔腹膜炎、输卵管卵巢脓肿（TOA）或全身脓毒症感染，需要急诊化验血常规并启动静脉强效抗生素治疗！',
  },
];

export const CLINIC_SYMPTOM_CONFIGS: SymptomConfig[] = [
  {
    id: 'bleeding',
    title: '异常阴道出血',
    badge: 'AUB',
    description: '经期延长、两次月经间不规则出血、同房后接触性出血或绝经后阴道出血',
    subCategories: [
      '月经周期紊乱（经期显著延长 >7天 或经量远超平常）',
      '两次月经之间的突破性点滴出血（排卵期出血或不规则点滴）',
      '同房性生活后接触性出血（外阴或宫颈摩擦后带血）',
      '绝经 1 年以上突发再次出现阴道点滴或持续出血',
    ],
    chiefComplaintTemplate: (ctx: ClinicContext): string => {
      const parts: string[] = ['患者主诉：异常阴道出血'];
      if (ctx.symptomDetail) parts.push(`具体特征为【${ctx.symptomDetail}】`);
      if (ctx.onsetDuration) parts.push(`发作时长：${ctx.onsetDuration}`);
      if (ctx.lmp) parts.push(`末次月经时间(LMP)：${ctx.lmp}`);
      if (ctx.cycleLength) parts.push(`平常月经周期：约 ${ctx.cycleLength} 天`);
      if (ctx.contraceptiveHistory) parts.push(`近期避孕用药史：${ctx.contraceptiveHistory}`);
      if (ctx.pregnancyTestStatus) parts.push(`自测尿早孕：${ctx.pregnancyTestStatus}`);
      if (ctx.emergencyRedFlags && ctx.emergencyRedFlags.length > 0) {
        parts.push(`伴随急腹症高危体征：${ctx.emergencyRedFlags.join('、')}`);
      }
      if (ctx.additionalNotes) parts.push(`患者补充情况：${ctx.additionalNotes}`);
      return parts.join('；') + '。';
    },
    recommendedQuestions: [
      '是否建议尽快完善妇科经阴道超声（或经腹部超声），以评估子宫内膜厚度并排除内膜息肉、粘膜下肌瘤等器质性病变？',
      '是否需要抽血查血清人绒毛膜促性腺激素 (HCG)，以 100% 排除早期不典型异位妊娠（宫外孕）或不全流产？',
      '根据目前的出血严重度，是否需要开具氨甲环酸等对症止血药物，或使用孕激素/短效避孕药调理周期？',
      '结合出血时机，是否有必要安排宫颈癌筛查（TCT 细胞学与高危型 HPV 联合检查），排查宫颈局部病变？',
    ],
    relatedArticle: 'abnormal-uterine-bleeding',
  },
  {
    id: 'pelvic-pain',
    title: '盆腔与下腹疼痛',
    badge: 'Pelvic Pain',
    description: '进行性加重痛经、深部性交痛、排卵期突发单侧隐痛或非经期持续下腹坠胀',
    subCategories: [
      '进行性加重的重度痛经（口服常规止痛药难以控制）',
      '性生活深部剧痛或同房后骨盆持续痉挛性抽痛',
      '月经中期（预计排卵日前后）突发一侧剧烈隐痛',
      '非经期持续性下腹隐痛、腰骶酸痛与骨盆下坠感',
    ],
    chiefComplaintTemplate: (ctx: ClinicContext): string => {
      const parts: string[] = ['患者主诉：盆腔与下腹疼痛'];
      if (ctx.symptomDetail) parts.push(`疼痛特征：【${ctx.symptomDetail}】`);
      if (ctx.painLevel !== undefined && ctx.painLevel !== '') parts.push(`自评疼痛评分(NRS)：${ctx.painLevel}/10 分`);
      if (ctx.onsetDuration) parts.push(`持续时间：${ctx.onsetDuration}`);
      if (ctx.lmp) parts.push(`末次月经(LMP)：${ctx.lmp}`);
      if (ctx.cycleLength) parts.push(`月经周期：约 ${ctx.cycleLength} 天`);
      if (ctx.contraceptiveHistory) parts.push(`近期避孕用药：${ctx.contraceptiveHistory}`);
      if (ctx.pregnancyTestStatus) parts.push(`验孕情况：${ctx.pregnancyTestStatus}`);
      if (ctx.emergencyRedFlags && ctx.emergencyRedFlags.length > 0) {
        parts.push(`伴随急腹症高危体征：${ctx.emergencyRedFlags.join('、')}`);
      }
      if (ctx.additionalNotes) parts.push(`患者补充情况：${ctx.additionalNotes}`);
      return parts.join('；') + '。';
    },
    recommendedQuestions: [
      '是否需要安排妇科双合诊与高分辨率经阴道超声，以排查子宫腺肌症、卵巢巧克力囊肿（子宫内膜异位症）或盆腔炎症？',
      '如高度怀疑内异症或腺肌症引起的继发痛经，目前阶段最适合的长期控制方案（如曼月乐节育系统、地诺孕素或短效口服避孕药）是什么？',
      '目前疼痛发作期，哪种非甾体抗炎药（如布洛芬缓释或萘普生）起效最快？服用时对胃肠道的保护建议是什么？',
      '根据疼痛发作的突发性，是否需要急查血/尿 HCG 及血常规，排除宫外孕破裂或黄体破裂等外科急腹症？',
    ],
    relatedArticle: 'body-dysmenorrhea',
  },
  {
    id: 'discharge-itch',
    title: '异常白带与瘙痒',
    badge: 'Vaginitis',
    description: '豆腐渣样凝乳白带、稀薄灰白鱼腥臭分泌物、黄绿泡沫脓性白带伴外阴烧灼瘙痒',
    subCategories: [
      '豆腐渣样/凝乳块状白带伴剧烈外阴瘙痒与红肿 (假丝酵母菌/霉菌倾向)',
      '灰白色均匀稀薄白带伴明显腥臭味 (细菌性阴道病 BV 倾向)',
      '黄绿色泡沫状脓性白带伴排尿刺痛与外阴灼热 (滴虫感染倾向)',
      '外阴干涩、反复烧灼感或无保护性行为后突发分泌物增多',
    ],
    chiefComplaintTemplate: (ctx: ClinicContext): string => {
      const parts: string[] = ['患者主诉：异常白带分泌物与外阴瘙痒'];
      if (ctx.symptomDetail) parts.push(`主要体征：【${ctx.symptomDetail}】`);
      if (ctx.onsetDuration) parts.push(`发作时长：${ctx.onsetDuration}`);
      if (ctx.lmp) parts.push(`末次月经(LMP)：${ctx.lmp}`);
      if (ctx.contraceptiveHistory) parts.push(`避孕及清洁习惯：${ctx.contraceptiveHistory}`);
      if (ctx.pregnancyTestStatus) parts.push(`验孕状态：${ctx.pregnancyTestStatus}`);
      if (ctx.emergencyRedFlags && ctx.emergencyRedFlags.length > 0) {
        parts.push(`伴随急症警示：${ctx.emergencyRedFlags.join('、')}`);
      }
      if (ctx.additionalNotes) parts.push(`患者补充情况：${ctx.additionalNotes}`);
      return parts.join('；') + '。';
    },
    recommendedQuestions: [
      '是否可以直接取阴道侧壁与后穹窿分泌物，进行白带常规与微生态显微镜镜检，明确致病病原体？',
      '在检查采样前（近 48 小时内）是否有阴道冲洗、局部塞药或性接触，是否会对化验准确性造成干扰？',
      '开具的阴道外用栓剂或口服抗菌药物在月经期需要暂停吗？用药一个疗程结束后建议何时回院复查？',
      '伴侣是否需要同步配合口服药物治疗以阻断相互反复交叉感染？治疗康复前是否需要严格避免无保护性生活？',
    ],
    relatedArticle: 'body-bacterial-vaginosis',
  },
  {
    id: 'contraception-routine',
    title: '避孕与常规查体咨询',
    badge: 'Consultation',
    description: '长效可逆避孕方式选型、口服避孕药不良反应干预、宫颈防癌筛查与健康体检',
    subCategories: [
      '高效长效避孕手段咨询（曼月乐节育系统 / 含铜环 / 皮下埋植剂）',
      '短效口服避孕药 (COC) 适应证评估与不良反应疑虑咨询',
      '宫颈癌防癌筛查 (HPV + TCT) 联合检查与妇科常规查体',
      '孕前优生健康检查与排卵周期基础评估',
    ],
    chiefComplaintTemplate: (ctx: ClinicContext): string => {
      const parts: string[] = ['患者主诉：避孕选型评估与妇科常规健康咨询'];
      if (ctx.symptomDetail) parts.push(`咨询重点：【${ctx.symptomDetail}】`);
      if (ctx.lmp) parts.push(`末次月经(LMP)：${ctx.lmp}`);
      if (ctx.cycleLength) parts.push(`月经周期：约 ${ctx.cycleLength} 天`);
      if (ctx.contraceptiveHistory) parts.push(`目前避孕措施：${ctx.contraceptiveHistory}`);
      if (ctx.pregnancyTestStatus) parts.push(`验孕情况：${ctx.pregnancyTestStatus}`);
      if (ctx.additionalNotes) parts.push(`患者期望了解：${ctx.additionalNotes}`);
      return parts.join('；') + '。';
    },
    recommendedQuestions: [
      '结合我的既往经量、痛经程度、生育计划及身体状况（如血栓倾向或偏头痛），从医学角度最推荐哪一种避孕方式？',
      '如果选择放置宫内节育器或皮下埋植剂，最佳的门诊放置时间点在月经周期的哪一天？术前需要做哪些分泌物与超声排查？',
      '本次门诊是否可以同步完善宫颈液基细胞学 (TCT) 与高危型 HPV 病毒联合筛查？',
      '对于刚开始使用长效避孕药具或短效口服药可能出现的适应期点滴出血，有何医学应对与随访指引？',
    ],
    relatedArticle: 'contraception-condoms',
  },
];
