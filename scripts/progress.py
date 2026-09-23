#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""progress.py — P0–P6 进度与内容级门禁检查。

不是只查文件存在，而是查"内容达标"：
  - P1 读题审计 + 题型判定 + **用户确认记录**（无确认不得进入求解）
  - P2 模型假设必须 ≥3 条
  - P3 验证必须有 ≥1 种验证手段的结果文件
  - P4 论文必须有摘要/结论等章节
  - P5 终稿不得残留 TODO/占位符
空目录应 FAIL，完整目录应 PASS。

用法:
  python scripts/progress.py --root . --all
  python scripts/progress.py --root . --gate P2
  python scripts/progress.py --root . --gate P3 --json
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PHASES = ["P0", "P1", "P2", "P3", "P4", "P5", "P6"]
CHECKLIST_PATH = Path(__file__).resolve().parents[1] / "assets" / "checklists" / "paper_checklist.json"
PROVENANCE_SCHEMA = "paper-checklist-provenance-v1"
SUBMISSION_SCHEMA = "submission-audit-v1"
SUBMISSION_REPORT_NAME = "submission_audit.json"
FRAMEWORK_BINDING_NAME = "F01_framework_binding.json"
FRAMEWORK_REPORT_NAME = "F01_framework_audit.json"


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        return ""


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _paper_source_sha256(path: Path) -> str | None:
    """Hash the paper input and local TeX/Bib sources without hashing bulky outputs."""
    if not path.is_file():
        return None
    sources = [path]
    if path.suffix.lower() == ".tex":
        sources = sorted({path} | {
            source
            for suffix in ("*.tex", "*.bib")
            for source in path.parent.rglob(suffix)
            if source.is_file()
        })
    digest = hashlib.sha256()
    for source in sources:
        relative = source.relative_to(path.parent).as_posix() if source != path else path.name
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _canonical_sha256(value) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256_tree(path: Path) -> str | None:
    if not path.is_dir():
        return None
    files = sorted(item for item in path.rglob("*") if item.is_file())
    if not files:
        return None
    digest = hashlib.sha256()
    for item in files:
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_provenance(
        paper_path: Path,
        report_dir: Path,
        sidecar_path: Path,
        statuses: dict[str, str],
        problems=None,
        archetype=None) -> dict:
    """Build portable metadata binding a report to its current inputs."""
    try:
        paper_relative = Path(os.path.relpath(paper_path, report_dir)).as_posix()
    except ValueError:
        paper_relative = ""
    payload = {
        "schema": PROVENANCE_SCHEMA,
        "generator_sha256": _sha256_file(Path(__file__).resolve().parent / "paper_checklist.py"),
        "paper_path": paper_relative,
        "paper_sha256": _paper_source_sha256(paper_path),
        "checklist_sha256": _sha256_file(CHECKLIST_PATH),
        "sidecar_sha256": _sha256_file(sidecar_path),
        "parameters": {"problems": problems, "archetype": archetype},
        "status_sha256": _canonical_sha256(statuses),
    }
    return {**payload, "fingerprint": _canonical_sha256(payload)}


def _gather_text(root: Path, exts=(".md", ".tex", ".txt", ".docx")) -> str:
    """汇总论文/求解目录下文本文件内容（docx 跳过二进制）。"""
    chunks = []
    for sub in ("论文", "求解", "."):
        d = root / sub if sub != "." else root
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if p.is_file() and p.suffix in (".md", ".tex", ".txt"):
                chunks.append(_read_text(p))
    return "\n".join(chunks)


def count_assumptions(text: str) -> int:
    """粗略数模型假设条数：命中'假设'附近的编号/项目行。"""
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"^(\d+[\.、)]|（\d+）|\(\d+\)|[-*•])", s) and ("假设" in s or "假定" in s):
            n += 1
    # 兜底：出现"模型假设"小节再数其下编号行
    return n


def has_user_confirmation(root: Path) -> bool:
    """反 AI 读题审计硬门禁：必须存在用户确认记录，才允许进入求解。

    兼容两种落盘形式：
      1) evidence-ledger.json（根目录或 题目/ 下），其中 user_confirmation 为真
         （布尔 True，或字符串 "true"/"yes"/"已确认"）。
      2) evidence-ledger.md / reading_audit.md 中出现明确的用户确认标记
         （"用户已确认" / "确认通过" / "user_confirmation: true" 等）。
    无任何确认记录 → 返回 False（P1 不通过，禁止抢跑求解）。
    """
    # 1) JSON 台账
    for rel in ("evidence-ledger.json", "题目/evidence-ledger.json",
                "evidence_ledger.json", "题目/evidence_ledger.json"):
        p = root / rel
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8-sig", errors="ignore"))
            except Exception:
                continue
            val = data.get("user_confirmation")
            if val is True or str(val).strip().lower() in ("true", "yes", "已确认", "确认"):
                return True
    # 2) Markdown 台账 / 读题审计报告中的确认标记
    for rel in ("evidence-ledger.md", "题目/evidence-ledger.md",
                "题目/reading_audit.md", "reading_audit.md"):
        p = root / rel
        if not p.is_file():
            continue
        text = _read_text(p)
        if re.search(r"(用户已确认|确认通过|用户确认\s*[:：=]?\s*是|user_confirmation\s*[:：=]\s*true|裁决已记录)", text, re.I):
            return True
    return False


