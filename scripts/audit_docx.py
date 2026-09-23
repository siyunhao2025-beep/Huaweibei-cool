#!/usr/bin/env python3
# [来源] 移植自 v2.1 华为杯_论文规范模板/tools/，相对路径已改为 CLI 参数驱动，Wave3 验证编译链路。
"""Inspect DOCX package-level format and anonymity invariants."""
from __future__ import annotations

import argparse
import json
import posixpath
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{" + W_NS + "}"
NS = {"w": W_NS}
IDENTITY_RE = re.compile(
    r"(?:学校(?:名称)?|所属学校|学院(?:名称)?|实验室(?:名称)?|参赛队号|队号|"
    r"队员(?:姓名)?(?:\s*[123一二三])?|指导(?:教师|老师)|学号|姓名|(?:电子)?邮箱)\s*[:：]|"
    r"\b(?:school|student|team|member|advisor|e-?mail)\s*(?:name|id|number)?\s*[:：]|"
    r"C:\\Users\\",
    re.IGNORECASE,
)
REFERENCE_HEADING_RE = re.compile(r"^\s*(?:\d+(?:\.\d+)*\s+)?(?:参考文献|References?)\s*$", re.I)
APPENDIX_HEADING_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\s+)?(?:附录|Appendix)(?:\s*[A-ZＡ-Ｚ0-9０-９]+)?"
    r"(?:\s*[:：—-]\s*.+|\s+.+)?\s*$",
    re.I,
)
SYMBOL_HEADING_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\s+)?(?:"
    r"主要符号(?:说明|定义|约定|表)?|全文符号(?:说明|定义|约定|表)?|"
    r"符号(?:说明|定义|约定|表)|变量(?:与|及)符号(?:说明|定义)|"
    r"符号(?:与|及)变量(?:说明|定义)"
    r")\s*$",
    re.I,
)
NUMBERED_QUESTION_HEADING_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\s+)?(?:问题\s*(?:[一二三四五六七八九十百]+|\d+)|"
    r"第\s*(?:[一二三四五六七八九十百]+|\d+)\s*问|Q\s*\d+|Question\s*\d+)",
    re.I,
)
PRE_SYMBOL_HEADING_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\s+)?(?:"
    r"(?:总体)?问题分析|数据(?:质量)?审计|(?:基本|模型|问题)?假设(?:说明)?"
    r")\s*$",
    re.I,
)
PLACEHOLDER_RE = re.compile(
    r"REPLACE_WITH_ACTUAL(?:_[A-Z0-9_]+)?|待补|待填写|待替换|请替换|占位|"
    r"\b(?:TODO|FIXME|TBD)\b",
    re.I,
)
TABLE_TAG_RE = re.compile(r"\[(tab:[^\[\]\s]+)\]")
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WPS_CUSTOM_DATA_NS = "http://www.wps.cn/officeDocument/2013/wpsCustomData"


def parse_xml(data: bytes):
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.fromstring(data, parser=parser)


def is_external_local_file_target(target: str, target_mode: str = "") -> bool:
    """Identify external relationships that expose a local/network path."""
    decoded = unquote(target).strip().replace("\\", "/")
    lower = decoded.lower()
    if lower.startswith("file:") or re.match(r"^[a-z]:/", lower):
        return True
    if decoded.startswith("//"):
        return True
    return target_mode.lower() == "external" and decoded.startswith("/")


