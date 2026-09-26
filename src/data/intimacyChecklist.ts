/**
 * intimacyChecklist.ts — 伴侣私密知情同意与偏好探索题库 (Yes / No / Maybe)
 * 遵循临床性治疗脱敏沟通原则与非暴力沟通 (NVC) 框架。
 * 纯前端离线运行，零数据留存与隐私回传，无原生彩色 Emoji。
 */

export interface ChecklistItem {
  id: string;
  title: string;
  physiological_reason: string;
  suggestion_text: string;
}

export interface ChecklistCategory {
  id: string;
  name: string;
  description: string;
  items: ChecklistItem[];
}

export const INTIMACY_CHECKLIST_CONFIGS: ChecklistCategory[] = [
  {
    id: 'category_posture_angle',
    name: '01 // 体位微调与角度',
    description:
      '通过微调骨盆倾角、重心接触点与进入轴线，减少深部钝痛，促进阴蒂平稳接触。',
    items: [
      {
        id: 'pos_pelvic_pillow',
        title: '骨盆下垫硬枕',
        physiological_reason:
          '抬高骶尾部 20°~30° 可展平阴道后穹窿并微调进入仰角，消除腰骶肌肉悬空紧张，降低宫颈深部对冲痛感。',
        suggestion_text:
          '“我们可以试着在我的臀下垫一个结实点的枕头，这样能减轻我腰部的受力，进出的角度也会更温和顺畅。”',
      },
      {
        id: 'pos_cat_technique',
        title: 'CAT贴合微磨',
        physiological_reason:
          '利用耻骨联合紧密贴紧阴蒂头与前庭球进行微幅前后研磨，替代活塞式大行程抽拉，维持持续平缓的阴蒂感觉输入。',
        suggestion_text:
          '“你可以把重心移到手肘上贴紧我，我们前后慢慢研磨，不要完全退出来，这样我的阴蒂会一直很有感觉。”',
      },
      {
        id: 'pos_spooning_embrace',
        title: '侧卧慢速深拥',
        physiological_reason:
          '侧向平行轴线进入受力均匀且体能消耗极低，后背紧贴可有效抑制交感神经兴奋过度，促进催产素分泌与骨盆底肌放松。',
        suggestion_text:
          '“我们并排侧躺着慢慢来，你从后面抱紧我，不用太费力气，这样能让我全身很放松、很有安全感。”',
      },
    ],
  },
  {
    id: 'category_warmup_arousal',
    name: '02 // 预热与唤起时间',
    description:
      '遵循女性性反应周期规律，充分保障前庭大腺与巴氏腺分泌及前庭海绵体充血舒张。',
    items: [
      {
        id: 'warm_extended_foreplay',
        title: '15~20分钟纯外围预热',
        physiological_reason:
          '女性性唤起并达到阴道充分润滑、后穹窿形成“帐篷效应”平均需要 15 至 40 分钟，充足外围刺激可预防插入期干涩与前庭撕裂。',
        suggestion_text:
          '“进入前我们先用 15 到 20 分钟多接吻和做外围抚触好吗？身体需要足够的时间自然准备好才不会痛。”',
      },
      {
        id: 'warm_hot_bath_relax',
        title: '温水沐浴放松',
        physiological_reason:
          '38℃~40℃ 温水沐浴或温敷能促进外周毛细血管扩张，缓解深层盆底肌群（如提肛肌与闭孔内肌）防御性紧缩痉挛。',
        suggestion_text:
          '“开始前我们一起去泡个热水澡或冲个温水淋浴吧，让身体彻底放松下来，能帮助褪去一整天的疲惫与紧绷。”',
      },
      {
        id: 'warm_full_body_touch',
        title: '全身肌肉抚触',
        physiological_reason:
          '从肩颈、背部及四肢非生殖器区域循序渐进抚触，可降低皮质醇水平并激活副交感神经系统，建立高耐受的亲密信任基底。',
        suggestion_text:
          '“先帮我揉揉肩膀和后背吧，先不要急着碰私密部位，慢一点让我慢慢进入状态。”',
      },
    ],
  },
  {
    id: 'category_lubricant_props',
    name: '03 // 辅助润滑与道具',
    description:
      '借助现代循证卫生辅助道具，消除生理润滑缺口，实现双重神经通路的愉悦唤醒。',
    items: [
      {
        id: 'lube_water_based_supply',
        title: '足量水基润滑剂补给',
        physiological_reason:
          '天然体液分泌易受焦虑、疲劳或激素波动影响而随时挥发，医用水基润滑剂可将剪切摩擦阻力降至最低，避免黏膜微裂伤。',
        suggestion_text:
          '“我们中途多补一点水基润滑剂在入口和避孕套上吧，润滑充足我才最舒服，完全不用担心‘是不是我不够兴奋’。”',
      },
      {
        id: 'lube_external_vibrator',
        title: '外用震动器协同刺激',
        physiological_reason:
          '70% 以上女性需阴蒂外部直接刺激方可达到高潮；在插入过程中外加震动器可协同激活阴蒂脚及阴部神经主干传导。',
        suggestion_text:
          '“我想在亲密时加上我们的小玩具一起刺激阴蒂，双重感觉会让我更容易专注体验高潮，我们一起探索。”',
      },
      {
        id: 'lube_hygiene_nail_care',
        title: '指交前清洁修剪指甲',
        physiological_reason:
          '长指甲或粗糙边缘极易刮伤娇嫩的阴道复层扁平上皮细胞，甲缝细菌亦是诱发外阴假丝酵母菌病或细菌性阴道病 (BV) 的主要媒介。',
        suggestion_text:
          '“在用手碰我私处前，请务必先仔细洗净双手并把指甲边缘打磨平整，这能保护我的阴道菌群不被刮伤感染。”',
      },
    ],
  },
  {
    id: 'category_rhythm_boundaries',
    name: '04 // 节奏与深度界限',
    description:
      '明确自主边界与知情同意权，杜绝冲撞损伤，以安全感为第一准则。',
    items: [
      {
        id: 'rhythm_female_control_speed',
        title: '女性主导进入速度',
        physiological_reason:
          '由女性掌握初始进入的速度与骨盆进退深度，可使阴道括约肌根据自主舒适度逐步接纳，避免诱发保护性阴道痉挛反射。',
        suggestion_text:
          '“刚开始进入的时候请完全由我来掌控速度与深度，你配合我的呼吸静止不要动，等我完全适应。”',
      },
      {
        id: 'rhythm_no_sudden_deep_thrust',
        title: '严禁突击性深插',
        physiological_reason:
          '突发性大行程深顶极易猛烈冲撞阴道穹窿深部的子宫颈外口，尤其是子宫后位女性会引发下腹剧痛、迷走神经性恶心及盆底充血痛。',
        suggestion_text:
          '“请千万不要突然用力到底深顶，我的子宫颈非常敏感脆弱，受大力撞击会像内脏撕裂一样剧痛。”',
      },
      {
        id: 'rhythm_safeword_emergency',
        title: '设置随时可叫停的安全词',
        physiological_reason:
          '预设无歧义的安全词（如“红色/停下”）能彻底剥离拒绝时的羞耻愧疚与解释负担，赋予双方绝对心理安全后盾。',
        suggestion_text:
          '“我们约定一个停下的安全词（比如‘红灯’），任何时候只要一方说出，对方必须立刻无条件停止并温柔退出来。”',
      },
      {
        id: 'rhythm_explicit_switch_consent',
        title: '动作切换前口头知情确认',
        physiological_reason:
          '体位切换时骨盆支撑点与进入轴线瞬间重置，未经预警的体位切换极易导致失控挫伤或引发伴侣情绪解离脱离。',
        suggestion_text:
          '“想换下一个姿势或者调整动作之前，先温柔地问我一句‘这样好不好’，得到我的同意后再慢慢换。”',
      },
    ],
  },
  {
    id: 'category_environment_sensory',
    name: '05 // 环境与感官调适',
    description:
      '优化感官环境降低边缘系统应激警报，后戏照护巩固亲密依恋关系。',
    items: [
      {
        id: 'env_soft_warm_lighting',
        title: '柔和暖光昏暗环境',
        physiological_reason:
          '刺眼的白炽顶光会激发视交叉上核的警觉反应，引发躯体焦虑与容貌身材焦虑；暖色微光环境利于褪黑素与催产素协同分泌。',
        suggestion_text:
          '“我们关掉头顶的大灯，只留一盏床头暖色小暗灯吧，昏暗柔和的氛围能让我放下防备、更加沉浸。”',
      },
      {
        id: 'env_bg_music_relaxation',
        title: '背景轻音乐消除紧张',
        physiological_reason:
          '节奏平缓舒缓的背景声音（如白噪音或轻柔器乐）可遮蔽外界环境杂音与尴尬声响，降低大脑额叶皮层对细微声音的过度警觉。',
        suggestion_text:
          '“放一点节奏轻缓的背景音乐吧，能盖住外面的杂音，也能让我们整个神经节律慢下来，专心感受彼此。”',
      },
      {
        id: 'env_aftercare_towel_hug',
        title: '结束后温热毛巾与紧拥',
        physiological_reason:
          '亲密结束后伴随多巴胺急跌可能出现“性交后烦躁 (PCD)”，温热毛巾擦拭与不少于 5 分钟的紧密相拥可维持催产素水平，建立坚实情感纽带。',
        suggestion_text:
          '“结束后不要马上翻身睡觉或看手机，帮我拿温热毛巾擦拭一下，然后抱紧我躺几分钟好吗，这对我很重要。”',
      },
    ],
  },
];
