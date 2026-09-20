# corpus/schemas · 四类卡片 Schema 说明

Wave1 产出的所有卡片必须用对应 JSON Schema 校验通过后再入库。本目录四个文件：

| 文件 | 卡片类型 | 覆盖量 |
|---|---|---|
| `brief-card.schema.json` | 简卡 brief | 全量 729 篇 |
| `deep-card.schema.json` | 深卡 deep | ≥80 篇（Wave1） |
| `playbook-card.schema.json` | 方法卡 playbook | 方法原型库（Wave1） |
| `track-card.schema.json` | 赛道档案 track | 按年-赛道 |

## 一、简卡 brief（729 篇全覆盖）

| 字段 | 含义 |
|---|---|
| `paper_id` | 自建编号 `年_赛道_文件名`，如 `2024_A_A24102940057` |
| `year` / `track` / `title` | 年份、赛道 A–F、论文题目 |
| `award_level` / `award_confidence` | 奖级（一二等/优秀论文/待确认）与置信度 |
| `problem_count` | 子问个数 |
| `task_types` | 任务类型（优化/预测/评价/分类…） |
| `models_and_algorithms` | 模型算法清单 |
| `data_modality` / `data_scale` | 数据模态与规模 |
| `validation_methods` | 检验方法 |
| `figure_count` / `figure_types` | 图数量与类型 |
| `innovation_points` | 1–3 条创新点 |
| `page_count` / `section_structure` | 页数与章节结构 |
| `source_locations` | 关键内容页码定位 |
| `confidence` / `notes` | 整体置信度与备注 |

## 二、深卡 deep（≥80 篇）

在简卡全部字段基础上增加：

| 字段 | 含义 |
|---|---|
| `per_question_method_chain` | 逐问 baseline→主模型→改进，含“为什么换” |
| `key_formulas_and_assumptions` | 关键公式与假设 |
| `objective_function` | 目标函数 |
| `evaluation_metrics` | 评估指标 |
| `algorithm_details_and_complexity` | 算法细节与复杂度 |
| `independent_validation_design` | 独立验证设计 |
| `sensitivity_robustness_ablation` | 敏感性/稳健性/消融 |
| `abstract_deconstruction` | 摘要首句/方法句/结果句/数字呈现解构 |
| `figure_narrative_order` | 图表叙事顺序 |
| `judge_high_score_reasons` | 评委高分理由 |
| `reusable_patterns` | 可复用范式 |
| `transferable_ability_card_candidates` | 可迁移能力卡候选 |
| `page_locations` | 精确到页的定位 |

## 三、方法卡 playbook

| 字段 | 含义 |
|---|---|
| `card_id` / `archetype` | 卡编号与原型名 |
| `trigger_criteria` | 什么题该用这张卡 |
| `input_units` | 输入单位/量纲 |
| `modeling_skeleton` | 建模骨架 |
| `algorithm_menu[]` | 每条：`name`/`when`(适用条件)/`param_source`/`complexity`/`common_failure` |
| `baseline_to_improvement_chain` | 基线到改进链 |
| `validation_playbook` | 验证套路 |
| `high_score_evidence_modules` | 高分证据模块 |
| `pitfalls` | 常见坑 |
| `huawei_case_locations` | 案例 `[年-赛道-paper_id-页码]` |
| `adjacent_method_distinction` | 与相邻方法区别 |
| `evidence_level` | A=获奖深卡支持 / B=简卡思路支持 / C=推断 |
| `source_count` | 引用来源数 |

## 四、赛道档案 track

| 字段 | 含义 |
|---|---|
| `year` / `track` | 年与赛道 |
| `topic` / `task_breakdown` | 主题与子问拆解 |
| `data_modality` / `data_scale` | 数据模态与规模 |
| `official_constraints` / `submission_format` | 官方约束与提交格式 |
| `archetype_mapping` | 方法原型映射 |
| `method_frequency` | 方法→出现篇数 |
| `representative_papers` | 代表 paper_id 列表 |
| `recommended_route` / `alternative_routes` | 推荐路线与备选 |
| `pitfalls` / `target_audience` / `sources` | 坑/受众/来源 |

## 校验

Wave1 产出卡片后，用 JSON Schema 校验（`jsonschema` 库或在线校验），
不通过不得入库。