def relationship_integrity(package: zipfile.ZipFile, names: set[str]) -> dict:
    """Return unresolved relationship references and missing internal targets."""
    relationship_ids: dict[str, set[str]] = {}
    missing_targets = []
    for rels_name in sorted(name for name in names if name.endswith(".rels")):
        if rels_name == "_rels/.rels":
            source_part = ""
        elif "/_rels/" in rels_name:
            prefix, rel_name = rels_name.rsplit("/_rels/", 1)
            source_part = f"{prefix}/{rel_name[:-5]}"
        else:
            continue
        relationships = parse_xml(package.read(rels_name))
        relationship_ids[source_part] = {
            relationship.get("Id", "") for relationship in relationships
        }
        source_dir = posixpath.dirname(source_part)
        for relationship in relationships:
            if relationship.get("TargetMode", "").lower() == "external":
                continue
            target = unquote(relationship.get("Target", "")).replace("\\", "/")
            if not target:
                continue
            resolved = (
                posixpath.normpath(target.lstrip("/"))
                if target.startswith("/")
                else posixpath.normpath(posixpath.join(source_dir, target))
            )
            if resolved not in names:
                missing_targets.append({
                    "source": source_part or "/",
                    "relationship": relationship.get("Id", ""),
                    "target": target,
                    "resolved": resolved,
                })

    dangling_references = []
    for part_name in sorted(name for name in names if name.endswith(".xml")):
        root = parse_xml(package.read(part_name))
        valid_ids = relationship_ids.get(part_name, set())
        for element in root.iter():
            for attribute, value in element.attrib.items():
                qname = etree.QName(attribute)
                if qname.namespace == R_NS and value not in valid_ids:
                    dangling_references.append({
                        "part": part_name,
                        "element": etree.QName(element).localname,
                        "attribute": qname.localname,
                        "relationship": value,
                    })
    return {
        "dangling_references": dangling_references,
        "missing_internal_targets": missing_targets,
    }


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


def paragraph_starts_new_page(paragraph, previous=None):
    ppr = paragraph.find("w:pPr", NS)
    page_break_before = ppr.find("w:pageBreakBefore", NS) if ppr is not None else None
    if on(page_break_before):
        return True
    if paragraph.xpath('.//w:br[@w:type="page"]', namespaces=NS):
        return True
    return bool(previous is not None and previous.xpath('.//w:br[@w:type="page"]', namespaces=NS))


