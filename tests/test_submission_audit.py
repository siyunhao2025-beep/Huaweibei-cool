# -*- coding: utf-8 -*-
"""Smoke-test the 2026 cover-aware submission audit."""

import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from conftest import ASSETS, REPO_ROOT, SCRIPTS

EXAMPLE = ASSETS / "paper-template" / "example.tex"
COVER_EXAMPLE = ASSETS / "paper-template" / "example-with-identity-cover.tex"


def filled_cover_text(source: str) -> str:
    values = {
        "schoolname": "甲大学",
        "baominghao": "TEAM-001",
        "membera": "甲",
        "memberb": "乙",
        "memberc": "丙",
    }
    for command, value in values.items():
        source = source.replace(rf"\{command}{{}}", rf"\{command}{{{value}}}")
    return source


def test_submission_audit_rejects_blank_cover_scaffold():
    """A blank template is a scaffold, not a formal submission."""
    assert EXAMPLE.is_file(), f"missing example.tex: {EXAMPLE}"
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPTS / "submission_audit.py"),
            "--paper",
            str(EXAMPLE),
            "--ai-used",
            "none",
            "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert proc.returncode == 1, f"unexpected exit code: {proc.returncode}\n{proc.stderr}"
    out = json.loads(proc.stdout)
    assert out["passed"] is False
    assert any(not check["ok"] and "均已填写" in check["desc"] for check in out["checks"])


def test_submission_audit_rejects_invisible_cover_values(tmp_path):
    """TeX spacing commands do not count as filled identity values."""
    invisible = EXAMPLE.read_text(encoding="utf-8")
    for command in ("schoolname", "baominghao", "membera", "memberb", "memberc"):
        invisible = invisible.replace(rf"\{command}{{}}", rf"\{command}{{\quad}}")
    paper = tmp_path / "invisible-cover.tex"
    paper.write_text(invisible, encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPTS / "submission_audit.py"),
            "--paper",
            str(paper),
            "--ai-used",
            "none",
            "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert proc.returncode == 1
    out = json.loads(proc.stdout)
    assert any(not check["ok"] and "均已填写" in check["desc"] for check in out["checks"])


