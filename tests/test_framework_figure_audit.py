# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import shutil

import pymupdf as fitz
from PIL import Image

import audit_framework_figure


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _binding(tmp_path, language: str = "zh-CN") -> tuple[dict, object]:
    source = tmp_path / "run" / "F01.png"
    upstream = tmp_path / "run" / "upstream-s5.png"
    target = tmp_path / "paper" / "F01.png"
    ledger = tmp_path / "run" / "labels.json"
    adaptation = tmp_path / "run" / "adaptation.md"
    prompts = tmp_path / "run" / "prompts.md"
    evidence = tmp_path / "run" / "measurement.txt"
    main_tex = tmp_path / "paper" / "main.tex"
    source.parent.mkdir()
    target.parent.mkdir()
    Image.new("RGB", (100, 60), "white").save(source)
    Image.new("RGB", (100, 60), "white").save(target)
    Image.new("RGB", (80, 50), "grey").save(upstream)
    tokens = ["ZH", "ZDR", "RMSE", "CSI35"]
    ledger.write_text(json.dumps({
        "labels": [{"source": "Flow", "target": "流程"}],
        "retained_technical_tokens": tokens,
    }, ensure_ascii=False), encoding="utf-8")
    adaptation.write_text("consumer adaptation", encoding="utf-8")
    prompts.write_text("localization prompt", encoding="utf-8")
    evidence.write_text("native component measurements", encoding="utf-8")
    main_tex.write_text(r"\includegraphics{F01.png}", encoding="utf-8")
    digest = audit_framework_figure.sha256(source)
    binding = {
        "schema_version": "1.0",
        "figure_id": "F01",
        "role": "complex_multi_question_framework",
        "document_language": language,
        "localization_mode": (
            "zh_primary_preserve_exact_tokens" if language == "zh-CN" else "source_language"
        ),
        "localization_origin": "explicit_post_s5_consumer_adaptation",
        "source_terminal_stage": "S5-CANDIDATE-IMAGE",
        "selected_source": "run/F01.png",
        "selected_source_sha256": digest,
        "latex_target": "paper/F01.png",
        "latex_target_sha256": digest,
        "main_tex": "paper/main.tex",
        "label": "fig:route",
        "label_ledger": "run/labels.json",
        "retained_technical_tokens": tokens,
        "unregistered_latin_prose_count": 0,
        "latin_font_policy": "times_new_roman_or_math_font",
        "user_authorization_record": "用户明确要求把选定总流程图中文化。",
        "consumer_adaptation_directory": "run",
        "upstream_s5_source": "run/upstream-s5.png",
        "upstream_s5_sha256": audit_framework_figure.sha256(upstream),
        "adaptation_record": "run/adaptation.md",
        "adaptation_record_sha256": audit_framework_figure.sha256(adaptation),
        "localization_prompt_record": "run/prompts.md",
        "localization_prompt_record_sha256": audit_framework_figure.sha256(prompts),
        "framework_text_qa": {
            "asset_kind": "raster",
            "target_insert_width_mm": 8,
            "minimum_ink_height_px": {
                "macro_group": 40, "node": 32, "edge_or_port": 25,
                "internal_micro": 25, "legend": 28,
            },
            "measurement_method": "native_pixel_component_measurement",
            "measurement_evidence": "run/measurement.txt",
            "measurement_evidence_sha256": audit_framework_figure.sha256(evidence),
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
    }
    path = tmp_path / "binding.json"
    return binding, path


def _paper_fields(binding: dict, pdf, page: int = 1) -> None:
    binding.update({
        "body_reference_before_figure": True,
        "caption_complete": True,
        "post_figure_interpretation": True,
        "compiled_pdf_visible": True,
        "compiled_pdf_page": page,
        "compiled_pdf": "paper/qa.pdf",
        "compiled_pdf_sha256": audit_framework_figure.sha256(pdf),
    })


def _vector_binding(tmp_path) -> tuple[dict, object]:
    binding, path = _binding(tmp_path)
    source = tmp_path / "run" / "F01.pdf"
    target = tmp_path / "paper" / "F01.pdf"
    document = fitz.open()
    page = document.new_page(width=200, height=100)
    page.draw_rect(fitz.Rect(10, 10, 190, 90), color=(0, 0.4, 0.8), width=2)
    page.insert_text((30, 58), "F01 VERIFIED VECTOR", fontsize=16)
    document.save(source)
    document.close()
    shutil.copyfile(source, target)
    digest = audit_framework_figure.sha256(source)
    binding.update({
        "selected_source": "run/F01.pdf",
        "selected_source_sha256": digest,
        "latex_target": "paper/F01.pdf",
        "latex_target_sha256": digest,
        "framework_text_qa": {
            "asset_kind": "vector_text",
            "target_insert_width_mm": 120,
            "minimum_effective_pt": {
                "macro_group": 11, "node": 10, "edge_or_port": 9,
                "internal_micro": 9, "legend": 9,
            },
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
    })
    (tmp_path / "paper" / "main.tex").write_text(
        r"\includegraphics[width=120mm]{F01.pdf}", encoding="utf-8"
    )
    return binding, path


def test_chinese_framework_figure_contract_passes(tmp_path):
    binding, path = _binding(tmp_path)
    path.write_text(json.dumps(binding, ensure_ascii=False), encoding="utf-8")

    result = audit_framework_figure.audit(path, tmp_path)

    assert result["status"] == "PASS", result["failures"]


def test_raster_fingerprint_supports_chinese_path(tmp_path):
    image = tmp_path / "论文" / "总流程图.png"
    image.parent.mkdir()
    Image.new("RGB", (17, 11), "navy").save(image)

    fingerprint = audit_framework_figure.raster_file_fingerprint(image)

    assert fingerprint[1:3] == (17, 11)


def test_collision_and_stale_hash_fail(tmp_path):
    binding, path = _binding(tmp_path)
    binding["framework_text_qa"]["violations"]["text_connector_collisions"] = 1
    binding["framework_text_qa"]["reviewed_asset_sha256"] = "0" * 64
    path.write_text(json.dumps(binding, ensure_ascii=False), encoding="utf-8")

    result = audit_framework_figure.audit(path, tmp_path)
    codes = {item["code"] for item in result["failures"]}

    assert result["status"] == "FAIL"
    assert "framework_zero_text_connector_collisions" in codes
    assert "framework_visual_qa_hash_is_current" in codes


def test_english_framework_figure_does_not_require_chinese_localization(tmp_path):
    binding, path = _binding(tmp_path, language="en")
    for key in (
        "label_ledger", "retained_technical_tokens",
        "unregistered_latin_prose_count", "latin_font_policy",
    ):
        binding.pop(key)
    path.write_text(json.dumps(binding, ensure_ascii=False), encoding="utf-8")

    result = audit_framework_figure.audit(path, tmp_path)

    assert result["status"] == "PASS", result["failures"]


def test_main_tex_must_reference_bound_asset(tmp_path):
    binding, path = _binding(tmp_path)
    (tmp_path / "paper" / "main.tex").write_text(
        r"\includegraphics{F01-old.png}", encoding="utf-8"
    )
    path.write_text(json.dumps(binding, ensure_ascii=False), encoding="utf-8")

    result = audit_framework_figure.audit(path, tmp_path)

    assert "framework_main_tex_references_bound_asset" in {
        item["code"] for item in result["failures"]
    }


def test_main_tex_simple_frameworkfigure_wrapper_resolves_exact_asset(tmp_path):
    binding, path = _binding(tmp_path)
    target = tmp_path / "paper" / "figures" / "F01.png"
    target.parent.mkdir()
    shutil.copyfile(tmp_path / "paper" / "F01.png", target)
    binding["latex_target"] = "paper/figures/F01.png"
    binding["latex_target_sha256"] = audit_framework_figure.sha256(target)
    (tmp_path / "paper" / "main.tex").write_text(
        r"""
\newcommand{\frameworkfigure}[3]{%
  \includegraphics[width=0.98\textwidth,keepaspectratio]{figures/#1.png}
  \caption{#2}\label{#3}}
\frameworkfigure{F01}{总流程图}{fig:route}
""",
        encoding="utf-8",
    )
    path.write_text(json.dumps(binding, ensure_ascii=False), encoding="utf-8")

    result = audit_framework_figure.audit(path, tmp_path)

    assert result["status"] == "PASS", result["failures"]


def test_paper_stage_verifies_pdf_page_contains_bound_image(tmp_path):
    binding, path = _binding(tmp_path)
    pdf = tmp_path / "paper" / "qa.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_image(fitz.Rect(0, 0, 100, 60), filename=str(tmp_path / "paper" / "F01.png"))
    document.save(pdf)
    document.close()
    _paper_fields(binding, pdf)
    path.write_text(json.dumps(binding, ensure_ascii=False), encoding="utf-8")

    result = audit_framework_figure.audit(path, tmp_path, stage="paper")

    assert result["status"] == "PASS", result["failures"]


def test_same_size_decoy_image_does_not_prove_pdf_binding(tmp_path):
    binding, path = _binding(tmp_path)
    decoy = tmp_path / "paper" / "decoy.png"
    Image.new("RGB", (100, 60), "black").save(decoy)
    pdf = tmp_path / "paper" / "qa.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_image(fitz.Rect(0, 0, 100, 60), filename=str(decoy))
    document.save(pdf)
    document.close()
    _paper_fields(binding, pdf)
    path.write_text(json.dumps(binding, ensure_ascii=False), encoding="utf-8")

    result = audit_framework_figure.audit(path, tmp_path, stage="paper")

    assert "framework_compiled_pdf_page_contains_bound_asset" in {
        item["code"] for item in result["failures"]
    }


def test_vector_text_paper_stage_uses_declared_region_visual_match(tmp_path):
    binding, path = _vector_binding(tmp_path)
    target = tmp_path / "paper" / "F01.pdf"
    pdf = tmp_path / "paper" / "qa.pdf"
    bbox = fitz.Rect(50, 100, 450, 300)
    source = fitz.open(target)
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.show_pdf_page(bbox, source, 0)
    document.save(pdf)
    document.close()
    source.close()
    binding["compiled_pdf_figure_bbox_pt"] = list(bbox)
    _paper_fields(binding, pdf)
    path.write_text(json.dumps(binding, ensure_ascii=False), encoding="utf-8")

    result = audit_framework_figure.audit(path, tmp_path, stage="paper")

    assert result["status"] == "PASS", result["failures"]


def test_vector_text_wrong_region_cannot_pass_pdf_binding(tmp_path):
    binding, path = _vector_binding(tmp_path)
    target = tmp_path / "paper" / "F01.pdf"
    pdf = tmp_path / "paper" / "qa.pdf"
    actual_bbox = fitz.Rect(50, 100, 450, 300)
    source = fitz.open(target)
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.show_pdf_page(actual_bbox, source, 0)
    document.save(pdf)
    document.close()
    source.close()
    binding["compiled_pdf_figure_bbox_pt"] = [50, 350, 450, 550]
    _paper_fields(binding, pdf)
    path.write_text(json.dumps(binding, ensure_ascii=False), encoding="utf-8")

    result = audit_framework_figure.audit(path, tmp_path, stage="paper")

    assert "framework_compiled_pdf_page_contains_bound_asset" in {
        item["code"] for item in result["failures"]
    }


def test_sparse_vector_blank_region_fails_despite_high_global_similarity(tmp_path):
    binding, path = _vector_binding(tmp_path)
    source_path = tmp_path / "run" / "F01.pdf"
    target_path = tmp_path / "paper" / "F01.pdf"
    sparse_path = tmp_path / "run" / "sparse.pdf"
    sparse = fitz.open()
    page = sparse.new_page(width=200, height=100)
    page.draw_line((70, 50), (130, 50), color=(0, 0, 0), width=2)
    sparse.save(sparse_path)
    sparse.close()
    shutil.copyfile(sparse_path, source_path)
    shutil.copyfile(source_path, target_path)
    digest = audit_framework_figure.sha256(source_path)
    binding["selected_source_sha256"] = digest
    binding["latex_target_sha256"] = digest
    binding["framework_text_qa"]["reviewed_asset_sha256"] = digest

    pdf = tmp_path / "paper" / "qa.pdf"
    actual_bbox = fitz.Rect(50, 100, 450, 300)
    source = fitz.open(target_path)
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.show_pdf_page(actual_bbox, source, 0)
    document.save(pdf)
    document.close()
    source.close()
    binding["compiled_pdf_figure_bbox_pt"] = [50, 350, 450, 550]
    _paper_fields(binding, pdf)
    path.write_text(json.dumps(binding, ensure_ascii=False), encoding="utf-8")

    result = audit_framework_figure.audit(path, tmp_path, stage="paper")
    contains_check = next(
        item for item in result["checks"]
        if item["code"] == "framework_compiled_pdf_page_contains_bound_asset"
    )

    assert contains_check["ok"] is False
    assert contains_check["verification"]["similarity"] > 0.97
    assert contains_check["verification"]["foreground_iou"] == 0