def run_measurements(run):
    if run is None:
        return {}
    rpr = run.find("w:rPr", NS)
    fonts = rpr.find("w:rFonts", NS) if rpr is not None else None
    size = rpr.find("w:sz", NS) if rpr is not None else None
    return {
        "eastAsia": fonts.get(W + "eastAsia") if fonts is not None else None,
        "ascii": fonts.get(W + "ascii") if fonts is not None else None,
        "hAnsi": fonts.get(W + "hAnsi") if fonts is not None else None,
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
        "ascii": fonts.get(W + "ascii") if fonts is not None else None,
        "hAnsi": fonts.get(W + "hAnsi") if fonts is not None else None,
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


def element_text(element):
    return "".join(element.xpath(".//w:t/text()", namespaces=NS)).strip()


def _border_value(parent, border_group, edge):
    border = parent.find(f"w:{border_group}/w:{edge}", NS)
    return border.get(W + "val") if border is not None else None


def _visible_border(value):
    return value not in {None, "nil", "none", "0"}


def _style_name(styles, style_id):
    if styles is None or not style_id:
        return ""
    style = next(
        (item for item in styles.xpath(".//w:style", namespaces=NS)
         if item.get(W + "styleId") == style_id),
        None,
    )
    if style is None:
        return ""
    names = style.xpath("./w:name/@w:val", namespaces=NS)
    return names[0] if names else ""


def _table_style_chain(styles, style_id):
    """Return table styles from the selected style through basedOn ancestors."""
    if styles is None or not style_id:
        return []
    by_id = {
        item.get(W + "styleId"): item
        for item in styles.xpath(".//w:style", namespaces=NS)
    }
    chain = []
    seen = set()
    current = style_id
    while current and current not in seen and current in by_id:
        seen.add(current)
        style = by_id[current]
        chain.append(style)
        based_on = style.find("w:basedOn", NS)
        current = based_on.get(W + "val", "") if based_on is not None else ""
    return chain


def _effective_table_border(properties, styles, style_id, edge):
    direct = _border_value(properties, "tblBorders", edge) if properties is not None else None
    if direct is not None:
        return direct
    for style in _table_style_chain(styles, style_id):
        table_properties = style.find("w:tblPr", NS)
        value = (
            _border_value(table_properties, "tblBorders", edge)
            if table_properties is not None else None
        )
        if value is not None:
            return value
    return None


def analyze_symbol_glossary(document, styles=None):
    """Check the user-required main-symbol table in direct body order."""
    body = document.find("w:body", NS)
    children = list(body) if body is not None else []
    headings = [
        (index, child, element_text(child), paragraph_outline_level(child))
        for index, child in enumerate(children)
        if child.tag == W + "p" and paragraph_outline_level(child) in {0, 1, 2}
    ]
    symbol_headings = [item for item in headings if SYMBOL_HEADING_RE.fullmatch(item[2])]
    symbol = symbol_headings[0] if symbol_headings else None
    failures = []
    if symbol is None:
        return {
            "ok": False,
            "failures": ["未识别到独立的主要符号说明标题。"],
            "heading": None,
            "symbol_heading_count": 0,
            "table_count": 0,
        }
    if len(symbol_headings) != 1:
        failures.append("全文必须且只能有一个独立的主要符号说明标题。")

    start, _, title, level = symbol
    end = len(children)
    for index, _, _, next_level in headings:
        if index > start and next_level is not None and next_level <= level:
            end = index
            break
    section_children = children[start + 1:end]
    tables = [child for child in section_children if child.tag == W + "tbl"]
    if len(tables) != 1:
        failures.append("主要符号说明标题范围内必须且只能有一张表。")
    table = tables[0] if len(tables) == 1 else None

    first_question = next(
        (index for index, _, heading_text, _ in headings
         if NUMBERED_QUESTION_HEADING_RE.match(heading_text)),
        None,
    )
    before_first_question = first_question is None or start < first_question
    if not before_first_question:
        failures.append("主要符号说明必须位于第一道编号问题之前。")
    preliminary_headings = [
        {"index": index, "title": heading_text}
        for index, _, heading_text, _ in headings
        if PRE_SYMBOL_HEADING_RE.fullmatch(heading_text)
        and (first_question is None or index < first_question)
    ]
    after_existing_preliminary_sections = all(
        item["index"] < start for item in preliminary_headings
    )
    if not after_existing_preliminary_sections:
        failures.append("若存在总体问题分析、数据审计或假设章节，主要符号说明必须位于这些章节之后。")

    details = {
        "ok": False,
        "failures": failures,
        "heading": title,
        "symbol_heading_count": len(symbol_headings),
        "before_first_question": before_first_question,
        "after_existing_preliminary_sections": after_existing_preliminary_sections,
        "preliminary_headings": preliminary_headings,
        "table_count": len(tables),
        "reference_before_table": False,
    }
    if table is None:
        return details

    table_index = children.index(table)
    captions = []
    caption_tags = []
    caption_bookmarks = set()
    caption_candidate = None
    for child in reversed(children[start + 1:table_index]):
        if child.tag != W + "p":
            break
        if not element_text(child).strip():
            continue
        caption_candidate = child
        break
    if caption_candidate is not None:
        child = caption_candidate
        paragraph_properties = child.find("w:pPr", NS)
        style_element = (
            paragraph_properties.find("w:pStyle", NS)
            if paragraph_properties is not None else None
        )
        style_id = style_element.get(W + "val", "") if style_element is not None else ""
        style_name = _style_name(styles, style_id)
        text = element_text(child)
        if "符号" in text and (
            "huaweitablecaption" in style_id.lower()
            or "huawei table caption" in style_name.lower()
        ) and not re.search(r"见表|所示|如下", text):
            captions.append({"text": text, "style_id": style_id, "style_name": style_name})
            caption_tags = TABLE_TAG_RE.findall(text)
            caption_bookmarks = set(child.xpath(".//w:bookmarkStart/@w:name", namespaces=NS))
    caption_ok = bool(captions)
    if not caption_ok:
        failures.append("主要符号表前缺少含“符号”的表题。")

    all_caption_tags = []
    for paragraph in document.xpath(".//w:body/w:p", namespaces=NS):
        paragraph_properties = paragraph.find("w:pPr", NS)
        style_element = (
            paragraph_properties.find("w:pStyle", NS)
            if paragraph_properties is not None else None
        )
        paragraph_style_id = (
            style_element.get(W + "val", "") if style_element is not None else ""
        )
        paragraph_style_name = _style_name(styles, paragraph_style_id)
        if (
            "huaweitablecaption" in paragraph_style_id.lower()
            or "huawei table caption" in paragraph_style_name.lower()
        ):
            all_caption_tags.extend(TABLE_TAG_RE.findall(element_text(paragraph)))
    caption_tag = caption_tags[0] if len(caption_tags) == 1 else None
    caption_tag_unique = bool(
        caption_tag and all_caption_tags.count(caption_tag) == 1
    )
    caption_target_ok = caption_tag_unique or bool(caption_bookmarks)
    if caption_ok and not caption_target_ok:
        failures.append("主要符号表题必须含唯一 [tab:...] 标签，或含供原生 REF 使用的题注书签。")

    caption_index = children.index(caption_candidate) if caption_candidate is not None else table_index
    bookmark_names = set(
        document.xpath(".//w:bookmarkStart/@w:name", namespaces=NS)
    )
    references = []
    for child in children[start + 1:caption_index]:
        if child.tag != W + "p":
            continue
        text = element_text(child)
        instructions = " ".join(child.xpath(".//w:instrText/text()", namespaces=NS))
        semantic = bool(re.search(r"见表|如表|表\s*\d+(?:\.\d+)?\s*所示", text))
        ref_names = [
            match.group(1) or match.group(2)
            for match in re.finditer(
                r'\bREF\s+(?:"([^"]+)"|([^\s\\]+))',
                instructions,
                re.I,
            )
        ]
        visible_tags = TABLE_TAG_RE.findall(text)
        tag_matches = bool(
            caption_tag_unique and visible_tags == [caption_tag]
        )
        ref_fields_valid = all(name in bookmark_names for name in ref_names)
        native_matches = bool(
            ref_names and caption_bookmarks.intersection(ref_names)
        )
        traceable = bool(
            ref_fields_valid
            and (not visible_tags or tag_matches)
            and (tag_matches or native_matches)
        )
        if semantic and traceable:
            references.append(
                {
                    "text": text,
                    "instruction": instructions,
                    "tags": visible_tags,
                    "ref_names": ref_names,
                }
            )
    reference_before_table = bool(references)
    if not reference_before_table:
        failures.append("主要符号表前缺少可追溯的正文引用。")

    rows = table.xpath("./w:tr", namespaces=NS)
    row_texts = [[element_text(cell) for cell in row.xpath("./w:tc", namespaces=NS)] for row in rows]
    header = row_texts[0] if row_texts else []
    symbol_columns = [index for index, value in enumerate(header) if "符号" in value]
    meaning_columns = [
        index for index, value in enumerate(header)
        if any(word in value for word in ("含义", "定义", "说明"))
    ]
    header_ok = len(header) >= 2 and any(
        symbol_index != meaning_index
        for symbol_index in symbol_columns
        for meaning_index in meaning_columns
    )
    if not header_ok:
        failures.append("主要符号表至少需要两个独立表头单元格，并分别包含“符号”和“含义/定义/说明”。")
    expected_column_count = len(header)
    nonempty_data_rows = [row for row in row_texts[1:] if any(value.strip() for value in row)]
    incomplete_data_rows = [
        row for row in nonempty_data_rows
        if len(row) != expected_column_count or any(not value.strip() for value in row)
    ]
    data_rows = [row for row in nonempty_data_rows if row not in incomplete_data_rows]
    if incomplete_data_rows:
        failures.append("主要符号表数据行必须与表头列数一致，且每个已声明字段均不得留空。")
    if len(data_rows) < 1:
        failures.append("主要符号表至少需要一条真实数据行。")
    placeholders = [
        value for row in nonempty_data_rows for value in row if PLACEHOLDER_RE.search(value)
    ]
    if placeholders:
        failures.append("主要符号表仍含待替换占位文本。")

    properties = table.find("w:tblPr", NS)
    style = properties.find("w:tblStyle", NS) if properties is not None else None
    style_id = style.get(W + "val", "") if style is not None else ""
    style_name = _style_name(styles, style_id)
    style_chain_names = [
        _style_name(styles, item.get(W + "styleId", ""))
        for item in _table_style_chain(styles, style_id)
    ]
    border_values = {
        edge: _effective_table_border(properties, styles, style_id, edge)
        for edge in ("top", "bottom", "left", "right", "insideH", "insideV")
    }
    outer_rules_ok = all(_visible_border(border_values[edge]) for edge in ("top", "bottom"))
    no_grid = not any(
        _visible_border(border_values[edge]) for edge in ("left", "right", "insideH", "insideV")
    )
    header_rules = []
    if rows:
        for cell in rows[0].xpath("./w:tc", namespaces=NS):
            tc_properties = cell.find("w:tcPr", NS)
            header_rules.append(
                _border_value(tc_properties, "tcBorders", "bottom") if tc_properties is not None else None
            )
    header_rule_ok = bool(header_rules) and all(_visible_border(value) for value in header_rules)
    visible_vertical_cell_borders = []
    for cell_index, cell in enumerate(table.xpath(".//w:tc", namespaces=NS), start=1):
        tc_properties = cell.find("w:tcPr", NS)
        for edge in ("left", "right", "insideV"):
            value = _border_value(tc_properties, "tcBorders", edge) if tc_properties is not None else None
            if _visible_border(value):
                visible_vertical_cell_borders.append({"cell": cell_index, "edge": edge, "value": value})
    visible_data_cell_horizontal_borders = []
    for row_index, row in enumerate(rows[1:], start=2):
        for cell_index, cell in enumerate(row.xpath("./w:tc", namespaces=NS), start=1):
            tc_properties = cell.find("w:tcPr", NS)
            for edge in ("top", "bottom", "insideH"):
                value = _border_value(tc_properties, "tcBorders", edge) if tc_properties is not None else None
                if _visible_border(value):
                    visible_data_cell_horizontal_borders.append({
                        "row": row_index,
                        "cell": cell_index,
                        "edge": edge,
                        "value": value,
                    })
    if (
        not outer_rules_ok
        or not header_rule_ok
        or not no_grid
        or visible_vertical_cell_borders
        or visible_data_cell_horizontal_borders
    ):
        failures.append("主要符号表必须是无竖线、无全网格的上/中/下三线表。")

    details.update({
        "ok": not failures,
        "failures": failures,
        "captions": captions,
        "caption_ok": caption_ok,
        "caption_tags": caption_tags,
        "caption_tag": caption_tag,
        "caption_tag_unique": caption_tag_unique,
        "caption_bookmarks": sorted(caption_bookmarks),
        "reference_before_table": reference_before_table,
        "references": references,
        "header": header,
        "header_ok": header_ok,
        "expected_column_count": expected_column_count,
        "data_row_count": len(data_rows),
        "incomplete_data_rows": incomplete_data_rows,
        "placeholders": placeholders,
        "table_style": style_id,
        "table_style_name": style_name,
        "table_style_chain": style_chain_names,
        "table_borders": border_values,
        "header_bottom_borders": header_rules,
        "visible_vertical_cell_borders": visible_vertical_cell_borders,
        "visible_data_cell_horizontal_borders": visible_data_cell_horizontal_borders,
    })
    return details


def audit(path: Path):
    checks = []
    with zipfile.ZipFile(path) as package:
        names = set(package.namelist())
        checks.append({"code": "hidden_custom_xml", "ok": not any(name.startswith("customXml/") for name in names)})
        checks.append({"code": "hidden_ole_payload", "ok": not any(name.startswith("word/embeddings/") for name in names)})
        checks.append({"code": "custom_properties_absent", "ok": "docProps/custom.xml" not in names})
        external_file_relationships = []
        for name in sorted(item for item in names if item.endswith(".rels")):
            relationships = parse_xml(package.read(name))
            for relationship in relationships:
                target = relationship.get("Target", "")
                if is_external_local_file_target(
                    target, relationship.get("TargetMode", "")
                ):
                    external_file_relationships.append({"part": name, "target": target})
        checks.append({
            "code": "no_external_file_relationships",
            "ok": not external_file_relationships,
            "relationships": external_file_relationships,
        })
        integrity = relationship_integrity(package, names)
        checks.append({
            "code": "relationship_integrity",
            "ok": not integrity["dangling_references"]
            and not integrity["missing_internal_targets"],
            **integrity,
        })
        document = parse_xml(package.read("word/document.xml"))
        styles = parse_xml(package.read("word/styles.xml"))
        paragraphs = document.xpath(".//w:body//w:p", namespaces=NS)
        text = "\n".join(document.xpath(".//w:body//w:t/text()", namespaces=NS))
        package_text = [text]
        for name in sorted(
            item for item in names
            if re.fullmatch(r"word/(?:header\d+|footer\d+|comments|footnotes|endnotes)\.xml", item)
        ):
            part = parse_xml(package.read(name))
            package_text.extend(part.xpath(".//w:t/text()", namespaces=NS))
        identity_hits = sorted({match.group(0) for match in IDENTITY_RE.finditer("\n".join(package_text))})
        checks.append({"code": "identity_text", "ok": not identity_hits, "matches": identity_hits})
        placeholders = sorted(
            {match.group(0) for match in PLACEHOLDER_RE.finditer(text)}
            | set(re.findall(r"(?<![A-Za-z0-9])x{2,}(?![A-Za-z0-9])", text, re.I))
        )
        checks.append({"code": "template_placeholders", "ok": not placeholders, "matches": placeholders})

        core = parse_xml(package.read("docProps/core.xml")) if "docProps/core.xml" in names else None
        core_fields = {}
        if core is not None:
            for element in core.iter():
                local = etree.QName(element).localname
                if local in {"creator", "lastModifiedBy", "description", "subject", "keywords", "category"}:
                    core_fields[local] = (element.text or "").strip()
        checks.append({
            "code": "personal_metadata_empty",
            "ok": bool(core_fields) and all(not value for value in core_fields.values()),
            "fields": core_fields,
        })
        settings = parse_xml(package.read("word/settings.xml"))
        document_variables = [
            {
                "name": element.get(W + "name", ""),
                "value": element.get(W + "val", ""),
            }
            for element in settings.xpath(".//w:docVar", namespaces=NS)
        ]
        checks.append({
            "code": "hidden_document_variables_absent",
            "ok": not document_variables,
            "variables": document_variables,
        })
        wps_tracking_metadata = []
        for name in sorted(
            item for item in names
            if item.startswith("word/") and item.endswith(".xml")
        ):
            root = parse_xml(package.read(name))
            for element in root.iter():
                qname = etree.QName(element)
                marker_values = [element.text or "", *element.attrib.values()]
                if (
                    qname.namespace == WPS_CUSTOM_DATA_NS
                    or any("KSO_DOCER_RESOURCE_TRACE_INFO" in value for value in marker_values)
                ):
                    wps_tracking_metadata.append({
                        "part": name,
                        "element": qname.localname,
                    })
        checks.append({
            "code": "wps_tracking_metadata_absent",
            "ok": not wps_tracking_metadata,
            "matches": wps_tracking_metadata,
        })
        app = parse_xml(package.read("docProps/app.xml")) if "docProps/app.xml" in names else None
        app_fields = {}
        if app is not None:
            for element in app.iter():
                local = etree.QName(element).localname
                if local in {"Application", "Template", "TotalTime", "Company", "Manager"}:
                    app_fields[local] = (element.text or "").strip()
        app_metadata_ok = (
            app_fields.get("Application") == "Microsoft Office Word"
            and app_fields.get("Template") == "Normal.dotm"
            and app_fields.get("TotalTime") == "0"
            and not app_fields.get("Company", "")
            and not app_fields.get("Manager", "")
        )
        checks.append({
            "code": "application_metadata_sanitized",
            "ok": app_metadata_ok,
            "fields": app_fields,
        })

        paragraph_texts = ["".join(p.xpath(".//w:t/text()", namespaces=NS)).strip() for p in paragraphs]
        symbol_glossary = analyze_symbol_glossary(document, styles)
        checks.append({
            "code": "main_symbol_glossary_is_complete_three_line_table",
            **symbol_glossary,
            "message": "这是 skill 的内部可读性规则，不是官方明文格式要求。",
        })
        terminal_headings = []
        for index, value in enumerate(paragraph_texts):
            role = "references" if REFERENCE_HEADING_RE.fullmatch(value) else (
                "appendix" if APPENDIX_HEADING_RE.fullmatch(value) else None
            )
            if role:
                terminal_headings.append({
                    "paragraph": index,
                    "title": value,
                    "role": role,
                    "starts_new_page": paragraph_starts_new_page(
                        paragraphs[index], paragraphs[index - 1] if index > 0 else None
                    ),
                })
        terminal_roles = {item["role"] for item in terminal_headings}
        missing_required_roles = {"references"} - terminal_roles
        checks.append({
            "code": "references_and_appendices_start_new_pages",
            "ok": not missing_required_roles
            and all(item["starts_new_page"] for item in terminal_headings),
            "headings": terminal_headings,
            "missing_roles": sorted(missing_required_roles),
            "optional_missing_roles": sorted({"appendix"} - terminal_roles),
            "message": "必须识别参考文献并另起一页；若论文含附录，附录标题也必须另起一页。",
        })
        toc_titles = [index for index, value in enumerate(paragraph_texts) if value == "目录"]
        toc_fields = []
        for index, paragraph in enumerate(paragraphs):
            instructions = " ".join(paragraph.xpath(".//w:instrText/text()", namespaces=NS))
            if re.search(r"\bTOC\b", instructions, re.I):
                toc_fields.append({"paragraph": index, "instruction": instructions})
        heading_indexes = [index for index, paragraph in enumerate(paragraphs)
                           if paragraph_outline_level(paragraph) in {0, 1, 2} and paragraph_texts[index]]
        checks.append({
            "code": "no_toc_between_abstract_and_body",
            "ok": not toc_titles and not toc_fields,
            "titles": toc_titles,
            "fields": toc_fields,
            "message": "官方规定：完整摘要后的下一页直接开始正文，不插入目录。",
        })
        checks.append({"code": "non_empty_outline_headings", "ok": bool(heading_indexes),
                       "count": len(heading_indexes)})

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
        expected_margins = {
            "top": "1701", "right": "1276", "bottom": "992", "left": "1276",
            "header": "850", "footer": "992",
        }
        geometry_ok = bool(section_results) and all(
            item["page_size"].get("w") == expected_size["w"]
            and item["page_size"].get("h") == expected_size["h"]
            and all(abs(int(item["margins"].get(key, "0")) - int(value)) <= 1 for key, value in expected_margins.items())
            for item in section_results
        )
        checks.append({"code": "a4_and_official_margins", "ok": geometry_ok, "sections": section_results})

        page_numbering_ok = bool(section_results) and all(
            item["page_number_start"] == "1" and not item["different_first_page"]
            for item in section_results
        )
        checks.append({"code": "page_number_starts_at_1", "ok": page_numbering_ok, "sections": section_results})

        body_breaks = len(document.xpath('.//w:body//w:br[@w:type="page"]', namespaces=NS))
        checks.append({
            "code": "abstract_to_body_page_break",
            "ok": body_breaks >= 1,
            "page_breaks": body_breaks,
            "message": "关键词后仅分页进入正文；不得额外插入目录页。",
        })

        ascii_font_violations = []
        for run in document.xpath(".//w:body//w:r", namespaces=NS):
            run_text = "".join(run.xpath(".//w:t/text()", namespaces=NS))
            if run_text and re.search(r"[A-Za-z0-9]", run_text):
                measurements = run_measurements(run)
                if measurements.get("ascii") != "Times New Roman" or measurements.get("hAnsi") != "Times New Roman":
                    ascii_font_violations.append({"text": run_text[:100], "measurements": measurements})
        checks.append({
            "code": "latin_runs_times_new_roman",
            "ok": not ascii_font_violations,
            "violations": ascii_font_violations[:20],
            "violation_count": len(ascii_font_violations),
        })

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
            and style_results["body"]["ascii"] == "Times New Roman"
            and style_results["body"]["hAnsi"] == "Times New Roman"
            and style_results["body"]["size_half_points"] == 24
            and style_results["body"]["line_twips"] in {None, 240}
            and style_results["body"]["line_rule"] in {None, "auto"}
            and not style_results["body"]["italic"]
            and style_results["heading1"] is not None
            and style_results["heading1"]["eastAsia"] == "黑体"
            and style_results["heading1"]["size_half_points"] == 28
            and style_results["heading1"]["bold"]
            and not style_results["heading1"]["italic"]
            and style_results["heading1"]["outline_level"] == "0"
            and style_results["heading1"]["line_twips"] in {None, 240}
            and style_results["heading1"]["line_rule"] in {None, "auto"}
            and style_results["heading2"] is not None
            and style_results["heading2"]["eastAsia"] == "宋体"
            and style_results["heading2"]["size_half_points"] == 24
            and style_results["heading2"]["line_twips"] in {None, 240}
            and style_results["heading2"]["line_rule"] in {None, "auto"}
            and not style_results["heading2"]["italic"]
            and style_results["heading2"]["outline_level"] == "1"
            and style_results["heading3"] is not None
            and style_results["heading3"]["outline_level"] == "2"
        )
        checks.append({"code": "body_and_heading_styles", "ok": style_ok, "styles": style_results})

        headers = []
        for name in sorted(item for item in names if item.startswith("word/header") and item.endswith(".xml")):
            header = parse_xml(package.read(name))
            headers.append({"part": name, "text": "".join(header.xpath(".//w:t/text()", namespaces=NS)).strip()})
        footer_fields = []
        for name in sorted(item for item in names if item.startswith("word/footer") and item.endswith(".xml")):
            footer = parse_xml(package.read(name))
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
