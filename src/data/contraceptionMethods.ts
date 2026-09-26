/**
 * contraceptionMethods.ts — 全品类现代避孕方式结构化数据集
 * 基于 WHO MEC（避孕方法选用的医学资格标准）与 CDC/ACOG 避孕有效率金标准构建。
 */

export interface ContraceptionMethod {
  id: string;
  name: string;
  en_name: string;
  category: 'barrier' | 'hormonal_short' | 'hormonal_long' | 'non_hormonal_long' | 'emergency' | 'permanent';
  /** 珍珠指数典型使用年失败率 (例如 "13%") */
  failure_rate_typical: string;
  /** 珍珠指数完美使用年失败率 (例如 "2%") */
  failure_rate_perfect: string;
  /** 有效持续时间 / 频次描述 */
  duration: string;
  /** 是否能阻断 HIV / STIs */
  protects_sti: boolean;
  /** 激素类型 */
  hormone_type: 'none' | 'combined' | 'progestin_only';
  /** 生育力恢复速度 */
  fertility_return: '立即' | '数天内' | '取出后迅速' | '永久不可逆';
  /** 对月经量的预期改变 */
  menses_effect: string;
  /** 核心优势点 */
  pros: string[];
  /** 常见不良反应与适应期 */
  cons: string[];
  /** 典型绝对/相对禁忌症（WHO MEC 标准） */
  contraindications: string[];
  /** 关联本站深度循证科普 slug（用于外键连通性门禁） */
  related_article: string;
}