def has_validation_result(root: Path) -> bool:
    """是否存在验证结果文件/关键词。"""
    for pat in ("*验证*", "*validation*", "*对比*", "*sensitivity*", "*灵敏度*", "*消融*"):
        if list(root.rglob(pat)):
            return True
    text = _gather_text(root)
    return bool(re.search(r"(误差|RMSE|对比|灵敏度|鲁棒|消融|交叉验证|对标)", text))


def has_locked_figure_count(root: Path) -> bool:
    """Check the user-confirmed top-level Figure lock without duplicating full plan QA."""
    for path in _visual_plan_candidates(root):
        if not path.is_file():
            continue
        try:
            plan = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        lock = plan.get("figure_count_lock", {})
        actual = len(plan.get("global_figures", []))
        for problem in plan.get("problems", []):
            actual += len(problem.get("figures", [])) + len(problem.get("schematics", []))
        proposed = int(lock.get("proposed_total", 0) or 0)
        requested = lock.get("user_requested_total")
        expected = int(requested) if requested is not None else proposed
        if (
            plan.get("schema_version") == "1.2"
            and plan.get("plan_status") == "ready"
            and lock.get("status") == "locked"
            and lock.get("counting_rule") == "numbered_top_level_figures"
            and proposed > 0
            and int(lock.get("final_total", 0) or 0) == expected == actual > 0
            and len(str(lock.get("confirmation_record", "")).strip()) >= 4
        ):
            return True
    return False


def has_user_page_decision(root: Path) -> bool:
    """Accept a numeric user lock or an explicit user choice of no fixed target."""
    candidates = [root / "config" / "contest.json", root / "contest.json"]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            config = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        target = config.get("paper", {}).get("internal_total_page_target", {})
        mode = str(target.get("mode", ""))
        authority = str(target.get("authority", ""))
        if mode == "user_locked" and int(target.get("target", 0) or 0) > 0 and authority.startswith("user_"):
            return True
        if mode == "off" and authority == "user_decision_no_fixed_target":
            return True
    return False


def _visual_plan_candidates(root: Path) -> list[Path]:
    return [root / "求解" / "视觉计划.json", root / "visual-plan.json", root / "视觉计划.json"]


def _complex_f01_declaration(root: Path) -> tuple[bool, list[str], list[str]]:
    """Return whether the visual plan declares a paper-level F01 and explicit paths."""
    declared = False
    bindings: list[str] = []
    reports: list[str] = []
    for path in _visual_plan_candidates(root):
        if not path.is_file():
            continue
        try:
            plan = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        entries = list(plan.get("global_figures", []))
        for problem in plan.get("problems", []):
            if isinstance(problem, dict):
                entries.extend(problem.get("figures", []))
                entries.extend(problem.get("schematics", []))
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("figure_id") != "F01":
                continue
            route = str(entry.get("route", "")).casefold()
            if (
                    entry.get("role") == "complex_multi_question_framework"
                    or entry.get("complex_framework") is True
                    or "paper-framework-figure-studio-pro" in route
                    or entry.get("framework_binding")):
                declared = True
            if isinstance(entry.get("framework_binding"), str):
                bindings.append(entry["framework_binding"])
            if isinstance(entry.get("framework_audit_report"), str):
                reports.append(entry["framework_audit_report"])
    return declared, bindings, reports


def _unique_existing_named_files(root: Path, name: str) -> list[Path]:
    return sorted({path.resolve() for path in root.rglob(name) if path.is_file()})


