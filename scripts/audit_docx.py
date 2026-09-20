#!/usr/bin/env python3
# [来源] 移植自 v2.1 华为杯_论文规范模板/tools/，相对路径已改为 CLI 参数驱动，Wave3 验证编译链路。
"""Inspect DOCX package-level format and anonymity invariants."""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{" + W_NS + "}"
NS = {"w": W_NS}
IDENTITY_RE = re.compile(
    r"学校|学院|实验室|参赛队号|队员姓名|指导教师|学号|邮箱|email|"
    r"\b(?:school|student|team|member|advisor)\b|C:\\Users\\",
    re.IGNORECASE,
)


def local_attrs(element):
    if element is None:
        return {}
    return {etree.QName(key).localname: value for key, value in element.attrib.items()}


def first_run_for_label(paragraph, label):
    for run in paragraph.xpath("./w:r", namespaces=NS):
        text = "".join(run.xpath(".//w:t/text()", namespaces=NS))
        if text.startswith(label):
            return run
    return None


def next_text_run_for_label(paragraph, label):
    found = False
    for run in paragraph.xpath("./w:r", namespaces=NS):
        text = "".join(run.xpath(".//w:t/text()", namespaces=NS))
        if text.startswith(label):
            found = True
            continue
        if found and text.strip():
            return run
    return None


def on(element):
    if element is None:
        return False
    return element.get(W + "val", "true").lower() not in {"0", "false", "off", "no"}


def run_measurements(run):
    if run is None:
        return {}
    rpr = run.find("w:rPr", NS)
    fonts = rpr.find("w:rFonts", NS) if rpr is not None else None
    size = rpr.find("w:sz", NS) if rpr is not None else None
    return {
        "eastAsia": fonts.get(W + "eastAsia") if fonts is not None else None,
        "ascii": fonts.get(W + "ascii") if fonts is not None else None,
        "size_half_points": int(size.get(W + "val")) if size is not None and size.get(W + "val", "").isdigit() else None,
        "bold": on(rpr.find("w:b", NS) if rpr is not None else None),
        "italic": on(rpr.find("w:i", NS) if rpr is not None else None)
        or on(rpr.find("w:iCs", NS) if rpr is not None else None),
    }


def effective_italic(run):
    """Return whether a run has an explicit effective italic property."""
    rpr = run.find("w:rPr", NS)
    if rpr is None:
        return False
    return on(rpr.find("w:i", NS)) or on(rpr.find("w:iCs", NS))


def style_measurements(styles, style_id):
    style = next(
        (item for item in styles.xpath(".//w:style", namespaces=NS) if item.get(W + "styleId") == style_id),
        None,
    )
    if style is None:
        return None
    rpr = style.find("w:rPr", NS)
    fonts = rpr.find("w:rFonts", NS) if rpr is not None else None
    size = rpr.find("w:sz", NS) if rpr is not None else None
    ppr = style.find("w:pPr", NS)
    spacing = ppr.find("w:spacing", NS) if ppr is not None else None
    return {
        "name": (style.xpath("./w:name/@w:val", namespaces=NS) or [style_id])[0],
        "eastAsia": fonts.get(W + "eastAsia") if fonts is not None else None,
        "size_half_points": int(size.get(W + "val")) if size is not None and size.get(W + "val", "").isdigit() else None,
        "bold": on(rpr.find("w:b", NS) if rpr is not None else None),
        "italic": on(rpr.find("w:i", NS) if rpr is not None else None)
        or on(rpr.find("w:iCs", NS) if rpr is not None else None),
        "line_twips": int(spacing.get(W + "line")) if spacing is not None and spacing.get(W + "line", "").isdigit() else None,
        "line_rule": spacing.get(W + "lineRule") if spacing is not None else None,
        "outline_level": (ppr.find("w:outlineLvl", NS).get(W + "val")
                          if ppr is not None and ppr.find("w:outlineLvl", NS) is not None else None),
    }


