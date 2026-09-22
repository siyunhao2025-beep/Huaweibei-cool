#!/usr/bin/env python3
# [来源] 移植自 v2.1 华为杯_求解规范/tools/，相对路径已改 CLI 参数驱动。
"""Audit Huawei Cup visual evidence at plan, render, or paper stage."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED_CATEGORIES = {
    "mechanism_geometry",
    "main_result",
    "independent_validation",
    "sensitivity_robustness",
}
VISUAL_FIRST_SHAPES = {
    "multi_point_scan",
    "repeated_trials",
    "distribution",
    "error_structure",
    "matrix_surface",
    "spatial_geometry",
}
VECTOR_EXTENSIONS = {".pdf", ".svg"}
EXPECTED_COLOR_SEMANTICS = {
    "baseline": "#2166AC",
    "risk_highlight": "#B2182B",
    "improvement": "#1B7837",
    "secondary": "#F1A340",
    "additional_model": "#762A83",
    "background": "#999999",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def project_path(project_root: Path, raw: str) -> Path:
    candidate = (project_root / raw).resolve()
    candidate.relative_to(project_root.resolve())
    return candidate


def _strip_tex_comment(line: str) -> str:
    """Strip a real TeX comment while preserving escaped percent signs."""
    for index, char in enumerate(line):
        if char != "%":
            continue
        backslashes = 0
        cursor = index - 1
        while cursor >= 0 and line[cursor] == "\\":
            backslashes += 1
            cursor -= 1
        if backslashes % 2 == 0:
            return line[:index]
    return line


def tex_closure(main: Path) -> str:
    seen: set[Path] = set()

    def read(path: Path) -> str:
        path = path.resolve()
        if path in seen or not path.is_file():
            return ""
        seen.add(path)
        text = path.read_text(encoding="utf-8-sig")
        clean = "\n".join(_strip_tex_comment(line) for line in text.splitlines())
        parts = [clean]
        for raw in re.findall(r"\\input\s*\{([^{}]+)\}", clean):
            child = (path.parent / raw).with_suffix(".tex") if not Path(raw).suffix else path.parent / raw
            parts.append(read(child))
        return "\n".join(parts)

    return read(main)


def count_numbered_figures(tex: str) -> int:
    """Count top-level numbered Figure environments; subfigures are panels, not figures."""
    environments = len(re.findall(r"\\begin\s*\{figure\*?\}", tex))
    # A wrapper macro normally contains one literal figure environment in its
    # definition.  Count calls, not the wrapper definition itself.
    wrappers = ("evidencefigure", "frameworkfigure")
    definitions = sum(
        len(re.findall(rf"\\newcommand\s*\{{\\{name}\}}", tex))
        for name in wrappers
    )
    calls = sum(len(re.findall(rf"\\{name}\s*\{{", tex)) for name in wrappers)
    return max(0, environments - definitions) + calls


def _macro_calls(tex: str, names: tuple[str, ...], argument_count: int = 3) -> list[dict]:
    """Return balanced-brace calls for the small paper figure wrappers."""
    calls: list[dict] = []
    pattern = re.compile(r"\\(" + "|".join(re.escape(name) for name in names) + r")\s*\{")
    for match in pattern.finditer(tex):
        cursor = match.end() - 1
        args: list[str] = []
        end = cursor
        valid = True
        for _ in range(argument_count):
            while cursor < len(tex) and tex[cursor].isspace():
                cursor += 1
            if cursor >= len(tex) or tex[cursor] != "{":
                valid = False
                break
            depth = 0
            start = cursor + 1
            while cursor < len(tex):
                char = tex[cursor]
                if char == "{" and (cursor == 0 or tex[cursor - 1] != "\\"):
                    depth += 1
                elif char == "}" and (cursor == 0 or tex[cursor - 1] != "\\"):
                    depth -= 1
                    if depth == 0:
                        args.append(tex[start:cursor])
                        cursor += 1
                        end = cursor
                        break
                cursor += 1
            else:
                valid = False
                break
        if valid and len(args) == argument_count:
            calls.append({"name": match.group(1), "args": args, "start": match.start(), "end": end})
    return calls


def figure_binding_audit(tex: str, labels: list[str]) -> dict:
    """Check source binding plus the pre/caption/post narrative contract."""
    wrapper_calls = _macro_calls(tex, ("evidencefigure", "frameworkfigure"))
    call_by_label = {call["args"][2].strip(): call for call in wrapper_calls}
    explicit_labels = {item: None for item in re.findall(r"\\label\s*\{([^{}]+)\}", tex)}
    missing_binding: list[str] = []
    missing_pre_reference: list[str] = []
    missing_post_narrative: list[str] = []
    weak_captions: list[str] = []

    for label in labels:
        call = call_by_label.get(label)
        if call is None and label not in explicit_labels:
            missing_binding.append(label)
            continue
        anchor = call["start"] if call else tex.find(r"\label{" + label + "}")
        before = tex[:anchor]
        if not re.search(rf"\\(?:ref|autoref)\s*\{{{re.escape(label)}\}}", before):
            missing_pre_reference.append(label)
        if call:
            caption = re.sub(r"\\[A-Za-z@]+|[{}$]", "", call["args"][1])
            end = call["end"]
        else:
            env_start = tex.rfind(r"\begin{figure", 0, anchor)
            env_end = tex.find(r"\end{figure", anchor)
            block = tex[env_start:env_end if env_end >= 0 else anchor + 1]
            caption_match = re.search(r"\\caption\s*\{([^{}]+)\}", block, re.S)
            caption = caption_match.group(1) if caption_match else ""
            end_marker = tex.find("}", env_end) if env_end >= 0 else anchor
            end = end_marker + 1
        if len(re.sub(r"\s+", "", caption)) < 12:
            weak_captions.append(label)
        tail = tex[end:end + 900]
        tail = re.split(r"\\(?:section|subsection|subsubsection|begin\s*\{figure)", tail, maxsplit=1)[0]
        tail = re.sub(r"\\[A-Za-z@]+(?:\[[^]]*\])?|[{}$%]", " ", tail)
        tail = re.sub(r"\s+", "", tail)
        if len(tail) < 24:
            missing_post_narrative.append(label)

    return {
        "missing_binding": missing_binding,
        "missing_pre_reference": missing_pre_reference,
        "missing_post_narrative": missing_post_narrative,
        "weak_captions": weak_captions,
    }


def audit(plan_path: Path, stage: str, project_root: Path, main_tex: Path | None) -> dict:
    checks: list[dict] = []
    failures: list[dict] = []
    warnings: list[dict] = []

    def add(code: str, ok: bool, severity: str = "FAIL", **details) -> None:
        item = {"code": code, "ok": ok, "severity": "PASS" if ok else severity, **details}
        checks.append(item)
        if not ok:
            (failures if severity == "FAIL" else warnings).append(item)

    try:
        plan = load_json(plan_path)
    except Exception as exc:
        add("plan_is_valid_json", False, error=str(exc))
        return {"status": "FAIL", "stage": stage, "checks": checks, "failures": failures, "warnings": warnings}

    required_root = {"schema_version", "project_title", "plan_status", "visual_encoding_path",
                     "problems", "global_figures", "flowcharts"}
    add("root_fields_present", required_root <= set(plan), missing=sorted(required_root - set(plan)))
    if failures:
        return {"status": "FAIL", "stage": stage, "checks": checks, "failures": failures, "warnings": warnings}

    schema_version = str(plan["schema_version"])
    add("schema_version_supported", schema_version in {"1.0", "1.1", "1.2"}, actual=schema_version)
    if schema_version in {"1.1", "1.2"}:
        add("table_ledger_root_present", "global_tables" in plan)
        add("semantic_palette_declared", plan.get("color_semantics") == EXPECTED_COLOR_SEMANTICS,
            actual=plan.get("color_semantics"), expected=EXPECTED_COLOR_SEMANTICS,
            message="全文统一语义色：蓝基线、红风险/唯一重点、绿改进、橙紫扩展、灰背景")
    else:
        add("legacy_schema_without_table_ledger", False, severity="WARN",
            actual=schema_version, message="1.0 计划仍可读取，但应升级到 1.2 以审计三线表与图数锁定")
    if schema_version == "1.2":
        add("figure_count_lock_present", "figure_count_lock" in plan)
    elif schema_version in {"1.0", "1.1"}:
        add("legacy_schema_without_figure_count_lock", False, severity="WARN",
            actual=schema_version, message="旧视觉计划没有用户确认的 Figure 总数硬锁；正式出图前应升级到 1.2")
    add("plan_marked_ready", plan["plan_status"] == "ready", actual=plan["plan_status"])
    problems = plan.get("problems", [])
    add("problems_present", bool(problems), count=len(problems))
    add("visual_encoding_declared", bool(str(plan.get("visual_encoding_path", "")).strip()))

    raw_global_figures = plan.get("global_figures", [])
    raw_global_tables = plan.get("global_tables", [])
    global_figure_errors = [
        {"index": index, "value": repr(item)}
        for index, item in enumerate(raw_global_figures)
        if not isinstance(item, dict)
    ]
    global_table_errors = [
        {"index": index, "value": repr(item)}
        for index, item in enumerate(raw_global_tables)
        if not isinstance(item, dict)
    ]
    add("global_figure_entries_are_objects", not global_figure_errors,
        invalid=global_figure_errors)
    if schema_version in {"1.1", "1.2"}:
        add("global_table_entries_are_objects", not global_table_errors,
            invalid=global_table_errors,
            message="表格账本条目必须是完整对象，不能只写表格 ID 字符串")
    all_figures: list[dict] = [item for item in raw_global_figures if isinstance(item, dict)]
    all_tables: list[dict] = [item for item in raw_global_tables if isinstance(item, dict)]
    all_schematics: list[dict] = []
    all_figure_ids: list[str] = []
    all_claim_ids: set[str] = set()
    all_evidence_ids: set[str] = set()
    problem_summaries: list[dict] = []

    for problem in problems:
        pid = str(problem.get("problem_id", ""))
        complexity = problem.get("complexity")
        raw_figures = problem.get("figures", [])
        raw_tables = problem.get("tables", [])
        raw_schematics = problem.get("schematics", [])
        figure_entry_errors = [
            {"index": index, "value": repr(item)}
            for index, item in enumerate(raw_figures)
            if not isinstance(item, dict)
        ]
        table_entry_errors = [
            {"index": index, "value": repr(item)}
            for index, item in enumerate(raw_tables)
            if not isinstance(item, dict)
        ]
        schematic_entry_errors = [
            {"index": index, "value": repr(item)}
            for index, item in enumerate(raw_schematics)
            if not isinstance(item, dict)
        ]
        figures = [item for item in raw_figures if isinstance(item, dict)]
        tables = [item for item in raw_tables if isinstance(item, dict)]
        schematics = [item for item in raw_schematics if isinstance(item, dict)]
        evidence = problem.get("evidence_matrix", [])
        claims = problem.get("claims", [])
        all_figures.extend(figures)
        all_tables.extend(tables)
        all_schematics.extend(schematics)

        if schema_version in {"1.1", "1.2"}:
            add(f"{pid}:table_ledger_fields_present",
                "tables" in problem and "low_table_exception" in problem)
            add(f"{pid}:table_entries_are_objects", not table_entry_errors,
                invalid=table_entry_errors,
                message="表格账本条目必须填写问题、证据、列、论文绑定和状态，不能只写 ID")

        add(f"{pid}:figure_entries_are_objects", not figure_entry_errors,
            invalid=figure_entry_errors)
        add(f"{pid}:schematic_entries_are_objects", not schematic_entry_errors,
            invalid=schematic_entry_errors)

        add(f"{pid}:complexity_valid", complexity in {"simple", "standard", "complex"}, actual=complexity)
        claim_ids = [str(item.get("claim_id", "")) for item in claims]
        add(f"{pid}:claims_defined", bool(claim_ids) and all(str(item.get("text", "")).strip() for item in claims))
        add(f"{pid}:claim_ids_unique", len(claim_ids) == len(set(claim_ids)), ids=claim_ids)
        all_claim_ids.update(claim_ids)

        evidence_ids = [str(item.get("evidence_id", "")) for item in evidence]
        categories = {item.get("category") for item in evidence}
        add(f"{pid}:required_coverage_reviewed", REQUIRED_CATEGORIES <= categories,
            missing=sorted(REQUIRED_CATEGORIES - categories))
        add(f"{pid}:evidence_ids_unique", len(evidence_ids) == len(set(evidence_ids)), ids=evidence_ids)
        all_evidence_ids.update(evidence_ids)
        if schema_version in {"1.1", "1.2"}:
            missing_table_links = [item.get("evidence_id") for item in evidence if "table_ids" not in item]
            add(f"{pid}:evidence_table_links_declared", not missing_table_links, ids=missing_table_links)

        pending = [item.get("evidence_id") for item in evidence
                   if item.get("applicability") == "pending" or item.get("representation") == "pending"
                   or item.get("data_shape") == "pending"]
        add(f"{pid}:evidence_decisions_complete", not pending, pending=pending)
        unexplained_na = [item.get("evidence_id") for item in evidence
                          if item.get("applicability") in {"not_needed", "not_possible"}
                          and len(str(item.get("reason", "")).strip()) < 10]
        add(f"{pid}:inapplicability_explained", not unexplained_na, ids=unexplained_na)

        visual_misses = [item.get("evidence_id") for item in evidence
                         if item.get("applicability") == "applicable"
                         and item.get("data_shape") in VISUAL_FIRST_SHAPES
                         and item.get("representation") not in {"figure", "schematic"}]
        add(f"{pid}:visual_first_evidence_mapped", not visual_misses,
            severity="WARN", ids=visual_misses,
            message="多点扫描、重复试验、分布、误差结构、矩阵或空间数据默认优先图形表达")

        main_evidence = [item for item in evidence if item.get("category") == "main_result"]
        main_visual = any(item.get("applicability") == "applicable"
                          and item.get("representation") in {"figure", "schematic"}
                          and item.get("figure_ids") for item in main_evidence)
        add(f"{pid}:main_result_has_visual", main_visual)

        validation_evidence = [item for item in evidence if item.get("category") == "independent_validation"]
        validation_visual = any(item.get("applicability") == "applicable"
                                and item.get("representation") == "figure"
                                and item.get("figure_ids") for item in validation_evidence)
        validation_ok = validation_visual or complexity == "simple"
        add(f"{pid}:validation_has_figure", validation_ok,
            message="标准/复杂问题必须有独立验证 Figure；简单问题可用可复核表或解析证据")

        threshold = 2 if complexity == "simple" else 3 if complexity == "standard" else 4
        upper_review = 3 if complexity == "simple" else 5 if complexity == "standard" else 7
        exception = str(problem.get("low_figure_exception") or "").strip()
        count_ok = len(figures) >= threshold or len(exception) >= 20
        add(f"{pid}:figure_review_threshold", count_ok, count=len(figures), threshold=threshold,
            exception=exception, message="少于审查阈值时必须提供具体不适用理由和替代证据")
        if len(figures) < threshold and len(exception) >= 20:
            add(f"{pid}:low_figure_exception_used", False, severity="WARN", count=len(figures), exception=exception)
        if len(figures) > upper_review:
            add(f"{pid}:high_figure_count_review", False, severity="WARN",
                count=len(figures), upper_review=upper_review,
                message="逐张证明独立信息增量；能合并面板或改表格的重复 Figure 应删除")

        families = {panel.get("figure_family") for fig in figures for panel in fig.get("panels", [])}
        if len(figures) >= 3:
            add(f"{pid}:figure_family_diversity", len(families) >= 2, severity="WARN", families=sorted(f for f in families if f))

        table_families = {str(item.get("table_family", "")) for item in tables if item.get("table_family")}
        if schema_version in {"1.1", "1.2"}:
            table_threshold = 1 if complexity == "simple" else 2 if complexity == "standard" else 3
            table_upper_review = 2 if complexity == "simple" else 4 if complexity == "standard" else 5
            table_exception = str(problem.get("low_table_exception") or "").strip()
            table_count_ok = len(tables) >= table_threshold or len(table_exception) >= 20
            add(f"{pid}:table_review_threshold", table_count_ok, count=len(tables), threshold=table_threshold,
                exception=table_exception, message="少于表格审查阈值时必须说明精确数值由何种可复核载体替代")
            if len(tables) < table_threshold and len(table_exception) >= 20:
                add(f"{pid}:low_table_exception_used", False, severity="WARN",
                    count=len(tables), exception=table_exception)
            if len(tables) > table_upper_review:
                add(f"{pid}:high_table_count_review", False, severity="WARN",
                    count=len(tables), upper_review=table_upper_review,
                    message="逐表证明精确查值任务不同；只重复正文数字或 Figure 结论的表应删除")
            if len(tables) >= 3:
                add(f"{pid}:table_family_diversity", len(table_families) >= 2, severity="WARN",
                    families=sorted(table_families))

        for schematic in schematics:
            add(f"{pid}:{schematic.get('schematic_id')}:sources_traceable",
                bool(schematic.get("source_refs")) and bool(schematic.get("elements")))
            paper = schematic.get("paper", {})
            add(f"{pid}:{schematic.get('schematic_id')}:paper_contract_declared",
                str(paper.get("label", "")).startswith("fig:")
                and bool(str(paper.get("caption", "")).strip())
                and bool(str(paper.get("reference_context", "")).strip()))

            if stage in {"render", "paper"}:
                required_files = [schematic.get("tex_source"), schematic.get("output_pdf"),
                                  schematic.get("preview_png")]
                missing = []
                for raw in required_files:
                    try:
                        path = project_path(project_root, str(raw))
                    except (ValueError, OSError):
                        missing.append(str(raw))
                        continue
                    if not path.is_file() or path.stat().st_size == 0:
                        missing.append(str(raw))
                add(f"{pid}:{schematic.get('schematic_id')}:render_artifacts_exist",
                    not missing, missing=missing)
                add(f"{pid}:{schematic.get('schematic_id')}:qa_status_pass",
                    schematic.get("status") == "qa_pass", actual=schematic.get("status"))

        problem_summaries.append({
            "problem_id": pid,
            "complexity": complexity,
            "figures": len(figures),
            "tables": len(tables),
            "schematics": len(schematics),
            "families": sorted(f for f in families if f),
            "table_families": sorted(table_families),
        })

    all_figure_ids = [str(fig.get("figure_id", "")) for fig in all_figures]
    add("figure_ids_unique", len(all_figure_ids) == len(set(all_figure_ids)), ids=all_figure_ids)
    figure_id_set = set(all_figure_ids)
    all_schematic_ids = [str(item.get("schematic_id", "")) for item in all_schematics]
    add("schematic_ids_unique", len(all_schematic_ids) == len(set(all_schematic_ids)),
        ids=all_schematic_ids)
    numbered_visual_ids = all_figure_ids + all_schematic_ids
    add("numbered_visual_ids_unique", len(numbered_visual_ids) == len(set(numbered_visual_ids)),
        ids=numbered_visual_ids)
    all_table_ids = [str(item.get("table_id", "")) for item in all_tables]
    add("table_ids_unique", len(all_table_ids) == len(set(all_table_ids)), ids=all_table_ids)

    actual_figure_total = len(numbered_visual_ids)
    if schema_version == "1.2":
        count_lock = plan.get("figure_count_lock", {})
        proposed_total = int(count_lock.get("proposed_total", 0) or 0)
        requested_total = count_lock.get("user_requested_total")
        final_total = int(count_lock.get("final_total", 0) or 0)
        add("figure_count_lock_status", count_lock.get("status") == "locked",
            actual=count_lock.get("status"), message="须先向用户展示逐图清单和建议总数，得到明确确认后才能锁定")
        add("figure_count_proposal_is_nonzero", proposed_total >= 1, proposed_total=proposed_total)
        add("figure_count_rule_is_top_level",
            count_lock.get("counting_rule") == "numbered_top_level_figures",
            actual=count_lock.get("counting_rule"),
            message="每个顶层 figure/figure* 环境计 1 张；子图面板、封皮 logo 与表格不计")
        add("figure_count_user_decision_consistent",
            final_total == (int(requested_total) if requested_total is not None else proposed_total),
            proposed_total=proposed_total, user_requested_total=requested_total, final_total=final_total)
        add("figure_count_matches_plan", final_total == actual_figure_total,
            final_total=final_total, planned_top_level_figures=actual_figure_total)
        confirmation = str(count_lock.get("confirmation_record", "")).strip()
        add("figure_count_confirmation_recorded", len(confirmation) >= 4,
            confirmation_record=confirmation)

    for table in all_tables:
        tid = str(table.get("table_id", ""))
        add(f"{tid}:question_declared", bool(str(table.get("question", "")).strip()))
        add(f"{tid}:claim_links_resolve", set(table.get("claim_ids", [])) <= all_claim_ids,
            unknown=sorted(set(table.get("claim_ids", [])) - all_claim_ids))
        add(f"{tid}:evidence_links_resolve", set(table.get("evidence_ids", [])) <= all_evidence_ids,
            unknown=sorted(set(table.get("evidence_ids", [])) - all_evidence_ids))
        add(f"{tid}:columns_declared", len(table.get("columns", [])) >= 2,
            columns=table.get("columns", []))
        add(f"{tid}:result_files_declared", bool(table.get("result_files")),
            result_files=table.get("result_files", []))
        paper = table.get("paper", {})
        add(f"{tid}:paper_contract_declared", str(paper.get("label", "")).startswith("tab:")
            and bool(str(paper.get("caption", "")).strip())
            and bool(str(paper.get("reference_context", "")).strip()))
        if stage in {"render", "paper"}:
            missing = []
            for raw in table.get("result_files", []):
                try:
                    path = project_path(project_root, str(raw))
                except (ValueError, OSError):
                    missing.append(str(raw))
                    continue
                if not path.is_file() or path.stat().st_size == 0:
                    missing.append(str(raw))
            add(f"{tid}:result_files_exist", not missing, missing=missing)
            add(f"{tid}:qa_status_pass", table.get("status") == "qa_pass", actual=table.get("status"))

    layouts: list[str] = []
    archetypes: list[str] = []
    output_paths: list[str] = []
    for fig in all_figures:
        fid = str(fig.get("figure_id", ""))
        panels = fig.get("panels", [])
        panel_ids = [str(panel.get("panel_id", "")) for panel in panels]
        layouts.append(str(fig.get("layout", "")))
        archetypes.append(str(fig.get("archetype", "")))
        add(f"{fid}:panel_ids_unique", len(panel_ids) == len(set(panel_ids)), ids=panel_ids)
        add(f"{fid}:panel_count_range", 1 <= len(panels) <= 6, count=len(panels))
        hero = fig.get("hero_panel")
        asymmetric = fig.get("archetype") in {"schematic_led", "image_plate_quant", "asymmetric_mixed"}
        add(f"{fid}:hero_contract", (hero in panel_ids) if asymmetric and len(panels) >= 3 else hero in panel_ids or hero is None,
            hero=hero, archetype=fig.get("archetype"))
        add(f"{fid}:claim_links_resolve", set(fig.get("claim_ids", [])) <= all_claim_ids,
            unknown=sorted(set(fig.get("claim_ids", [])) - all_claim_ids))
        add(f"{fid}:evidence_links_resolve", set(fig.get("evidence_ids", [])) <= all_evidence_ids,
            unknown=sorted(set(fig.get("evidence_ids", [])) - all_evidence_ids))
        vector = str(fig.get("outputs", {}).get("vector", ""))
        preview = str(fig.get("outputs", {}).get("preview", ""))
        output_paths.extend([vector, preview])
        add(f"{fid}:vector_and_preview_declared", Path(vector).suffix.lower() in VECTOR_EXTENSIONS and Path(preview).suffix.lower() == ".png",
            vector=vector, preview=preview)
        paper = fig.get("paper", {})
        add(f"{fid}:paper_contract_declared", str(paper.get("label", "")).startswith("fig:")
            and bool(str(paper.get("caption", "")).strip()) and bool(str(paper.get("reference_context", "")).strip()))

        if stage in {"render", "paper"}:
            required_files = [fig.get("script"), vector, preview, fig.get("statistics_report"), fig.get("qa_report")]
            required_files += [panel.get("result_file") for panel in panels]
            missing = []
            for raw in required_files:
                try:
                    path = project_path(project_root, str(raw))
                except (ValueError, OSError):
                    missing.append(str(raw))
                    continue
                if not path.is_file() or path.stat().st_size == 0:
                    missing.append(str(raw))
            add(f"{fid}:render_artifacts_exist", not missing, missing=missing)
            add(f"{fid}:qa_status_pass", fig.get("status") == "qa_pass", actual=fig.get("status"))

    figure_signatures: dict[tuple[tuple[str, ...], str], list[str]] = {}
    for fig in all_figures:
        signature = (
            tuple(sorted(str(item) for item in fig.get("evidence_ids", []))),
            re.sub(r"\s+", "", str(fig.get("scientific_question", ""))).lower(),
        )
        figure_signatures.setdefault(signature, []).append(str(fig.get("figure_id", "")))
    duplicate_figures = [ids for signature, ids in figure_signatures.items()
                         if signature[0] and signature[1] and len(ids) > 1]
    add("figure_question_evidence_not_duplicated", not duplicate_figures, severity="WARN",
        duplicates=duplicate_figures,
        message="相同问题与证据不得仅换图型重复展示；应合并面板或保留信息增量更高者")

    table_signatures: dict[tuple[tuple[str, ...], str], list[str]] = {}
    for table in all_tables:
        signature = (
            tuple(sorted(str(item) for item in table.get("evidence_ids", []))),
            re.sub(r"\s+", "", str(table.get("question", ""))).lower(),
        )
        table_signatures.setdefault(signature, []).append(str(table.get("table_id", "")))
    duplicate_tables = [ids for signature, ids in table_signatures.items()
                        if signature[0] and signature[1] and len(ids) > 1]
    add("table_question_evidence_not_duplicated", not duplicate_tables, severity="WARN",
        duplicates=duplicate_tables,
        message="相同问题与证据不得拆成多张表重复列值")
    cross_media_duplicates = []
    for signature, figure_ids in figure_signatures.items():
        if signature in table_signatures and signature[0] and signature[1]:
            cross_media_duplicates.append({"figures": figure_ids, "tables": table_signatures[signature]})
    add("figure_table_roles_are_distinct", not cross_media_duplicates, severity="WARN",
        duplicates=cross_media_duplicates,
        message="图与表可共享实验，但必须分别回答趋势/结构与精确查值的不同问题")

    add("output_paths_unique", len(output_paths) == len(set(output_paths)), duplicates=sorted({p for p in output_paths if output_paths.count(p) > 1}))
    if len(all_figures) >= 4:
        add("layout_not_monoculture", len(set(layouts)) >= 2, severity="WARN", layouts=layouts)
    if len(all_figures) >= 6:
        add("archetype_not_monoculture", len(set(archetypes)) >= 2, severity="WARN", archetypes=archetypes)
    standard_complex = sum(1 for p in problems if p.get("complexity") in {"standard", "complex"})
    if standard_complex >= 4:
        add("portfolio_target_15_to_25_review", len(all_figures) >= 15, severity="WARN",
            count=len(all_figures), message="四个标准/复杂问题通常规划 15--25 个非冗余 Figure")
        if len(all_figures) > 25:
            add("portfolio_above_25_review", False, severity="WARN", count=len(all_figures),
                message="全篇 Figure 超过 25 个时逐张复核信息增量，优先合并或删除重复证据")
        if schema_version in {"1.1", "1.2"}:
            add("table_portfolio_target_8_to_16_review", len(all_tables) >= 8, severity="WARN",
                count=len(all_tables), message="四个标准/复杂问题通常规划 8--16 张承担精确查值任务的非冗余三线表")
            if len(all_tables) > 16:
                add("table_portfolio_above_16_review", False, severity="WARN", count=len(all_tables),
                    message="全篇表格超过 16 张时逐表复核独立查值任务，删除重复列表")

    allowed_visual_ids = figure_id_set | set(all_schematic_ids)
    unknown_figure_links = []
    for problem in problems:
        for item in problem.get("evidence_matrix", []):
            unknown_figure_links.extend(fid for fid in item.get("figure_ids", []) if fid not in allowed_visual_ids)
    add("evidence_visual_links_resolve", not unknown_figure_links,
        unknown=sorted(set(unknown_figure_links)))
    table_id_set = set(all_table_ids)
    unknown_table_links = []
    for problem in problems:
        for item in problem.get("evidence_matrix", []):
            unknown_table_links.extend(tid for tid in item.get("table_ids", []) if tid not in table_id_set)
    add("evidence_table_links_resolve", not unknown_table_links,
        unknown=sorted(set(unknown_table_links)))

    flowcharts = plan.get("flowcharts", [])
    flow_pending = [item.get("scope") for item in flowcharts if item.get("needed") == "pending"]
    add("flowchart_decisions_complete", not flow_pending, pending=flow_pending)
    bad_flow = [item.get("scope") for item in flowcharts
                if item.get("needed") in {"yes", "no"} and len(str(item.get("reason", "")).strip()) < 10]
    add("flowchart_decisions_explained", not bad_flow, scopes=bad_flow)
    flow_contract_errors = [item.get("scope") for item in flowcharts
                            if (item.get("needed") == "yes" and not item.get("plan_id"))
                            or (item.get("needed") == "no" and
                                (item.get("plan_id") is not None or item.get("status") != "not_applicable"))]
    add("flowchart_plan_contracts_valid", not flow_contract_errors, scopes=flow_contract_errors,
        message="需要流程图时必须登记 plan_id；不需要时 plan_id 为空且状态为 not_applicable")
    unresolved_flow_ids = [item.get("plan_id") for item in flowcharts
                           if item.get("needed") == "yes" and item.get("plan_id") not in allowed_visual_ids]
    add("flowchart_plan_ids_resolve", not unresolved_flow_ids,
        ids=sorted(set(str(item) for item in unresolved_flow_ids)),
        message="流程图必须登记为已计入总数的 Figure 或 Schematic，不能游离在图数锁之外")
    if stage in {"render", "paper"}:
        flow_not_passed = [item.get("scope") for item in flowcharts
                           if item.get("needed") == "yes" and item.get("status") != "qa_pass"]
        add("required_flowcharts_qa_pass", not flow_not_passed, scopes=flow_not_passed)

    if stage == "paper":
        add("main_tex_provided", main_tex is not None and main_tex.is_file(), path=str(main_tex) if main_tex else None)
        if main_tex is not None and main_tex.is_file():
            tex = tex_closure(main_tex)
            labels = set(re.findall(r"\\label\s*\{([^{}]+)\}", tex))
            labels.update(
                call["args"][2].strip()
                for call in _macro_calls(tex, ("evidencefigure", "frameworkfigure"))
            )
            graphics = {raw.replace("\\", "/") for raw in re.findall(r"\\includegraphics(?:\[[^]]*\])?\s*\{([^{}]+)\}", tex)}
            missing_labels = [fig.get("paper", {}).get("label") for fig in all_figures
                              if fig.get("paper", {}).get("label") not in labels]
            missing_labels.extend(item.get("paper", {}).get("label") for item in all_schematics
                                  if item.get("paper", {}).get("label") not in labels)
            missing_labels.extend(item.get("paper", {}).get("label") for item in all_tables
                                  if item.get("paper", {}).get("label") not in labels)
            add("planned_visual_labels_in_tex", not missing_labels,
                missing=sorted(set(label for label in missing_labels if label)))
            planned_labels = [
                str(item.get("paper", {}).get("label", "")).strip()
                for item in [*all_figures, *all_schematics]
                if str(item.get("paper", {}).get("label", "")).strip()
            ]
            narrative = figure_binding_audit(tex, planned_labels)
            add("planned_visuals_bound_to_source", not narrative["missing_binding"],
                missing=narrative["missing_binding"])
            add("planned_visuals_have_pre_reference", not narrative["missing_pre_reference"],
                missing=narrative["missing_pre_reference"],
                message="每张图前必须用唯一标签说明读图目的与口径")
            add("planned_visuals_have_substantive_caption", not narrative["weak_captions"],
                missing=narrative["weak_captions"],
                message="图注须说明对象、范围及必要的面板/颜色/箭头语义")
            add("planned_visuals_have_post_narrative", not narrative["missing_post_narrative"],
                missing=narrative["missing_post_narrative"],
                message="图后须解释至少一个具体证据、含义与边界，不能直接跳到下一标题")
            planned_names = {Path(str(fig.get("outputs", {}).get(key, ""))).name for fig in all_figures for key in ("vector", "preview")}
            planned_names.update(Path(str(item.get(key, ""))).name for item in all_schematics
                                 for key in ("output_pdf", "preview_png"))
            unplanned = [raw for raw in graphics if "求解" in raw and Path(raw).name not in planned_names]
            add("paper_result_graphics_are_planned", not unplanned, unplanned=unplanned)
            if schema_version == "1.2":
                actual_tex_total = count_numbered_figures(tex)
                locked_total = int(plan.get("figure_count_lock", {}).get("final_total", 0) or 0)
                add("paper_figure_count_matches_lock", actual_tex_total == locked_total,
                    locked_total=locked_total, tex_top_level_figures=actual_tex_total,
                    message="最终 LaTeX 的顶层 Figure 数必须与用户锁定值完全一致")

    status = "FAIL" if failures else "PASS"
    return {
        "status": status,
        "stage": stage,
        "plan": str(plan_path),
        "project_root": str(project_root),
        "summary": {
            "problems": problem_summaries,
            "figures": len(all_figures),
            "numbered_figures": actual_figure_total,
            "tables": len(all_tables),
            "schematics": len(all_schematics),
            "failures": len(failures),
            "warnings": len(warnings),
        },
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--stage", choices=("plan", "render", "paper"), default="plan")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--main-tex", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    plan = args.plan.resolve()
    project_root = args.project_root.resolve() if args.project_root else (
        plan.parent.parent if plan.parent.name == "求解" else plan.parent
    )
    main_tex = args.main_tex.resolve() if args.main_tex else None
    result = audit(plan, args.stage, project_root, main_tex)
    report = args.report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
