#!/usr/bin/env python3
# [来源] 移植自 v2.1 华为杯_论文规范模板/tools/，相对路径已改为 CLI 参数驱动，Wave3 验证编译链路。
"""Audit a rendered PDF against Huawei Cup page and chapter rules.

The audit is deliberately conservative. It reports confidence and unknowns
rather than pretending that broken Chinese PDF CMaps yield reliable text.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    import pymupdf
except ImportError:  # compatibility with older installations
    import fitz as pymupdf


IDENTITY_RE = re.compile(
    r"学校|学院|实验室|参赛队号|队员姓名|指导教师|学号|邮箱|email|"
    r"\b(?:school|student|team|member|advisor)\b|C:\\Users\\",
    re.IGNORECASE,
)
REFERENCE_RE = re.compile(r"^\s*(参考文献|References?)\s*$", re.IGNORECASE)
APPENDIX_RE = re.compile(r"^\s*(附录|Appendix)\s*[A-ZＡ-Ｚ0-9０-９]*\s*$", re.IGNORECASE)
PAGE_RE = re.compile(r"(?<!\d)(\d{1,3})(?!\d)")
COVER_MARKERS = ("学校", "参赛队号", "队员姓名")


def load_contest_config(start: Path, explicit: Path | None = None) -> dict:
    if explicit is not None:
        candidate = explicit.resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"比赛配置不存在: {candidate}")
        return json.loads(candidate.read_text(encoding="utf-8-sig"))
    for base in [start.resolve(), *start.resolve().parents]:
        candidate = base / "比赛配置.json"
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8-sig"))
    return {}


def resolve_body_gate(targets: dict, contest_config: dict) -> tuple[int, str, str]:
    """Return (minimum, mode, authority). mode: off|warning|error."""
    gate = contest_config.get("paper", {}).get("body_page_gate", {}) if contest_config else {}
    minimum = gate.get("minimum", targets.get("required_body_pages", 0))
    mode = str(gate.get("mode", targets.get("body_page_gate_mode", "warning"))).lower()
    authority = str(gate.get("authority", targets.get("body_page_gate_authority", "project_heuristic")))
    if mode not in {"off", "warning", "error"}:
        raise ValueError(f"body_page_gate.mode 无效: {mode}")
    return int(minimum or 0), mode, authority


def pdf_pages(pdf: Path) -> int:
    doc = pymupdf.open(str(pdf))
    count = len(doc)
    doc.close()
    return count


def extract_page_records(pdf: Path):
    doc = pymupdf.open(str(pdf))
    records = []
    for physical, page in enumerate(doc, 1):
        blocks = page.get_text("blocks")
        text = "\n".join(str(block[4]) for block in blocks if len(block) >= 5)
        spans = []
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    spans.append({
                        "text": span.get("text", ""),
                        "font": span.get("font", ""),
                        "size": span.get("size", 0),
                        "bbox": span.get("bbox", []),
                    })
        records.append({
            "physical_page": physical,
            "text": text,
            "spans": spans,
            "width": float(page.rect.width),
            "height": float(page.rect.height),
        })
    doc.close()
    return records


def first_page_text(page):
    return " ".join(line.strip() for line in page["text"].splitlines() if line.strip())


def detect_heading_pages(records, heading_manifest):
    output = []
    for item in heading_manifest:
        title = item.get("rendered_title") or item.get("title", "")
        aliases = [title, item.get("title", ""), *item.get("aliases", [])]
        # Word heading JSON records the exact visible title text and its page.
        # Keep all exact matches; the next heading determines the range.
        matches = []
        for record in records:
            text = first_page_text(record)
            if any(alias and alias in text for alias in aliases):
                matches.append(record["physical_page"])
        output.append({**item, "physical_pages": matches, "confidence": "high" if matches else "unknown"})
    return output


def detect_heading_pages_from_manifest(records, chapters):
    """Use rendered titles supplied by the generator when PDF CMaps are broken."""
    output = []
    for item in chapters:
        title = item.get("rendered_title") or item.get("title", "")
        normalized = re.sub(r"^[0-9.\s]+", "", title)
        matches = []
        for record in records:
            text = first_page_text(record)
            if normalized and normalized in text:
                matches.append(record["physical_page"])
        output.append({**item, "physical_pages": matches, "confidence": "medium" if matches else "unknown"})
    return output


def printed_page_offset(records):
    # Look near the footer; page labels are often the only short numeric block.
    for record in records[:8]:
        candidates = []
        for span in record["spans"]:
            text = span["text"].strip()
            if PAGE_RE.fullmatch(text):
                y = span["bbox"][3] if len(span["bbox"]) >= 4 else 0
                if y > record.get("height", 842) - 100:
                    candidates.append(int(text))
        if candidates:
            return candidates[0] - record["physical_page"]
    return 0


def centered_footer_numbers(record):
    """Return short numeric footer labels centered on the physical page."""
    labels = []
    width = record.get("width", 595)
    height = record.get("height", 842)
    for span in record["spans"]:
        text = span["text"].strip()
        bbox = span.get("bbox", [])
        if not PAGE_RE.fullmatch(text) or len(bbox) < 4:
            continue
        center_x = (bbox[0] + bbox[2]) / 2
        if bbox[3] > height - 100 and abs(center_x - width / 2) <= max(40, width * 0.1):
            labels.append(int(text))
    return labels


def header_text_spans(records):
    """Collect visible text in the header zone; official papers must have none."""
    hits = []
    for record in records:
        for span in record["spans"]:
            text = span["text"].strip()
            bbox = span.get("bbox", [])
            if text and len(bbox) >= 4 and bbox[1] < 55:
                hits.append({"page": record["physical_page"], "text": text[:100], "bbox": bbox})
    return hits


def role_ranges(chapters, records):
    # Use heading starts and the next heading, with references/appendix as body boundaries.
    starts = []
    for chapter in chapters:
        pages = chapter.get("physical_pages", [])
        if pages:
            starts.append((min(pages), chapter))
    starts.sort(key=lambda x: x[0])
    result = []
    for index, (start, chapter) in enumerate(starts):
        end = (starts[index + 1][0] - 1) if index + 1 < len(starts) else len(records)
        end = max(start, end)
        result.append({
            "title": chapter.get("title"),
            "role": chapter.get("role"),
            "level": chapter.get("level", 1),
            "start_physical_page": start,
            "end_physical_page": end,
            "touched_pages": max(0, end - start + 1),
        })
    return result


def body_pages(chapter_ranges):
    body = [item for item in chapter_ranges if item.get("role") not in {"references", "appendix"}]
    if not body:
        return {"start": None, "end": None, "pages": 0}
    start = min(item["start_physical_page"] for item in body)
    end = max(item["end_physical_page"] for item in body)
    return {"start": start, "end": end, "pages": end - start + 1}


def pdfinfo(pdf: Path) -> dict[str, str]:
    try:
        proc = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return {}
    # 中文 Windows 上 pdfinfo 可能输出 GBK 字节；按字节安全解码，避免 UnicodeDecodeError 崩溃。
    raw = proc.stdout or b""
    out = None
    for enc in ("utf-8", "gbk", "cp936", "latin-1"):
        try:
            out = raw.decode(enc); break
        except UnicodeDecodeError:
            continue
    if out is None:
        out = raw.decode("utf-8", errors="ignore")
    values = {}
    for line in out.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--heading-json", type=Path)
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--targets", type=Path)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--source", type=Path)
    ap.add_argument("--contest-config", type=Path, help="根目录比赛配置.json；省略时自动向上查找")
    args = ap.parse_args()
    pdf = args.pdf.resolve()
    records = extract_page_records(pdf)
    headings = json.loads(args.heading_json.read_text(encoding="utf-8-sig")) if args.heading_json and args.heading_json.exists() else {"headings": []}
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig")) if args.manifest and args.manifest.exists() else {"chapters": []}
    matched = detect_heading_pages(records, headings.get("headings", [])) if headings.get("headings") else []
    if not matched and manifest.get("chapters"):
        matched = detect_heading_pages(records, manifest["chapters"])
    if not any(item.get("physical_pages") for item in matched) and manifest.get("chapters"):
        matched = detect_heading_pages_from_manifest(records, manifest["chapters"])
    ranges = role_ranges(matched, records)
    body = body_pages(ranges)
    targets = json.loads(args.targets.read_text(encoding="utf-8-sig")) if args.targets and args.targets.exists() else {}
    contest_config = load_contest_config(pdf.parent, args.contest_config)
    required_body, body_gate_mode, body_gate_authority = resolve_body_gate(targets, contest_config)
    role_targets = targets.get("role_targets", {})
    issues = []
    for chapter in ranges:
        role_target = role_targets.get(chapter.get("role"), {})
        pages = chapter.get("touched_pages", 0)
        if role_target and (pages < role_target.get("min_pages", 0) or pages > role_target.get("max_pages", 10**9)):
            issues.append({
                "code": "chapter_pages_outside_role_window",
                "severity": "warning",
                "title": chapter.get("title"),
                "role": chapter.get("role"),
                "actual": pages,
                "min": role_target.get("min_pages"),
                "max": role_target.get("max_pages"),
            })
    if body_gate_mode != "off" and required_body > 0 and body["pages"] < required_body:
        issues.append({"code": "body_pages_below_minimum", "severity": "error" if body_gate_mode == "error" else "warning", "actual": body["pages"], "required": required_body, "gate_mode": body_gate_mode, "authority": body_gate_authority, "message": "页数门禁按比赛配置执行；当届官方规则优先于项目经验阈值。"})
    if not matched:
        issues.append({"code": "headings_not_detected", "severity": "warning", "message": "未检测到可靠的章节标题；请提供 Word 标题 JSON 或开启 OCR 复核。"})
    cover_text = re.sub(r"\s+", "", records[0]["text"]) if records else ""
    missing_cover_markers = [marker for marker in COVER_MARKERS if marker not in cover_text]
    if missing_cover_markers:
        issues.append({
            "code": "required_identity_cover_missing",
            "severity": "error",
            "missing_markers": missing_cover_markers,
            "message": "2026 正式提交 PDF 的物理首页必须是官方参赛信息封皮。",
        })
    anonymous_text = "\n".join(record["text"] for record in records[1:])
    identity_hits = sorted(set(IDENTITY_RE.findall(anonymous_text)))
    if identity_hits:
        issues.append({"code": "possible_identity_text_after_cover", "severity": "error", "matches": identity_hits[:20]})
    header_hits = header_text_spans(records[1:])
    if header_hits:
        issues.append({
            "code": "header_text_detected",
            "severity": "error",
            "message": "官方格式要求无页眉。",
            "spans": header_hits[:20],
        })
    cover_footer = centered_footer_numbers(records[0]) if records else []
    abstract_footer = centered_footer_numbers(records[1]) if len(records) >= 2 else []
    if 0 not in cover_footer:
        issues.append({
            "code": "cover_page_number_missing",
            "severity": "error",
            "message": "正式封皮页脚中部必须显示页码 0。",
            "labels": cover_footer,
        })
    if 1 not in abstract_footer:
        issues.append({
            "code": "abstract_page_number_missing",
            "severity": "error",
            "message": "摘要页页脚中部必须显示阿拉伯页码 1。",
            "labels": abstract_footer,
        })
    # We cannot prove font correctness from a PDF with broken CMaps, but can flag obvious fonts.
    fonts = sorted({span["font"] for record in records for span in record["spans"] if span.get("font")})
    forbidden_fonts = [font for font in fonts if any(token in font.lower() for token in ("lishu", "kaiti"))]
    if forbidden_fonts:
        issues.append({"code": "non_body_font_detected", "severity": "warning", "fonts": forbidden_fonts, "message": "标签可使用隶书；正文/关键词内容应人工确认是否为宋体。"})
    report = {
        "pdf": str(pdf),
        "pdfinfo": pdfinfo(pdf),
        "physical_pages": len(records),
        "printed_page_offset": printed_page_offset(records),
        "cover_page_centered_footer_numbers": cover_footer,
        "abstract_page_centered_footer_numbers": abstract_footer,
        "header_text_spans": header_hits,
        "body": body,
        "body_page_gate": {"minimum": required_body, "mode": body_gate_mode, "authority": body_gate_authority},
        "chapter_ranges": ranges,
        "detected_fonts": fonts,
        "issues": issues,
        "status": "FAIL" if any(item["severity"] == "error" for item in issues) else "PASS_WITH_WARNINGS" if issues else "PASS",
        "limitations": [
            "最终页数以本 PDF 为准；DOCX docProps/app.xml 的 Pages 不参与验收。",
            "中文字体 CMap 损坏时，章节/身份检测可能需要 OCR 或 Word 标题 JSON 交叉验证。",
            "问题章节区间是历史经验先验，不是要求所有章节等长。",
            "比赛配置.json 中的 official_rules_priority=true：当届官方页数/字数/格式规则优先；默认45页仅作经验预警。",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(1 if report["status"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
