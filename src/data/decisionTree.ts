/**
 * decisionTree.ts — 紧急状况交互决策树数据契约与图结构 (ADR-0002)
 * 循证支撑：WHO 紧急避孕与计划生育指南、FIGO 异常子宫出血分类、默沙东大众版
 */

export type DecisionUrgency = 'emergency' | 'warning' | 'info' | 'reassurance';

export interface DecisionOption {
  label: string;
  desc?: string;
  nextNodeId?: string;
  outcomeId?: string;
}

export interface DecisionNode {
  id: string;
  category: 'contraception_accident' | 'missed_pill' | 'abnormal_bleeding';
  question: string;
  hint?: string;
  options: DecisionOption[];
}

export interface DecisionOutcome {
  id: string;
  category: 'contraception_accident' | 'missed_pill' | 'abnormal_bleeding';
  urgency: DecisionUrgency;
  title: string;
  headline: string;
  actionItems: string[];
  timelineGuide?: string;
  redFlags?: string[];
  reassuranceNote?: string;
  relatedArticleSlug?: string;
  sourceAuthority: string;
  /** 跨工具状态透传：一键直达实用工具箱对应计算器并预填参数 */
  directToolLink?: {
    toolId: string;
    urlParams: string;
    buttonText: string;
  };
}

export interface DecisionTreeData {
  initialCategories: Array<{
    id: string;
    title: string;
    icon: string;
    desc: string;
    startNodeId: string;
  }>;
  nodes: Record<string, DecisionNode>;
  outcomes: Record<string, DecisionOutcome>;
}