def _resolve_declared_file(raw: str, root: Path) -> Path | None:
    path = Path(raw)
    if path.is_absolute():
        return None
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def validate_framework_figure_report(
        report_path: Path,
        binding_path: Path,
        root: Path,
        *,
        expected_source: Path | None = None,
        expected_pdf: Path | None = None,
        require_submission_binding: bool = False) -> tuple[bool, str]:
    """Require a current paper-stage F01 report and rerun its authoritative audit."""
    if report_path.parent.resolve() != binding_path.parent.resolve():
        return False, "F01 结构化报告必须与 binding 位于同一目录"
    try:
        stored = json.loads(report_path.read_text(encoding="utf-8-sig"))
        binding = json.loads(binding_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return False, f"F01 结构化审计产物无法解析：{exc}"
    if not isinstance(stored, dict) or stored.get("stage") != "paper":
        return False, "F01 结构化报告必须来自 stage=paper"
    if stored.get("status") != "PASS":
        return False, "F01 结构化报告不是 PASS"
    raw_report_binding = stored.get("binding")
    if not isinstance(raw_report_binding, str):
        return False, "F01 结构化报告未绑定 binding 文件"
    reported_binding = Path(raw_report_binding)
    if not reported_binding.is_absolute():
        reported_binding = (report_path.parent / reported_binding).resolve()
    if reported_binding.resolve() != binding_path.resolve():
        return False, "F01 结构化报告绑定了其他 binding 文件"

    try:
        from audit_framework_figure import audit, resolve_project_file  # type: ignore
    except ImportError as exc:
        return False, f"无法加载 F01 权威审计：{exc}"
    main_tex = resolve_project_file(root, binding.get("main_tex"))
    compiled_pdf = resolve_project_file(root, binding.get("compiled_pdf"))
    if require_submission_binding and (expected_source is None or expected_pdf is None):
        return False, "P6 F01 审计无法取得同一提交链的 TeX 主稿或最终 PDF"
    if expected_source is not None and (
            main_tex is None or main_tex.resolve() != expected_source.resolve()):
        return False, "F01 binding 的 main_tex 与当前权威 TeX 主稿不一致"
    if expected_pdf is not None and (
            compiled_pdf is None or compiled_pdf.resolve() != expected_pdf.resolve()):
        return False, "F01 binding 的 compiled_pdf 与当前最终提交 PDF 不一致"

    try:
        current = audit(binding_path.resolve(), root.resolve(), stage="paper")
    except Exception as exc:
        return False, f"F01 权威审计现场重跑失败：{exc}"
    if current.get("status") != "PASS":
        return False, "F01 权威审计现场重跑未通过"
    if _canonical_sha256(stored) != _canonical_sha256(current):
        return False, "F01 结构化报告已陈旧或与现场重跑不一致"
    return True, "F01 binding、正式图、TeX 与编译 PDF 已现场复核"


def framework_figure_gate(
        root: Path,
        *,
        expected_source: Path | None = None,
        expected_pdf: Path | None = None,
        require_submission_binding: bool = False) -> tuple[bool, str]:
    """Gate only explicitly declared or materially present complex F01 projects."""
    declared, explicit_bindings, explicit_reports = _complex_f01_declaration(root)
    named_bindings = _unique_existing_named_files(root, FRAMEWORK_BINDING_NAME)
    if not declared and not named_bindings:
        return True, "不适用（未声明复杂多问 F01）"

    if explicit_bindings:
        resolved = [_resolve_declared_file(raw, root) for raw in explicit_bindings]
        if len(explicit_bindings) != 1 or resolved[0] is None:
            return False, "复杂 F01 必须声明唯一且有效的 framework_binding 相对路径"
        binding_path = resolved[0]
    elif len(named_bindings) == 1:
        binding_path = named_bindings[0]
    elif not named_bindings:
        return False, f"复杂 F01 已声明，但缺少 {FRAMEWORK_BINDING_NAME}"
    else:
        return False, "发现多个 F01 binding；请在视觉计划中声明唯一 framework_binding"

    if explicit_reports:
        resolved_reports = [_resolve_declared_file(raw, root) for raw in explicit_reports]
        if len(explicit_reports) != 1 or resolved_reports[0] is None:
            return False, "复杂 F01 必须声明唯一且有效的 framework_audit_report 相对路径"
        report_path = resolved_reports[0]
    else:
        report_path = binding_path.with_name(FRAMEWORK_REPORT_NAME)
    if not report_path.is_file():
        return False, f"复杂 F01 缺少 paper-stage 结构化报告 {report_path.name}"
    return validate_framework_figure_report(
        report_path,
        binding_path,
        root,
        expected_source=expected_source,
        expected_pdf=expected_pdf,
        require_submission_binding=require_submission_binding,
    )


def has_plausible_final_pdf(root: Path) -> bool:
    """Reject empty/header-only PDF placeholders without adding a PDF dependency."""
    for path in root.rglob("*.pdf"):
        try:
            size = path.stat().st_size
            if size < 1024:
                continue
            with path.open("rb") as stream:
                header = stream.read(8)
                stream.seek(max(0, size - 4096))
                trailer = stream.read()
            if header.startswith(b"%PDF-") and b"startxref" in trailer and b"%%EOF" in trailer:
                return True
        except OSError:
            continue
    return False


# --- 优秀论文自检表门禁（Wave6-B）---

def _find_selfcheck(root: Path, names):
    """在比赛工作目录 论文/ 与根下查找自检表文件。"""
    for base in (root / "论文", root):
        for name in names:
            p = base / name
            if p.is_file():
                return p
    return None


def find_p4_checklist(root: Path):
    """P4：写作阶段的自检表（边写边勾）。"""
    return _find_selfcheck(root, (
        "优秀论文自检表.md", "论文自检表.md", "paper_checklist.md"))


def find_p6_checked(root: Path):
    """P6：已勾选自检表（100% 闭环产物）。"""
    return _find_selfcheck(root, (
        "论文自检表_已勾选.md", "优秀论文自检表_已勾选.md", "自检表_已勾选.md"))


def find_sidecar(root: Path):
    """P6：人工条目裁决 sidecar。"""
    return _find_selfcheck(root, ("paper_checklist_decisions.json",))


def _checklist_contract() -> tuple[set[str], set[str], str]:
    """Return all IDs, manual IDs and a load error for the canonical checklist."""
    try:
        data = json.loads(CHECKLIST_PATH.read_text(encoding="utf-8-sig"))
        items = data["items"]
        ids = [item["id"] for item in items]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return set(), set(), f"无法读取标准自检清单：{exc}"
    if not ids or len(ids) != len(set(ids)):
        return set(), set(), "标准自检清单为空或含重复 ID"
    manual_ids = {
        item["id"] for item in items
        if item.get("check_method") == "manual"
    }
    if not manual_ids:
        return set(), set(), "标准自检清单未定义人工条目"
    return set(ids), manual_ids, ""


def _decision_mapping(data) -> tuple[dict | None, str]:
    """Normalize the current mapping schema and the former list wrapper."""
    if isinstance(data, dict) and not any(
            key in data for key in ("decisions", "items", "checklist", "results")):
        return data, ""

    records = data
    if isinstance(data, dict):
        wrappers = [
            data[key] for key in ("decisions", "items", "checklist", "results")
            if key in data
        ]
        if len(wrappers) != 1:
            return None, "旧版 sidecar 必须且只能包含一个裁决列表"
        records = wrappers[0]
    if isinstance(records, dict):
        return records, ""
    if not isinstance(records, list):
        return None, "sidecar 必须是 ID 到裁决的映射"

    decisions = {}
    for record in records:
        if not isinstance(record, dict) or not str(record.get("id", "")).strip():
            return None, "旧版 sidecar 的每条裁决必须包含 id"
        item_id = str(record["id"]).strip()
        if item_id in decisions:
            return None, f"sidecar 含重复 ID：{item_id}"
        decisions[item_id] = {
            "status": record.get("status"),
            "note": record.get("note", record.get("reason", "")),
        }
    return decisions, ""


def validate_sidecar(sidecar: Path) -> tuple[bool, str]:
    """Require one valid decision for every and only every manual checklist ID."""
    all_ids, manual_ids, error = _checklist_contract()
    if error:
        return False, error
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return False, f"sidecar 无法解析：{exc}"
    decisions, error = _decision_mapping(data)
    if error:
        return False, error

    supplied = set(decisions)
    unknown = sorted(supplied - all_ids)
    machine = sorted((supplied & all_ids) - manual_ids)
    missing = sorted(manual_ids - supplied)
    if unknown:
        return False, f"sidecar 含未知 ID：{', '.join(unknown[:5])}"
    if machine:
        return False, f"sidecar 不得覆盖机检 ID：{', '.join(machine[:5])}"
    if missing:
        return False, f"sidecar 缺少 {len(missing)} 个人工 ID（如 {', '.join(missing[:5])}）"

    for item_id in sorted(manual_ids):
        decision = decisions[item_id]
        if not isinstance(decision, dict):
            return False, f"{item_id} 的裁决必须是对象"
        status = str(decision.get("status", "")).strip().lower()
        if status not in {"pass", "na"}:
            return False, f"{item_id} 的状态必须为 pass 或 na"
        note = str(decision.get("note", decision.get("reason", ""))).strip()
        if status == "na" and len(note) < 4:
            return False, f"{item_id}=na 必须给出具体理由（至少 4 个字符）"
    return True, f"sidecar 完整覆盖 {len(manual_ids)} 个规范人工 ID"


_REPORT_ITEM_RE = re.compile(r"^-\s*(✅|❌|☐|➖)\s*\*\*([^*]+)\*\*", re.MULTILINE)
_REPORT_SUMMARY_RE = re.compile(
    r"^统计[：:]\s*✅\s*(\d+)\s*❌\s*(\d+)\s*☐\s*(\d+)\s*➖\s*(\d+)\s*$",
    re.MULTILINE,
)
_PROVENANCE_RE = re.compile(
    r"^<!--\s*paper-checklist-provenance:\s*(\{.*\})\s*-->$",
    re.MULTILINE,
)


def validate_checked_report(report: Path) -> tuple[bool, str]:
    """Verify the checked report is complete and its zero-failure summary is truthful."""
    all_ids, _, error = _checklist_contract()
    if error:
        return False, error
    text = _read_text(report)
    if not text.strip():
        return False, "已勾选报告为空"

    rows = _REPORT_ITEM_RE.findall(text)
    row_ids = [item_id.strip() for _, item_id in rows]
    if len(row_ids) != len(set(row_ids)):
        return False, "已勾选报告含重复 ID"
    missing = sorted(all_ids - set(row_ids))
    unknown = sorted(set(row_ids) - all_ids)
    if unknown:
        return False, f"已勾选报告含未知 ID：{', '.join(unknown[:5])}"
    if missing:
        return False, f"已勾选报告缺少 {len(missing)} 个清单 ID（如 {', '.join(missing[:5])}）"

    summaries = _REPORT_SUMMARY_RE.findall(text)
    if len(summaries) != 1:
        return False, "已勾选报告必须且只能包含一行规范统计"
    summary = tuple(map(int, summaries[0]))
    actual = tuple(sum(icon == marker for icon, _ in rows) for marker in ("✅", "❌", "☐", "➖"))
    if summary != actual:
        return False, "已勾选报告统计与逐项状态不一致"
    if summary[1] or summary[2]:
        return False, f"已勾选报告仍有 FAIL={summary[1]}、PENDING={summary[2]}"
    return True, f"已勾选报告完整，FAIL=0、PENDING=0（共 {len(all_ids)} 项）"


def validate_artifact_binding(report: Path, sidecar: Path, root: Path) -> tuple[bool, str]:
    """Bind report rows to the colocated sidecar and the current paper inputs."""
    if report.parent.resolve() != sidecar.parent.resolve():
        return False, "报告与 sidecar 必须位于同一目录"

    all_ids, manual_ids, error = _checklist_contract()
    if error:
        return False, error
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return False, f"sidecar 无法解析：{exc}"
    decisions, error = _decision_mapping(data)
    if error:
        return False, error

    text = _read_text(report)
    report_statuses = {
        item_id.strip(): icon for icon, item_id in _REPORT_ITEM_RE.findall(text)
    }
    expected_icons = {"pass": "✅", "na": "➖"}
    mismatches = []
    for item_id in sorted(manual_ids):
        decision = decisions.get(item_id)
        status = str(decision.get("status", "")).strip().lower() if isinstance(decision, dict) else ""
        expected = expected_icons.get(status)
        actual = report_statuses.get(item_id)
        if expected != actual:
            mismatches.append(f"{item_id}:{status or 'missing'}→{actual or 'missing'}")
    if mismatches:
        return False, "报告与 sidecar 人工裁决不一致：" + ", ".join(mismatches[:5])

    matches = _PROVENANCE_RE.findall(text)
    if len(matches) != 1:
        return False, "报告缺少唯一 provenance；旧报告须重新运行 paper_checklist（fail closed）"
    try:
        provenance = json.loads(matches[0])
    except (TypeError, ValueError) as exc:
        return False, f"报告 provenance 无法解析：{exc}"
    if not isinstance(provenance, dict) or provenance.get("schema") != PROVENANCE_SCHEMA:
        return False, "报告 provenance schema 不受支持；请重新运行 paper_checklist"

    paper_relative = provenance.get("paper_path")
    if not isinstance(paper_relative, str) or not paper_relative.strip():
        return False, "报告 provenance 未绑定论文路径"
    raw_paper_path = Path(paper_relative)
    if raw_paper_path.is_absolute():
        return False, "报告 provenance 不得记录绝对论文路径"
    paper_path = (report.parent / raw_paper_path).resolve()
    try:
        paper_path.relative_to(root.resolve())
    except ValueError:
        return False, "报告 provenance 的论文路径越出比赛工作目录"
    if not paper_path.is_file():
        return False, "报告 provenance 绑定的论文文件不存在"

    parameters = provenance.get("parameters")
    if not isinstance(parameters, dict) or set(parameters) != {"problems", "archetype"}:
        return False, "报告 provenance 缺少 problems/archetype 参数"
    if parameters["problems"] is not None and (
            not isinstance(parameters["problems"], int) or parameters["problems"] < 1):
        return False, "报告 provenance 的 problems 参数无效"
    if parameters["archetype"] is not None and not isinstance(parameters["archetype"], str):
        return False, "报告 provenance 的 archetype 参数无效"

    payload = {key: value for key, value in provenance.items() if key != "fingerprint"}
    expected = build_provenance(
        paper_path,
        report.parent,
        sidecar,
        report_statuses,
        parameters["problems"],
        parameters["archetype"],
    )
    if set(provenance) != set(expected):
        return False, "报告 provenance 字段集合不符合当前 schema"
    if provenance.get("fingerprint") != _canonical_sha256(payload):
        return False, "报告 provenance fingerprint 已损坏"
    for key in (
            "generator_sha256", "paper_path", "paper_sha256", "checklist_sha256",
            "sidecar_sha256", "parameters", "status_sha256", "fingerprint"):
        if provenance.get(key) != expected.get(key):
            return False, f"报告 provenance 已陈旧或被修改：{key} 不一致"
    if set(report_statuses) != all_ids:
        return False, "报告状态集合与当前清单不一致"

    try:
        from paper_checklist import (  # type: ignore
            PaperContext,
            load_checklist,
            run_machine_checks,
            split_sections,
        )
        from audit_tex import expand_tex_in_order, find_project_root  # type: ignore
    except ImportError as exc:
        return False, f"无法加载 paper_checklist 权威机检：{exc}"
    if paper_path.suffix.lower() != ".tex":
        return False, "P6 权威机检要求 provenance 绑定可读 TeX 主稿"
    try:
        context = PaperContext(
            tex_path=paper_path,
            docx_path=None,
            problems=parameters["problems"],
            archetype=parameters["archetype"],
            decisions=decisions,
        )
        project_root = find_project_root(paper_path.parent)
        context.tex_text, context.tex_expansion_errors = expand_tex_in_order(
            paper_path,
            project_root,
            base=paper_path.parent,
        )
        context.tex_lines = context.tex_text.splitlines()
        context.sections, _ = split_sections(context.tex_text)
        recomputed = run_machine_checks(context)
        machine_ids = {
            item["id"] for item in load_checklist()["items"]
            if item["check_method"] == "machine"
        }
    except Exception as exc:
        return False, f"paper_checklist 权威机检现场重算失败：{exc}"
    result_icons = {"pass": "✅", "fail": "❌", "pending": "☐", "na": "➖"}
    machine_mismatches = []
    for item_id in sorted(machine_ids):
        result = recomputed.get(item_id)
        expected_icon = result_icons.get(result.status) if result is not None else None
        actual_icon = report_statuses.get(item_id)
        if expected_icon != actual_icon:
            machine_mismatches.append(
                f"{item_id}:{getattr(result, 'status', 'missing')}→{actual_icon or 'missing'}"
            )
    if machine_mismatches:
        return False, "报告机器项与当前论文现场重算不一致：" + ", ".join(machine_mismatches[:5])
    return True, "报告、sidecar、论文、清单与参数 fingerprint 一致"


def _bound_relative_path(raw, base: Path, root: Path, *, directory=False) -> Path | None:
    if not isinstance(raw, str) or not raw.strip() or Path(raw).is_absolute():
        return None
    path = (base / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return path if (path.is_dir() if directory else path.is_file()) else None


def _checklist_bound_source(report: Path, root: Path) -> Path | None:
    matches = _PROVENANCE_RE.findall(_read_text(report))
    if len(matches) != 1:
        return None
    try:
        provenance = json.loads(matches[0])
    except (TypeError, ValueError):
        return None
    return _bound_relative_path(provenance.get("paper_path"), report.parent, root)


def _submission_bound_pdf(report: Path, root: Path) -> Path | None:
    try:
        data = json.loads(report.read_text(encoding="utf-8-sig"))
        provenance = data.get("provenance", {})
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(provenance, dict):
        return None
    return _bound_relative_path(provenance.get("paper_path"), report.parent, root)


def validate_submission_audit_report(
        path: Path, root: Path, expected_source: Path | None = None) -> tuple[bool, str]:
    """Verify and rerun the authoritative final-submission audit."""
    try:
        report = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return False, f"submission_audit 报告无法解析：{exc}"
    if not isinstance(report, dict) or report.get("schema") != SUBMISSION_SCHEMA:
        return False, "submission_audit 报告 schema 缺失或不受支持"
    if report.get("passed") is not True:
        return False, "submission_audit 报告不是 PASS"
    provenance = report.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("schema") != SUBMISSION_SCHEMA:
        return False, "submission_audit provenance 缺失或无效"

    paper = _bound_relative_path(provenance.get("paper_path"), path.parent, root)
    source = _bound_relative_path(provenance.get("source_path"), path.parent, root)
    manifest = _bound_relative_path(provenance.get("manifest_path"), path.parent, root)
    attachments = _bound_relative_path(
        provenance.get("attachments_path"), path.parent, root, directory=True
    )
    ai_raw = provenance.get("ai_file_path")
    ai_file = (
        _bound_relative_path(ai_raw, path.parent, root)
        if ai_raw is not None else None
    )
    if paper is None or paper.suffix.lower() != ".pdf":
        return False, "submission_audit 必须绑定比赛工作目录内的最终 PDF"
    if source is None or source.suffix.lower() != ".tex":
        return False, "submission_audit 必须绑定可读 TeX 主稿"
    if manifest is None or manifest.suffix.lower() != ".json":
        return False, "submission_audit 必须绑定可读的原始论文 manifest"
    if expected_source is None or source.resolve() != expected_source.resolve():
        return False, "submission_audit 绑定的 TeX 与 paper_checklist 审计源稿不一致"
    submission_dir = (root / "提交附件").resolve()
    try:
        paper.relative_to(submission_dir)
    except ValueError:
        return False, "submission_audit 绑定的最终 PDF 必须位于提交附件目录"
    if attachments is None or attachments.resolve() != submission_dir:
        return False, "submission_audit 必须绑定非空的提交附件目录"

    parameters = provenance.get("parameters")
    if not isinstance(parameters, dict) or set(parameters) != {
            "max_total_pages", "ai_used", "cover_policy"}:
        return False, "submission_audit 参数集合不完整"
    if parameters["ai_used"] == "unknown":
        return False, "P6 必须明确声明 AI 使用方式，不能为 unknown"
    if parameters["cover_policy"] != "required":
        return False, "P6 正式提交审计必须使用 cover_policy=required"
    if parameters["ai_used"] != "none" and ai_file is None:
        return False, "已声明使用 AI，但 submission_audit 未绑定 AI 说明文件"

    audit_view = {
        key: report.get(key)
        for key in ("passed", "pages", "ai_used", "cover_policy", "checks", "warnings")
    }
    payload = {key: value for key, value in provenance.items() if key != "fingerprint"}
    expected_fields = {
        "schema", "generator_sha256", "paper_path", "paper_sha256",
        "paper_page_count", "paper_page_sizes", "paper_text_sha256",
        "paper_render_sha256",
        "source_path", "source_tree_sha256",
        "manifest_path", "manifest_sha256",
        "attachments_path", "attachments_sha256", "ai_file_path", "ai_file_sha256",
        "parameters", "audit_sha256", "fingerprint",
    }
    if set(provenance) != expected_fields:
        return False, "submission_audit provenance 字段集合不符合当前 schema"
    try:
        from submission_audit import pdf_fingerprints, source_tree_sha256  # type: ignore
    except ImportError as exc:
        return False, f"无法加载 submission_audit 源树审计：{exc}"
    paper_fingerprints = pdf_fingerprints(paper)
    current_values = {
        "generator_sha256": _sha256_file(Path(__file__).resolve().parent / "submission_audit.py"),
        "paper_sha256": _sha256_file(paper),
        "paper_page_count": paper_fingerprints.get("page_count"),
        "paper_page_sizes": paper_fingerprints.get("page_sizes"),
        "paper_text_sha256": paper_fingerprints.get("text_sha256"),
        "paper_render_sha256": paper_fingerprints.get("render_sha256"),
        "source_tree_sha256": source_tree_sha256(source),
        "manifest_sha256": _sha256_file(manifest),
        "attachments_sha256": _sha256_tree(attachments),
        "ai_file_sha256": _sha256_file(ai_file) if ai_file else None,
        "audit_sha256": _canonical_sha256(audit_view),
    }
    if provenance.get("fingerprint") != _canonical_sha256(payload):
        return False, "submission_audit fingerprint 已损坏"
    for key, value in current_values.items():
        if provenance.get(key) != value:
            return False, f"submission_audit 已陈旧或被修改：{key} 不一致"

    command = [
        sys.executable,
        "-X", "utf8",
        str(Path(__file__).resolve().parent / "submission_audit.py"),
        "--paper", str(paper),
        "--source", str(source),
        "--manifest", str(manifest),
        "--attachments", str(attachments),
        "--ai-used", parameters["ai_used"],
        "--cover-policy", parameters["cover_policy"],
        "--json",
    ]
    if parameters["max_total_pages"] is not None:
        command.extend(["--max-total-pages", str(parameters["max_total_pages"])])
    if ai_file is not None:
        command.extend(["--ai-file", str(ai_file)])
    try:
        rerun = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"submission_audit 现场重跑失败：{exc}"
    try:
        current = json.loads(rerun.stdout)
    except ValueError:
        return False, "submission_audit 现场重跑未返回有效 JSON"
    current_view = {
        key: current.get(key)
        for key in ("passed", "pages", "ai_used", "cover_policy", "checks", "warnings")
    }
    if rerun.returncode != 0 or current.get("passed") is not True:
        return False, "submission_audit 现场重跑未通过"
    if _canonical_sha256(current_view) != provenance.get("audit_sha256"):
        return False, "submission_audit 报告与现场重跑结果不一致"
    return True, "submission_audit PASS，最终 PDF、附件与 AI 披露均已现场复核"


def count_undecided_decisions(sidecar: Path) -> int:
    """Backward-compatible API: only a fully valid sidecar has zero undecided items."""
    return 0 if validate_sidecar(sidecar)[0] else -1


def check_phase(phase: str, root: Path) -> tuple:
    """返回 (passed, [检查项])。每项 (ok, 描述)。"""
    items = []

    def need(cond, desc):
        items.append((bool(cond), desc))

    if phase == "P0":
        need(any((root / "题目").glob("*")) if (root / "题目").is_dir() else
             any(root.glob("*题*")) or any(root.glob("*.pdf")),
             "题面/题目文件已落盘")
        need((root / "config" / "contest.json").exists() or (root / "contest.json").exists(),
             "contest.json 存在")
        need(root.is_dir(), "工作目录存在")

    elif phase == "P1":
        text = _gather_text(root)
        need(re.search(r"约束|问题分析|拆解|直接目标", text), "有题面约束/问题拆解记录")
        need(re.search(r"原型|optimization|prediction|evaluation|匹配", text) or
             any(root.rglob("*match*")), "有题型/原型判定记录")
        need(has_user_confirmation(root), "反AI读题审计：存在用户确认记录（evidence-ledger user_confirmation=true）")
        need(has_locked_figure_count(root), "Figure 总数已由用户确认并写入视觉计划 1.2 锁")

    elif phase == "P2":
        text = _gather_text(root)
        n = count_assumptions(text)
        need(n >= 3, f"模型假设 ≥3 条（检出 {n} 条）")
        need(re.search(r"目标函数|min|max|minimize|maximize", text, re.I), "有目标函数/模型链")
        need(any(root.rglob("*.m")) or any(root.rglob("*.py")), "有 baseline 求解脚本")

    elif phase == "P3":
        need(any(root.rglob("*.m")) or any(root.rglob("*.py")), "有求解代码")
        need(any(root.rglob("*.mat")) or any(root.rglob("*.csv")) or any(root.rglob("*.json")),
             "有结构化结果落盘")
        need(has_validation_result(root), "有 ≥1 种验证手段的结果/记录")
        need(has_locked_figure_count(root), "visual plan 的 Figure 总数锁仍有效且与计划项一致")

    elif phase == "P4":
        text = _gather_text(root)
        need(re.search(r"摘\s*要|Abstract", text), "论文含摘要")
        need(re.search(r"结论|总结", text), "论文含结论")
        need(re.search(r"模型假设|问题重述|参考文献", text), "论文含主要章节")
        # 分章节清单检查：写作阶段边写边勾，工作目录下应有自检表
        need(find_p4_checklist(root) is not None,
             "分章节清单检查：比赛工作目录存在自检表（论文/优秀论文自检表.md）")
        need(has_user_page_decision(root),
             "用户已选择具体完整 PDF 页数，或明确选择“证据充分即可”")

    elif phase == "P5":
        text = _gather_text(root)
        need(not re.search(r"TODO|待补|占位|XXX|FIXME", text), "无 TODO/占位符残留")
        need(re.search(r"参考文献|References|\[\d+\]", text), "有参考文献/引用标注")
        anonymous_text = text
        for command in ("schoolname", "baominghao", "membera", "memberb", "memberc"):
            anonymous_text = re.sub(rf"\\{command}\s*\{{[^{{}}]*\}}", "", anonymous_text, flags=re.S)
        need(not re.search(r"大学|学院|导师|姓名", anonymous_text),
             "封皮后匿名化（官方封皮字段除外；启发式）")
        ok, detail = framework_figure_gate(root)
        need(ok, f"复杂 F01 专项审计：{detail}")

    elif phase == "P6":
        sub = root / "提交附件"
        need(sub.is_dir() and any(sub.glob("*")), "提交附件目录非空")
        text = _gather_text(root)
        need(re.search(r"人工智能工具|AI工具|人工智能辅助|AI辅助", text), "有 AI 使用披露")
        need(has_plausible_final_pdf(root), "有可解析结构特征的最终论文 PDF（拒绝空壳占位文件）")
        # 自检表 100% 闭环（Wave6-B 硬退出）
        checked_report = find_p6_checked(root)
        if checked_report is None:
            need(False, "P6 自检表闭环：《论文自检表_已勾选.md》缺失")
        else:
            ok, detail = validate_checked_report(checked_report)
            need(ok, f"P6 自检表闭环：{detail}")
        sidecar = find_sidecar(root)
        if sidecar is None:
            need(False, "人工条目裁决：待运行 paper_checklist（sidecar paper_checklist_decisions.json 缺失）")
        else:
            ok, detail = validate_sidecar(sidecar)
            need(ok, f"人工条目裁决：{detail}")
        if checked_report is not None and sidecar is not None:
            ok, detail = validate_artifact_binding(checked_report, sidecar, root)
            need(ok, f"P6 产物绑定：{detail}")
        submission_report = (
            checked_report.parent / SUBMISSION_REPORT_NAME
            if checked_report is not None else root / "论文" / SUBMISSION_REPORT_NAME
        )
        if not submission_report.is_file():
            need(False, f"权威提交审计报告缺失：{SUBMISSION_REPORT_NAME}")
            submission_pdf = None
        else:
            source = (
                _checklist_bound_source(checked_report, root)
                if checked_report is not None else None
            )
            submission_pdf = _submission_bound_pdf(submission_report, root)
            ok, detail = validate_submission_audit_report(
                submission_report, root, expected_source=source
            )
            need(ok, f"权威提交审计：{detail}")
        source = (
            _checklist_bound_source(checked_report, root)
            if checked_report is not None else None
        )
        ok, detail = framework_figure_gate(
            root,
            expected_source=source,
            expected_pdf=submission_pdf,
            require_submission_binding=True,
        )
        need(ok, f"复杂 F01 权威审计：{detail}")

    passed = all(ok for ok, _ in items)
    return passed, items


def main(argv=None):
    ap = argparse.ArgumentParser(description="P0-P6 内容级门禁检查")
    ap.add_argument("--root", default=".", help="比赛工作目录（默认当前目录）")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--gate", choices=PHASES, help="只检查单个阶段")
    g.add_argument("--all", action="store_true", help="检查全部阶段")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print(f"[FAIL] 目录不存在: {root}")
        return 1

    phases = [args.gate] if args.gate else PHASES
    results = {}
    overall = True
    for ph in phases:
        ok, items = check_phase(ph, root)
        results[ph] = {"passed": ok, "items": [{"ok": o, "desc": d} for o, d in items]}
        overall = overall and ok

    if args.json:
        print(__import__("json").dumps({"root": str(root), "overall": overall,
                                        "phases": results}, ensure_ascii=False, indent=2))
    else:
        for ph in phases:
            r = results[ph]
            print(f"[{ 'PASS' if r['passed'] else 'FAIL' }] {ph}")
            for it in r["items"]:
                print(f"    [{'x' if it['ok'] else ' '}] {it['desc']}")
        print(f"\n总体: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
