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
