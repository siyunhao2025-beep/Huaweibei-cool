# -*- coding: utf-8 -*-
"""Regression checks for PDF audit patterns and footer detection."""

import shutil
import subprocess

import audit_paper

from conftest import ASSETS


def test_footer_page_label_and_text_patterns():
    record = {
        "width": 595.28,
        "height": 841.89,
        "spans": [{"text": "1", "bbox": (294.6, 813.0, 300.6, 825.0)}],
    }
    assert audit_paper.PAGE_RE.fullmatch("1")
    assert not audit_paper.PAGE_RE.fullmatch("1a")
    assert audit_paper.centered_footer_numbers(record) == [1]
    assert audit_paper.REFERENCE_RE.fullmatch(" References ")
    assert audit_paper.APPENDIX_RE.fullmatch("Appendix A")


def test_english_and_windows_identity_markers():
    user_path = "C:" + chr(92) + "Users" + chr(92) + "ASUS"
    assert audit_paper.IDENTITY_RE.search("School of Mathematics")
    assert audit_paper.IDENTITY_RE.search(user_path)


def test_heading_manifest_can_declare_verified_physical_page_when_cmap_is_broken():
    records = [
        {"physical_page": 1, "text": "摘要"},
        {"physical_page": 2, "text": "���� A"},
        {"physical_page": 3, "text": "附录正文"},
    ]
    headings = [{"title": "附录 A", "role": "appendix", "physical_page": 2}]

    matched = audit_paper.detect_heading_pages(records, headings)

    assert matched[0]["physical_pages"] == [2]
    assert matched[0]["confidence"] == "declared"


def test_heading_manifest_rejects_out_of_range_declared_page():
    records = [{"physical_page": 1, "text": "正文"}]
    headings = [{"title": "附录 A", "physical_pages": [99, "bad"]}]

    matched = audit_paper.detect_heading_pages(records, headings)

    assert matched[0]["physical_pages"] == []
    assert matched[0]["confidence"] == "invalid_declared_page"


def test_page_gate_defaults_off_when_official_limit_is_absent():
    assert audit_paper.resolve_body_gate({}, {}) == (0, None, "off", "not_configured")


def test_page_gate_reads_an_explicit_official_maximum():
    config = {
        "paper": {
            "body_page_gate": {
                "minimum": 0,
                "maximum": 60,
                "mode": "error",
                "authority": "official_notice",
            }
        }
    }
    assert audit_paper.resolve_body_gate({}, config) == (0, 60, "error", "official_notice")


def test_internal_total_page_target_defaults_off():
    assert audit_paper.resolve_internal_total_target({}, {}) == (0, "off", "not_configured")


def test_internal_total_page_target_is_separate_from_official_gate():
    targets = {
        "internal_total_page_target": {
            "target": 50,
            "mode": "evidence_conditional",
            "authority": "user_internal_preference",
        }
    }
    assert audit_paper.resolve_internal_total_target(targets, {}) == (
        50,
        "evidence_conditional",
        "user_internal_preference",
    )


def test_internal_total_page_target_can_wait_for_user_or_lock_user_value():
    pending = {
        "internal_total_page_target": {
            "target": None,
            "mode": "user_decides",
            "authority": "pending_user_confirmation_after_figure_lock",
        }
    }
    locked = {
        "internal_total_page_target": {
            "target": 56,
            "mode": "user_locked",
            "authority": "user_confirmation",
        }
    }
    assert audit_paper.resolve_internal_total_target(pending, {}) == (
        0,
        "user_decides",
        "pending_user_confirmation_after_figure_lock",
    )
    assert audit_paper.resolve_internal_total_target(locked, {}) == (
        56,
        "user_locked",
        "user_confirmation",
    )


def _front_matter_manifest(title):
    return {
        "title": title,
        "keywords": ["雷达", "降水", "校准"],
        "chapters": [
            {"title": "问题重述", "role": "problem", "order": 1},
            {"title": "参考文献", "role": "references", "order": 2},
        ],
    }


def _title_line(text, y, width, size=16.0):
    bbox = [180.0, y, 180.0 + width, y + 18.0]
    return {
        "text": text,
        "bbox": bbox,
        "spans": [{"text": text, "size": size, "bbox": bbox}],
    }