def test_submission_audit_accepts_filled_cover_entry(tmp_path):
    """A filled cover with anonymous following pages is submission-ready."""
    assert COVER_EXAMPLE.is_file(), f"missing cover example: {COVER_EXAMPLE}"
    filled = tmp_path / "filled-cover.tex"
    filled.write_text(
        filled_cover_text(COVER_EXAMPLE.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPTS / "submission_audit.py"),
            "--paper",
            str(filled),
            "--ai-used",
            "none",
            "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["passed"] is True
    assert any(check["ok"] and "封皮" in check["desc"] for check in out["checks"])


def test_submission_audit_rejects_identity_after_cover(tmp_path):
    """Identity text outside the permitted cover must fail."""
    leaked = tmp_path / "leaked.tex"
    text = filled_cover_text(EXAMPLE.read_text(encoding="utf-8"))
    text = text.replace(r"\section{问题重述}", "学校：测试大学\n" + r"\section{问题重述}")
    leaked.write_text(text, encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPTS / "submission_audit.py"),
            "--paper",
            str(leaked),
            "--ai-used",
            "none",
            "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert proc.returncode == 1
    out = json.loads(proc.stdout)
    assert out["passed"] is False
    assert any(not check["ok"] and "封皮之后" in check["desc"] for check in out["checks"])


def test_submission_audit_rejects_blank_cover_pdf(tmp_path):
    """The compiled blank sample must not masquerade as a filled formal PDF."""
    import submission_audit

    pdf = tmp_path / "blank-cover.pdf"
    pymupdf = submission_audit.load_pymupdf()
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((80, 370), "SCHOOL")
    page.insert_text((80, 410), "TEAM")
    page.insert_text((80, 460), "MEMBERS 1 2 3")
    document.save(pdf)
    document.close()
    assert submission_audit.pdf_cover_fields_complete(pdf) is False


@pytest.mark.parametrize(
    "placeholder",
    [
        "TODO", "FIXME", "TBD", "REPLACE_WITH_ACTUAL", "____", "----", "xx",
        "待填", "请填写", "占位",
    ],
)
def test_cover_value_rejects_placeholder_tokens(placeholder):
    import submission_audit

    assert submission_audit.cover_value_is_valid(placeholder) is False


@pytest.mark.parametrize(
    "placeholder",
    ["TODO", "FIXME", "TBD", "REPLACE_WITH_ACTUAL", "____", "----", "xx"],
)
def test_pdf_cover_rejects_five_placeholder_fields(tmp_path, placeholder):
    import submission_audit

    pdf = tmp_path / f"placeholder-{placeholder[:4]}.pdf"
    pymupdf = submission_audit.load_pymupdf()
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    for point in ((200, 365), (200, 410), (240, 450), (240, 486), (240, 525)):
        page.insert_text(point, placeholder)
    document.save(pdf)
    document.close()
    assert submission_audit.pdf_cover_fields_complete(pdf) is False


def _write_bound_manifest(tmp_path, *, references=True, appendix=False):
    chapters = [{
        "chapter_id": "body", "title": "Body", "role": "preliminary",
        "order": 1, "tex_path": "body.tex",
    }]
    if references:
        chapters.append({
            "chapter_id": "refs", "title": "References", "role": "references",
            "order": len(chapters) + 1, "tex_path": "refs.tex",
        })
    if appendix:
        chapters.append({
            "chapter_id": "appendix-a", "title": "Appendix A Code", "role": "appendix",
            "order": len(chapters) + 1, "tex_path": "appendix.tex",
        })
    inputs = ["abstract.tex", *(chapter["tex_path"] for chapter in chapters)]
    for name in inputs:
        (tmp_path / name).write_text("fragment", encoding="utf-8")
    source = tmp_path / "main.tex"
    source.write_text(
        "\n".join(rf"\input{{{name}}}" for name in inputs),
        encoding="utf-8",
    )
    manifest = tmp_path / "论文输入.json"
    manifest.write_text(
        json.dumps({
            "title": "Bound audit paper",
            "keywords": ["alpha", "beta", "gamma"],
            "abstract_tex_path": "abstract.tex",
            "appendix_pseudocode": (
                {"required": True} if appendix else
                {"required": False, "reason": "纯解析推导，不涉及程序求解与数据处理"}
            ),
            "chapters": chapters,
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    paper = tmp_path / "paper.pdf"
    paper.write_bytes(b"%PDF synthetic")
    return paper, source, manifest


def _terminal_record(page, *rows):
    return {
        "physical_page": page,
        "text": "\n".join(rows),
        "lines": [
            {"text": text, "bbox": [72.0, 72.0 + index * 24, 300.0, 88.0 + index * 24]}
            for index, text in enumerate(rows)
        ],
        "spans": [],
        "width": 595.0,
        "height": 842.0,
    }


def _patch_front_matter(monkeypatch, records):
    import audit_paper

    monkeypatch.setattr(audit_paper, "extract_page_records", lambda _paper: records)
    monkeypatch.setattr(
        audit_paper,
        "abstract_front_matter_audit",
        lambda _records, _manifest: {"details": {"verifiable": True}, "failures": []},
    )


def test_manifest_bound_submission_rejects_terminal_heading_after_same_page_residue(
        tmp_path, monkeypatch):
    import submission_audit

    paper, source, manifest = _write_bound_manifest(tmp_path)
    _patch_front_matter(
        monkeypatch,
        [_terminal_record(1, "Conclusion residue", "References", "[1] Source")],
    )
    result = submission_audit.audit_manifest_bound_pdf(paper, source, manifest)
    assert result["ok"] is False
    assert "terminal_chapter_does_not_start_physical_page" in {
        item["code"] for item in result["terminal_chapters"]["failures"]
    }


def test_manifest_bound_submission_rejects_missing_references_role(tmp_path, monkeypatch):
    import submission_audit

    paper, source, manifest = _write_bound_manifest(tmp_path, references=False)
    _patch_front_matter(monkeypatch, [_terminal_record(1, "Body")])
    result = submission_audit.audit_manifest_bound_pdf(paper, source, manifest)
    assert result["ok"] is False
    assert "manifest_must_declare_one_references_chapter" in {
        item["code"] for item in result["terminal_chapters"]["failures"]
    }


def test_manifest_bound_submission_rejects_front_matter_overflow(tmp_path, monkeypatch):
    import audit_paper
    import submission_audit

    paper, source, manifest = _write_bound_manifest(tmp_path)
    records = [_terminal_record(1, "Body"), _terminal_record(2, "References")]
    monkeypatch.setattr(audit_paper, "extract_page_records", lambda _paper: records)
    monkeypatch.setattr(
        audit_paper,
        "abstract_front_matter_audit",
        lambda _records, _manifest: {
            "details": {"verifiable": True},
            "failures": [{"code": "keywords_overflow_to_physical_page3"}],
        },
    )
    result = submission_audit.audit_manifest_bound_pdf(paper, source, manifest)
    assert result["ok"] is False
    assert result["abstract_front_matter"]["failures"] == [
        {"code": "keywords_overflow_to_physical_page3"}
    ]


@pytest.mark.parametrize("appendix", [False, True])
def test_manifest_bound_submission_accepts_page_head_terminals_and_optional_appendix(
        tmp_path, monkeypatch, appendix):
    import submission_audit

    paper, source, manifest = _write_bound_manifest(tmp_path, appendix=appendix)
    records = [
        _terminal_record(1, "Body"),
        _terminal_record(2, "References", "[1] Source"),
    ]
    if appendix:
        records.append(_terminal_record(3, "Appendix A Code", "Algorithm"))
    _patch_front_matter(monkeypatch, records)
    result = submission_audit.audit_manifest_bound_pdf(paper, source, manifest)
    assert result["ok"] is True
    assert result["abstract_front_matter"]["failures"] == []
    assert result["terminal_chapters"]["failures"] == []
    assert result["binding"]["manifest_path"] == "论文输入.json"
    assert result["binding"]["manifest_sha256"] == submission_audit.file_sha256(manifest)


def test_manifest_binding_is_part_of_submission_provenance_and_source_hash(
        tmp_path, monkeypatch):
    import submission_audit

    paper, source, manifest = _write_bound_manifest(tmp_path)
    _patch_front_matter(
        monkeypatch,
        [_terminal_record(1, "Body"), _terminal_record(2, "References", "[1] Source")],
    )
    contract = submission_audit.audit_manifest_bound_pdf(paper, source, manifest)
    payload = {
        "passed": True,
        "pages": 2,
        "ai_used": "none",
        "cover_policy": "required",
        "checks": [{"ok": True, "desc": "bound", "evidence": contract["binding"]}],
        "warnings": [],
        "manifest_pdf_contract": contract,
    }
    args = SimpleNamespace(
        paper=str(paper), source=str(source), attachments=None, ai_file=None,
        max_total_pages=None, ai_used="none", cover_policy="required",
    )
    provenance = submission_audit.build_submission_provenance(args, tmp_path, payload)
    assert provenance["manifest_path"] == "论文输入.json"
    assert provenance["manifest_sha256"] == submission_audit.file_sha256(manifest)
    before = provenance["source_tree_sha256"]
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["title"] = "Changed bound audit paper"
    manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert submission_audit.source_tree_sha256(source) != before


def test_formal_source_bound_submission_cannot_skip_missing_manifest(
        tmp_path, monkeypatch, capsys):
    import submission_audit

    paper = tmp_path / "paper.pdf"
    pymupdf = submission_audit.load_pymupdf()
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "paper")
    document.save(paper)
    document.close()
    source = tmp_path / "main.tex"
    source.write_text(r"\documentclass{article}\begin{document}paper\end{document}", encoding="utf-8")
    signature = {"same": True}
    monkeypatch.setattr(
        submission_audit, "compile_tex_fingerprints",
        lambda _source: (signature, "test compile"),
    )
    monkeypatch.setattr(submission_audit, "pdf_fingerprints", lambda _paper: signature)
    return_code = submission_audit.main([
        "--paper", str(paper),
        "--source", str(source),
        "--cover-policy", "required",
        "--ai-used", "none",
        "--json",
    ])
    report = json.loads(capsys.readouterr().out)
    binding = next(item for item in report["checks"] if item.get("code") == "paper_manifest_binding")
    assert return_code == 1
    assert binding["ok"] is False
    assert binding["evidence"]["status"] == "not_found"
