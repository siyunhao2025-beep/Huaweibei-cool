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
import shutil
import subprocess
import unicodedata
from pathlib import Path

try:
    import pymupdf
except ImportError:  # compatibility with older installations
    import fitz as pymupdf


IDENTITY_RE = re.compile(
    r"(?:学校|学院|实验室|参赛队号|队员姓名|指导教师|学号|邮箱)\s*[:：]|"
    r"\b(?:school\s+of|student\s*(?:id|number)|team\s*(?:id|number)|"
    r"member\s+name|advisor\s+name|e-?mail)\b|C:\\Users\\",
    re.IGNORECASE,
)
REFERENCE_RE = re.compile(r"^\s*(参考文献|References?)\s*$", re.IGNORECASE)
APPENDIX_RE = re.compile(r"^\s*(附录|Appendix)\s*[A-ZＡ-Ｚ0-9０-９]*\s*$", re.IGNORECASE)
PAGE_RE = re.compile(r"(?<!\d)(\d{1,3})(?!\d)")
COVER_MARKERS = ("学校", "参赛队号", "队员姓名")
TITLE_BALANCE_MIN_RATIO = 0.85
ABSTRACT_BODY_BASELINE_PT = 12.0
ABSTRACT_BODY_MIN_PT = 11.5
ABSTRACT_BODY_MAX_PT = 12.5
TITLE_CONTENT_BASELINE_PT = 16.0
TITLE_CONTENT_MIN_PT = 15.5
TITLE_CONTENT_MAX_PT = 16.5
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


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


def resolve_body_gate(targets: dict, contest_config: dict) -> tuple[int, int | None, str, str]:
    """Return (minimum, maximum, mode, authority). mode: off|warning|error."""
    gate = contest_config.get("paper", {}).get("body_page_gate", {}) if contest_config else {}
    minimum = gate.get("minimum", targets.get("required_body_pages", 0))
    maximum = gate.get("maximum", targets.get("maximum_body_pages"))
    mode = str(gate.get("mode", targets.get("body_page_gate_mode", "off"))).lower()
    authority = str(gate.get("authority", targets.get("body_page_gate_authority", "not_configured")))
    if mode not in {"off", "warning", "error"}:
        raise ValueError(f"body_page_gate.mode 无效: {mode}")
    return int(minimum or 0), int(maximum) if maximum is not None else None, mode, authority


def resolve_internal_total_target(targets: dict, contest_config: dict) -> tuple[int, str, str]:
    """Return (target, mode, authority) for the user's non-official PDF decision."""
    fallback = targets.get("internal_total_page_target", {}) if targets else {}
    configured = contest_config.get("paper", {}).get("internal_total_page_target", {}) if contest_config else {}
    target_config = configured or fallback
    mode = str(target_config.get("mode", "off")).lower()
    if mode not in {"off", "user_decides", "user_locked", "evidence_conditional"}:
        raise ValueError(f"internal_total_page_target.mode 无效: {mode}")
    target = int(target_config.get("target", 0) or 0)
    authority = str(target_config.get("authority", "not_configured"))
    return target, mode, authority


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
        lines = []
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                line_spans = []
                for span in line.get("spans", []):
                    span_record = {
                        "text": span.get("text", ""),
                        "font": span.get("font", ""),
                        "size": span.get("size", 0),
                        "bbox": span.get("bbox", []),
                    }
                    spans.append(span_record)
                    line_spans.append(span_record)
                if line_spans:
                    lines.append({
                        "text": "".join(item["text"] for item in line_spans),
                        "bbox": line.get("bbox", []),
                        "spans": line_spans,
                    })
        records.append({
            "physical_page": physical,
            "text": text,
            "spans": spans,
            "lines": lines,
            "width": float(page.rect.width),
            "height": float(page.rect.height),
            "image_count": len(page.get_images(full=True)),
        })
    doc.close()
    return records


def _compact_text(value) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value or "")))


def _rendered_label_row(record: dict, label: str) -> str | None:
    """Return a rendered row only when it starts with the exact label."""
    rows = []
    for line in record.get("lines", []):
        text = _compact_text(line.get("text", ""))
        bbox = line.get("bbox", [])
        if not text or len(bbox) < 4:
            continue
        center = (float(bbox[1]) + float(bbox[3])) / 2
        row = next((item for item in rows if abs(item["baseline"] - center) <= 2.0), None)
        if row is None:
            row = {"baseline": center, "lines": []}
            rows.append(row)
        row["lines"].append({"text": text, "x": float(bbox[0])})
    rows.sort(key=lambda item: item["baseline"])
    pattern = re.compile(rf"^{re.escape(label)}[:：]")
    for row in rows:
        text = "".join(
            line["text"] for line in sorted(row["lines"], key=lambda item: item["x"])
        )
        if pattern.match(text):
            return text
    return None