def _front_matter_records(
        title_lines, *, page3_text="问题重述", abstract_size=12.0,
        keyword_size=12.0, extra_body_spans=None):
    title = "".join(line["text"] for line in title_lines)
    first_y = min((line["bbox"][1] for line in title_lines), default=188.0)
    last_y = max((line["bbox"][3] for line in title_lines), default=206.0)
    abstract_y = last_y + 24.0
    body_y = abstract_y + 32.0
    keywords_y = body_y + 34.0
    body_spans = [
        {
            "text": "摘要正文包含模型x",
            "size": abstract_size,
            "bbox": [64.0, body_y, 320.0, body_y + 16.0],
        },
        {
            "text": "2",
            "size": 7.0,
            "bbox": [321.0, body_y - 3.0, 327.0, body_y + 7.0],
        },
        *(extra_body_spans or []),
    ]
    page2_lines = [
        {"text": "题 目：", "bbox": [70.0, first_y, 150.0, first_y + 18.0]},
        *title_lines,
        {"text": "摘 要：", "bbox": [260.0, abstract_y, 335.0, abstract_y + 18.0]},
        {
            "text": "".join(span["text"] for span in body_spans),
            "bbox": [64.0, body_y - 3.0, 400.0, body_y + 18.0],
            "spans": body_spans,
        },
        {
            "text": "关键词：雷达降水校准",
            "bbox": [64.0, keywords_y, 300.0, keywords_y + 18.0],
            "spans": [
                {
                    "text": "关键词：",
                    "size": 18.0,
                    "bbox": [64.0, keywords_y, 130.0, keywords_y + 18.0],
                },
                {
                    "text": "雷达降水校准",
                    "size": keyword_size,
                    "bbox": [132.0, keywords_y, 300.0, keywords_y + 16.0],
                },
            ],
        },
    ]
    return [
        {"physical_page": 1, "text": "参赛信息封皮", "lines": []},
        {
            "physical_page": 2,
            "text": f"题 目：{title}\n摘 要：摘要正文\n关键词：雷达 降水 校准",
            "lines": page2_lines,
        },
        {"physical_page": 3, "text": page3_text, "lines": []},
    ]


def test_abstract_front_matter_accepts_one_rendered_title_line():
    lines = [_title_line("强对流降水临近预报", 188.0, 190.0)]
    result = audit_paper.abstract_front_matter_audit(
        _front_matter_records(lines),
        _front_matter_manifest("强对流降水临近预报"),
    )
    assert result["failures"] == []
    assert result["details"]["title_line_count"] == 1
    font = result["details"]["abstract_body_font"]
    assert font["dominant_pt"] == 12.0
    assert font["ignored_small_span_weight_ratio"] > 0
    assert "18.0" not in font["size_weight_histogram"]


