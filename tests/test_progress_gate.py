# -*- coding: utf-8 -*-
"""test_progress_gate.py — P0-P6 内容级门禁正反例测试。

重点（反 AI 读题审计硬门禁）：
  - 空目录 → P0 FAIL
  - 有题面/原型记录但【无用户确认记录】→ P1 FAIL（不得进入求解）
  - 有 evidence-ledger.json 且 user_confirmation=true → P1 PASS
  - 有 markdown 台账且含确认标记 → P1 PASS
  - 模型假设 ≥3 条 + 目标函数 + 求解脚本 → P2 PASS
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path


from conftest import SCRIPTS


def _load_progress():
    import importlib.util
    spec = importlib.util.spec_from_file_location("progress_mod", SCRIPTS / "progress.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


prog = _load_progress()


def test_empty_dir_p0_fail(tmp_path):
    passed, _ = prog.check_phase("P0", tmp_path)
    assert passed is False, "空目录 P0 必须 FAIL"


def _seed_reading_audit(root: Path):
    """写入题面约束/拆解 + 原型判定记录（但不放用户确认记录）。"""
    (root / "题目").mkdir(exist_ok=True)
    (root / "题目" / "题面.txt").write_text(
        "风电场有功功率分配。约束：疲劳损伤上限。问题分析：需做功率分配优化拆解。",
        encoding="utf-8")
    (root / "原型判定.md").write_text(
        "题型判定：主原型 optimization，辅 prediction。", encoding="utf-8")
    (root / "contest.json").write_text("{}", encoding="utf-8")
    (root / "求解").mkdir(exist_ok=True)
    (root / "求解" / "视觉计划.json").write_text(
        json.dumps({
            "schema_version": "1.2",
            "plan_status": "ready",
            "figure_count_lock": {
                "status": "locked",
                "proposed_total": 1,
                "user_requested_total": None,
                "final_total": 1,
                "counting_rule": "numbered_top_level_figures",
                "confirmation_record": "用户确认锁定 1 张",
            },
            "global_figures": [{"figure_id": "F01"}],
            "problems": [],
        }, ensure_ascii=False),
        encoding="utf-8",
    )


def test_p1_fails_without_user_confirmation(tmp_path):
    _seed_reading_audit(tmp_path)
    passed, items = prog.check_phase("P1", tmp_path)
    assert passed is False, "无用户确认记录时 P1 必须 FAIL（反AI硬门禁）"
    descs = " ".join(d for _, d in items)
    assert "确认" in descs, "P1 检查项应包含用户确认记录检查"


def test_p1_passes_with_json_confirmation(tmp_path):
    _seed_reading_audit(tmp_path)
    (tmp_path / "evidence-ledger.json").write_text(
        json.dumps({"user_confirmation": True, "裁决": "认可优化路线"}, ensure_ascii=False),
        encoding="utf-8")
    passed, _ = prog.check_phase("P1", tmp_path)
    assert passed is True, "有 evidence-ledger.json/user_confirmation=true 时 P1 应 PASS"


def test_p1_passes_with_markdown_ledger(tmp_path):
    _seed_reading_audit(tmp_path)
    (tmp_path / "题目" / "evidence-ledger.md").write_text(
        "# 证据台账\n用户已确认：认可主原型与图表计划，裁决已记录。\n",
        encoding="utf-8")
    passed, _ = prog.check_phase("P1", tmp_path)
    assert passed is True, "markdown 台账含确认标记时 P1 应 PASS"


def test_p1_fails_when_figure_count_is_not_locked(tmp_path):
    _seed_reading_audit(tmp_path)
    (tmp_path / "evidence-ledger.json").write_text(
        json.dumps({"user_confirmation": True}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "求解" / "视觉计划.json").unlink()
    passed, items = prog.check_phase("P1", tmp_path)
    assert passed is False
    assert "Figure 总数" in " ".join(desc for _, desc in items)


def test_p2_passes_with_three_assumptions(tmp_path):
    (tmp_path / "求解").mkdir()
    (tmp_path / "求解" / "model.py").write_text("print('baseline')", encoding="utf-8")
    (tmp_path / "求解" / "假设.md").write_text(
        "模型假设：\n"
        "1. 假设所有风机出力可独立调节\n"
        "2. 假设风功率预测误差服从正态分布\n"
        "3. 假设疲劳损伤按线性雨流累积\n"
        "目标函数：min 总疲劳代价 s.t. 功率平衡\n",
        encoding="utf-8")
    passed, items = prog.check_phase("P2", tmp_path)
    assert passed is True, f"≥3条假设+目标函数+求解脚本时 P2 应 PASS，items={items}"


def test_p2_fails_with_too_few_assumptions(tmp_path):
    (tmp_path / "求解").mkdir()
    (tmp_path / "求解" / "model.py").write_text("print('x')", encoding="utf-8")
    (tmp_path / "求解" / "假设.md").write_text(
        "模型假设：\n1. 假设风机出力可独立调节\n", encoding="utf-8")
    passed, _ = prog.check_phase("P2", tmp_path)
    assert passed is False, "假设<3条时 P2 必须 FAIL"


# --- 优秀论文自检表门禁（Wave6-B）正反例 ---

_CHECKLIST = json.loads(
    (SCRIPTS.parent / "assets" / "checklists" / "paper_checklist.json").read_text(
        encoding="utf-8"
    )
)
_CHECKLIST_ITEMS = _CHECKLIST["items"]
_MANUAL_IDS = [item["id"] for item in _CHECKLIST_ITEMS if item["check_method"] == "manual"]


def _valid_decisions():
    decisions = {
        item_id: {"status": "pass", "note": "已按论文逐项人工核验"}
        for item_id in _MANUAL_IDS
    }
    decisions[_MANUAL_IDS[0]] = {"status": "na", "note": "该测试场景明确不适用"}
    return decisions


def _write_sidecar(root: Path, decisions, directory=None):
    directory = Path(directory) if directory is not None else root / "论文"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "paper_checklist_decisions.json"
    path.write_text(json.dumps(decisions, ensure_ascii=False), encoding="utf-8")
    return path


def _write_checked_report(
        root: Path, overrides=None, *, empty=False, sidecar=None, directory=None,
        problems=None, archetype=None, paper_path=None):
    directory = Path(directory) if directory is not None else root / "论文"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "论文自检表_已勾选.md"
    if empty:
        path.write_text("", encoding="utf-8")
        return path
    sidecar = Path(sidecar) if sidecar is not None else directory / "paper_checklist_decisions.json"
    decisions = {}
    if sidecar.is_file():
        raw = json.loads(sidecar.read_text(encoding="utf-8"))
        decisions, _ = prog._decision_mapping(raw)
        decisions = decisions or {}
    overrides = overrides or {}
    icons = []
    status_map = {}
    for item in _CHECKLIST_ITEMS:
        decision = decisions.get(item["id"], {})
        default_icon = "➖" if decision.get("status") == "na" else "✅"
        icon = overrides.get(item["id"], default_icon)
        status_map[item["id"]] = icon
        icons.append(icon)
    provenance = prog.build_provenance(
        Path(paper_path) if paper_path is not None else root / "论文" / "paper.txt",
        directory,
        sidecar,
        status_map,
        problems,
        archetype,
    )
    provenance_json = json.dumps(
        provenance, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    lines = [
        "# 论文自检表_已勾选",
        "",
        f"<!-- paper-checklist-provenance: {provenance_json} -->",
        "",
    ]
    for item in _CHECKLIST_ITEMS:
        icon = status_map[item["id"]]
        lines.append(f"- {icon} **{item['id']}** {item['item']}")
    counts = [icons.count(icon) for icon in ("✅", "❌", "☐", "➖")]
    lines.extend(["", "---", f"统计：✅ {counts[0]}  ❌ {counts[1]}  ☐ {counts[2]}  ➖ {counts[3]}"])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path

def _seed_p4_base(root: Path):
    """写出一份含摘要/结论/主要章节的论文正文（不含自检表）。"""
    (root / "论文").mkdir(exist_ok=True)
    (root / "论文" / "paper.md").write_text(
        "摘要：本文做了功率分配。\n模型假设：...\n问题重述：...\n参考文献：[1]\n结论：完成。\n",
        encoding="utf-8")
    (root / "contest.json").write_text(
        json.dumps({
            "paper": {
                "internal_total_page_target": {
                    "mode": "off",
                    "target": None,
                    "authority": "user_decision_no_fixed_target",
                }
            }
        }, ensure_ascii=False),
        encoding="utf-8",
    )


def test_p4_fails_without_checklist(tmp_path):
    _seed_p4_base(tmp_path)
    passed, items = prog.check_phase("P4", tmp_path)
    assert passed is False, "无自检表文件时 P4 必须 FAIL"
    descs = " ".join(d for _, d in items)
    assert "自检表" in descs, "P4 应含自检表存在性检查"


def test_p4_passes_with_checklist(tmp_path):
    _seed_p4_base(tmp_path)
    (tmp_path / "论文" / "优秀论文自检表.md").write_text(
        "# 优秀论文自检表\n- [ ] A01 ...\n", encoding="utf-8")
    passed, items = prog.check_phase("P4", tmp_path)
    assert passed is True, f"有自检表文件时 P4 应 PASS，items={items}"


def test_p4_fails_while_page_length_still_awaits_user(tmp_path):
    _seed_p4_base(tmp_path)
    (tmp_path / "论文" / "优秀论文自检表.md").write_text("# 自检表\n", encoding="utf-8")
    (tmp_path / "contest.json").write_text(
        json.dumps({
            "paper": {
                "internal_total_page_target": {
                    "mode": "user_decides",
                    "target": None,
                    "authority": "pending_user_confirmation_after_figure_lock",
                }
            }
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    passed, items = prog.check_phase("P4", tmp_path)
    assert passed is False
    assert "用户已选择" in " ".join(desc for _, desc in items)


def _seed_p5_base(root: Path):
    paper = root / "论文"
    paper.mkdir(exist_ok=True)
    (paper / "paper.md").write_text(
        "匿名终稿正文引用了方法[1]。\n参考文献\n[1] 可核查来源。\n",
        encoding="utf-8",
    )


def _write_valid_framework_audit(root: Path):
    import audit_framework_figure
    import pymupdf
    from PIL import Image

    run_dir = root / "run"
    figure_dir = root / "论文" / "figures"
    run_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    source = run_dir / "F01.png"
    target = figure_dir / "F01.png"
    Image.new("RGB", (100, 60), (235, 245, 255)).save(source)
    shutil.copy2(source, target)
    for name in ("s1-contract.json", "s4-contract.json"):
        (run_dir / name).write_text("{}", encoding="utf-8")
    main_tex = root / "论文" / "main.tex"
    main_tex.write_text(
        r"\includegraphics[width=8mm]{figures/F01.png}", encoding="utf-8"
    )
    compiled_pdf = root / "论文" / "framework-paper.pdf"
    document = pymupdf.open()
    page = document.new_page(width=300, height=200)
    page.insert_image(pymupdf.Rect(20, 20, 120, 80), filename=str(target))
    document.save(compiled_pdf)
    document.close()
    digest = audit_framework_figure.sha256(source)
    binding = {
        "schema_version": "1.0",
        "figure_id": "F01",
        "role": "complex_multi_question_framework",
        "document_language": "en",
        "localization_mode": "source_language",
        "localization_origin": "s1_s4_visible_text_contract",
        "source_terminal_stage": "S5-CANDIDATE-IMAGE",
        "selected_source": "run/F01.png",
        "selected_source_sha256": digest,
        "latex_target": "论文/figures/F01.png",
        "latex_target_sha256": digest,
        "label": "fig:route",
        "main_tex": "论文/main.tex",
        "s1_visible_text_contract": "run/s1-contract.json",
        "s4_visible_text_contract": "run/s4-contract.json",
        "framework_text_qa": {
            "asset_kind": "raster",
            "target_insert_width_mm": 8,
            "minimum_ink_height_px": {
                "macro_group": 40,
                "node": 32,
                "edge_or_port": 25,
                "internal_micro": 25,
                "legend": 28,
            },
            "measurement_method": "native_pixel_component_measurement",
            "measurement_evidence": "run/s1-contract.json",
            "measurement_evidence_sha256": audit_framework_figure.sha256(
                run_dir / "s1-contract.json"
            ),
            "effective_ppi": 317.5,
            "resolution_exception": "",
            "violations": {
                "text_text_collisions": 0,
                "text_connector_collisions": 0,
                "boundary_overflows": 0,
                "clipped_elements": 0,
                "garbled_cjk_glyphs": 0,
                "semantic_mismatches": 0,
            },
            "reviewed_asset_sha256": digest,
        },
        "body_reference_before_figure": True,
        "caption_complete": True,
        "post_figure_interpretation": True,
        "compiled_pdf_visible": True,
        "compiled_pdf_page": 1,
        "compiled_pdf": "论文/framework-paper.pdf",
        "compiled_pdf_sha256": audit_framework_figure.sha256(compiled_pdf),
    }
    binding_path = figure_dir / prog.FRAMEWORK_BINDING_NAME
    binding_path.write_text(json.dumps(binding), encoding="utf-8")
    result = audit_framework_figure.audit(binding_path.resolve(), root.resolve(), stage="paper")
    assert result["status"] == "PASS", result["failures"]
    report_path = figure_dir / prog.FRAMEWORK_REPORT_NAME
    report_path.write_text(json.dumps(result), encoding="utf-8")
    return binding_path, report_path, main_tex, compiled_pdf, target


def test_p5_skips_framework_gate_for_normal_paper_without_complex_f01(tmp_path):
    _seed_p5_base(tmp_path)
    passed, items = prog.check_phase("P5", tmp_path)
    assert passed is True, items
    assert "不适用" in " ".join(desc for _, desc in items)


def test_p5_rejects_declared_complex_f01_without_binding(tmp_path):
    _seed_p5_base(tmp_path)
    solve = tmp_path / "求解"
    solve.mkdir()
    (solve / "视觉计划.json").write_text(json.dumps({
        "global_figures": [{
            "figure_id": "F01",
            "route": "paper-framework-figure-studio-pro S0--S5",
        }],
        "problems": [],
    }), encoding="utf-8")
    passed, items = prog.check_phase("P5", tmp_path)
    assert passed is False
    assert "缺少 F01_framework_binding.json" in " ".join(desc for _, desc in items)


def test_p5_accepts_current_paper_stage_framework_report(tmp_path):
    _seed_p5_base(tmp_path)
    _write_valid_framework_audit(tmp_path)
    passed, items = prog.check_phase("P5", tmp_path)
    assert passed is True, items


def test_framework_gate_rejects_stale_report_and_wrong_submission_pdf(tmp_path):
    _seed_p5_base(tmp_path)
    binding, report, main_tex, compiled_pdf, target = _write_valid_framework_audit(tmp_path)
    ok, detail = prog.framework_figure_gate(
        tmp_path,
        expected_source=main_tex,
        expected_pdf=compiled_pdf,
        require_submission_binding=True,
    )
    assert ok is True, detail

    wrong_pdf = tmp_path / "论文" / "other.pdf"
    shutil.copy2(compiled_pdf, wrong_pdf)
    ok, detail = prog.validate_framework_figure_report(
        report,
        binding,
        tmp_path,
        expected_source=main_tex,
        expected_pdf=wrong_pdf,
        require_submission_binding=True,
    )
    assert ok is False
    assert "最终提交 PDF 不一致" in detail

    target.write_bytes(target.read_bytes() + b"stale")
    ok, detail = prog.validate_framework_figure_report(report, binding, tmp_path)
    assert ok is False
    assert "现场重跑未通过" in detail or "已陈旧" in detail


def _seed_p6_base(root: Path):
    """写出 P6 必需的附件/AI披露/PDF（不含自检表闭环产物）。"""
    (root / "提交附件").mkdir(exist_ok=True)
    (root / "提交附件" / "solve.m").write_text("disp('ok');", encoding="utf-8")
    (root / "论文").mkdir(exist_ok=True)
    (root / "论文" / "paper.txt").write_text(
        "本文使用了AI工具辅助数据分析与编程。\n参考文献：[1]\n", encoding="utf-8")
    (root / "论文" / "paper.pdf").write_bytes(b"%PDF-1.4 fake")


def _make_filled_cover_pdf(target: Path):
    import submission_audit

    pymupdf = submission_audit.load_pymupdf()
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    for point, label in (
        ((50, 350), "学校"),
        ((50, 400), "参赛队号"),
        ((50, 445), "队员姓名"),
    ):
        page.insert_text(point, label, fontname="china-s", fontsize=12)
    for point, value in (
        ((200, 365), "University A"),
        ((200, 410), "TEAM-001"),
        ((240, 450), "Member A"),
        ((240, 486), "Member B"),
        ((240, 525), "Member C"),
    ):
        page.insert_text(point, value)
    document.save(target)
    document.close()


def _compile_same_source_submission(source: Path, target: Path):
    command = [
        "xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        source.name,
    ]
    run = None
    for _ in range(2):
        run = subprocess.run(
            command,
            cwd=source.parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
    shutil.copy2(source.with_suffix(".pdf"), target)


def _run_submission_report(
        root: Path, paper: Path, attachments: Path, ai_used: str,
        ai_file=None, source=None, manifest=None):
    report = root / "论文" / "submission_audit.json"
    command = [
        sys.executable,
        "-X", "utf8",
        str(SCRIPTS / "submission_audit.py"),
        "--paper", str(paper),
        "--attachments", str(attachments),
        "--ai-used", ai_used,
        "--cover-policy", "required",
        "--report", str(report),
        "--json",
    ]
    if source is not None:
        command.extend(["--source", str(source)])
    if manifest is not None:
        command.extend(["--manifest", str(manifest)])
    if ai_file is not None:
        command.extend(["--ai-file", str(ai_file)])
    run = subprocess.run(
        command,
        cwd=SCRIPTS.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return run, report


def test_p6_fails_without_checked_table(tmp_path):
    _seed_p6_base(tmp_path)
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False, "无《论文自检表_已勾选.md》时 P6 必须 FAIL"
    descs = " ".join(d for _, d in items)
    assert "已勾选" in descs, "P6 应含已勾选自检表落盘检查"


def test_p6_rejects_header_only_fake_pdf(tmp_path):
    _seed_p6_base(tmp_path)
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    pdf_checks = [(ok, desc) for ok, desc in items if "PDF" in desc]
    assert pdf_checks and pdf_checks[0][0] is False


def test_p6_fails_when_sidecar_missing(tmp_path):
    _seed_p6_base(tmp_path)
    _write_checked_report(tmp_path)
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False, "缺 sidecar（待运行 paper_checklist）时 P6 必须 FAIL"
    descs = " ".join(d for _, d in items)
    assert "待运行 paper_checklist" in descs, "缺 sidecar 应提示待运行 paper_checklist"


def test_p6_rejects_two_record_legacy_sidecar(tmp_path):
    _seed_p6_base(tmp_path)
    sidecar = _write_sidecar(
        tmp_path,
        {"decisions": [
            {"id": _MANUAL_IDS[0], "status": "pass"},
            {"id": _MANUAL_IDS[1], "status": "pass"},
        ]},
    )
    _write_checked_report(tmp_path, sidecar=sidecar)
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False, "只有两条记录的旧 sidecar 不得伪绿"
    assert "缺少" in " ".join(desc for _, desc in items)


def test_p6_passes_with_checked_table_and_clean_sidecar(tmp_path):
    import build_latex

    paper_dir = tmp_path / "论文"
    paper_dir.mkdir()
    source_dir = tmp_path / "paper-source"
    source_dir.mkdir()
    quickstart = SCRIPTS.parent / "docs" / "examples" / "quickstart"
    shutil.copy2(
        quickstart / "paper_checklist_decisions.json",
        paper_dir / "paper_checklist_decisions.json",
    )
    quickstart_text = (quickstart / "main.tex").read_text(encoding="utf-8")
    body_start = quickstart_text.index(r"\section{引言}")
    references_start = quickstart_text.index(r"\clearpage", body_start)
    (source_dir / "abstract.tex").write_text(
        "针对问题1，本文建立单变量二次规划模型，以解析解确定最优产量，并在成本系数上下浮动百分之十时重算最优解。"
        "标称情形得到最优产量 30、最大利润 800 元；灵敏度分析给出产量与利润的变化区间，"
        "用于说明结论的适用边界。",
        encoding="utf-8",
    )
    (source_dir / "body.tex").write_text(
        quickstart_text[body_start:references_start],
        encoding="utf-8",
    )
    references = quickstart_text[references_start:].replace(r"\clearpage", "", 1)
    references = references.rsplit(r"\end{document}", 1)[0]
    (source_dir / "references.tex").write_text(references, encoding="utf-8")
    manifest = source_dir / "论文输入.json"
    manifest.write_text(
        json.dumps({
            "title": "产品 A 单变量生产优化",
            "keywords": ["单变量优化", "二次规划", "灵敏度分析", "鲁棒性"],
            "abstract_tex_path": "abstract.tex",
            "appendix_pseudocode": {
                "required": False,
                "reason": "闭式解析推导不依赖程序求解，附件脚本仅用于复核算式",
            },
            "chapters": [
                {
                    "chapter_id": "body", "title": "引言", "role": "preliminary",
                    "order": 1, "tex_path": "body.tex",
                },
                {
                    "chapter_id": "references", "title": "参考文献", "role": "references",
                    "order": 2, "tex_path": "references.tex",
                },
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    loaded_manifest = build_latex.load_manifest(manifest)
    main_text, _ = build_latex.build_main(
        loaded_manifest,
        source_dir,
        {"contest": {"verified_against_official_rules": True, "edition_cn": "二十三"}},
    )
    build_latex.copy_assets(SCRIPTS.parent / "assets" / "paper-template", source_dir)
    main_tex = source_dir / "main.tex"
    for command, value in {
        "schoolname": "University A", "baominghao": "TEAM-001",
        "membera": "Member A", "memberb": "Member B", "memberc": "Member C",
    }.items():
        main_text = main_text.replace(rf"\{command}{{}}", rf"\{command}{{{value}}}")
    main_tex.write_text(main_text, encoding="utf-8")
    (paper_dir / "AI使用披露.txt").write_text(
        "本文使用了AI工具辅助数据分析与编程。", encoding="utf-8"
    )
    submission = tmp_path / "提交附件"
    submission.mkdir()
    (submission / "solve.m").write_text("disp('ok');", encoding="utf-8")
    ai_file = submission / "AI使用说明.txt"
    ai_file.write_text("AI 工具用于编程与文字检查，最终内容已由队伍复核。", encoding="utf-8")
    final_pdf = submission / "final-paper.pdf"
    _compile_same_source_submission(main_tex, final_pdf)
    run = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "paper_checklist.py"),
            "--tex", str(main_tex),
            "--problems", "1",
            "--archetype", "optimization",
            "--outdir", str(paper_dir),
            "--strict",
        ],
        cwd=SCRIPTS.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert run.returncode == 0, run.stderr
    submission_run, _ = _run_submission_report(
        tmp_path, final_pdf, submission, "mixed", ai_file,
        source=main_tex, manifest=manifest,
    )
    assert submission_run.returncode == 0, submission_run.stdout + submission_run.stderr
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is True, f"真实 strict 报告 + sidecar 时 P6 应 PASS，items={items}"
    manifest.unlink()
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "manifest" in " ".join(desc for _, desc in items)


def test_p6_rejects_submission_audit_with_empty_attachments(tmp_path):
    _seed_p6_base(tmp_path)
    empty_attachments = tmp_path / "提交附件"
    for item in list(empty_attachments.iterdir()):
        item.unlink()
    final_pdf = tmp_path / "论文" / "final-paper.pdf"
    _make_filled_cover_pdf(final_pdf)
    run, report = _run_submission_report(
        tmp_path, final_pdf, empty_attachments, "mixed", tmp_path / "missing-ai.txt"
    )
    assert run.returncode == 1
    assert json.loads(report.read_text(encoding="utf-8"))["passed"] is False
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "不是 PASS" in " ".join(desc for _, desc in items)


def test_p6_rejects_arbitrary_reference_pdf_as_final_submission(tmp_path):
    _seed_p6_base(tmp_path)
    submission = tmp_path / "提交附件"
    reference_pdf = submission / "reference.pdf"
    shutil.copy2(
        SCRIPTS.parent / "docs" / "examples" / "quickstart" / "main.pdf",
        reference_pdf,
    )
    run, report = _run_submission_report(
        tmp_path, reference_pdf, submission, "mixed", tmp_path / "missing-ai.txt"
    )
    assert run.returncode == 1
    assert json.loads(report.read_text(encoding="utf-8"))["passed"] is False
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "不是 PASS" in " ".join(desc for _, desc in items)


def test_submission_audit_rejects_source_a_with_unrelated_pdf_b(tmp_path):
    paper_dir = tmp_path / "论文"
    paper_dir.mkdir()
    source = paper_dir / "main.tex"
    shutil.copy2(
        SCRIPTS.parent / "docs" / "examples" / "quickstart" / "main.tex",
        source,
    )
    submission = tmp_path / "提交附件"
    submission.mkdir()
    unrelated = submission / "unrelated-filled-cover.pdf"
    _make_filled_cover_pdf(unrelated)
    run, report = _run_submission_report(
        tmp_path, unrelated, submission, "none", source=source
    )
    assert run.returncode == 1
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert any(
        not check["ok"] and "同源" in check["desc"]
        for check in payload["checks"]
    )


def test_submission_audit_rejects_white_overlay_with_unchanged_text_layer(tmp_path):
    import submission_audit

    source_dir = tmp_path / "paper-source"
    source_dir.mkdir()
    source = source_dir / "main.tex"
    shutil.copy2(
        SCRIPTS.parent / "docs" / "examples" / "quickstart" / "main.tex",
        source,
    )
    submission = tmp_path / "提交附件"
    submission.mkdir()
    final_pdf = submission / "final-paper.pdf"
    _compile_same_source_submission(source, final_pdf)
    original = submission_audit.pdf_fingerprints(final_pdf)

    pymupdf = submission_audit.load_pymupdf()
    document = pymupdf.open(final_pdf)
    page = document[0]
    page.draw_rect(page.rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
    masked = submission / "masked.pdf"
    document.save(masked)
    document.close()
    masked.replace(final_pdf)

    changed = submission_audit.pdf_fingerprints(final_pdf)
    assert changed["text_sha256"] == original["text_sha256"]
    assert changed["render_sha256"] != original["render_sha256"]
    report = tmp_path / "submission_audit.json"
    run = subprocess.run(
        [
            sys.executable,
            "-X", "utf8",
            str(SCRIPTS / "submission_audit.py"),
            "--paper", str(final_pdf),
            "--source", str(source),
            "--attachments", str(submission),
            "--ai-used", "none",
            "--cover-policy", "forbidden",
            "--report", str(report),
            "--json",
        ],
        cwd=SCRIPTS.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert run.returncode == 1
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert any(
        not check["ok"] and "固定 DPI 像素" in check["desc"]
        for check in payload["checks"]
    )


def test_p6_rejects_ai_disclosure_bypass_with_none_declaration(tmp_path):
    _seed_p6_base(tmp_path)
    submission = tmp_path / "提交附件"
    final_pdf = submission / "final-paper.pdf"
    _make_filled_cover_pdf(final_pdf)
    ai_file = submission / "AI使用说明.txt"
    ai_file.write_text("本文实际使用 AI 辅助。", encoding="utf-8")
    run, report = _run_submission_report(
        tmp_path, final_pdf, submission, "none", ai_file
    )
    assert run.returncode == 1
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert any(not check["ok"] and "相互矛盾" in check["desc"] for check in payload["checks"])
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "不是 PASS" in " ".join(desc for _, desc in items)


def test_p6_rejects_report_sidecar_status_mismatch(tmp_path):
    _seed_p6_base(tmp_path)
    decisions = _valid_decisions()
    sidecar = _write_sidecar(tmp_path, decisions)
    _write_checked_report(
        tmp_path,
        {_MANUAL_IDS[0]: "✅"},
        sidecar=sidecar,
    )
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "人工裁决不一致" in " ".join(desc for _, desc in items)


def test_p6_rejects_handwritten_machine_green_report_for_minimal_tex(tmp_path):
    _seed_p6_base(tmp_path)
    paper = tmp_path / "论文" / "paper.tex"
    paper.write_text(
        "\\documentclass{article}\n\\begin{document}\n"
        "本文使用AI工具辅助。\\section{摘要}空白\\end{document}\n",
        encoding="utf-8",
    )
    shutil.copy2(
        SCRIPTS.parent / "docs" / "examples" / "quickstart" / "main.pdf",
        tmp_path / "论文" / "paper.pdf",
    )
    sidecar = _write_sidecar(tmp_path, _valid_decisions())
    _write_checked_report(
        tmp_path,
        sidecar=sidecar,
        paper_path=paper,
        problems=1,
        archetype="optimization",
    )
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "机器项与当前论文现场重算不一致" in " ".join(desc for _, desc in items)


def test_p6_rejects_report_and_sidecar_in_different_directories(tmp_path):
    _seed_p6_base(tmp_path)
    sidecar = _write_sidecar(tmp_path, _valid_decisions(), directory=tmp_path)
    _write_checked_report(tmp_path, sidecar=sidecar)
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "必须位于同一目录" in " ".join(desc for _, desc in items)


def test_p6_rejects_report_after_paper_changes(tmp_path):
    _seed_p6_base(tmp_path)
    sidecar = _write_sidecar(tmp_path, _valid_decisions())
    _write_checked_report(tmp_path, sidecar=sidecar, problems=1, archetype="optimization")
    paper = tmp_path / "论文" / "paper.txt"
    paper.write_text(paper.read_text(encoding="utf-8") + "结论已变化。\n", encoding="utf-8")
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "paper_sha256 不一致" in " ".join(desc for _, desc in items)


def test_p6_rejects_legacy_report_without_provenance(tmp_path):
    _seed_p6_base(tmp_path)
    sidecar = _write_sidecar(tmp_path, _valid_decisions())
    report = _write_checked_report(tmp_path, sidecar=sidecar)
    text = report.read_text(encoding="utf-8")
    text = "\n".join(
        line for line in text.splitlines()
        if "paper-checklist-provenance:" not in line
    )
    report.write_text(text, encoding="utf-8")
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "旧报告须重新运行" in " ".join(desc for _, desc in items)


def test_p6_rejects_sidecar_missing_one_manual_id(tmp_path):
    _seed_p6_base(tmp_path)
    decisions = _valid_decisions()
    decisions.pop(_MANUAL_IDS[-1])
    sidecar = _write_sidecar(tmp_path, decisions)
    _write_checked_report(tmp_path, sidecar=sidecar)
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "缺少 1 个人工 ID" in " ".join(desc for _, desc in items)


def test_p6_rejects_sidecar_unknown_id(tmp_path):
    _seed_p6_base(tmp_path)
    decisions = _valid_decisions()
    decisions["UNKNOWN99"] = {"status": "pass", "note": "不应存在"}
    sidecar = _write_sidecar(tmp_path, decisions)
    _write_checked_report(tmp_path, sidecar=sidecar)
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "未知 ID" in " ".join(desc for _, desc in items)


def test_p6_rejects_invalid_status_and_unexplained_na(tmp_path):
    _seed_p6_base(tmp_path)
    decisions = _valid_decisions()
    decisions[_MANUAL_IDS[0]] = {"status": "passed", "note": "非法状态"}
    sidecar = _write_sidecar(tmp_path, decisions)
    _write_checked_report(tmp_path, sidecar=sidecar)
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "pass 或 na" in " ".join(desc for _, desc in items)

    decisions[_MANUAL_IDS[0]] = {"status": "na", "note": "无"}
    sidecar = _write_sidecar(tmp_path, decisions)
    _write_checked_report(tmp_path, sidecar=sidecar)
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "具体理由" in " ".join(desc for _, desc in items)


def test_p6_rejects_empty_checked_report(tmp_path):
    _seed_p6_base(tmp_path)
    _write_sidecar(tmp_path, _valid_decisions())
    _write_checked_report(tmp_path, empty=True)
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "报告为空" in " ".join(desc for _, desc in items)


def test_p6_rejects_checked_report_with_failure_or_pending(tmp_path):
    _seed_p6_base(tmp_path)
    sidecar = _write_sidecar(tmp_path, _valid_decisions())
    _write_checked_report(
        tmp_path,
        {_CHECKLIST_ITEMS[0]["id"]: "❌", _CHECKLIST_ITEMS[1]["id"]: "☐"},
        sidecar=sidecar,
    )
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False
    assert "FAIL=1、PENDING=1" in " ".join(desc for _, desc in items)


def test_p6_accepts_complete_legacy_list_sidecar(tmp_path):
    records = [
        {"id": item_id, "status": "pass", "note": "已逐项人工核验"}
        for item_id in _MANUAL_IDS
    ]
    sidecar = _write_sidecar(tmp_path, {"decisions": records})
    passed, detail = prog.validate_sidecar(sidecar)
    assert passed is True, detail
