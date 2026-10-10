/**
 * intimacyPreferences.ts — 伴侣双人偏好双盲知情核对题库与结构化元数据
 * 基于循证性生理力学、女性性健康指南与 FRIES 知情同意原则构建
 * 纯客户端离线计算，零数据上传与网络通信
 */

export type PreferenceLevel = 'desire' | 'willing' | 'reject';

export type IntimacyCategoryKey =
  | 'foreplay'
  | 'positions'
  | 'sensory'
  | 'boundaries'
  | 'aftercare';

export interface IntimacyCategoryMeta {
  id: IntimacyCategoryKey;
  label: string;
  stamp: string;
  description: string;
}

export interface IntimacyItem {
  id: string;
  category: IntimacyCategoryKey;
  title: string;
  description: string;
  guidance: string;
  related_article: string;
}

export const INTIMACY_CATEGORIES: Record<IntimacyCategoryKey, IntimacyCategoryMeta> = {
  foreplay: {
    id: 'foreplay',
    label: '前戏探索',
    stamp: '[ 01 // 前戏探索 ]',
    description: '慢节奏非插入式神经唤起、充分润滑与消除生理紧绷',
  },
  positions: {
    id: 'positions',
    label: '体位力学',
    stamp: '[ 02 // 体位力学 ]',
    description: '盆底解剖角度、阴蒂可达度与深部撞击痛自主防护',
  },
  sensory: {
    id: 'sensory',
    label: '感官情调',
    stamp: '[ 03 // 感官情调 ]',
    description: '视觉温光、听觉反馈、温热触抚与适度情趣辅助',
  },
  boundaries: {
    id: 'boundaries',
    label: '心理与边界',
    stamp: '[ 04 // 心理与边界 ]',
    description: '随时一票否决权、安全词机制、零内疚拒绝与安全防护底线',
  },
  aftercare: {
    id: 'aftercare',
    label: '温存与复盘',
    stamp: '[ 05 // 温存与复盘 ]',
    description: '事后防低落保暖拥抱、卫生排尿冲洗与赞赏式去防备交流',
  },
};