def _compile_identity_example_pdf(tmp_path, source):
    assert shutil.which("xelatex") is not None, "xelatex is required for this integration test"
    template = ASSETS / "paper-template"
    project = tmp_path / "paper"
    figures = project / "figures"
    figures.mkdir(parents=True)
    for name in ("gmcmthesis.cls", "gmcm-title.sty"):
        shutil.copy2(template / name, project / name)
    for name in (
            "identity-cpipc.png", "identity-gmcm.png",
            "identity-huawei.jpg", "identity-xjtu.png"):
        shutil.copy2(template / "figures" / name, figures / name)

    main = project / "main.tex"
    main.write_text(source, encoding="utf-8")
    command = [
        "xelatex", "-interaction=nonstopmode", "-halt-on-error",
        "-file-line-error", main.name,
    ]
    for _ in range(2):
        run = subprocess.run(
            command,
            cwd=project,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
    return main.with_suffix(".pdf")


def test_tracked_identity_pdf_uses_true_keyword_label_and_full_abstract_region(tmp_path):
    template = ASSETS / "paper-template"
    source = (template / "example-with-identity-cover.tex").read_text(encoding="utf-8")
    pdf = _compile_identity_example_pdf(tmp_path, source)
    manifest = {
        "title": "请替换为匿名论文题目",
        "keywords": ["数学建模", "封皮后匿名", "格式核对", "可复现"],
        "chapters": [{"title": "问题重述", "role": "problem", "order": 1}],
    }
    result = audit_paper.abstract_front_matter_audit(
        audit_paper.extract_page_records(pdf), manifest
    )
    assert result["failures"] == []
    details = result["details"]
    font = details["abstract_body_font"]
    assert details["label_rows"] == {
        "title": "题目:请替换为匿名论文题目",
        "abstract": "摘要:",
        "keywords": "关键词:数学建模",
    }
    assert "普通年份、编号和中间量不机械加粗" in font["audited_body_text"]
    assert font["audited_keyword_content_text"] == "数学建模封皮后匿名格式核对可复现"
    assert details["title_content_font"]["dominant_pt"] == 16.0


def test_rendered_label_rows_require_exact_compact_prefix():
    record = {
        "lines": [
            {"text": "论文题目含摘要一词", "bbox": [64.0, 100.0, 300.0, 118.0]},
            {"text": "正文讨论关键词：不是标签", "bbox": [64.0, 130.0, 330.0, 148.0]},
        ]
    }
    assert audit_paper._rendered_label_row(record, "题目") is None
    assert audit_paper._rendered_label_row(record, "摘要") is None
    assert audit_paper._rendered_label_row(record, "关键词") is None


def test_abstract_front_matter_accepts_balanced_two_rendered_title_lines():
    lines = [
        _title_line("基于多源雷达数据的", 188.0, 210.0),
        _title_line("强对流降水临近预报", 210.0, 180.0),
    ]
    title = "基于多源雷达数据的强对流降水临近预报"
    result = audit_paper.abstract_front_matter_audit(
        _front_matter_records(lines), _front_matter_manifest(title)
    )
    assert result["failures"] == []
    assert result["details"]["title_line_count"] == 2
    assert result["details"]["title_two_line_width_ratio"] == 0.8571


def test_abstract_front_matter_rejects_extremely_short_second_title_line():
    lines = [
        _title_line("基于多源雷达数据的强对流降水", 188.0, 240.0),
        _title_line("预报", 210.0, 36.0),
    ]
    title = "基于多源雷达数据的强对流降水预报"
    result = audit_paper.abstract_front_matter_audit(
        _front_matter_records(lines), _front_matter_manifest(title)
    )
    assert "abstract_page_title_two_line_unbalanced" in {
        item["code"] for item in result["failures"]
    }
    assert result["details"]["title_two_line_min_ratio_authority"] == (
        "internal_quality_rule_not_official"
    )


def test_abstract_front_matter_rejects_three_title_lines():
    lines = [
        _title_line("基于雷达", 188.0, 120.0),
        _title_line("强对流降水", 210.0, 130.0),
        _title_line("临近预报", 232.0, 100.0),
    ]
    title = "基于雷达强对流降水临近预报"
    result = audit_paper.abstract_front_matter_audit(
        _front_matter_records(lines), _front_matter_manifest(title)
    )
    assert "abstract_page_title_line_count_invalid" in {
        item["code"] for item in result["failures"]
    }


def test_abstract_front_matter_rejects_keywords_overflow_to_page3():
    lines = [_title_line("强对流降水临近预报", 188.0, 190.0)]
    result = audit_paper.abstract_front_matter_audit(
        _front_matter_records(lines, page3_text="关键词：校准\n问题重述"),
        _front_matter_manifest("强对流降水临近预报"),
    )
    assert "keywords_overflow_to_physical_page3" in {
        item["code"] for item in result["failures"]
    }


def test_abstract_front_matter_rejects_body_not_starting_on_page3():
    lines = [_title_line("强对流降水临近预报", 188.0, 190.0)]
    result = audit_paper.abstract_front_matter_audit(
        _front_matter_records(lines, page3_text="摘要延续内容"),
        _front_matter_manifest("强对流降水临近预报"),
    )
    assert "body_not_starting_on_physical_page3" in {
        item["code"] for item in result["failures"]
    }


def test_abstract_front_matter_rejects_residue_before_page3_body_heading():
    lines = [_title_line("强对流降水临近预报", 188.0, 190.0)]
    result = audit_paper.abstract_front_matter_audit(
        _front_matter_records(lines, page3_text="摘要延续内容\n1 问题重述"),
        _front_matter_manifest("强对流降水临近预报"),
    )
    assert result["details"]["first_body_title_on_page3"] is True
    assert "abstract_residue_before_body_on_physical_page3" in {
        item["code"] for item in result["failures"]
    }


def test_abstract_front_matter_ignores_title_repeated_inside_abstract_body():
    title = "强对流降水临近预报"
    records = _front_matter_records([])
    records[1]["text"] = (
        f"题 目：\n摘 要：本文研究{title}问题\n"
        "关键词：雷达 降水 校准"
    )
    records[1]["lines"].append(
        {"text": f"本文研究{title}问题", "bbox": [64.0, 280.0, 500.0, 298.0]}
    )
    result = audit_paper.abstract_front_matter_audit(
        records, _front_matter_manifest(title)
    )
    assert result["details"]["title_present"] is True
    assert result["details"]["title_line_count"] == 0
    assert "abstract_page_title_line_count_invalid" in {
        item["code"] for item in result["failures"]
    }


def test_abstract_front_matter_rejects_body_title_as_sentence_substring():
    lines = [_title_line("强对流降水临近预报", 188.0, 190.0)]
    result = audit_paper.abstract_front_matter_audit(
        _front_matter_records(lines, page3_text="问题重述用于说明摘要残留"),
        _front_matter_manifest("强对流降水临近预报"),
    )
    assert result["details"]["first_body_title_on_page3"] is False
    assert "body_not_starting_on_physical_page3" in {
        item["code"] for item in result["failures"]
    }


def test_abstract_front_matter_rejects_globally_shrunken_abstract_font():
    title = "强对流降水临近预报"
    lines = [_title_line(title, 188.0, 190.0)]
    result = audit_paper.abstract_front_matter_audit(
        _front_matter_records(lines, abstract_size=10.9),
        _front_matter_manifest(title),
    )
    assert result["details"]["abstract_body_font"]["dominant_pt"] == 10.9
    assert "abstract_body_dominant_font_too_small" in {
        item["code"] for item in result["failures"]
    }


def test_abstract_front_matter_rejects_globally_enlarged_abstract_font():
    title = "强对流降水临近预报"
    lines = [_title_line(title, 188.0, 190.0)]
    result = audit_paper.abstract_front_matter_audit(
        _front_matter_records(lines, abstract_size=14.0, keyword_size=14.0),
        _front_matter_manifest(title),
    )
    assert result["details"]["abstract_body_font"]["dominant_pt"] == 14.0
    assert "abstract_body_dominant_font_too_large" in {
        item["code"] for item in result["failures"]
    }


def test_abstract_front_matter_rejects_small_cjk_span_even_when_shifted_and_minor():
    title = "强对流降水临近预报"
    lines = [_title_line(title, 188.0, 190.0)]
    result = audit_paper.abstract_front_matter_audit(
        _front_matter_records(
            lines,
            extra_body_spans=[{
                "text": "短段",
                "size": 10.0,
                "bbox": [332.0, 259.0, 370.0, 269.0],
            }],
        ),
        _front_matter_manifest(title),
    )
    assert result["details"]["abstract_body_font"]["dominant_pt"] == 12.0
    assert "abstract_body_cjk_span_too_small" in {
        item["code"] for item in result["failures"]
    }


def test_abstract_front_matter_rejects_shrunken_keyword_content():
    title = "强对流降水临近预报"
    lines = [_title_line(title, 188.0, 190.0)]
    result = audit_paper.abstract_front_matter_audit(
        _front_matter_records(lines, keyword_size=10.0),
        _front_matter_manifest(title),
    )
    font = result["details"]["abstract_body_font"]
    assert font["keyword_content_span_count"] == 1
    assert "abstract_keyword_content_font_out_of_range" in {
        item["code"] for item in result["failures"]
    }


def test_manifest_keyword_must_appear_in_keyword_block_not_only_abstract_body():
    title = "强对流降水临近预报"
    lines = [_title_line(title, 188.0, 190.0)]
    records = _front_matter_records(
        lines,
        extra_body_spans=[{
            "text": "独有词",
            "size": 12.0,
            "bbox": [332.0, 262.0, 380.0, 278.0],
        }],
    )
    records[1]["text"] = records[1]["text"].replace("摘要正文", "摘要正文独有词")
    manifest = _front_matter_manifest(title)
    manifest["keywords"].append("独有词")
    result = audit_paper.abstract_front_matter_audit(records, manifest)
    assert "独有词" in audit_paper._compact_text(records[1]["text"])
    assert result["details"]["missing_keywords"] == ["独有词"]
    assert "abstract_page_keywords_missing" in {
        item["code"] for item in result["failures"]
    }


def test_real_pdf_rejects_abstract_and_title_shrunk_through_macro_alias(tmp_path):
    template = ASSETS / "paper-template"
    source = (template / "example-with-identity-cover.tex").read_text(encoding="utf-8")
    source = source.replace(
        r"\title{请替换为匿名论文题目}",
        "\\newcommand{\\shrinktitle}{\\small}\n"
        "\\title{\\shrinktitle 请替换为匿名论文题目}",
        1,
    )
    for command, value in {
        "schoolname": "Test University",
        "baominghao": "TEAM-001",
        "membera": "Member A",
        "memberb": "Member B",
        "memberc": "Member C",
    }.items():
        source = source.replace(rf"\{command}{{}}", rf"\{command}{{{value}}}")
    source = source.replace(
        r"\begin{document}",
        "\\newcommand{\\shrinkabstract}{\\small}\n\\begin{document}",
        1,
    ).replace(
        r"\begin{abstract}",
        "\\begin{abstract}\n\\shrinkabstract",
        1,
    )
    pdf = _compile_identity_example_pdf(tmp_path, source)
    records = audit_paper.extract_page_records(pdf)
    manifest = {
        "title": "请替换为匿名论文题目",
        "keywords": ["数学建模", "封皮后匿名", "格式核对", "可复现"],
        "chapters": [{"title": "问题重述", "role": "problem", "order": 1}],
    }
    result = audit_paper.abstract_front_matter_audit(records, manifest)
    assert result["details"]["abstract_body_font"]["dominant_pt"] < 11.5
    assert result["details"]["title_content_font"]["dominant_pt"] < 15.5
    assert "abstract_body_dominant_font_too_small" in {
        item["code"] for item in result["failures"]
    }
    assert "abstract_page_title_font_out_of_range" in {
        item["code"] for item in result["failures"]
    }


def _terminal_record(page, *rows):
    lines = [
        {"text": text, "bbox": [60.0, 60.0 + index * 24, 400.0, 78.0 + index * 24]}
        for index, text in enumerate(rows)
    ]
    return {
        "physical_page": page,
        "text": "\n".join(rows),
        "lines": lines,
        "spans": [],
        "width": 595.0,
        "height": 842.0,
    }


def test_terminal_chapters_start_on_new_physical_pages_and_appendix_is_optional():
    records = [
        _terminal_record(1, "结论正文"),
        _terminal_record(2, "参考文献", "[1] 文献条目"),
    ]
    manifest = {
        "chapters": [
            {"chapter_id": "refs", "title": "参考文献", "role": "references"},
        ]
    }
    result = audit_paper.terminal_chapter_page_audit(
        records, manifest, manifest_supplied=True
    )
    assert result["failures"] == []
    assert result["details"]["declared_appendix_count"] == 0

    records.append(_terminal_record(3, "附录 A 可复现代码", "算法步骤"))
    manifest["chapters"].append({
        "chapter_id": "appendix-a",
        "title": "附录 A 可复现代码",
        "role": "appendix",
    })
    result = audit_paper.terminal_chapter_page_audit(
        records, manifest, manifest_supplied=True
    )
    assert result["failures"] == []
    assert result["details"]["rendered_appendix_pages"] == [3]


def test_terminal_chapter_audit_rejects_missing_references_manifest_role():
    result = audit_paper.terminal_chapter_page_audit(
        [_terminal_record(1, "问题重述")],
        {"chapters": [{"chapter_id": "body", "title": "问题重述", "role": "problem"}]},
        manifest_supplied=True,
    )
    assert "manifest_must_declare_one_references_chapter" in {
        item["code"] for item in result["failures"]
    }


def test_terminal_chapter_audit_rejects_undeclared_rendered_appendix():
    records = [
        _terminal_record(1, "参考文献", "[1] 文献条目"),
        _terminal_record(2, "附录 A 代码框架", "算法步骤"),
    ]
    manifest = {
        "chapters": [
            {"chapter_id": "refs", "title": "参考文献", "role": "references"},
        ]
    }
    result = audit_paper.terminal_chapter_page_audit(
        records, manifest, manifest_supplied=True
    )
    assert "rendered_appendix_missing_manifest_role" in {
        item["code"] for item in result["failures"]
    }


def test_terminal_chapter_audit_rejects_heading_after_body_on_same_page():
    records = [_terminal_record(1, "结论尾段", "参考文献", "[1] 文献条目")]
    manifest = {
        "chapters": [
            {"chapter_id": "refs", "title": "参考文献", "role": "references"},
        ]
    }
    result = audit_paper.terminal_chapter_page_audit(
        records, manifest, manifest_supplied=True
    )
    assert "terminal_chapter_does_not_start_physical_page" in {
        item["code"] for item in result["failures"]
    }


def test_terminal_chapter_audit_is_unverifiable_without_manifest_not_fake_pass():
    result = audit_paper.terminal_chapter_page_audit(
        [_terminal_record(1, "参考文献")], {}, manifest_supplied=False
    )
    assert result["details"]["verifiable"] is False
    assert result["failures"] == []