def _title_render_lines(record: dict, title: str) -> list[dict]:
    """Return title-cell baselines between the rendered title/abstract labels."""
    title_compact = _compact_text(title)
    raw_lines = []
    for line in record.get("lines", []):
        text = _compact_text(line.get("text", ""))
        bbox = line.get("bbox", [])
        if text and len(bbox) >= 4:
            raw_lines.append({
                "text": text,
                "bbox": [float(value) for value in bbox[:4]],
                "spans": line.get("spans", []),
            })
    raw_lines.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))

    rows = []
    for line in raw_lines:
        center = (line["bbox"][1] + line["bbox"][3]) / 2
        row = next((item for item in rows if abs(item["baseline"] - center) <= 2.0), None)
        if row is None:
            row = {"baseline": center, "lines": []}
            rows.append(row)
        row["lines"].append(line)
    rows.sort(key=lambda item: item["baseline"])
    for row in rows:
        row["lines"].sort(key=lambda item: item["bbox"][0])
        row["text"] = "".join(item["text"] for item in row["lines"])

    title_label_row = next(
        (row for row in rows if re.match(r"^题目[:：]", row["text"])),
        None,
    )
    abstract_label_row = next(
        (
            row for row in rows
            if title_label_row is not None
            and row["baseline"] > title_label_row["baseline"]
            and re.match(r"^摘要[:：]", row["text"])
        ),
        None,
    )
    if title_label_row is None or abstract_label_row is None:
        return []

    label_parts = []
    label_text = ""
    for line in title_label_row["lines"]:
        label_parts.append(line)
        label_text += line["text"]
        if "题目" in label_text:
            break
    label_right = max(line["bbox"][2] for line in label_parts)
    candidates = [
        line for line in raw_lines
        if (line["bbox"][1] + line["bbox"][3]) / 2
        >= title_label_row["baseline"] - 2.0
        and (line["bbox"][1] + line["bbox"][3]) / 2
        < abstract_label_row["baseline"] - 2.0
        and line not in label_parts
        and line["bbox"][0] >= label_right - 2.0
    ]
    compact = "".join(item["text"] for item in candidates)
    start = compact.find(title_compact)
    if not title_compact or start < 0:
        return []
    end = start + len(title_compact)
    contributing = []
    cursor = 0
    for line in candidates:
        next_cursor = cursor + len(line["text"])
        if max(cursor, start) < min(next_cursor, end):
            contributing.append(line)
        cursor = next_cursor

    groups = []
    for line in contributing:
        x0, y0, x1, y1 = line["bbox"]
        center = (y0 + y1) / 2
        matched = next(
            (group for group in groups if abs(group["baseline"] - center) <= 2.0),
            None,
        )
        if matched is None:
            groups.append({
                "baseline": center,
                "bbox": [x0, y0, x1, y1],
                "text": line["text"],
                "spans": list(line["spans"]),
            })
        else:
            matched["bbox"] = [
                min(matched["bbox"][0], x0),
                min(matched["bbox"][1], y0),
                max(matched["bbox"][2], x1),
                max(matched["bbox"][3], y1),
            ]
            matched["text"] += line["text"]
            matched["spans"].extend(line["spans"])
    groups.sort(key=lambda item: item["baseline"])
    for group in groups:
        group["width"] = group["bbox"][2] - group["bbox"][0]
    return groups


def _title_content_font_audit(title_lines: list[dict]) -> dict:
    """Verify that rendered title content keeps the template's 16 pt size."""
    details = {
        "verifiable": False,
        "template_baseline_pt": TITLE_CONTENT_BASELINE_PT,
        "minimum_pt": TITLE_CONTENT_MIN_PT,
        "maximum_pt": TITLE_CONTENT_MAX_PT,
        "dominant_pt": None,
        "size_weight_histogram": {},
    }
    histogram: dict[float, int] = {}
    for line in title_lines:
        for span in line.get("spans", []):
            text = _compact_text(span.get("text", ""))
            try:
                size = round(float(span.get("size", 0)), 1)
            except (TypeError, ValueError):
                continue
            if not text or size <= 0:
                continue
            histogram[size] = histogram.get(size, 0) + len(text)
    if not histogram:
        return {
            "details": details,
            "failures": [{"code": "abstract_page_title_font_size_unverifiable"}],
        }

    dominant = max(histogram, key=lambda size: (histogram[size], size))
    details.update({
        "verifiable": True,
        "dominant_pt": dominant,
        "size_weight_histogram": {
            f"{size:.1f}": histogram[size] for size in sorted(histogram)
        },
    })
    failures = []
    if not TITLE_CONTENT_MIN_PT <= dominant <= TITLE_CONTENT_MAX_PT:
        failures.append({
            "code": "abstract_page_title_font_out_of_range",
            "actual_pt": dominant,
            "minimum_pt": TITLE_CONTENT_MIN_PT,
            "maximum_pt": TITLE_CONTENT_MAX_PT,
            "template_baseline_pt": TITLE_CONTENT_BASELINE_PT,
        })
    return {"details": details, "failures": failures}


