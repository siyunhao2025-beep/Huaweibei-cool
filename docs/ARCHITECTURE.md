# docs/ARCHITECTURE.md · 仓库架构

## 1. 目录结构

```
Huaweibei-cool/
├─ SKILL.md                  # 入口：启动路由 + 模块表 + 硬规则 + 脚本索引
├─ modules/                  # 21 个任务契约模块
│  ├─ workflow.md phases.md kickoff-audit.md track-selection.md
│  ├─ problem-typing.md solving.md validation.md evidence-ledger.md
│  ├─ figures-interface.md technical-roadmap.md paper-writing.md abstract.md deai-writing.md
│  ├─ innovation.md submission.md review-panel.md polishing.md
│  └─ change-management.md distillation.md matlab-conventions.md training.md
├─ playbooks/                # 8 原型 51 方法卡 + INDEX + match_rules.json
│  ├─ optimization/ evaluation/ prediction/ classification-cv/
│  ├─ mechanism/ signal/ spatial-graph/ simulation/
├─ tracks/                   # 2022–2025 共 24 题档案（按年/字母）
├─ corpus/
│  ├─ cards/
│  │  ├─ brief/{年}.json      # 729 简卡
│  │  ├─ deep/{paper_id}.json # 80 深卡
│  │  ├─ AGGREGATE_STATS.md S3_star_patterns.md S4_recent_trends.md
│  ├─ problem_analysis/       # innovation_algorithms/ai_prompts/CODE_INVENTORY
│  ├─ method_frequency.json track_archetype_matrix.json papers_index.*
├─ scripts/                  # 工程脚本 + 5 个新脚本
├─ assets/
│  ├─ paper-template/        # gmcmthesis 模板 + page_targets.json
│  └─ scaffold/               # 比赛工作目录骨架
├─ config/                    # contest.json + schema
├─ skills/academic-figure/    # 绘图子 skill（vendored，勿改）
└─ docs/                     # 本文档集 + UPSTREAM + TRACK_ARCHIVE
```

## 2. 数据流

```
729 篇获奖 PDF（只读外部）
  → corpus_build.py / corpus_cards.py
  → corpus/cards/brief(729) + deep(80)
  → 统计聚合：AGGREGATE_STATS / S3 / S4 / method_frequency
  → 蒸馏：playbooks(51 方法卡) + tracks(24 题档案)
  → 工程化：modules(21 契约) + scripts(门禁/匹配/评审脚本)
  → 比赛日：SKILL.md 路由 → 用户按 phases 执行
```

## 3. 模块依赖（谁引用谁）

- `workflow.md` 是总地图 → 引 `phases.md` / `track-selection.md` / `solving.md`。
- `problem-typing.md` → 调 `playbook_match.py` → `playbooks/`。
- `solving.md` → `playbooks/<原型>/` 方法卡。
- `validation.md` → 被 `phases.md` P3 引用。
- `abstract.md` / `innovation.md` → 引 `corpus/cards/S3_star_patterns.md`。
- `submission.md` / `SCORING_RUBRIC.md` → 引官方规则（official_rules_research）。
- `matlab-conventions.md` → 引 `corpus/problem_analysis/CODE_INVENTORY.md`。

## 4. 脚本索引

| 脚本 | 用途 | 新增? |
|---|---|---|
| corpus_build/cards.py | 语料抽文与卡片 | Wave0 |
| contest_init.py | 比赛目录初始化 | 移植 |
| build_latex/audit_tex/audit_paper/build_docx/audit_docx.py | 论文构建审计链 | 移植 |
| visual_plan_init/audit.py | 视觉计划 | 移植 |
| **playbook_match.py** | 题面→原型匹配 | Wave2B 新 |
| **evidence.py** | 证据账本校验 | Wave2B 新 |
| **progress.py** | P0–P6 内容级门禁 | Wave2B 新 |
| **review.py** | 评审团启发式打分 | Wave2B 新 |
| **submission_audit.py** | 提交前审计 | Wave2B 新 |
| **blind_check.py** | 留出盲检辅助 | Wave2B 新 |

## 5. 边界

- 获奖论文 PDF 为外部只读资产，不入库。
- `skills/academic-figure/` 是 vendored 子 skill，不改其内部。
- 上游 v2.1 来源记录在 `docs/UPSTREAM.md`。