export const INTIMACY_PREFERENCES: IntimacyItem[] = [
  // 1. 前戏探索 (foreplay)
  {
    id: 'foreplay_slow_arousal',
    category: 'foreplay',
    title: '充分唤起与慢节奏前戏 (20-40分钟)',
    description: '留足充分的非插入式抚触、亲吻与慢节奏唤起时间，配合女性副交感神经充血与前庭大腺润滑节律。',
    guidance: '女性血管充血与阴蒂勃起通常需 20-40 分钟，充足前戏能显著降低阴道痉挛与摩擦痛风险。',
    related_article: 'pleasure-arousal-time-physiology',
  },
  {
    id: 'foreplay_clitoral_direct',
    category: 'foreplay',
    title: '直接/间接阴蒂外生殖器轻柔刺激',
    description: '在充分湿润状态下，使用指腹、轻柔画圈或震动辅助探索阴蒂体与包皮敏感区。',
    guidance: '80% 以上女性需要直接或间接阴蒂刺激达成高潮；初始阶段避免干燥直接大力摩擦阴蒂头。',
    related_article: 'female-pleasure-clitoris',
  },
  {
    id: 'foreplay_dual_control_tuning',
    category: 'foreplay',
    title: '性唤起油门踩踏与刹车排查',
    description: '共同创造低压力、私密安全的环境，主动消除焦虑源（如关好房门、调暗灯光、放下工作与手机）。',
    guidance: '依据双重控制模型，关掉焦虑与分心的刹车信号往往比盲目加大油门刺激更为关键。',
    related_article: 'pleasure-responsive-desire-dual-control',
  },
  {
    id: 'foreplay_lubricant_generous',
    category: 'foreplay',
    title: '足量优质水性/硅基润滑剂支持',
    description: '在前戏与接触全程主动且足量使用专业润滑剂，不将天然分泌量作为衡量兴奋度的唯一标准。',
    guidance: '自体润滑受生理周期、激素波动及药物影响；足量使用润滑剂可大幅减少微黏膜撕裂与不适。',
    related_article: 'pleasure-lubricant-guide',
  },

  // 2. 体位力学 (positions)
  {
    id: 'positions_woman_on_top',
    category: 'positions',
    title: '女上位主导节律与进入深度',
    description: '由女性跨坐于上方，自主掌控盆底起伏角度、进入深度与摩擦节奏。',
    guidance: '该体位女性对宫颈撞击与疼痛拥有最高防御掌控权，便于精准调控对阴蒂的对位研磨。',
    related_article: 'pleasure-woman-on-top-mechanics',
  },
  {
    id: 'positions_cat_alignment',
    category: 'positions',
    title: 'CAT 对齐技术（前向恒定研磨）',
    description: '男上位骨盆向上滑动对齐，以阴茎根部紧贴并持续轻压研磨阴蒂，不做大幅度抽动。',
    guidance: 'CAT 技术的恒定对位研磨能够提供持续阴蒂刺激，被临床性治疗广泛推荐为易高潮体位。',
    related_article: 'pleasure-cat-technique-alignment',
  },
  {
    id: 'positions_side_spooning',
    category: 'positions',
    title: '侧卧匙羹位（低耗能温热贴合）',
    description: '两人同向侧卧微曲双膝，进入角度平缓，体能消耗低且身体贴合面积大。',
    guidance: '匙羹位进入轴线平缓、不易撞击后穹窿宫颈，适合疲劳、孕期或经期前后需要放松时。',
    related_article: 'pleasure-side-lying-spooning',
  },
  {
    id: 'positions_pelvic_pillow',
    category: 'positions',
    title: '骨盆垫枕与仰卧角度微调',
    description: '在女性臀下或腰骶部垫上软枕，抬高骨盆以改变进入迎角并提供持续腰骶支撑。',
    guidance: '垫枕改变阴道轴线角度，既可减轻腰肌劳损，也能缓解特定角度的深部牵拉不适感。',
    related_article: 'pleasure-rear-entry-angles',
  },

  // 3. 感官情调 (sensory)
  {
    id: 'sensory_visual_lighting',
    category: 'sensory',
    title: '可调暖光/微暗氛围与视觉安全感',
    description: '使用暖色调间接照明、微弱灯光或烛光，营造安全放松且不具凝视压迫感的视觉空间。',
    guidance: '柔和光线有助于降低身体外貌焦虑（Body Image Anxiety），释放交感神经紧张。',
    related_article: 'pleasure-responsive-desire-dual-control',
  },
  {
    id: 'sensory_auditory_feedback',
    category: 'sensory',
    title: '呼吸与非语言声音积极反馈',
    description: '在亲密过程中自然表达舒服的呼吸声、轻声赞许或非语言正向反馈。',
    guidance: '及时、真诚的声音反馈能够让伴侣获得确信，避免猜忌或机械化动作。',
    related_article: 'intimacy-fries-consent',
  },
  {
    id: 'sensory_temperature_touch',
    category: 'sensory',
    title: '温感触觉与背部/肩颈放松按摩',
    description: '同房前先进行温热毛巾敷贴、温暖双手或非性敏感带（背、颈、足部）的舒缓推拿。',
    guidance: '激活皮肤的触觉 C 触觉传入纤维，促进催产素分泌，为副交感神经主导的性唤起奠定基础。',
    related_article: 'pleasure-arousal-time-physiology',
  },
  {
    id: 'sensory_toys_integration',
    category: 'sensory',
    title: '伴侣情趣器具与震动玩具协同',
    description: '共同引入外用阴蒂震动玩具或温和辅助用具，作为双人亲密中的中立探索工具。',
    guidance: '情趣用品是伴侣双方探索神经愉悦的辅助延伸，使用前需明确消毒清洁与防水安全规范。',
    related_article: 'pleasure-female-masturbation',
  },

  // 4. 心理与边界 (boundaries)
  {
    id: 'boundaries_safe_word',
    category: 'boundaries',
    title: '设立安全词与无条件一票否决权',
    description: '约定简明安全词（如红灯或特定暂停手势），任何一方喊出即刻暂停并拥抱复位。',
    guidance: 'FRIES 原则强调同意是可随时撤回的，明确的退出机制反而带来最高心理安全感。',
    related_article: 'intimacy-fries-consent',
  },
  {
    id: 'boundaries_saying_no_without_guilt',
    category: 'boundaries',
    title: '去内疚感拒绝与状态不佳叫停',
    description: '无论前戏进行到哪一步，感到疲惫、疼痛或不适时均可坦诚说今天先到这里，伴侣不施加冷暴力。',
    guidance: '强行配合会导致下意识的盆底肌防御性痉挛与性厌恶；温柔拒绝是长久亲密关系的防护网。',
    related_article: 'intimacy-sexual-boundary-saying-no',
  },
  {
    id: 'boundaries_condom_routine',
    category: 'boundaries',
    title: '全程严格正确佩戴安全套',
    description: '从任何生殖器直接接触的第一秒起即全程佩戴正规安全套，兼顾避孕与防 STI 安全。',
    guidance: '拒绝体外射精或侥幸心理，建立安全防护共识是双方身体健康负责的基本底线。',
    related_article: 'contraception-condoms',
  },
  {
    id: 'boundaries_pain_zero_tolerance',
    category: 'boundaries',
    title: '对疼痛零容忍与深部不适沟通',
    description: '出现任何尖锐痛、撕裂感或下腹酸胀时立即沟通调整，绝不咬牙忍耐。',
    guidance: '痛觉信号是机体组织损伤的生理警报；持续忍痛会诱发慢性盆底前庭炎与条件反射性痉挛。',
    related_article: 'pleasure-dyspareunia-pain',
  },

  // 5. 温存与复盘 (aftercare)
  {
    id: 'aftercare_cuddle_hydration',
    category: 'aftercare',
    title: '事后静卧拥抱、盖毯保暖与温水补水',
    description: '结束后留出 10-20 分钟静静依偎拥抱，轻柔擦拭汗水，饮用适量温水，避免立刻各自刷手机。',
    guidance: '高潮后催产素与催乳素急剧升高，伴随温度下降与心理脆弱期，保暖与拥抱能有效防范事后低落（PCD）。',
    related_article: 'pleasure-arousal-time-physiology',
  },
  {
    id: 'aftercare_hygiene_urination',
    category: 'aftercare',
    title: '事后排尿与温水外阴简易清洗',
    description: '结束后适时起身排尿冲刷尿道，并用流动的温水由前向后轻柔冲洗外阴，吸干水分。',
    guidance: '性生活后排尿有助于将机械挤压进入尿道的细菌冲刷排出，有效预防急性蜜月期尿路感染。',
    related_article: 'intimacy-sti-prevention',
  },
  {
    id: 'aftercare_feedback_debrief',
    category: 'aftercare',
    title: '低防备心双向舒适度复盘',
    description: '用刚刚那个角度特别舒服或下次前面我们再慢一点好吗的赞赏夹心法交流真实感受。',
    guidance: '复盘应聚焦于生理舒适度与彼此连接，避免评判表现或将是否高潮作为唯一及格线。',
    related_article: 'intimacy-healthy-boundaries',
  },
  {
    id: 'aftercare_emotional_checkin',
    category: 'aftercare',
    title: '情绪感受确认与脆弱表达接纳',
    description: '彼此询问你现在心情感觉如何，倾听对方的隐微情绪，给予确定性的爱意言语肯定。',
    guidance: '性的本质是亲密与信任连接，情绪确认能消除不安全感与依恋焦虑，深化长久信任。',
    related_article: 'intimacy-fries-consent',
  },
];