def _is_math_or_script_span(span_record: dict) -> bool:
    """Allow tiny non-CJK math symbols or genuinely shifted scripts only."""
    text = _compact_text(span_record.get("text", ""))
    if not text or CJK_RE.search(text):
        return False
    if "math" in str(span_record.get("font", "")).casefold():
        return True
    if all(
            unicodedata.category(character).startswith("S")
            or character in "+-=<>/|()[]{}.,:;"
            for character in text):
        return True

    span_bbox = span_record.get("bbox", [])
    line_bbox = span_record.get("line_bbox", [])
    if len(span_bbox) < 4 or len(line_bbox) < 4:
        return False
    line_height = float(line_bbox[3]) - float(line_bbox[1])
    if line_height <= 0:
        return False
    span_center = (float(span_bbox[1]) + float(span_bbox[3])) / 2
    line_center = (float(line_bbox[1]) + float(line_bbox[3])) / 2
    shifted = abs(span_center - line_center) >= max(1.5, line_height * 0.15)
    math_like = all(
        character.isascii() and (character.isalnum() or character in "+-=<>/|()[]{}.,:;")
        or unicodedata.category(character).startswith("S")
        for character in text
    )
    return shifted and math_like and len(text) <= 4


def _abstract_body_font_audit(record: dict) -> dict:
    """Audit abstract body and keyword-content sizes against the 12 pt template."""
    details = {
        "verifiable": False,
        "template_baseline_pt": ABSTRACT_BODY_BASELINE_PT,
        "minimum_pt": ABSTRACT_BODY_MIN_PT,
        "maximum_pt": ABSTRACT_BODY_MAX_PT,
        "dominant_pt": None,
        "size_weight_histogram": {},
        "ignored_small_span_weight_ratio": 0.0,
        "keyword_content_span_count": 0,
        "keyword_label_row_text": None,
        "audited_body_text": "",
        "audited_keyword_content_text": "",
    }
    failures = []
    lines = []
    for line in record.get("lines", []):
        text = _compact_text(line.get("text", ""))
        bbox = line.get("bbox", [])
        if text and len(bbox) >= 4:
            lines.append({
                "text": text,
                "bbox": [float(value) for value in bbox[:4]],
                "spans": line.get("spans", []),
            })
    lines.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))

    rows = []
    for line in lines:
        center = (line["bbox"][1] + line["bbox"][3]) / 2
        row = next((item for item in rows if abs(item["baseline"] - center) <= 2.0), None)
        if row is None:
            row = {"baseline": center, "lines": []}
            rows.append(row)
        row["lines"].append(line)
    rows.sort(key=lambda item: item["baseline"])
    for row in rows:
        row["text"] = "".join(
            line["text"] for line in sorted(row["lines"], key=lambda item: item["bbox"][0])
        )
    abstract_row = next(
        (row for row in rows if re.match(r"^摘要[:：]", row["text"])),
        None,
    )
    keywords_row = next(
        (
            row for row in rows
            if abstract_row is not None
            and row["baseline"] > abstract_row["baseline"]
            and re.match(r"^关键词[:：]", row["text"])
        ),
        None,
    )
    if abstract_row is None or keywords_row is None:
        failures.append({"code": "abstract_body_font_region_unverifiable"})
        return {"details": details, "failures": failures}

    span_records = []
    for line in lines:
        center = (line["bbox"][1] + line["bbox"][3]) / 2
        scope = None
        if abstract_row["baseline"] + 2.0 < center < keywords_row["baseline"] - 2.0:
            scope = "body"
        elif abs(center - keywords_row["baseline"]) <= 2.0:
            scope = "keywords"
        elif (
                center > keywords_row["baseline"] + 2.0
                and line["bbox"][3] < float(record.get("height", 841.89)) - 100.0
                and not re.fullmatch(r"\d{1,3}", line["text"])):
            scope = "keywords"
        if scope is None:
            continue

        keyword_label_remaining = (
            "关键词"
            if abs(center - keywords_row["baseline"]) <= 2.0
            and "关键词" in line["text"]
            else ""
        )
        for span in line["spans"]:
            text = _compact_text(span.get("text", ""))
            try:
                size = round(float(span.get("size", 0)), 1)
            except (TypeError, ValueError):
                continue
            if not text or size <= 0:
                continue

            if keyword_label_remaining:
                consumed = 0
                while (
                        consumed < len(text)
                        and keyword_label_remaining
                        and text[consumed] == keyword_label_remaining[0]):
                    keyword_label_remaining = keyword_label_remaining[1:]
                    consumed += 1
                if keyword_label_remaining:
                    continue
                text = text[consumed:].lstrip(":：")
            if not text:
                continue
            bbox = span.get("bbox", [])
            span_records.append({
                "text": text,
                "size": size,
                "weight": len(text),
                "scope": scope,
                "font": span.get("font", ""),
                "bbox": [float(value) for value in bbox[:4]] if len(bbox) >= 4 else [],
                "line_bbox": line["bbox"],
            })

    histogram: dict[float, int] = {}
    ignored_weight = 0
    total_weight = sum(item["weight"] for item in span_records)
    for item in span_records:
        if item["size"] < ABSTRACT_BODY_MIN_PT and _is_math_or_script_span(item):
            ignored_weight += item["weight"]
            continue
        histogram[item["size"]] = histogram.get(item["size"], 0) + item["weight"]
    if not histogram:
        failures.append({"code": "abstract_body_font_size_unverifiable"})
        return {"details": details, "failures": failures}

    dominant = max(histogram, key=lambda size: (histogram[size], size))
    small_ratio = ignored_weight / total_weight if total_weight else 0.0
    details.update({
        "verifiable": True,
        "dominant_pt": dominant,
        "matches_template_baseline": abs(dominant - ABSTRACT_BODY_BASELINE_PT) <= 0.5,
        "size_weight_histogram": {
            f"{size:.1f}": histogram[size] for size in sorted(histogram)
        },
        "ignored_small_span_weight_ratio": round(small_ratio, 4),
        "keyword_content_span_count": sum(
            item["scope"] == "keywords" for item in span_records
        ),
        "keyword_label_row_text": keywords_row["text"],
        "audited_body_text": "".join(
            item["text"] for item in span_records if item["scope"] == "body"
        ),
        "audited_keyword_content_text": "".join(
            item["text"] for item in span_records if item["scope"] == "keywords"
        ),
    })
    if details["keyword_content_span_count"] == 0:
        failures.append({"code": "abstract_keyword_font_size_unverifiable"})
    if dominant < ABSTRACT_BODY_MIN_PT:
        failures.append({
            "code": "abstract_body_dominant_font_too_small",
            "actual_pt": dominant,
            "minimum_pt": ABSTRACT_BODY_MIN_PT,
            "template_baseline_pt": ABSTRACT_BODY_BASELINE_PT,
        })
    if dominant > ABSTRACT_BODY_MAX_PT:
        failures.append({
            "code": "abstract_body_dominant_font_too_large",
            "actual_pt": dominant,
            "maximum_pt": ABSTRACT_BODY_MAX_PT,
            "template_baseline_pt": ABSTRACT_BODY_BASELINE_PT,
        })

    for item in span_records:
        if item["scope"] == "keywords" and not (
                ABSTRACT_BODY_MIN_PT <= item["size"] <= ABSTRACT_BODY_MAX_PT):
            failures.append({
                "code": "abstract_keyword_content_font_out_of_range",
                "text": item["text"],
                "actual_pt": item["size"],
                "minimum_pt": ABSTRACT_BODY_MIN_PT,
                "maximum_pt": ABSTRACT_BODY_MAX_PT,
            })
        elif CJK_RE.search(item["text"]) and item["size"] < ABSTRACT_BODY_MIN_PT:
            failures.append({
                "code": "abstract_body_cjk_span_too_small",
                "text": item["text"],
                "actual_pt": item["size"],
                "minimum_pt": ABSTRACT_BODY_MIN_PT,
            })
        elif (
                item["size"] < ABSTRACT_BODY_MIN_PT
                and not _is_math_or_script_span(item)):
            failures.append({
                "code": "abstract_body_non_math_span_too_small",
                "text": item["text"],
                "actual_pt": item["size"],
                "minimum_pt": ABSTRACT_BODY_MIN_PT,
            })
    return {"details": details, "failures": failures}