export const CONTRACEPTION_METHODS: ContraceptionMethod[] = [
  {
    id: 'male-condom',
    name: '男用避孕套',
    en_name: 'Male Condom',
    category: 'barrier',
    failure_rate_typical: '13%',
    failure_rate_perfect: '2%',
    duration: '单次同房',
    protects_sti: true,
    hormone_type: 'none',
    fertility_return: '立即',
    menses_effect: '对月经周期与经量无影响',
    pros: [
      '唯一可有效阻断 HIV 与常见性传播疾病 (STI) 的避孕手段',
      '无内源激素干扰，不影响自然排卵与内分泌生理周期',
      '随用随停，购买极度便捷，无需处方或专业医护操作',
    ],
    cons: [
      '高度依赖全程规范佩戴，易受破裂、滑脱、油性润滑剂侵蚀等失误影响',
      '典型使用年失败率高达 13%，远高于长效可逆手段',
      '少数人群对天然乳胶材质可能发生过敏反应',
    ],
    contraindications: [
      '对乳胶严重过敏者（应选用聚氨酯或聚异戊二烯材质避孕套）',
    ],
    related_article: 'contraception-condoms',
  },
  {
    id: 'combined-oral-pill',
    name: '复方短效口服避孕药 (COC)',
    en_name: 'Combined Oral Contraceptives (COC)',
    category: 'hormonal_short',
    failure_rate_typical: '7%',
    failure_rate_perfect: '0.3%',
    duration: '每日固定时间服药（21天服/7天停或28天连续）',
    protects_sti: false,
    hormone_type: 'combined',
    fertility_return: '数天内',
    menses_effect: '规律可预测的月经撤退性出血，显著减轻原发性痛经与月经过多',
    pros: [
      '规范准时服药时避孕有效率高达 99.7%，且高度可逆',
      '调节紊乱周期，显著改善中重度痤疮、经期水肿与痛经',
      '停药后下个月经周期即可自然恢复正常排卵与受孕能力',
    ],
    cons: [
      '高度依赖服药自律性，漏服（尤其是周期第一周）会造成保护力断崖',
      '完全无法防御任何性传播感染 (STI)',
      '服药初期（前1-3个月）可能出现点滴出血、乳房触痛或轻微恶心',
    ],
    contraindications: [
      '年龄≥35岁且长期吸烟者（心血管与血栓风险极高，WHO MEC 4级）',
      '伴先兆的偏头痛病史（脑卒中风险，WHO MEC 4级）',
      '深静脉血栓形成 (DVT) 或肺栓塞 (PE) 个人史',
      '控制不佳的中重度高血压（收缩压≥160 或舒张压≥100 mmHg）',
    ],
    related_article: 'contraception-oral-pills',
  },
  {
    id: 'lng-ius',
    name: '左炔诺孕酮宫内节育系统 (曼月乐/LNG-IUS)',
    en_name: 'Levonorgestrel Intrauterine System (Mirena / LNG-IUS)',
    category: 'hormonal_long',
    failure_rate_typical: '0.1% - 0.2%',
    failure_rate_perfect: '0.1% - 0.2%',
    duration: '5 - 8 年',
    protects_sti: false,
    hormone_type: 'progestin_only',
    fertility_return: '取出后迅速',
    menses_effect: '经量锐减 70%~90%，经期显著缩短，约20%~50%的使用者出现生理性闭经（内膜处于休眠保护态，完全无害）',
    pros: [
      '长效可逆避孕（LARC）最高阶金标准，典型使用失败率与完美使用一致（<0.2%）',
      '单次放置提供 5~8 年免维护长效守护，完全消除日常遗忘焦虑',
      '同时是临床治疗特发性月经过多 (AUB-HMB) 与子宫腺肌症痛经的一线治疗方案',
    ],
    cons: [
      '放置后前 3~6 个月常有少量点滴突破性出血或周期不规则',
      '需要由具备资质的妇产科医师在门诊进行宫腔放置与取出操作',
      '极少数个体（约3%~5%）在初期可能发生环体移位或脱落',
    ],
    contraindications: [
      '原因不明的异常阴道出血（需先排查子宫内膜器质性病变）',
      '现患急性盆腔炎性疾病 (PID) 或未治愈的化脓性宫颈炎',
      '严重扭曲子宫宫腔形态的粘膜下肌瘤或先天解剖畸形',
      '现患或既往患有孕激素受体阳性乳腺癌',
    ],
    related_article: 'contraception-iud-guide',
  },
  {
    id: 'copper-iud',
    name: '含铜宫内节育器 (TCu-IUD)',
    en_name: 'Copper Intrauterine Device (Copper IUD)',
    category: 'non_hormonal_long',
    failure_rate_typical: '0.8%',
    failure_rate_perfect: '0.6%',
    duration: '5 - 10 年',
    protects_sti: false,
    hormone_type: 'none',
    fertility_return: '取出后迅速',
    menses_effect: '初期可能导致经血量增多（增加20%~50%）及经期下腹隐痛坠胀',
    pros: [
      '100% 不含任何外源性激素，完全保留女性自然内源激素轴与排卵节律',
      '超长服役周期（单次放置有效长达 10 年），全生命周期避孕经济成本最低',
      '无保护性行为后 5 天内紧急放置，是成功率最高的紧急避孕补救措施（失败率<0.1%）',
    ],
    cons: [
      '常见经量增多与痛经加剧，贫血体质者使用需谨慎',
      '完全无法阻断性传播疾病传播',
      '极低概率发生子宫穿孔（通常发生在初次放置时，约 1/1000）',
    ],
    contraindications: [
      '威尔逊氏病（遗传性全身铜代谢沉积障碍）或已知铜金属过敏',
      '重度缺铁性贫血或基础经量极大的原发性月经过多患者',
      '生殖系统恶性肿瘤或未控制的急性生殖道感染',
    ],
    related_article: 'contraception-iud-guide',
  },
  {
    id: 'etonogestrel-implant',
    name: '皮下埋植剂 (依托孕烯/依诺孕素)',
    en_name: 'Etonogestrel Contraceptive Implant (Implanon / Nexplanon)',
    category: 'hormonal_long',
    failure_rate_typical: '0.05%',
    failure_rate_perfect: '0.05%',
    duration: '3 - 5 年',
    protects_sti: false,
    hormone_type: 'progestin_only',
    fertility_return: '取出后迅速',
    menses_effect: '出血模式改变（约三分之一人群经量减少或闭经，另有部分人群初期散在点滴出血）',
    pros: [
      '所有可逆避孕方式中珍珠指数最低（年失败率仅 0.05%），比男性结扎更有效',
      '上臂内侧皮下微创埋植，无需进行任何宫腔操作，无子宫穿孔或脱落风险',
      '单次植入管用 3~5 年，隐蔽性极高，取出后生育力数周内即刻恢复',
    ],
    cons: [
      '出血模式具有不确定性，部分使用者前半年可能经历长期点滴出血',
      '需要经培训的医生在上臂内侧皮下进行微创穿刺植入与小切口取出',
      '少数个体可能报告轻微头痛、情绪波动、痤疮或体重微量变化',
    ],
    contraindications: [
      '现患活动性乳腺癌或孕激素敏感性恶性肿瘤',
      '不明原因的急性阴道出血（未排除恶性病变前）',
      '急性重症肝炎或严重肝脏良恶性肿瘤',
    ],
    related_article: 'contraception-iud-guide',
  },
  {
    id: 'progestin-only-pill',
    name: '单纯孕激素避孕药 (POP / 迷你避孕药)',
    en_name: 'Progestin-Only Pill (POP / Mini-pill)',
    category: 'hormonal_short',
    failure_rate_typical: '7%',
    failure_rate_perfect: '0.3%',
    duration: '每日固定时间服药（不设无药间隔期）',
    protects_sti: false,
    hormone_type: 'progestin_only',
    fertility_return: '数天内',
    menses_effect: '月经周期可能缩短、延长或不规则点滴出血，部分人可能出现偶发闭经',
    pros: [
      '完全不含雌激素，哺乳期女性及产后产妇的理想口服避孕方案（不影响泌乳）',
      '不增加下肢深静脉血栓 (DVT) 风险，吸烟或高血压女性在医学评估后可用',
      '对有雌激素禁忌（如先兆偏头痛）的人群友好',
    ],
    cons: [
      '传统左炔诺孕酮/炔诺酮剂型时间容差极窄（通常需严格在同个3小时窗口内服用）',
      '不预防任何性传播感染',
      '月经突破性点滴出血的发生率高于复方短效口服避孕药',
    ],
    contraindications: [
      '现患乳腺癌或既往孕激素敏感肿瘤病史',
      '重度肝硬化失代偿期或急性重型肝炎',
    ],
    related_article: 'contraception-oral-pills',
  },
  {
    id: 'female-condom',
    name: '女用避孕套',
    en_name: 'Female Condom (Internal Condom)',
    category: 'barrier',
    failure_rate_typical: '21%',
    failure_rate_perfect: '5%',
    duration: '单次同房',
    protects_sti: true,
    hormone_type: 'none',
    fertility_return: '立即',
    menses_effect: '对月经周期与经量无影响',
    pros: [
      '赋予女性完全自主掌握避孕与预防 STI 的主动权',
      '可于性行为前数小时提前置入阴道，无需在亲密兴奋时中断前戏',
      '通常采用聚氨酯或合成丁腈材料，完全不引起天然乳胶过敏，导热性更自然',
    ],
    cons: [
      '初次置入需要耐心练习与技巧，使用不当易导致阴茎误入套囊外侧',
      '典型使用年失败率高达 21%，显著劣于男用避孕套与长效药物',
      '单只价格通常高于男用避孕套，且药店与便利店可及性偏低',
    ],
    contraindications: [
      '极个别对聚氨酯或丁腈合成材质过敏者',
    ],
    related_article: 'contraception-condoms',
  },
  {
    id: 'lng-emergency-pill',
    name: '左炔诺孕酮紧急避孕药 (LNG-ECP)',
    en_name: 'Levonorgestrel Emergency Contraceptive Pill',
    category: 'emergency',
    failure_rate_typical: '1.5% - 2.6%',
    failure_rate_perfect: '1.0%',
    duration: '单次事后补救 (72小时内)',
    protects_sti: false,
    hormone_type: 'progestin_only',
    fertility_return: '数天内',
    menses_effect: '可能导致下次月经提前或推迟数天，或伴随暂时性撤退性阴道出血',
    pros: [
      '属于非处方药 (OTC)，药店与网络平台极易合法合规购得，购买门槛低',
      '事后 72 小时（3天）内单次服用即可大幅降低意外妊娠风险，越早服用效果越好',
      '主要机制为推迟排卵，对已着床的受精卵无毒害或堕胎作用，安全性高',
    ],
    cons: [
      '保护效力随时间递减，且如果排卵已发生，则几乎无法阻止受孕',
      '大剂量单次孕激素可能引发恶心、呕吐、下腹坠胀或短暂周期紊乱',
      '体重较高或 BMI≥25 的女性体内血药浓度降低，避孕有效率显著下降',
    ],
    contraindications: [
      '已知已确诊临床妊娠者（服药无效，但并不会导致胚胎畸形）',
    ],
    related_article: 'contraception-emergency-pill',
  },
  {
    id: 'upa-emergency-pill',
    name: '醋酸乌利司他紧急避孕药 (UPA)',
    en_name: 'Ulipristal Acetate Emergency Contraceptive Pill',
    category: 'emergency',
    failure_rate_typical: '1.0% - 1.4%',
    failure_rate_perfect: '0.9%',
    duration: '单次事后补救 (120小时内)',
    protects_sti: false,
    hormone_type: 'progestin_only',
    fertility_return: '数天内',
    menses_effect: '下次月经通常在预计日期前后来潮，部分人出现轻度延迟 2~3 天',
    pros: [
      '事后保护时间窗口长达 120 小时（5天整），且有效率在整个 120 小时内保持平稳不衰减',
      '即使在黄体生成素 (LH) 激增高峰已开始后，仍能推迟卵泡破裂排卵',
      '对超重与肥胖人群（BMI≥30）的有效率显著优于左炔诺孕酮',
    ],
    cons: [
      '需医师处方，部分线下零售药店未常规备货，紧急获取门槛高于普通避孕药',
      '服药后 5 天内不能马上启动常规短效避孕药（会相互削弱疗效）',
      '单次购买费用相对左炔诺孕酮略高',
    ],
    contraindications: [
      '严重重度肝功能损害或肝衰竭患者',
      '对醋酸乌利司他分子或任何辅料严重过敏者',
    ],
    related_article: 'contraception-emergency-pill',
  },
  {
    id: 'sterilization-permanent',
    name: '输卵管结扎 / 输精管结扎术',
    en_name: 'Tubal Ligation / Vasectomy',
    category: 'permanent',
    failure_rate_typical: '0.15% - 0.5%',
    failure_rate_perfect: '0.1% - 0.2%',
    duration: '终身永久有效',
    protects_sti: false,
    hormone_type: 'none',
    fertility_return: '永久不可逆',
    menses_effect: '完全不改变卵巢或睾丸内分泌，月经周期、经量与排卵完全保持自然状态',
    pros: [
      '终身永久避孕，一次手术彻底摆脱所有避孕药具的繁琐与担忧',
      '完全不影响性功能、射精、性高潮体验与内源性性激素平衡',
      '男用输精管结扎在门诊局麻即可微创完成，创伤微小且并发症显著低于女用开腹结扎',
    ],
    cons: [
      '属于永久性不可逆绝育，未来复通手术复杂且无法保证恢复自然生育力',
      '存在外科手术的一般并发症风险（局部血肿、感染或术后短期隐痛）',
      '完全不能预防任何性传播感染 (STI/HIV)',
    ],
    contraindications: [
      '未来仍有任何潜在生育意向或处于心理决策摇摆期者',
      '伴有严重全身凝血功能障碍或无法耐受门诊外科手术者',
    ],
    related_article: 'contraception-iud-guide',
  },
];
