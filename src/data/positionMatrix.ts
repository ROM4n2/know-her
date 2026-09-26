/**
 * positionMatrix.ts — 8 大循证性生理力学体位数据集
 * 基于女性盆底解剖学、进入轴线几何学与性高潮对齐技术 (CAT) 循证构建。
 * 遵循 Academic Modern Editorial 纸墨美学，全量关联站内深度循证科普长文。
 */

export interface SexualPosition {
  id: string;
  name: string;
  en_name: string;
  category: 'female_control' | 'intimacy_close' | 'low_energy' | 'deep_penetration';
  clitoral_access: 'high' | 'moderate' | 'low';
  cervical_collision_risk: 'low' | 'moderate' | 'high';
  energy_expenditure: 'low' | 'moderate' | 'high';
  pelvic_support_advice: string;
  coital_angle_desc: string;
  pros: string[];
  cons: string[];
  communication_tip: string;
  related_article: string;
}

export const POSITION_METHODS: SexualPosition[] = [
  {
    id: 'woman-on-top-forward',
    name: '正向女上位',
    en_name: 'Missionary On Top / Coital Alignment',
    category: 'female_control',
    clitoral_access: 'high',
    cervical_collision_risk: 'low',
    energy_expenditure: 'moderate',
    pelvic_support_advice:
      '女性可略微前倾躯干，将耻骨联合紧贴伴侣耻骨联合处；若膝部受力不适，可在膝下垫置 5~10cm 记忆海绵软垫分散重力压力。',
    coital_angle_desc:
      '骨盆前倾约 30°~45°，躯干前倾贴合。进入角度更贴近阴道前壁与阴蒂内角支柱，避开宫颈垂直冲撞。',
    pros: [
      '女性拥有对插入深度、抽插频率与摆动角度的 100% 自主控制权',
      '耻骨紧密贴合利于持续微磨阴蒂头及前庭球海绵体',
      '可有效避免伴侣盲目猛烈撞击引发的宫颈深部性交痛',
    ],
    cons: [
      '女性大腿四头肌与膝关节持续承重，维持时间过长易诱发疲劳',
      '若润滑不足，盆底剧烈移动易引发前庭皮肤摩擦擦伤',
    ],
    communication_tip:
      '“让我来主导节奏和下沉深度，身体前倾贴紧时感觉更舒适安全。”',
    related_article: 'pleasure-woman-on-top-mechanics',
  },
  {
    id: 'woman-on-top-reverse',
    name: '反向女上位',
    en_name: 'Reverse Cowgirl / Posterior Alignment',
    category: 'female_control',
    clitoral_access: 'moderate',
    cervical_collision_risk: 'low',
    energy_expenditure: 'high',
    pelvic_support_advice:
      '背向伴侣跨坐，伴侣双腿并拢或微屈提供背向大腿支撑；女性双手可支撑于伴侣小腿或床面维持重心平衡。',
    coital_angle_desc:
      '背向纵轴入径，进入角度偏向阴道后壁；女性直立或微后仰时阴道轴线呈 45° 倾角。需严格控制下坐幅度避免阴茎根部意外折角。',
    pros: [
      '提供全新视觉与背部抚触维度，女性完全主导垂直起伏深度',
      '避开阴道前壁尿道周围敏感区，适合前壁敏感或易尿意紧迫者',
      '伴侣双手自由，可从后方辅助抚触臀部与腰部',
    ],
    cons: [
      '耻骨间无自然研磨接触，需单手外置震动器或伴侣手部协助方可触及阴蒂',
      '重心控制难度较高，若重心失控失准存在阴茎韧带损伤风险',
    ],
    communication_tip:
      '“动作放慢一点，等我调整好坐下的重心与节奏，不要突然向上顶。”',
    related_article: 'pleasure-woman-on-top-mechanics',
  },
  {
    id: 'spooning-lateral',
    name: '侧卧匙羹式',
    en_name: 'Spooning / Lateral Coitus',
    category: 'low_energy',
    clitoral_access: 'high',
    cervical_collision_risk: 'low',
    energy_expenditure: 'low',
    pelvic_support_advice:
      '双方同向侧卧微屈膝，女性双腿之间可夹入一枚长条薄枕以稳定骨盆倾角，同时防止大腿内侧过度压迫。',
    coital_angle_desc:
      '从身体后侧平行轴线平缓进入，夹角约 15°~30°。阴茎沿阴道轴线平滑贴合滑行，对宫颈外口的垂直压力降至最低。',
    pros: [
      '全身骨骼肌肉完全放松，体能消耗极低，极其适合疲劳、经期前后或孕期伴侣',
      '伴侣胸口紧贴女性后背，躯体包裹感与心理安全感极高',
      '女性前方空间充裕，双手或伴侣右手可自如环抱并直接刺激阴蒂',
    ],
    cons: [
      '受限于侧卧活动度，抽插幅度与冲刺冲程较短',
      '体位移动受限，若骨盆高度未对齐可能造成进入初始阶段轻微困难',
    ],
    communication_tip:
      '“我们并排侧躺慢慢抱在一起，我腿间夹个枕头，这样最轻松舒适。”',
    related_article: 'pleasure-side-lying-spooning',
  },
  {
    id: 'scissors-oblique',
    name: '侧卧剪刀交叉式',
    en_name: 'Scissors / Lateral Oblique',
    category: 'intimacy_close',
    clitoral_access: 'high',
    cervical_collision_risk: 'low',
    energy_expenditure: 'low',
    pelvic_support_advice:
      '双方呈斜角 45° 面对面交错侧卧，彼此一条腿交搭在对方腰胯上方，骨盆紧密扣合形成稳固的三角力学支点。',
    coital_angle_desc:
      '斜切对角进入轴线，伴侣大腿根部与女性耻骨联合形成交错杠杆。抽插转变为骨盆间的斜向挤压与持续平移研磨。',
    pros: [
      '面对面近距离注视与亲吻，面部表情知情反馈最直接',
      '大腿内侧与骨盆交错锁合，在不消耗体能的前提下提供深层包覆挤压感',
      '骨盆交错运动带来极其持续的前庭与阴蒂基底压迫刺激',
    ],
    cons: [
      '对双侧髋关节柔韧度有一定要求，髋关节活动受限者易感酸胀',
      '摆动冲程受限，主要依靠骨盆微幅研磨而非大幅抽拉',
    ],
    communication_tip:
      '“把腿交错搭在我腰上，我们看着对方慢慢磨，不用大幅度抽动。”',
    related_article: 'pleasure-side-lying-spooning',
  },
  {
    id: 'modified-cat',
    name: '经典改良男上位',
    en_name: 'Modified Missionary / CAT',
    category: 'intimacy_close',
    clitoral_access: 'high',
    cervical_collision_risk: 'low',
    energy_expenditure: 'moderate',
    pelvic_support_advice:
      '伴侣身体整体向前上方平移数厘米，阴茎根部耻骨紧紧压合女性阴蒂包皮部位；伴侣用手肘与胸膛承重，避免重力完全倾轧女性胸腹。',
    coital_angle_desc:
      '同轴平滑贴合，伴侣骨盆向上向前微移。抽动改变为同向同步的微幅剪切与前后研磨运动，完全摒弃进出活塞式抽插。',
    pros: [
      '医学界公认的女性性高潮对齐技术 (CAT)，使 85% 以上女性在插入中获得连续阴蒂摩擦',
      '躯体全面贴合，胸腹温热接触，心跳与呼吸生理共振显著',
      '避免活塞式猛烈抽插导致的黏膜磨损与干燥',
    ],
    cons: [
      '伴侣需依靠双肘与膝盖精准支撑体重，维持核心肌肉平移研磨较耗体力',
      '对伴侣动作克制度要求极高，若退回本能大开大合抽插则失去 CAT 优势',
    ],
    communication_tip:
      '“身体往前移一点，把重心放在手肘上，贴紧我耻骨前后慢磨，不要拉出来。”',
    related_article: 'pleasure-cat-technique-alignment',
  },
  {
    id: 'elevated-pelvis-wedge',
    name: '骨盆垫枕高迎角式',
    en_name: 'Elevated Pelvis / Wedge Pillow',
    category: 'deep_penetration',
    clitoral_access: 'moderate',
    cervical_collision_risk: 'moderate',
    energy_expenditure: 'low',
    pelvic_support_advice:
      '在女性骶尾骨与臀部正下方垫入 10~15cm 高硬质梯形枕或紧实折叠毛毯，将骨盆水平抬高 20°~30°。',
    coital_angle_desc:
      '抬升骨盆使阴道轴线呈陡峭向后下倾斜迎角。重力使阴道后穹窿充分自然展平，深度提升同时有效避开前壁尿道直击。',
    pros: [
      '骨盆自然前展受托，女性腰肌与臀肌零负荷放松，显著消除腰骶酸痛',
      '微调进入仰角，使伴侣阴茎自然顺滑滑入，极为契合子宫前位女性',
      '仰角抬高使体液与润滑剂不易迅速流失，前庭湿润度保持更持久',
    ],
    cons: [
      '若子宫为过度后倾后屈位，过深进入可能轻微触碰后穹窿敏感区',
      '枕头硬度需充足，软枕容易塌陷导致骨盆支撑力丧失',
    ],
    communication_tip:
      '“在臀下垫个结实的枕头，这样我腰部彻底放松，进入的角度也顺畅温和。”',
    related_article: 'pleasure-arousal-time-physiology',
  },
  {
    id: 'modified-rear-entry',
    name: '改良屈膝后入式',
    en_name: 'Modified Rear-entry / Low Incline',
    category: 'deep_penetration',
    clitoral_access: 'moderate',
    cervical_collision_risk: 'moderate',
    energy_expenditure: 'moderate',
    pelvic_support_advice:
      '女性屈膝跪姿，胸口与前臂平贴床面大枕头上（胸膝卧位降低躯干倾角），大腿与躯干保持 90°~105° 钝角缓冲。',
    coital_angle_desc:
      '从后方低倾角进入。躯干下压使子宫自然由于重力向前腹壁前移下垂，扩大后穹窿安全缓冲空间，避免对宫颈外口形成顶角撞击。',
    pros: [
      '相比传统垂直跪姿后入，胸膝低俯角显著降低了宫颈强力对冲的深部疼痛风险',
      '伴侣进入阻力小，阴道容受性良好，深度充实感明确',
      '女性前方空出双手，极易自如使用手指或震动器进行外在阴蒂联合刺激',
    ],
    cons: [
      '女性跪姿膝关节仍有接触压强，膝盖骨敏感者需铺设软垫保护',
      '若伴侣推力过猛且未沟通深度，依然存在过度深插的隐患',
    ],
    communication_tip:
      '“我把胸口贴在枕头上趴低一点，你从后面慢慢进，不要到底，保持浅中层节奏。”',
    related_article: 'pleasure-rear-entry-angles',
  },
  {
    id: 'prone-flat-rear',
    name: '俯卧平躺后位入径',
    en_name: 'Prone Rear-entry / Flat Doggy',
    category: 'low_energy',
    clitoral_access: 'low',
    cervical_collision_risk: 'low',
    energy_expenditure: 'low',
    pelvic_support_advice:
      '女性完全平趴于床面，下腹耻骨下可垫入约 5cm 薄枕抬高骨盆微隙；双腿自然伸直并拢或微张。伴侣覆于其上轻缓进入。',
    coital_angle_desc:
      '平卧极窄入径角度。女性双腿并拢收缩阴道外口横截面积，进入轴线水平贴合阴道后壁，有效阻止阴茎过度深插触碰宫颈。',
    pros: [
      '双腿并拢显著增强盆底与阴道外口物理夹紧感，摩擦力饱满而无需过度深插',
      '女性全身躯干贴床零肌肉耗能，彻底规避跪姿膝盖韧带酸痛与腰部疲劳',
      '深度天然受限受控，是子宫后位或易发深部性交痛伴侣最安全可靠的后位替代选择',
    ],
    cons: [
      '女性俯卧平贴床面，外力触及阴蒂难度较高，难以直接进行阴蒂手动刺激',
      '若伴侣体重完全压迫女性背部可能造成呼吸局促，伴侣需以手肘支撑部分自重',
    ],
    communication_tip:
      '“我们平趴着试，双腿并拢一点会更紧致，而且我的肚子和宫颈完全不会痛。”',
    related_article: 'pleasure-rear-entry-angles',
  },
];