def _page_content_before_title(record: dict, title: str) -> tuple[bool, list[str]]:
    """Return whether a body heading is present and substantive text before it."""
    title_compact = _compact_text(title)
    if not title_compact:
        return False, []
    rendered = []
    for line in record.get("lines", []):
        text = _compact_text(line.get("text", ""))
        bbox = line.get("bbox", [])
        if text and len(bbox) >= 4:
            rendered.append({"text": text, "bbox": [float(value) for value in bbox[:4]]})
    rendered.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    if rendered:
        rows = []
        height = float(record.get("height", 841.89))
        for line in rendered:
            center = (line["bbox"][1] + line["bbox"][3]) / 2
            if line["bbox"][3] > height - 100 and re.fullmatch(r"\d{1,3}", line["text"]):
                continue
            row = next((item for item in rows if abs(item["baseline"] - center) <= 2.0), None)
            if row is None:
                row = {"baseline": center, "lines": []}
                rows.append(row)
            row["lines"].append(line)
        rows.sort(key=lambda item: item["baseline"])
        texts = [
            "".join(line["text"] for line in sorted(row["lines"], key=lambda item: item["bbox"][0]))
            for row in rows
        ]
    else:
        texts = [_compact_text(line) for line in str(record.get("text", "")).splitlines()]
        texts = [text for text in texts if text]

    numbering = re.compile(
        r"^(?:"
        r"第[0-9０-９一二三四五六七八九十百]+(?:章|节|问|部分)|"
        r"[0-9０-９]+(?:[.．][0-9０-９]+)*|"
        r"[一二三四五六七八九十百]+|"
        r"[（(][0-9０-９一二三四五六七八九十百]+[）)]"
        r")[.．、：:]?"
    )
    allowed_title = re.compile(rf"^{re.escape(title_compact)}[：:。．.]?$")
    for index, text in enumerate(texts):
        candidates = [text]
        prefix = numbering.match(text)
        if prefix:
            candidates.append(text[prefix.end():])
        if any(allowed_title.fullmatch(candidate) for candidate in candidates):
            return True, texts[:index]
    return False, texts


