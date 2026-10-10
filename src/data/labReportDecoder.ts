/**
 * labReportDecoder.ts — 妇科检查报告通俗解码与过度治疗防坑知识库
 * 遵循 FIGO / ACOG / 默沙东大众版临床循证标准。
 * 纯前端离线点选运行，零化验单数据上传，无原生彩色 Emoji。
 */

export type LabManagementTier =
  | 'normal_physiologic' // 正常生理现象，无需用药/手术
  | 'routine_monitoring' // 建议择期随访观察，无需盲目治疗
  | 'specialist_consult'; // 建议前往正规公立医院妇科门诊规范诊治

export interface LabReportItem {
  id: string;
  name: string;
  en_name: string;
  category: string;
  clinical_definition: string;
  plain_language_meaning: string;
  management_tier: LabManagementTier;
  overtreatment_redflags: string[];
  doctor_questions: string[];
  related_article: string;
}

export interface LabCategoryConfig {
  id: string;
  name: string;
  badge: string;
  description: string;
  items: LabReportItem[];
}

export const LAB_REPORT_CATEGORIES: LabCategoryConfig[] = [
  {
    id: 'discharge',
    name: '白带常规与微生态',
    badge: '01 // DISCHARGE',
    description:
      '阴道分泌物显微镜检查与微生态菌群评估，重点辨识真菌、细菌性阴道病、滴虫感染与正常微生态波动。',
    items: [
      {
        id: 'cleanliness_grade_3_4',
        name: '阴道分泌物清洁度 III~IV 度',
        en_name: 'Vaginal Cleanliness Grade III-IV',
        category: 'discharge',
        clinical_definition:
          '白带涂片高倍显微镜下乳酸杆菌明显减少、杂菌与白细胞（WBC > 15~30/HP）增多，提示阴道微生态失衡或菌群活跃。',
        plain_language_meaning:
          '清洁度主要反映阴道内乳酸杆菌比例与杂菌活跃度，而非严重疾病罪证。若患者没有任何外阴瘙痒、异味、灼痛、豆腐渣或黄脓性白带等不适症状，单纯清洁度 III 度通常属于经期前后、性生活后或免疫微降时的生理性微生态波动，不代表感染妇科病。',
        management_tier: 'routine_monitoring',
        overtreatment_redflags: [
          '[ 避坑提示 ] 零症状下仅凭清洁度 III 度推销各类“阴道深度冲洗”、“臭氧雾化杀菌”、“红光理疗”等高价套餐；高压冲洗反而会冲走保护性乳酸杆菌破坏酸性屏障。',
          '[ 避坑提示 ] 自行盲目购买强效广谱抗生素栓剂或中草药洗液，极易打破微生态防御屏障诱发二重真菌（霉菌）感染。',
        ],
        doctor_questions: [
          '“我现在没有任何瘙痒、异味或灼痛感，这种情况需要用药还是保持清水清洁自行观察？”',
          '“化验单中保护性乳酸杆菌是否偏少？是否有必要检测阴道微生态评估有益菌比例？”',
        ],
        related_article: 'body-bacterial-vaginosis',
      },
      {
        id: 'clue_cells_positive',
        name: '线索细胞阳性 (细菌性阴道病 BV)',
        en_name: 'Clue Cells Positive / Bacterial Vaginosis',
        category: 'discharge',
        clinical_definition:
          '脱落阴道鳞状上皮细胞边缘黏附大量加德纳菌等小短杆菌形成毛玻璃样模糊边缘（占上皮细胞20%以上），结合胺试验阳性与 pH > 4.5 为 BV 的 Amsel 诊断金标准。',
        plain_language_meaning:
          '保护性乳酸杆菌减少，以加德纳菌为主的厌氧菌群过度繁殖。典型表现为灰白色均质、稀薄、带有明显鱼腥臭味的分泌物，性生活后气味往往加重。BV 是阴道内源性菌群紊乱，并非性传播疾病，但需由医生开具规范抗菌药物恢复微生态平衡。',
        management_tier: 'specialist_consult',
        overtreatment_redflags: [
          '[ 避坑提示 ] 被不良机构恐吓“阴道炎会扩散癌变/导致终身不孕”，诱导开具数千元微波理疗或阴道深度灌洗。国际指南首选甲硝唑或克林霉素口服/阴道局部规范抗菌治疗。',
          '[ 避坑提示 ] 盲目要求男性伴侣一同大量服用抗生素；临床循证证实无症状男性伴侣通常不需要常规同步治疗 BV。',
        ],
        doctor_questions: [
          '“针对我的情况，甲硝唑阴道外用栓剂还是口服方案更为推荐？”',
          '“规范抗菌疗程结束后，是否需要补充阴道乳酸杆菌制剂以辅助重建屏障、降低复发率？”',
        ],
        related_article: 'body-bacterial-vaginosis',
      },
      {
        id: 'candida_hyphae_spores',
        name: '真菌假菌丝 / 芽生孢子阳性 (外阴阴道假丝酵母菌病 VVC)',
        en_name: 'Fungal Hyphae & Spores / VVC',
        category: 'discharge',
        clinical_definition:
          '分泌物显微镜检查或革兰染色镜检发现白色念珠菌等假丝酵母菌的假菌丝或出芽孢子，伴随上皮充血损伤，提示念珠菌处于致病侵袭态。',
        plain_language_meaning:
          '念珠菌是人体阴道常见的机会致病菌。在免疫力波动、长期使用抗生素、孕期激素变化或潮湿闷热时，念珠菌菌丝大量生长，引发外阴奇痒无比、灼痛刺痛、红肿，分泌物常呈豆腐渣样或白色凝乳块状。需遵医嘱使用抗真菌药物治疗。',
        management_tier: 'specialist_consult',
        overtreatment_redflags: [
          '[ 避坑提示 ] 听信偏方使用高浓度高锰酸钾坐浴引起化学烧伤，或自行口服阿奇霉素、头孢类抗生素；抗生素杀灭乳酸杆菌反而让真菌爆发更为严重。',
          '[ 避坑提示 ] 购买“私密紧致排毒凝胶”、“中药阴道熏蒸”，非灭菌三无产品会进一步加重阴道黏膜机械和化学损伤。',
        ],
        doctor_questions: [
          '“目前适合单次大剂量克霉唑阴道片还是口服氟康唑治疗？”',
          '“如果过去一年发作达到或超过4次（复发性VVC），后续的长程巩固抑制抗真菌方案应如何规划？”',
        ],
        related_article: 'body-vaginal-yeast-infection',
      },
      {
        id: 'trichomonas_vaginalis',
        name: '阴道毛滴虫阳性 (滴虫性阴道炎 TV)',
        en_name: 'Trichomonas Vaginalis',
        category: 'discharge',
        clinical_definition:
          '白带显微镜湿片镜检观察到梨形、具备多根鞭毛并活跃呈波状运动的阴道毛滴虫滋养体，为明确的性传播寄生原虫感染。',
        plain_language_meaning:
          '由滴虫原虫引起的阴道感染，典型表现为黄绿色、稀薄脓性、泡沫状且有明显恶臭的白带，伴随剧烈外阴瘙痒与排尿疼痛。滴虫主要通过性接触传播，且常寄生于尿道旁腺与前庭大腺，必须规范使用全身口服药物治疗，不可单纯依赖外用洗剂。',
        management_tier: 'specialist_consult',
        overtreatment_redflags: [
          '[ 避坑提示 ] 仅开具外用洗剂局部冲洗而未服用口服全身性抗滴虫药；单纯局部给药无法根除隐藏在尿道旁腺的滴虫，复发率极高。',
          '[ 避坑提示 ] 忽略伴侣同治——滴虫属于严格的性传播感染，性伴侣双方必须同时接受同等剂量规范口服治疗，用药期间严格禁止无保护性生活以防乒乓感染。',
        ],
        doctor_questions: [
          '“是否能同时为我的性伴侣开具足量口服甲硝唑或替硝唑处方同步治疗？”',
          '“服用甲硝唑/替硝唑期间及停药后数天内需要严格避免饮酒（防双硫仑样反应）对吗？”',
        ],
        related_article: 'body-bacterial-vaginosis',
      },
    ],
  },
  {
    id: 'ultrasound',
    name: '妇科经阴道/经腹超声',
    badge: '02 // ULTRASOUND',
    description:
      '子宫形态、内膜厚度、肌壁回声与双侧附件区声像学评估，重点澄清生理性积液与囊肿误区。',
    items: [
      {
        id: 'pelvic_free_fluid',
        name: '盆腔积液 (深径 < 20mm 生理性渗出)',
        en_name: 'Physiological Pelvic Fluid (< 20mm)',
        category: 'ultrasound',
        clinical_definition:
          '超声下子宫直肠陷凹（Douglas窝）探及微量无回声暗区，前后径液性深度通常在 10~20mm 以内，盆腔器官无充血粘连压痛。',
        plain_language_meaning:
          '腹膜本身具备润滑分泌与吸收液体的生理功能。在女性排卵期，卵泡破裂释放的卵泡液会自然流向盆腔最低处；经期少量经血逆流也会形成微量积液（通常在 10~20mm 左右）。只要患者无急性剧烈腹痛、发热或妇科内诊压痛，这完全是正常生理现象，不需要任何吃药打针。',
        management_tier: 'normal_physiologic',
        overtreatment_redflags: [
          '[ 避坑提示 ] 妇科黑心诊所重灾区！恐吓患者“盆腔积液不治会导致不孕、盆腔黏连或腹膜炎”，诱导数千元“盆腔灌肠排毒”、“红光微波理疗”或连续输液打抗生素。',
          '[ 避坑提示 ] 零症状生理性微量积液绝对不需要盲目抽水穿刺化验或预防性消炎吊水。',
        ],
        doctor_questions: [
          '“积液深度在生理正常范围以内吗？目前是否处于排卵期或月经刚结束阶段？”',
          '“内诊检查是否有子宫附件区压痛或宫颈举痛？如果没有任何压痛是否无需任何药物干预？”',
        ],
        related_article: 'body-endometriosis',
      },
      {
        id: 'endometrial_thickness',
        name: '子宫内膜周期性增厚',
        en_name: 'Endometrial Thickness Variation',
        category: 'ultrasound',
        clinical_definition:
          '超声提示子宫内膜双层厚度随雌孕激素水平波动呈动态变化：增殖期由 4~8mm 增生至排卵期三线征，分泌期（黄体期）可增厚至 10~15mm。',
        plain_language_meaning:
          '子宫内膜并非固定不变的静态组织，而是每月随月经周期“脱落变薄-增殖长厚-剥脱来潮”的动态结构。月经前黄体期达到 10~14mm 是为了受精卵着床准备的健康生理表现；评估内膜真实基线厚度的黄金窗口是月经刚干净（第 5~7 天），此时若仍异常增厚 > 10mm 或绝经后 > 4mm 才需进一步排查。',
        management_tier: 'routine_monitoring',
        overtreatment_redflags: [
          '[ 避坑提示 ] 在快来月经前几天做超声测出内膜 12mm，被非正规机构恐吓“内膜过厚癌变风险高，需紧急刮宫手术”；脱离月经周期的单次内膜测量毫无诊断意义。',
          '[ 避坑提示 ] 推销“暖宫精油按摩”、“卵巢保养贴片”宣称能调理内膜厚度，均无循证医学支持。',
        ],
        doctor_questions: [
          '“本次超声是在月经周期的第几天检查的？内膜厚度与当期激素阶段是否吻合？”',
          '“是否有必要在下次月经刚完全干净后的第 5~7 天复查超声，以评估内膜剥脱彻底后的真实基线厚度？”',
        ],
        related_article: 'abnormal-uterine-bleeding',
      },
      {
        id: 'uterine_myoma_hypoechoic',
        name: '子宫肌壁低回声结节 (子宫肌瘤)',
        en_name: 'Uterine Leiomyoma / Fibroid',
        category: 'ultrasound',
        clinical_definition:
          '超声下子宫肌层内探及圆形或类圆形低回声/等回声结节，边界清，周边见假包膜环状血流信号，为育龄期女性极常见的子宫平滑肌良性增生。',
        plain_language_meaning:
          '子宫肌瘤是育龄期女性最常见的良性肿瘤。绝大多数体积较小（< 3~5cm）、生长在肌壁间或浆膜下的肌瘤终身无症状，恶变几率极低（远小于 0.5%）。若无严重月经量增多致贫血、尿频压迫或短期内迅速增大，通常只需每 6~12 个月定期超声复查随访，无需开刀或服药。',
        management_tier: 'routine_monitoring',
        overtreatment_redflags: [
          '[ 避坑提示 ] 声称吃“消瘤神丹”、“中药活血茶包”或做“卵巢保养”可以消除肌瘤；目前没有任何口服药物能安全彻底根除肌瘤。',
          '[ 避坑提示 ] 对无症状且小于 4cm 的良性小肌瘤极力劝说开腹或微创手术切除，导致不必要的麻醉与子宫瘢痕创伤。',
        ],
        doctor_questions: [
          '“肌瘤的具体生长位置是黏膜下、肌壁间还是浆膜下？对宫腔内膜形态是否有压迫变形？”',
          '“以目前的结节大小与血流表现，是否每 6~12 个月定期超声监测即可？”',
        ],
        related_article: 'abnormal-uterine-bleeding',
      },
      {
        id: 'ovarian_anechoic_cyst',
        name: '卵巢无回声区 (生理性滤泡/黄体囊肿)',
        en_name: 'Physiological Ovarian Cyst (Follicular/Corpus Luteum)',
        category: 'ultrasound',
        clinical_definition:
          '单侧卵巢见圆形囊性无回声暗区，直径多在 20~50mm，壁薄平滑，透声清亮，后方回声增强，多为卵泡未破裂或排卵后黄体内积液形成。',
        plain_language_meaning:
          '卵巢每月排卵过程中均会形成卵泡或黄体。未破裂卵泡或排卵后黄体积液形成的生理性囊肿极为普遍，通常会在 2~3 个月经周期内随激素波动自行萎缩吸收并完全消失。在未经 2~3 个月经周期随访复查前，切勿过早恐慌。',
        management_tier: 'routine_monitoring',
        overtreatment_redflags: [
          '[ 避坑提示 ] 首次查出 3~4cm 囊肿便急促建议患者住院进行“腹腔镜切除手术”或“穿刺抽液”；绝大多数属于生理性囊肿，下次月经干净后复查即可自然消失。',
          '[ 避坑提示 ] 兜售昂贵的清热解毒、消除囊肿中草药包，囊肿消失是人体的自然吸收过程，与药物无因果关联。',
        ],
        doctor_questions: [
          '“该囊肿壁厚与透声特征是否符合良性生理性囊肿的表现？”',
          '“建议在 1~2 次月经来潮干净后的第 5 天复查超声对比囊肿是否自然缩小或消失吗？”',
        ],
        related_article: 'normal-menstrual-cycle',
      },
    ],
  },
  {
    id: 'cervical',
    name: '宫颈癌前筛查 TCT+HPV',
    badge: '03 // CERVICAL SCREENING',
    description:
      '液基薄层细胞学 (TCT) 与人乳头瘤病毒 (HPV) 分子分型联合筛查，破除宫颈糜烂与病毒转阴骗局。',
    items: [
      {
        id: 'cervical_columnar_ectopy',
        name: '宫颈糜烂样改变 (生理性柱状上皮外翻)',
        en_name: 'Cervical Ectropion / Columnar Ectopy',
        category: 'cervical',
        clinical_definition:
          '妇科视诊宫颈外口呈红色颗粒状粗糙区域，病理本质为宫颈管内单层柱状上皮受雌激素影响向外延伸，因薄层上皮透出间质血管肉眼呈红润糜烂样。',
        plain_language_meaning:
          '我国妇产科学教材早已废除“宫颈糜烂”这一疾病名称！它根本不是真正病理意义上的糜烂或溃疡，而是年轻女性雌激素充沛时的正常生理现象（柱状上皮外翻）。只要 TCT 细胞学和 HPV 病毒筛查正常且无接触性出血，不需要做任何手术或上药治疗。',
        management_tier: 'normal_physiologic',
        overtreatment_redflags: [
          '[ 避坑提示 ] 妇科民营黑心机构第一大陷阱！恐吓“宫颈糜烂度数高会变成宫颈癌/导致不孕”，诱导患者花费数千元接受激光、微波、冷冻或 LEEP 刀物理手术，术后瘢痕易致宫颈管狭窄粘连影响分娩生育。',
          '[ 避坑提示 ] 购买“宫颈排毒丸”、“排毒凝胶”，这类非药品腐蚀性栓剂极易造成阴道和宫颈化学灼伤。',
        ],
        doctor_questions: [
          '“我的宫颈癌筛查（TCT 与高危 HPV）结果是否均为阴性？若阴性是否完全不需要物理治疗？”',
          '“如果没有接触性异常流血，是否只需按照国家指南进行定期常规筛查即可？”',
        ],
        related_article: 'body-hpv-vaccine-screening',
      },
      {
        id: 'tct_nilm_negative',
        name: 'TCT: 未见上皮内病变或恶性病变 (NILM)',
        en_name: 'TCT Negative for Intraepithelial Lesion (NILM)',
        category: 'cervical',
        clinical_definition:
          '液基薄层细胞学标本满意，显微镜视野内脱落宫颈鳞状细胞与腺细胞形态结构正常，未观察到不典型增生、低度/高度病变或恶性肿瘤细胞。',
        plain_language_meaning:
          '宫颈防癌细胞学检查完全过关的最佳健康报告！表明宫颈脱落细胞形态健康，无癌前病变或癌细胞。报告单常备注“轻度炎症反应性细胞改变”，这是阴道正常微环境的微观共存现象，完全无需紧张焦虑，保持健康生活与正常筛查周期即可。',
        management_tier: 'normal_physiologic',
        overtreatment_redflags: [
          '[ 避坑提示 ] 针对报告单注明的“轻度炎症反应”开具大量口服消炎药、高价阴道栓剂或要求冲洗理疗；阴道本身即是有菌微环境，轻度炎症细胞并不等同于妇科疾病。',
          '[ 避坑提示 ] NILM 且 HPV 阴性的低风险人群被某些体检机构劝说每隔三到六个月就频繁重复筛查。',
        ],
        doctor_questions: [
          '“结合我的年龄与本次阴性筛查结果，下一次 TCT 联合复查建议定在几年后？”',
          '“报告单备注的良性反应性改变是否无需任何额外用药？”',
        ],
        related_article: 'body-hpv-vaccine-screening',
      },
      {
        id: 'tct_asc_us_equivocal',
        name: 'TCT: 非典型鳞状细胞意义未明 (ASC-US)',
        en_name: 'Atypical Squamous Cells of Undetermined Significance (ASC-US)',
        category: 'cervical',
        clinical_definition:
          '显微镜下部分鳞状上皮细胞形态呈轻度核异质改变，但未达到低度鳞状上皮内病变 (LSIL) 的判读阈值，多由局部普通炎症反应刺激、宫颈萎缩或早期 HPV 感染引起。',
        plain_language_meaning:
          '检验技师在显微镜下看到了少数“形态略有异常但性质暂无法明确”的细胞，这既不是癌，也不代表一定有癌前病变。绝大多数 ASC-US 仅是由普通局部炎症刺激造成的良性改变。此时关键看高危型 HPV 结果：若高危 HPV 为阴性，1 年后复查 TCT 即可；若高危 HPV 阳性，则需转诊阴道镜下进一步确认。',
        management_tier: 'routine_monitoring',
        overtreatment_redflags: [
          '[ 避坑提示 ] 一看到 ASC-US 就被恐吓“马上要变癌了”，直接在无病理活检前提下实施大范围宫颈锥切手术；临床指南明确必须先做 HPV 分流或阴道镜评估。',
          '[ 避坑提示 ] 推销昂贵的中药抗癌敷贴或所谓抗癌私密排毒套餐，制造精神焦虑敛财。',
        ],
        doctor_questions: [
          '“我的高危型 HPV 检查是阴性还是阳性？是否需要进一步预约阴道镜检查，还是 1 年后复查？”',
          '“如果属于局部轻度炎症刺激引起的细胞反应，是否需要针对性对症消除炎症刺激？”',
        ],
        related_article: 'body-hpv-vaccine-screening',
      },
      {
        id: 'hpv_16_18_positive',
        name: '高危型 HPV 16 / 18 型阳性',
        en_name: 'High-Risk HPV Types 16 / 18 Positive',
        category: 'cervical',
        clinical_definition:
          'PCR 核酸分子检测证实感染高危型人乳头瘤病毒 16 型或 18 型 DNA。这两种型别是宫颈癌及高级别癌前病变最主要的致病元凶（致病占比约 70%）。',
        plain_language_meaning:
          '检测到与宫颈癌关联度最高的两种高危病毒型别。但请务必明确：感染病毒绝不等于得了宫颈癌！从单纯病毒感染进展为浸润癌通常需要 8~10 年以上持续存在的高级别病变。指南规范要求：只要 16 或 18 型阳性，不论 TCT 是否正常，均必须前往公立专科医院接受阴道镜检查及多点活检评估宫颈组织真实情况。',
        management_tier: 'specialist_consult',
        overtreatment_redflags: [
          '[ 避坑提示 ] 花费数千上万元购买所谓的“HPV 靶向转阴凝胶”、“抗体敷料”、“清毒洗剂”；世卫组织与权威妇产科指南明确证实：全球尚无任何药物能直接杀灭清除 HPV 病毒！',
          '[ 避坑提示 ] 绕过公立医院阴道镜活检病理金标准，直接在非正规机构盲目进行宫颈表面激光烧灼或电熨术。',
        ],
        doctor_questions: [
          '“我需要尽快预约阴道镜检查并在可疑区域取病理活检明确诊断对吗？”',
          '“阴道镜检查前 48 小时内需要严格避免性生活、阴道冲洗和阴道塞药对吗？”',
        ],
        related_article: 'body-hpv-vaccine-screening',
      },
      {
        id: 'hpv_other_high_risk_positive',
        name: 'HPV 其他高危型阳性 (非 16/18 型)',
        en_name: 'Other High-Risk HPV Types Positive (Non 16/18)',
        category: 'cervical',
        clinical_definition:
          '检测到除 16/18 型以外的其他高危型别（如 31、33、45、52、58 等）阳性。其致癌风险显著低于 16/18 型，多数表现为一过性感染。',
        plain_language_meaning:
          '在成年健康女性中非常多见，类似宫颈经历了一次微型感冒。约 80%~90% 的 HPV 感染会在 8~24 个月内依靠人体自身免疫力自然清除转阴。临床处置关键看 TCT：若 TCT 完全正常，无需任何吃药、输液或手术，12 个月后复查即可；若 TCT 发现异常细胞，才需预约阴道镜检查。',
        management_tier: 'routine_monitoring',
        overtreatment_redflags: [
          '[ 避坑提示 ] 恐慌性消费高发区！开具多个疗程的“重组人干扰素凝胶”或推销昂贵红光照射；临床循证证实自身免疫力才是清除病毒的关键，没有任何神药保证快速转阴。',
          '[ 避坑提示 ] 恐慌到不敢与家人同桌吃饭或共用马桶；HPV 不通过消化道、共用餐具或马桶垫传播，日常性生活全程正确使用避孕套可减少交叉病毒载量。',
        ],
        doctor_questions: [
          '“我的 TCT 结果是否完全正常（NILM）？如果正常，是否建议 12 个月后再复查双筛？”',
          '“在等待自身免疫转阴期间，保持规律作息、戒烟、运动与减轻压力对病毒清除的作用有多大？”',
        ],
        related_article: 'body-hpv-vaccine-screening',
      },
    ],
  },
  {
    id: 'pregnancy_endocrine',
    name: '早孕与内分泌血液指标',
    badge: '04 // PREGNANCY & ENDOCRINE',
    description:
      '尿早孕定性与血清 β-hCG 定量翻倍动力学，科学评估早期胚胎活力并警惕异位妊娠红旗。',
    items: [
      {
        id: 'urine_hcg_weak_positive',
        name: '尿早孕试纸弱阳性 / 一深一浅',
        en_name: 'Urine hCG Weak Positive / Faint Line',
        category: 'pregnancy_endocrine',
        clinical_definition:
          '胶体金法免疫层析尿试纸检测人绒毛膜促性腺激素 (hCG)，检测线 (T线) 显色浅于对照线 (C线)，提示尿液 hCG 浓度接近试纸检出限（通常 10~25 mIU/mL）。',
        plain_language_meaning:
          '试纸检测到了微量 hCG，常见于受精卵着床极早期（受精后 7~10 天）、饮水过多尿液被稀释，或读取时间过长出现的蒸发线。尿试纸仅为定性初筛，不能确认胚胎着床位置（宫内还是宫外），亦无法评估胚胎发育质量，建议隔日使用晨尿复测或赴公立医院抽血检测定量 β-hCG。',
        management_tier: 'routine_monitoring',
        overtreatment_redflags: [
          '[ 避坑提示 ] 仅凭试纸浅粉色杠就在停经仅 2~3 天时急切做超声；此时孕囊极小经阴道超声也极难看清，容易引发不必要的“宫外孕”恐慌。通常停经 5~6 周以上（血 hCG > 1500~2000 IU/L）超声才可见孕囊。',
          '[ 避坑提示 ] 盲目购买昂贵的中医保胎汤药或私自大剂量口服黄体酮；未排除宫外孕前盲目用药可能延误急腹症救治。',
        ],
        doctor_questions: [
          '“建议抽静脉血定量测定血清 β-hCG 与孕酮以建立精确基线吗？”',
          '“目前若无腹痛和出血，建议在停经多少天后再预约首次早孕超声检查？”',
        ],
        related_article: 'normal-menstrual-cycle',
      },
      {
        id: 'serum_beta_hcg_doubling',
        name: '血清 β-hCG 翻倍规律与数值',
        en_name: 'Serum β-hCG Dynamics & Doubling Time',
        category: 'pregnancy_endocrine',
        clinical_definition:
          '静脉全血免疫化学发光法定量测定游离及结合态 β-hCG 浓度。早期正常宫内妊娠（< 2000 mIU/mL）血清浓度通常呈现每 48 小时增长 66%~100%（约每 2 天翻倍）的动力学规律。',
        plain_language_meaning:
          '血清 β-hCG 是评估早孕胚胎活力最精准客观的血液指标。健康宫内妊娠早期数值每 48 小时应大幅上升。如果 48 小时增长迟缓停滞、数值不升反降，或伴随突发单侧撕裂样下腹痛、阴道持续淋漓暗红出血，必须高度警惕异位妊娠（宫外孕）或流产风险，需紧急就医排查。',
        management_tier: 'specialist_consult',
        overtreatment_redflags: [
          '[ 避坑提示 ] 脱离 48 小时动态对比单看单次抽血绝对数值妄下断言；个体着床时间存在早晚差异，单次绝对值范围跨度极大。',
          '[ 避坑提示 ] β-hCG 翻倍良好但孕酮稍低时，在非正规诊所接受大剂量黄体酮针剂注射盲目保胎；循证医学明确表明无流产病史的健康孕妇不能从盲目黄体酮支持中获益。',
        ],
        doctor_questions: [
          '“两次抽血化验是否严格符合间隔 48 小时的动态对比标准？”',
          '“如果出现下腹剧痛或阴道出血等危险信号，应如何最快就近前往急诊排查异位妊娠？”',
        ],
        related_article: 'abnormal-uterine-bleeding',
      },
    ],
  },
];
