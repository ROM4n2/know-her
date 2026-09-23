## 变更说明

<!-- 简述本 PR 改了什么、为什么改。 -->

## 关联 Issue

<!-- Closes #xxx（如有） -->

## 审核自查清单（四段审核 · ADR-0001 D2/D5）

> 四段审核全部勾选方可合并；医学准确性席位未就位时按 D4 如实标记"未获医学复审"降级，**不得留空、不得代勾**。

### 1. 来源核验（reviewed_source）

- [ ] `source_url` 指向原始权威来源，非转载/二手汇编
- [ ] `source_snapshot_date` 已更新为本次取证日期（YYYY-MM-DD）
- [ ] 正文内容与来源一致，未引入来源之外的断言

### 2. 版权检查（reviewed_copyright）

- [ ] 符合"外链 + 短摘要"原则，未转载原文全文
- [ ] 摘要为原创改写，引用已标注出处

### 3. 医学复审状态标记（reviewed_medical）

- [ ] `reviewed_medical` 已明确填写 `true` / `false`（不可留空）
- [ ] 若 `false`：页面将显示"未获医学复审"降级横幅（D4），且 `review_status` 未标为绕过降级的已发布态
- [ ] 若 `true`：`review_date` 已填写，`review_interval_months` 在 6–24 之间

### 4. 敏感度与红旗清单（reviewed_sensitivity）

- [ ] `red_flags` 急症红旗清单已填写（可为空数组但字段必填），指征来源为 WHO/ACOG/中华妇产科指南
- [ ] 正文为第三人称枚举，无第二人称条件句、无个体化建议（`has_individual_advice: false`）
- [ ] 年龄提示与免责声明组件未被移除或遮挡

## 构建验证

- [ ] `pnpm check`（astro check）零错误
- [ ] `pnpm build` 通过