def abstract_front_matter_audit(records: list[dict], manifest: dict) -> dict:
    """Audit the rendered anonymous abstract page against manifest metadata."""
    title = str(manifest.get("title", "")).strip() if isinstance(manifest, dict) else ""
    raw_keywords = manifest.get("keywords") if isinstance(manifest, dict) else None
    keywords = (
        [str(item).strip() for item in raw_keywords if str(item).strip()]
        if isinstance(raw_keywords, list) else []
    )
    details = {
        "verifiable": bool(title and keywords),
        "physical_abstract_page": 2,
        "physical_body_start_page": 3,
        "title": title,
        "keywords": keywords,
        "title_line_count": None,
        "title_line_bboxes": [],
        "title_two_line_width_ratio": None,
        "title_two_line_min_ratio": TITLE_BALANCE_MIN_RATIO,
        "title_two_line_min_ratio_authority": "internal_quality_rule_not_official",
    }
    failures = []
    if not details["verifiable"]:
        details["unverifiable_reason"] = "manifest 缺少非空 title 或 keywords"
        return {"details": details, "failures": failures}

    by_page = {record.get("physical_page"): record for record in records}
    page2 = by_page.get(2)
    page3 = by_page.get(3)
    if page2 is None:
        failures.append({"code": "abstract_physical_page_missing", "physical_page": 2})
        return {"details": details, "failures": failures}

    page2_text = _compact_text(page2.get("text", ""))
    title_compact = _compact_text(title)
    title_label_row = _rendered_label_row(page2, "题目")
    abstract_label_row = _rendered_label_row(page2, "摘要")
    keywords_label_row = _rendered_label_row(page2, "关键词")
    details["title_present"] = title_compact in page2_text
    details["title_label_present"] = title_label_row is not None
    details["abstract_label_present"] = abstract_label_row is not None
    details["keywords_label_present"] = keywords_label_row is not None
    details["label_rows"] = {
        "title": title_label_row,
        "abstract": abstract_label_row,
        "keywords": keywords_label_row,
    }
    font_audit = _abstract_body_font_audit(page2)
    details["abstract_body_font"] = font_audit["details"]
    failures.extend(font_audit["failures"])
    keyword_block_text = _compact_text(
        font_audit["details"].get("audited_keyword_content_text", "")
    )
    missing_keywords = [
        item for item in keywords if _compact_text(item) not in keyword_block_text
    ]
    details["missing_keywords"] = missing_keywords
    if not details["title_present"]:
        failures.append({"code": "abstract_page_title_missing", "physical_page": 2})
    if not details["title_label_present"]:
        failures.append({"code": "abstract_page_title_label_missing", "physical_page": 2})
    if not details["abstract_label_present"]:
        failures.append({"code": "abstract_page_abstract_label_missing", "physical_page": 2})
    if not details["keywords_label_present"]:
        failures.append({"code": "abstract_page_keywords_label_missing", "physical_page": 2})
    if missing_keywords:
        failures.append({
            "code": "abstract_page_keywords_missing",
            "physical_page": 2,
            "keywords": missing_keywords,
        })

    title_lines = _title_render_lines(page2, title)
    details["title_line_count"] = len(title_lines)
    details["title_line_bboxes"] = [line["bbox"] for line in title_lines]
    title_font_audit = _title_content_font_audit(title_lines)
    details["title_content_font"] = title_font_audit["details"]
    failures.extend(title_font_audit["failures"])
    if len(title_lines) not in {1, 2}:
        failures.append({
            "code": "abstract_page_title_line_count_invalid",
            "actual": len(title_lines),
            "allowed": [1, 2],
        })
    elif len(title_lines) == 2:
        widths = [line["width"] for line in title_lines]
        ratio = min(widths) / max(widths) if max(widths) > 0 else 0.0
        details["title_two_line_width_ratio"] = round(ratio, 4)
        if ratio < TITLE_BALANCE_MIN_RATIO:
            failures.append({
                "code": "abstract_page_title_two_line_unbalanced",
                "actual_ratio": round(ratio, 4),
                "minimum_ratio": TITLE_BALANCE_MIN_RATIO,
                "authority": "internal_quality_rule_not_official",
            })

    body_chapters = [
        chapter for chapter in manifest.get("chapters", [])
        if isinstance(chapter, dict)
        and str(chapter.get("role", "")) not in {"references", "appendix"}
        and str(chapter.get("title", "")).strip()
    ]
    def chapter_order(chapter):
        try:
            return int(chapter.get("order", 10**9))
        except (TypeError, ValueError):
            return 10**9

    body_chapters.sort(key=chapter_order)
    first_body_title = str(body_chapters[0]["title"]).strip() if body_chapters else ""
    details["first_body_title"] = first_body_title or None
    page3_text = _compact_text(page3.get("text", "")) if page3 else ""
    body_title_found, content_before_body = (
        _page_content_before_title(page3, first_body_title)
        if page3 is not None else (False, [])
    )
    details["first_body_title_on_page3"] = body_title_found
    details["page3_content_before_body_title"] = content_before_body
    details["keywords_label_repeated_on_page3"] = "关键词" in page3_text
    details["paper_title_repeated_on_page3"] = title_compact in page3_text
    if page3 is None or not body_title_found:
        failures.append({
            "code": "body_not_starting_on_physical_page3",
            "physical_page": 3,
            "expected_title": first_body_title or None,
        })
    elif content_before_body:
        failures.append({
            "code": "abstract_residue_before_body_on_physical_page3",
            "physical_page": 3,
            "content": content_before_body[:5],
        })
    if details["keywords_label_repeated_on_page3"]:
        failures.append({"code": "keywords_overflow_to_physical_page3", "physical_page": 3})
    if details["paper_title_repeated_on_page3"]:
        failures.append({"code": "paper_title_repeated_on_physical_page3", "physical_page": 3})
    return {"details": details, "failures": failures}