def paragraph_outline_level(paragraph):
    ppr = paragraph.find("w:pPr", NS)
    outline = ppr.find("w:outlineLvl", NS) if ppr is not None else None
    value = outline.get(W + "val") if outline is not None else None
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def audit(path: Path):
    checks = []
    with zipfile.ZipFile(path) as package:
        names = set(package.namelist())
        checks.append({"code": "hidden_custom_xml", "ok": not any(name.startswith("customXml/") for name in names)})
        checks.append({"code": "hidden_ole_payload", "ok": not any(name.startswith("word/embeddings/") for name in names)})
        document = etree.fromstring(package.read("word/document.xml"))
        styles = etree.fromstring(package.read("word/styles.xml"))
        paragraphs = document.xpath(".//w:body/w:p", namespaces=NS)
        text = "\n".join("".join(p.xpath(".//w:t/text()", namespaces=NS)) for p in paragraphs)
        identity_hits = sorted(set(IDENTITY_RE.findall(text)))
        checks.append({"code": "identity_text", "ok": not identity_hits, "matches": identity_hits})
        checks.append({"code": "template_placeholders", "ok": "xx" not in text, "matches": ["xx"] if "xx" in text else []})

        paragraph_texts = ["".join(p.xpath(".//w:t/text()", namespaces=NS)).strip() for p in paragraphs]
        toc_titles = [index for index, value in enumerate(paragraph_texts) if value == "目录"]
        toc_fields = []
        for index, paragraph in enumerate(paragraphs):
            instructions = " ".join(paragraph.xpath(".//w:instrText/text()", namespaces=NS))
            if re.search(r"\bTOC\b", instructions, re.I):
                toc_fields.append({"paragraph": index, "instruction": instructions})
        toc_switch_ok = bool(toc_fields and re.search(r"\\o\s+\"1-3\"", toc_fields[0]["instruction"]) and
                              re.search(r"\\h", toc_fields[0]["instruction"]) and
                              re.search(r"\\z", toc_fields[0]["instruction"]) and
                              re.search(r"\\u", toc_fields[0]["instruction"]))
        heading_indexes = [index for index, paragraph in enumerate(paragraphs)
                           if paragraph_outline_level(paragraph) in {0, 1, 2} and paragraph_texts[index]]
        toc_order_ok = bool(toc_titles and toc_fields and heading_indexes and
                            toc_titles[0] < toc_fields[0]["paragraph"] < heading_indexes[0])
        checks.append({"code": "dynamic_toc_field", "ok": toc_switch_ok, "fields": toc_fields,
                       "message": 'TOC \\o "1-3" \\h \\z \\u field is required'})
        checks.append({"code": "toc_title_and_order", "ok": toc_order_ok,
                       "title_paragraphs": toc_titles, "heading_paragraphs": heading_indexes[:20]})
        checks.append({"code": "non_empty_outline_headings", "ok": bool(heading_indexes),
                       "count": len(heading_indexes)})

        settings_update = False
        if "word/settings.xml" in names:
            settings = etree.fromstring(package.read("word/settings.xml"))
            settings_update = bool(settings.xpath('.//w:updateFields[@w:val="true"]', namespaces=NS))
        checks.append({"code": "toc_update_on_open", "ok": settings_update})

        chinese_italic_runs = []
        for paragraph_index, paragraph in enumerate(paragraphs, start=1):
            for run_index, run in enumerate(paragraph.xpath("./w:r", namespaces=NS), start=1):
                run_text = "".join(run.xpath(".//w:t/text()", namespaces=NS))
                if run_text and re.search(r"[\u3400-\u9fff]", run_text) and effective_italic(run):
                    chinese_italic_runs.append({
                        "paragraph": paragraph_index,
                        "run": run_index,
                        "text": run_text[:100],
                    })
        checks.append({
            "code": "chinese_text_not_italic",
            "ok": not chinese_italic_runs,
            "violations": chinese_italic_runs[:20],
            "violation_count": len(chinese_italic_runs),
        })

        sections = document.xpath(".//w:body/w:sectPr | .//w:p/w:pPr/w:sectPr", namespaces=NS)
        section_results = []
        for section in sections:
            pg_size = section.find("w:pgSz", NS)
            margins = section.find("w:pgMar", NS)
            page_numbering = section.find("w:pgNumType", NS)
            section_results.append({
                "page_size": local_attrs(pg_size),
                "margins": local_attrs(margins),
                "page_number_start": page_numbering.get(W + "start") if page_numbering is not None else None,
                "different_first_page": section.find("w:titlePg", NS) is not None,
            })
        expected_size = {"w": "11906", "h": "16838"}
        expected_margins = {"top": "1418", "right": "1418", "bottom": "1418", "left": "1418"}
        geometry_ok = bool(section_results) and all(
            item["page_size"].get("w") == expected_size["w"]
            and item["page_size"].get("h") == expected_size["h"]
            and all(abs(int(item["margins"].get(key, "0")) - int(value)) <= 1 for key, value in expected_margins.items())
            for item in section_results
        )
        checks.append({"code": "a4_and_25mm_margins", "ok": geometry_ok, "sections": section_results})

        page_numbering_ok = bool(section_results) and all(
            item["page_number_start"] == "1" and not item["different_first_page"]
            for item in section_results
        )
        checks.append({"code": "page_number_starts_at_1", "ok": page_numbering_ok, "sections": section_results})

        body_breaks = len(document.xpath('.//w:body//w:br[@w:type="page"]', namespaces=NS))
        checks.append({"code": "abstract_to_toc_and_body_page_breaks", "ok": body_breaks >= 2, "page_breaks": body_breaks})

        label_measurements = {}
        for label in ("题 目：", "摘 要：", "关键词："):
            paragraph = next(
                (p for p in paragraphs if "".join(p.xpath(".//w:t/text()", namespaces=NS)).startswith(label)),
                None,
            )
            measurement = run_measurements(first_run_for_label(paragraph, label)) if paragraph is not None else None
            label_measurements[label] = measurement
        title_paragraph = next(
            (p for p in paragraphs if "".join(p.xpath(".//w:t/text()", namespaces=NS)).startswith("题 目：")),
            None,
        )
        title_measurement = run_measurements(next_text_run_for_label(title_paragraph, "题 目：")) if title_paragraph is not None else None
        label_ok = all(
            value is not None and value.get("eastAsia") == "隶书" and value.get("size_half_points") == 36
            for value in label_measurements.values()
        )
        title_ok = title_measurement is not None and title_measurement.get("eastAsia") == "黑体" and title_measurement.get("size_half_points") == 32
        checks.append({
            "code": "front_matter_labels",
            "ok": label_ok and title_ok,
            "measurements": label_measurements,
            "title_measurement": title_measurement,
        })

        style_results = {
            key: style_measurements(styles, style_id)
            for key, style_id in {
                "body": "HuaweiBody",
                "heading1": "HuaweiHeading1",
                "heading2": "HuaweiHeading2",
                "heading3": "HuaweiHeading3",
            }.items()
        }
        style_ok = (
            style_results["body"] is not None
            and style_results["body"]["eastAsia"] == "宋体"
            and style_results["body"]["size_half_points"] == 24
            and style_results["body"]["line_twips"] == 360
            and style_results["body"]["line_rule"] == "exact"
            and not style_results["body"]["italic"]
            and style_results["heading1"] is not None
            and style_results["heading1"]["eastAsia"] == "黑体"
            and style_results["heading1"]["size_half_points"] == 28
            and style_results["heading1"]["bold"]
            and not style_results["heading1"]["italic"]
            and style_results["heading1"]["outline_level"] == "0"
            and style_results["heading1"]["line_twips"] == 480
            and style_results["heading1"]["line_rule"] == "exact"
            and style_results["heading2"] is not None
            and style_results["heading2"]["eastAsia"] == "宋体"
            and style_results["heading2"]["size_half_points"] == 24
            and style_results["heading2"]["line_twips"] == 360
            and style_results["heading2"]["line_rule"] == "exact"
            and not style_results["heading2"]["italic"]
            and style_results["heading2"]["outline_level"] == "1"
            and style_results["heading3"] is not None
            and style_results["heading3"]["outline_level"] == "2"
        )
        checks.append({"code": "body_and_heading_styles", "ok": style_ok, "styles": style_results})

        headers = []
        for name in sorted(item for item in names if item.startswith("word/header") and item.endswith(".xml")):
            header = etree.fromstring(package.read(name))
            headers.append({"part": name, "text": "".join(header.xpath(".//w:t/text()", namespaces=NS)).strip()})
        footer_fields = []
        for name in sorted(item for item in names if item.startswith("word/footer") and item.endswith(".xml")):
            footer = etree.fromstring(package.read(name))
            footer_fields.append({
                "part": name,
                "has_page_field": bool(footer.xpath('.//w:instrText[contains(., "PAGE")]', namespaces=NS)),
                "centered": bool(footer.xpath('.//w:p[w:pPr/w:jc/@w:val="center"]', namespaces=NS)),
            })
        checks.append({"code": "header_empty", "ok": all(not item["text"] for item in headers), "headers": headers})
        checks.append({
            "code": "footer_page_field",
            "ok": any(item["has_page_field"] and item["centered"] for item in footer_fields),
            "footers": footer_fields,
        })

    failures = [item for item in checks if not item["ok"]]
    return {"docx": str(path), "status": "PASS" if not failures else "FAIL", "checks": checks, "failures": failures}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docx", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.docx.resolve())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