export const DECISION_TREE: DecisionTreeData = {
  initialCategories: [
    {
      id: "condom_accident",
      title: "避孕套破损 / 脱落 / 事故",
      icon: "contraception",
      desc: "同房中途避孕套破裂、滑脱在体内、或未全程佩戴",
      startNodeId: "node_condom_time"
    },
    {
      id: "missed_pill",
      title: "短效口服避孕药 (COC) 漏服",
      icon: "pill",
      desc: "忘记服药 1 天或连续漏服 2 天以上的分步抢救",
      startNodeId: "node_pill_days"
    },
    {
      id: "abnormal_bleeding",
      title: "非经期出血 / 咖啡色分泌物",
      icon: "bleeding",
      desc: "月经刚完又有少量褐血、两次经期正中间点滴、或同房出血",
      startNodeId: "node_bleeding_timing"
    }
  ],
  nodes: {
    node_condom_time: {
      id: "node_condom_time",
      category: "contraception_accident",
      question: "距离发生无保护接触或避孕套破损，大概过去了多久？",
      hint: "紧急避孕药具有严格的时间递减效应，越早补救效果越好",
      options: [
        {
          label: "不到 24 小时",
          desc: "处于黄金干预窗口，成功率最高",
          nextNodeId: "node_condom_cycle"
        },
        {
          label: "24 ~ 72 小时 (1~3 天)",
          desc: "常规口服紧急避孕药的有效窗口内",
          nextNodeId: "node_condom_cycle"
        },
        {
          label: "72 ~ 120 小时 (3~5 天)",
          desc: "已超出普通紧急药最佳期，但仍有终极医疗方案",
          outcomeId: "outcome_condom_120h"
        },
        {
          label: "超过 120 小时 (5 天以上)",
          desc: "已错过所有紧急避孕干预窗口",
          outcomeId: "outcome_condom_expired"
        }
      ]
    },
    node_condom_cycle: {
      id: "node_condom_cycle",
      category: "contraception_accident",
      question: "当前处于月经周期的什么阶段？",
      hint: "精子在女性生殖道内可存活长达 3~5 天",
      options: [
        {
          label: "处于排卵期前后（两次月经正中间）",
          desc: "受孕概率极高，属于高危暴露",
          outcomeId: "outcome_condom_72h_high_risk"
        },
        {
          label: "自测属于安全期 / 刚干净 / 快来月经",
          desc: "排卵可能因情绪、劳累发生意外漂移",
          outcomeId: "outcome_condom_72h_standard"
        },
        {
          label: "周期很不规律 / 完全算不清",
          desc: "无法依赖安全期，一律按可能排卵审慎处置",
          outcomeId: "outcome_condom_72h_high_risk"
        }
      ]
    },
    node_pill_days: {
      id: "node_pill_days",
      category: "missed_pill",
      question: "请问是漏服了几天（几片）药？",
      hint: "以通常应服药的时间算起，超过 12~24 小时未吃视为漏服",
      options: [
        {
          label: "仅漏服 1 天（1 片）",
          desc: "距离原定服药时间未超过 24 小时或刚想起来",
          outcomeId: "outcome_pill_missed_1"
        },
        {
          label: "连续漏服 2 天或 2 天以上（>=2 片）",
          desc: "体内激素水平已出现明显断崖式下跌",
          nextNodeId: "node_pill_week"
        }
      ]
    },
    node_pill_week: {
      id: "node_pill_week",
      category: "missed_pill",
      question: "连续漏服发生在这盒药（通常21或28片板）的哪一周？",
      hint: "不同周期的卵泡发育阶段不同，排卵复苏风险有显著差异",
      options: [
        {
          label: "第 1 周（刚停药结束开始吃新的一板）",
          desc: "紧接着无激素间隔期，卵泡极易苏醒并意外排卵",
          outcomeId: "outcome_pill_missed_week1"
        },
        {
          label: "第 2 周（药板中间段，已规律服药满 7 天）",
          desc: "下丘脑-垂体轴抑制相对稳定",
          outcomeId: "outcome_pill_missed_week2"
        },
        {
          label: "第 3 周（临近吃完或即将进入停药期）",
          desc: "需要防止无激素期提前诱发排卵",
          outcomeId: "outcome_pill_missed_week3"
        }
      ]
    },
    node_bleeding_timing: {
      id: "node_bleeding_timing",
      category: "abnormal_bleeding",
      question: "异常出血或分泌物发生在周期的什么具体时刻？",
      hint: "非经期出血按 PALM-COEIN 分类法，多与激素波动或局部病变相关",
      options: [
        {
          label: "两次月经正中间（大概周期的第 12~16 天）",
          desc: "通常量极少，呈粉红或淡咖啡色点滴，1~3 天自止",
          outcomeId: "outcome_bleeding_ovulation"
        },
        {
          label: "月经刚干净后拖尾（持续有少量褐色分泌物）",
          desc: "经期总天数在 6~8 天内，无异味无剧痛",
          outcomeId: "outcome_bleeding_tailing"
        },
        {
          label: "同房后接触性出血 / 持续淋漓超过 10 天",
          desc: "性生活后有鲜红色血迹，或不规则持续出血",
          nextNodeId: "node_bleeding_symptoms"
        }
      ]
    },
    node_bleeding_symptoms: {
      id: "node_bleeding_symptoms",
      category: "abnormal_bleeding",
      question: "出血是否伴随以下任何剧烈不适体征？",
      hint: "急性下腹剧痛、发热可能提示黄体破裂、宫外孕或急性盆腔炎",
      options: [
        {
          label: "伴随单侧剧烈撕裂样腹痛、虚脱冷汗、肛门坠胀或高热",
          desc: "属于临床高危急症信号，需立即就医",
          outcomeId: "outcome_bleeding_red_flag"
        },
        {
          label: "无明显下腹剧痛，仅偶尔隐痛或无任何感觉",
          desc: "多为器质性良性改变（如息肉、宫颈管或内分泌紊乱）",
          outcomeId: "outcome_bleeding_chronic"
        }
      ]
    }
  },
  outcomes: {
    outcome_condom_72h_high_risk: {
      id: "outcome_condom_72h_high_risk",
      category: "contraception_accident",
      urgency: "emergency",
      title: "建议尽快服用紧急避孕药补救",
      headline: "处于排卵高危期，请争分夺秒在 72 小时内服药，越快越好！",
      actionItems: [
        "优先选择单剂左炔诺孕酮（1.5mg，如金毓婷等）或醋酸乌利司他（30mg）；",
        "在事故发生后 24 小时内服药避孕有效率高达 95% 以上，48~72 小时内递减至 58%~85%；",
        "服药后 2 小时内若发生呕吐，必须立即补服同等剂量 1 片；",
        "服药后本周期随后的性行为必须全程加用避孕套，切勿心存侥幸以为本月可以‘无限放开’。"
      ],
      timelineGuide: "同房后 14 天晨起使用验孕棒测试晨尿，或同房后 10 天前往医院查血 HCG 排除妊娠。",
      reassuranceNote: "紧急避孕药的主要原理是推迟排卵，它绝非堕胎药，如果已经着床怀孕并不会引起流产，也不会损害身体长期生育力，切勿过分自责或恐慌。",
      relatedArticleSlug: "contraception-emergency-pill",
      sourceAuthority: "世界卫生组织 (WHO) 紧急避孕实况报道",
      directToolLink: {
        toolId: "ec-countdown",
        urlParams: "tool=ec-countdown&hours=6",
        buttonText: "启动 72h 紧急避孕倒计时"
      }
    },
    outcome_condom_72h_standard: {
      id: "outcome_condom_72h_standard",
      category: "contraception_accident",
      urgency: "warning",
      title: "建议权衡补救：不可迷信所谓的‘绝对安全期’",
      headline: "排卵易受情绪、压力与作息漂移，72 小时内补服口服紧急避孕药最为稳妥。",
      actionItems: [
        "临床医学已明确否定‘前七后八安全期绝对安全’的说法，月经周期中任何时候都有额外排卵可能；",
        "若坚决不打算要孩子，建议在 72 小时内尽早服用单剂左炔诺孕酮（1.5mg）；",
        "服药后几天可能会出现撤退性点滴出血或月经轻度推迟，属于常见孕激素撤退反应；",
        "同房后 14 天自测验孕棒进行最终确认。"
      ],
      timelineGuide: "同房后满 14 天测晨尿验孕棒。",
      reassuranceNote: "单次科学补服紧急避孕药不会对长期健康造成不可逆损伤，按说明书使用即可。",
      relatedArticleSlug: "contraception-emergency-pill",
      sourceAuthority: "世界卫生组织 (WHO) 家庭生育规划指南",
      directToolLink: {
        toolId: "ec-countdown",
        urlParams: "tool=ec-countdown&hours=24",
        buttonText: "启动 72h 紧急避孕倒计时"
      }
    },
    outcome_condom_120h: {
      id: "outcome_condom_120h",
      category: "contraception_accident",
      urgency: "warning",
      title: "超出普通口服药黄金期：可选择含铜节育环终极补救",
      headline: "已过 72 小时，普通口服药效果极微；5 天内放置含铜 IUD 仍有 99% 有效率！",
      actionItems: [
        "口服左炔诺孕酮超过 72 小时后效果大幅下降，常规不推荐作为主方案；",
        "世界卫生组织推荐：在无保护性行为后 120 小时（5 天）内，前往正规公立医院妇科急诊放置含铜宫内节育器（Copper IUD），避孕有效率高达 99% 以上；",
        "含铜 IUD 还可作为后续 5~10 年的长期高效避孕方式；",
        "若不考虑上环，需耐心等待至同房后 14 天进行血/尿 HCG 验孕排查。"
      ],
      timelineGuide: "事故后 5 天（120h）内为上环终极窗口；事故后 14 天进行验孕复核。",
      relatedArticleSlug: "contraception-emergency-pill",
      sourceAuthority: "世界卫生组织 (WHO) 紧急避孕临床实践指南",
      directToolLink: {
        toolId: "ec-countdown",
        urlParams: "tool=ec-countdown&hours=96",
        buttonText: "启动 120h 医疗终极窗口倒计时"
      }
    },
    outcome_condom_expired: {
      id: "outcome_condom_expired",
      category: "contraception_accident",
      urgency: "info",
      title: "已错过紧急避孕窗口：请勿乱吃药，等待 14 天验孕",
      headline: "超过 5 天后受精卵若形成已接近着床，任何紧急药物均已无效，切勿盲目乱吃药损伤内膜。",
      actionItems: [
        "千万不要听信偏方或超大剂量乱吃避孕药，此时药物不仅无法避孕，反而会导致严重内分泌紊乱和大出血；",
        "保持心情平静，在事故同房后满 14 天，使用晨尿验孕棒检测；或在月经推迟 3 天后复测；",
        "若测出阳性弱阳性，请第一时间前往公立医院妇科门诊查超声和血 HCG，由正规医生面诊评估。"
      ],
      timelineGuide: "同房后 14 天首测 → 月经推迟 3~7 天复测。",
      relatedArticleSlug: "contraception-condom-myths",
      sourceAuthority: "默沙东诊疗手册大众版",
      directToolLink: {
        toolId: "clinic-memo",
        urlParams: "tool=clinic-memo&complaint=bleeding",
        buttonText: "生成验孕随访主诉便签"
      }
    },
    outcome_pill_missed_1: {
      id: "outcome_pill_missed_1",
      category: "missed_pill",
      urgency: "reassurance",
      title: "仅漏服 1 天：立即补服，避孕保护依然有效",
      headline: "不要慌张！立即补吃 1 片，即使同一天吃 2 片也完全安全。",
      actionItems: [
        "【第一步】想起来的当下，立刻补服漏服的那 1 片药；",
        "【第二步】今天的下一片药依然在常规固定时间服用（即使在同一天或同时吃下 2 片药也完全合规）；",
        "【后续防护】无需加用避孕套，此种情况下避孕效果不受显著削弱。"
      ],
      reassuranceNote: "短效复方口服避孕药对单日漏服有充分的半衰期容错空间，只要及时补上，下丘脑排卵抑制机制依然在起作用。",
      relatedArticleSlug: "contraception-oral-pills",
      sourceAuthority: "默沙东诊疗手册大众版 激素避孕方法",
      directToolLink: {
        toolId: "coc-remedy",
        urlParams: "tool=coc-remedy",
        buttonText: "启动短效药漏服补救计算器"
      }
    },
    outcome_pill_missed_week1: {
      id: "outcome_pill_missed_week1",
      category: "missed_pill",
      urgency: "emergency",
      title: "第 1 周连续漏服 2 片以上：立即补服 + 严禁裸奔 7 天",
      headline: "处于停药期后最危险期！立即补服，并在接下来 7 天内性生活必须严格加用避孕套！",
      actionItems: [
        "【立即补服】立即补吃最近漏掉的 1 片（舍弃更早漏掉的），随后的药片按原计划每天按时服用；",
        "【附加防护】在接下来的连续 7 天内，发生性生活必须全程佩戴避孕套；",
        "【紧急评估】如果此前在漏服前的 5 天内曾有过无保护性行为，必须在 72 小时内加服紧急避孕药补救。"
      ],
      timelineGuide: "严格执行 7 天避孕套附加防护期。",
      relatedArticleSlug: "contraception-oral-pills",
      sourceAuthority: "世界卫生组织 (WHO) 与英国 FSRH 避孕用药指南",
      directToolLink: {
        toolId: "coc-remedy",
        urlParams: "tool=coc-remedy",
        buttonText: "启动短效药漏服补救计算器"
      }
    },
    outcome_pill_missed_week2: {
      id: "outcome_pill_missed_week2",
      category: "missed_pill",
      urgency: "warning",
      title: "第 2 周连续漏服 2 片以上：补服 + 视情况附加防护 7 天",
      headline: "立即补吃最近漏服的药片，若此前服药规律通常风险较低，但仍建议 7 天双保险。",
      actionItems: [
        "【立即补服】立即补服最近漏掉的 1 片，今天原本的药片在正常时间吃；",
        "【常规服药】继续每天按时服用，直到吃完这盒药；",
        "【防护建议】若此前 7 天均规律服药，通常无需额外紧急避孕，但稳妥起见建议未来 7 天性生活加用避孕套。"
      ],
      relatedArticleSlug: "contraception-oral-pills",
      sourceAuthority: "默沙东诊疗手册大众版",
      directToolLink: {
        toolId: "coc-remedy",
        urlParams: "tool=coc-remedy",
        buttonText: "启动短效药漏服补救计算器"
      }
    },
    outcome_pill_missed_week3: {
      id: "outcome_pill_missed_week3",
      category: "missed_pill",
      urgency: "warning",
      title: "第 3 周连续漏服 2 片以上：直接连吃下一板，跳过停药期！",
      headline: "立即补服，吃完本板有效药后不进入 7 天停药期，直接无缝开启下一板！",
      actionItems: [
        "【立即补服】补服最近漏掉的 1 片，继续规律每天吃药；",
        "【跳过停药期】服完这盒药中剩余的活性药片后，**直接开始服用下一盒新药**，不要进入 7 天停药期（28片包装者直接丢弃最后的安慰剂片）；",
        "【可能现象】在服用第二盒药期间可能会有轻微点滴突破性出血，属于正常现象，不停药继续吃即可。"
      ],
      relatedArticleSlug: "contraception-oral-pills",
      sourceAuthority: "默沙东诊疗手册大众版",
      directToolLink: {
        toolId: "coc-remedy",
        urlParams: "tool=coc-remedy",
        buttonText: "启动短效药漏服补救计算器"
      }
    },
    outcome_bleeding_ovulation: {
      id: "outcome_bleeding_ovulation",
      category: "abnormal_bleeding",
      urgency: "reassurance",
      title: "排卵期生理性出血：极常见的荷尔蒙短暂波动",
      headline: "发生在两次月经正中间、无剧痛、持续 1~3 天自止，通常完全良性生理现象。",
      actionItems: [
        "【产生原理】排卵前后体内雌激素短暂撤退，导致子宫内膜少量突破性脱落出血，常伴有拉丝状透明白带；",
        "【处置建议】保持外阴清洁干爽，无需服用任何止血药或抗生素；",
        "【后续观察】若出血持续超过 4 天、血量接近月经量或伴随明显腹痛，才需就医排查内膜息肉。"
      ],
      reassuranceNote: "临床统计约 20%~30% 的育龄期女性在一生中经历过排卵期出血，不要过度恐慌焦虑。",
      relatedArticleSlug: "abnormal-uterine-bleeding",
      sourceAuthority: "国际妇产科联合会 (FIGO) 临床指导原则",
      directToolLink: {
        toolId: "cycle-assess",
        urlParams: "tool=cycle-assess",
        buttonText: "启动月经四大指标自测"
      }
    },
    outcome_bleeding_tailing: {
      id: "outcome_bleeding_tailing",
      category: "abnormal_bleeding",
      urgency: "reassurance",
      title: "经期末尾咖啡色分泌物：陈旧血氧化，无需恐慌",
      headline: "月经快结束时血流缓慢，血液在阴道弱酸性环境下氧化变褐，属于正常生理过程。",
      actionItems: [
        "【生理机制】经期末期子宫内膜脱落速度减缓，少量经血在阴道内停留时间较长，血红蛋白铁元素氧化为三价铁呈褐色/咖啡色；",
        "【日常护理】使用透气护垫，勤换内裤，切勿使用阴道冲洗器破坏菌群自洁平衡；",
        "【就医界限】只要总经期未超过 8 天（FIGO 国际标准），均属于健康范畴；若拖尾超过 10 天以上建议做妇科经阴道 B 超排查息肉。"
      ],
      relatedArticleSlug: "normal-menstrual-cycle",
      sourceAuthority: "默沙东诊疗手册大众版 月经周期",
      directToolLink: {
        toolId: "cycle-assess",
        urlParams: "tool=cycle-assess",
        buttonText: "启动月经四大指标自测"
      }
    },
    outcome_bleeding_red_flag: {
      id: "outcome_bleeding_red_flag",
      category: "abnormal_bleeding",
      urgency: "emergency",
      title: "医疗红旗警报：伴随急性下腹剧痛，请立即前往急诊！",
      headline: "出血伴剧烈撕裂样下腹痛、冷汗或肛门下坠感，提示黄体破裂或异位妊娠急症风险！",
      actionItems: [
        "【立即行动】立刻停下手中事务，不要强忍，建议由伴侣或家人陪同前往附近公立三甲医院急诊妇产科；",
        "【严禁盲目止痛】在医生确诊前，**千万不要自行服用布洛芬或止痛药**，以免掩盖急腹症病征贻误病情；",
        "【就诊排查重点】医生通常会进行急诊经阴道后穹隆穿刺、血 HCG 与急诊妇科彩超，排查黄体破裂内出血或宫外孕。"
      ],
      redFlags: [
        "排卵期后（黄体期）剧烈运动或同房后突发下腹撕裂样绞痛",
        "伴随头晕、面色苍白、冷汗、血压下降或直肠肛门下坠感",
        "阴道出血伴随 38.5℃ 以上高热与异味脓性白带"
      ],
      relatedArticleSlug: "abnormal-uterine-bleeding",
      sourceAuthority: "中华医学会妇产科学分会 急腹症诊疗规范",
      directToolLink: {
        toolId: "clinic-memo",
        urlParams: "tool=clinic-memo&complaint=pelvic-pain",
        buttonText: "生成急诊主诉沟通便签"
      }
    },
    outcome_bleeding_chronic: {
      id: "outcome_bleeding_chronic",
      category: "abnormal_bleeding",
      urgency: "warning",
      title: "同房接触性出血或长期不规则出血：建议择期挂专科门诊",
      headline: "无急性剧痛，但接触性出血需要引起重视，建议月经干净后 3~7 天进行常规妇科检查。",
      actionItems: [
        "【预约门诊】择期挂正规公立医院妇科门诊（非急诊）；",
        "【检查推荐】遵医嘱进行妇科窥器内诊、宫颈 TCT + HPV 联合筛查以及经阴道子宫附件彩超；",
        "【常见良性诱因】宫颈息肉、宫颈柱状上皮异位（俗称轻度糜烂样改变）、子宫内膜微小息肉或轻度盆腔充血均可能导致少量同房出血，绝大多数可微创或对症解决，切勿盲目恐慌。"
      ],
      timelineGuide: "建议在下次月经完全干净后 3~5 天（不同房）前往医院检查最为准确。",
      relatedArticleSlug: "body-hpv-vaccine-screening",
      sourceAuthority: "默沙东诊疗手册大众版 妇科症状诊断",
      directToolLink: {
        toolId: "clinic-memo",
        urlParams: "tool=clinic-memo&complaint=bleeding",
        buttonText: "生成门诊主诉沟通便签"
      }
    }
  }
};