def first_page_text(page):
    return " ".join(line.strip() for line in page["text"].splitlines() if line.strip())


def detect_heading_pages(records, heading_manifest):
    output = []
    valid_pages = {record["physical_page"] for record in records}
    for item in heading_manifest:
        declared = item.get("physical_pages", item.get("physical_page"))
        if declared is not None:
            values = declared if isinstance(declared, list) else [declared]
            pages = []
            for value in values:
                try:
                    page = int(value)
                except (TypeError, ValueError):
                    continue
                if page in valid_pages and page not in pages:
                    pages.append(page)
            output.append({
                **item,
                "physical_pages": sorted(pages),
                "confidence": "declared" if pages else "invalid_declared_page",
            })
            continue
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


def _terminal_page_rows(record: dict) -> list[dict]:
    rows = []
    for index, line in enumerate(record.get("lines", [])):
        text = str(line.get("text", "")).strip()
        bbox = line.get("bbox", [])
        if text:
            rows.append({
                "text": text,
                "y": float(bbox[1]) if len(bbox) >= 4 else float(index),
                "index": index,
            })
    if rows:
        return rows
    return [
        {"text": text.strip(), "y": float(index), "index": index}
        for index, text in enumerate(str(record.get("text", "")).splitlines())
        if text.strip()
    ]


def _terminal_heading_matches(text: str, title: str, role: str) -> bool:
    candidate = _compact_text(text)
    target = _compact_text(title)
    if not candidate or not target:
        return False
    variants = {candidate}
    variants.add(re.sub(
        r"^(?:第?[一二三四五六七八九十百0-9]+(?:章|节|问)|"
        r"[0-9]+(?:\.[0-9]+)*(?:[.、]))",
        "",
        candidate,
    ))
    if role == "appendix":
        variants.add(re.sub(r"^附录[A-ZＡ-Ｚ0-9０-９]*", "", candidate))
        variants.add(re.sub(r"^Appendix[A-Z0-9]*", "", candidate, flags=re.IGNORECASE))
    return target in variants


def _rendered_appendix_heading(text: str) -> bool:
    compact = unicodedata.normalize("NFKC", str(text or "")).strip()
    return bool(re.fullmatch(
        r"(?:附录(?:\s*[A-Z0-9]+)?(?:\s+.+)?|"
        r"Appendix(?:\s+[A-Z0-9]+)?(?:\s+.+)?)",
        compact,
        re.IGNORECASE,
    ))


