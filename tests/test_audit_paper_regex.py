# -*- coding: utf-8 -*-
"""Regression checks for PDF audit patterns and footer detection."""

import audit_paper


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