def terminal_chapter_page_audit(
        records: list[dict], manifest: dict, *, manifest_supplied: bool) -> dict:
    """Verify declared references/appendices begin at the top of physical pages."""
    details = {
        "verifiable": bool(manifest_supplied),
        "declared_reference_count": 0,
        "declared_appendix_count": 0,
        "rendered_appendix_pages": [],
        "chapters": [],
    }
    failures = []
    if not manifest_supplied:
        return {"details": details, "failures": failures}

    chapters = manifest.get("chapters", []) if isinstance(manifest, dict) else []
    if not isinstance(chapters, list):
        failures.append({"code": "terminal_chapter_manifest_invalid"})
        return {"details": details, "failures": failures}
    terminal = [
        chapter for chapter in chapters
        if isinstance(chapter, dict) and chapter.get("role") in {"references", "appendix"}
    ]
    references = [chapter for chapter in terminal if chapter.get("role") == "references"]
    appendices = [chapter for chapter in terminal if chapter.get("role") == "appendix"]
    details["declared_reference_count"] = len(references)
    details["declared_appendix_count"] = len(appendices)
    if len(references) != 1:
        failures.append({
            "code": "manifest_must_declare_one_references_chapter",
            "actual": len(references),
        })

    rendered_appendix_pages = []
    for record in records:
        if any(_rendered_appendix_heading(row["text"]) for row in _terminal_page_rows(record)):
            rendered_appendix_pages.append(record.get("physical_page"))
    details["rendered_appendix_pages"] = rendered_appendix_pages
    if rendered_appendix_pages and not appendices:
        failures.append({
            "code": "rendered_appendix_missing_manifest_role",
            "physical_pages": rendered_appendix_pages,
        })

    for chapter in terminal:
        title = str(chapter.get("rendered_title") or chapter.get("title") or "").strip()
        role = str(chapter.get("role"))
        matches = []
        for record in records:
            rows = _terminal_page_rows(record)
            for row in rows:
                if _terminal_heading_matches(row["text"], title, role):
                    matches.append((record, row, rows))
        entry = {
            "chapter_id": chapter.get("chapter_id"),
            "role": role,
            "title": title,
            "physical_pages": sorted({match[0].get("physical_page") for match in matches}),
            "starts_physical_page": False,
            "content_before_heading": [],
        }
        if len(matches) != 1:
            failures.append({
                "code": "terminal_chapter_heading_not_unique_in_pdf",
                "role": role,
                "title": title,
                "matches": len(matches),
            })
        else:
            record, heading, rows = matches[0]
            preceding = []
            for row in rows:
                if row is heading or (row["y"], row["index"]) >= (heading["y"], heading["index"]):
                    continue
                compact = _compact_text(row["text"])
                if compact and not PAGE_RE.fullmatch(compact):
                    preceding.append(row["text"])
            entry["content_before_heading"] = preceding
            entry["starts_physical_page"] = not preceding
            if preceding:
                failures.append({
                    "code": "terminal_chapter_does_not_start_physical_page",
                    "role": role,
                    "title": title,
                    "physical_page": record.get("physical_page"),
                    "content_before_heading": preceding[:5],
                })
        details["chapters"].append(entry)
    return {"details": details, "failures": failures}


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
    executable = shutil.which("pdfinfo")
    if executable is None:
        return {}
    try:
        proc = subprocess.run([executable, str(pdf)], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return {}
    # 中文 Windows 上 pdfinfo 可能输出 GBK 字节；按字节安全解码，避免 UnicodeDecodeError 崩溃。
    raw = proc.stdout or b""
    out = None
    for enc in ("utf-8", "gbk", "cp936", "latin-1"):
        try:
            out = raw.decode(enc)
            break
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
    manifest_supplied = bool(args.manifest and args.manifest.exists())
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig")) if manifest_supplied else {"chapters": []}
    matched = detect_heading_pages(records, headings.get("headings", [])) if headings.get("headings") else []
    if not matched and manifest.get("chapters"):
        matched = detect_heading_pages(records, manifest["chapters"])
    if not any(item.get("physical_pages") for item in matched) and manifest.get("chapters"):
        matched = detect_heading_pages_from_manifest(records, manifest["chapters"])
    ranges = role_ranges(matched, records)
    body = body_pages(ranges)
    targets = json.loads(args.targets.read_text(encoding="utf-8-sig")) if args.targets and args.targets.exists() else {}
    contest_config = load_contest_config(pdf.parent, args.contest_config)
    required_body, maximum_body, body_gate_mode, body_gate_authority = resolve_body_gate(targets, contest_config)
    internal_total_target, internal_target_mode, internal_target_authority = resolve_internal_total_target(
        targets, contest_config
    )
    paper_config = contest_config.get("paper", {}) if contest_config else {}
    role_windows_enabled = bool(paper_config.get("role_windows_enabled", targets.get("role_windows_enabled", False)))
    role_targets = targets.get("role_targets", {}) if role_windows_enabled else {}
    issues = []
    front_matter = abstract_front_matter_audit(records, manifest)
    if not front_matter["details"]["verifiable"]:
        issues.append({
            "code": "abstract_front_matter_unverifiable",
            "severity": "warning",
            "message": "manifest 缺少非空 title/keywords，不声称摘要页自动审计通过。",
        })
    for failure in front_matter["failures"]:
        issues.append({
            **failure,
            "severity": "error",
            "message": "物理第 2 页的题目、摘要、关键词或正文起页不符合摘要页内部门禁。",
        })
    terminal_pages = terminal_chapter_page_audit(
        records, manifest, manifest_supplied=manifest_supplied
    )
    for failure in terminal_pages["failures"]:
        issues.append({
            **failure,
            "severity": "error",
            "message": "manifest 终端章节声明或参考文献/附录的成品 PDF 物理分页不合规。",
        })
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
    if body_gate_mode != "off" and maximum_body is not None and body["pages"] > maximum_body:
        issues.append({"code": "body_pages_above_maximum", "severity": "error" if body_gate_mode == "error" else "warning", "actual": body["pages"], "maximum": maximum_body, "gate_mode": body_gate_mode, "authority": body_gate_authority, "message": "正文页数超过已配置的当届明确上限；请先确认该上限口径，再删减冗余并保留核心证据链。"})
    if internal_target_mode == "user_decides":
        issues.append({
            "code": "internal_total_page_target_pending_user_decision",
            "severity": "warning",
            "actual": len(records),
            "scope": "physical_pdf_pages",
            "authority": internal_target_authority,
            "message": "Figure 总数锁定后，须把证据支撑的预计页数区间交给用户；由用户回复“论文总页数：XX”或“论文长度：证据充分即可”。",
        })
    elif internal_target_mode == "user_locked" and internal_total_target > 0 and len(records) != internal_total_target:
        issues.append({
            "code": "user_locked_total_page_target_not_met",
            "severity": "warning",
            "actual": len(records),
            "target": internal_total_target,
            "scope": "physical_pdf_pages",
            "authority": internal_target_authority,
            "message": "完整 PDF 页数与用户锁定值不同。先调整真实证据的取舍与编排；不得用套话、重复图表、放大图表或强制分页凑到目标。",
        })
    elif internal_target_mode == "evidence_conditional" and internal_total_target > 0 and len(records) < internal_total_target:
        issues.append({
            "code": "internal_total_page_target_not_reached",
            "severity": "warning",
            "actual": len(records),
            "target": internal_total_target,
            "scope": "physical_pdf_pages",
            "authority": internal_target_authority,
            "message": f"内部 {internal_total_target}+ 目标尚未达到。先审计真实证据缺口；严禁用套话、重复图表、放大图表、强制分页或无效模型凑页。若证据已完整，应接受较短稿并说明原因。",
        })
    if not matched:
        issues.append({
            "code": "headings_not_detected",
            "severity": "error" if manifest.get("chapters") else "warning",
            "message": "未检测到可靠的章节标题；已提供章节清单时不能据此声称正文页数审计通过。",
        })
    if len(records) < 2:
        issues.append({
            "code": "paper_too_short_for_cover_and_abstract",
            "severity": "error",
            "actual_pages": len(records),
            "message": "正式稿至少需要独立封皮页和匿名摘要页。",
        })
    non_a4_pages = [
        record["physical_page"] for record in records
        if abs(record["width"] - 595.28) > 3 or abs(record["height"] - 841.89) > 3
    ]
    if non_a4_pages:
        issues.append({
            "code": "non_a4_page_geometry",
            "severity": "error",
            "pages": non_a4_pages,
            "message": "所有页面必须保持 A4 纵向尺寸。",
        })
    cover_text = re.sub(r"\s+", "", records[0]["text"]) if records else ""
    missing_cover_markers = [marker for marker in COVER_MARKERS if marker not in cover_text]
    if missing_cover_markers:
        issues.append({
            "code": "required_identity_cover_missing",
            "severity": "error",
            "missing_markers": missing_cover_markers,
            "message": "2026 正式提交 PDF 的物理首页必须是官方参赛信息封皮。",
        })
    cover_image_count = records[0]["image_count"] if records else 0
    if cover_image_count < 4:
        issues.append({
            "code": "official_cover_logos_not_confirmed",
            "severity": "error",
            "image_count": cover_image_count,
            "message": "封皮未检测到四个独立图像对象，不能确认四个官方 logo 均保留；请人工复核渲染页。",
        })
    anonymous_text = "\n".join(record["text"] for record in records[1:])
    if not anonymous_text.strip():
        issues.append({
            "code": "anonymous_pages_text_unreadable",
            "severity": "error",
            "message": "封皮后的文字无法提取，匿名性与章节结构不能自动确认。",
        })
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
    if cover_footer:
        issues.append({
            "code": "cover_page_number_visible",
            "severity": "error",
            "message": "按本项目用户裁决，正式封皮不得显示页码；匿名摘要页仍从 1 开始编号。",
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
    latin_fonts = sorted({
        span["font"]
        for record in records
        for span in record["spans"]
        if re.search(r"[A-Za-z0-9]", span.get("text", "")) and span.get("font")
    })
    exact_times = [font for font in latin_fonts if "timesnewroman" in re.sub(r"[^a-z]", "", font.lower())]
    compatible_times = [font for font in latin_fonts if any(
        token in re.sub(r"[^a-z]", "", font.lower())
        for token in ("texgyretermes", "timesroman", "nimbusroman")
    )]
    unexpected_latin_fonts = [font for font in latin_fonts if font not in exact_times and font not in compatible_times]
    if unexpected_latin_fonts:
        issues.append({
            "code": "latin_text_not_times_family",
            "severity": "error",
            "fonts": unexpected_latin_fonts,
            "message": "含英文或数字的文本使用了非 Times 系字体。",
        })
    if compatible_times and not exact_times:
        issues.append({
            "code": "overleaf_times_new_roman_fallback",
            "severity": "warning",
            "fonts": compatible_times,
            "message": "当前 PDF 使用可再分发的 Times 兼容字体而非微软 Times New Roman；若必须逐字体一致，需在有授权的环境编译并复核。",
        })
    report = {
        "pdf": str(pdf),
        "pdfinfo": pdfinfo(pdf),
        "physical_pages": len(records),
        "printed_page_offset": printed_page_offset(records),
        "cover_page_centered_footer_numbers": cover_footer,
        "abstract_page_centered_footer_numbers": abstract_footer,
        "header_text_spans": header_hits,
        "body": body,
        "body_page_gate": {"minimum": required_body, "maximum": maximum_body, "mode": body_gate_mode, "authority": body_gate_authority},
        "internal_total_page_target": {
            "target": internal_total_target,
            "mode": internal_target_mode,
            "scope": "physical_pdf_pages",
            "authority": internal_target_authority,
            "official_requirement": False,
        },
        "role_windows_enabled": role_windows_enabled,
        "chapter_ranges": ranges,
        "detected_fonts": fonts,
        "latin_fonts": latin_fonts,
        "cover_image_count": cover_image_count,
        "abstract_front_matter": front_matter["details"],
        "terminal_chapter_pages": terminal_pages["details"],
        "issues": issues,
        "status": "FAIL" if any(item["severity"] == "error" for item in issues) else "PASS_WITH_WARNINGS" if issues else "PASS",
        "limitations": [
            "最终页数以本 PDF 为准；DOCX docProps/app.xml 的 Pages 不参与验收。",
            "中文字体 CMap 损坏时，章节/身份检测可能需要 OCR 或 Word 标题 JSON 交叉验证。",
            "历史论文的章节页数只作描述性观察，不要求所有章节等长，也不参与默认通过/失败判定。",
            "contest.json 中的 official_rules_priority=true：仅在当届题面或官方通知明确给出页数限制时开启页数门禁；截至 2026-09-22，默认关闭。",
            "论文长度由用户在 Figure 总数锁定后决定；数值目标不是官方门槛，也不得以凑页方式修复。",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(1 if report["status"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
