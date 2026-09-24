# -*- coding: utf-8 -*-
"""Guard the audited figures4papers coverage and mixed-license boundary."""
from __future__ import annotations

import hashlib
import json
import re
import runpy

from conftest import REPO_ROOT


SKILL = REPO_ROOT / "skills" / "academic-figure"
LOCK = SKILL / "references" / "figures4papers.lock.json"
EXPECTED_COMMIT = "3c181f85e82c6f24948fcaaf3be6696102b41d8d"  # pragma: allowlist secret


def _git_blob_sha(data: bytes) -> str:
    # Git may check text files out with CRLF on Windows. Provenance is tied to
    # the canonical upstream blob, so normalize transport newlines first.
    data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def test_figures4papers_inventory_covers_the_locked_tree_76_of_76():
    data = json.loads(LOCK.read_text(encoding="utf-8"))
    files = data["files"]
    expected = data["expected"]

    assert data["upstream"]["commit"] == EXPECTED_COMMIT
    assert data["upstream"]["license"] == "CC BY-NC 4.0"
    assert expected == {
        "tree_entries": 95,
        "files": 76,
        "bytes": 33_947_895,
        "python": 25,
        "png": 39,
        "pdf": 3,
        "markdown": 7,
    }
    assert len(files) == expected["files"]
    assert len({item["path"] for item in files}) == expected["files"]
    assert sum(item["bytes"] for item in files) == expected["bytes"]
    assert all(item["disposition"] for item in files)


def test_redistributed_figures4papers_files_are_mapped_and_exact_files_still_match():
    data = json.loads(LOCK.read_text(encoding="utf-8"))
    mapped = [item for item in data["files"] if item.get("target")]
    exact = [item for item in mapped if item["disposition"] == "existing-cc-by-nc-exact"]
    adapted = [item for item in mapped if item["disposition"] == "existing-cc-by-nc-adapted"]
    skill_exact = [
        item
        for item in mapped
        if item["disposition"] == "redistributed-cc-by-nc-exact"
    ]
    skill_adapted = [
        item
        for item in mapped
        if item["disposition"] == "redistributed-cc-by-nc-adapted"
    ]

    assert len(mapped) == 26
    assert len(exact) == 17
    assert len(adapted) == 3
    assert len(skill_exact) == 4
    assert len(skill_adapted) == 2
    for item in mapped:
        target = REPO_ROOT / item["target"]
        assert target.is_file(), item["target"]
    for item in exact + skill_exact:
        target = REPO_ROOT / item["target"]
        assert _git_blob_sha(target.read_bytes()) == item["blob_sha"], item["target"]
    for item in skill_adapted:
        target = REPO_ROOT / item["target"]
        assert _git_blob_sha(target.read_bytes()) != item["blob_sha"], item["target"]


def test_scientific_figure_making_skill_is_independently_distributed():
    nested = REPO_ROOT / "skills" / "scientific-figure-making"
    required = {
        "SKILL.md",
        "SOURCE.md",
        "LICENSE",
        "agents/openai.yaml",
        "references/api.md",
        "references/common-patterns.md",
        "references/demos.md",
        "references/design-theory.md",
        "references/tutorials.md",
    }
    assert required == {
        path.relative_to(nested).as_posix()
        for path in nested.rglob("*")
        if path.is_file()
    }

    source = (nested / "SOURCE.md").read_text(encoding="utf-8")
    skill = (nested / "SKILL.md").read_text(encoding="utf-8")
    demos = (nested / "references" / "demos.md").read_text(encoding="utf-8")
    license_text = (nested / "LICENSE").read_text(encoding="utf-8")
    for required_text in (
        "ChenLiu-1996/figures4papers",
        EXPECTED_COMMIT,
        "CC BY-NC 4.0",
        "do not relicense",
    ):
        assert required_text.lower() in source.lower()
    assert "figures4papers safety profile" in skill
    assert "commercial, enterprise, paid, or unclear" in skill
    assert "tree/main/" not in demos
    assert demos.count(EXPECTED_COMMIT) >= 9
    assert "Attribution-NonCommercial 4.0 International" in license_text
    assert license_text == (SKILL / "LICENSES" / "CC-BY-NC-4.0.txt").read_text(
        encoding="utf-8"
    )

    for install_doc in (
        REPO_ROOT / "README.md",
        SKILL / "README.md",
        SKILL / "README_EN.md",
    ):
        install_text = install_doc.read_text(encoding="utf-8")
        assert "skills/scientific-figure-making" in install_text.replace("\\", "/")
        assert ".codex/skills/scientific-figure-making" in install_text.replace(
            "\\", "/"
        )


def test_notice_license_and_safety_profile_travel_with_the_files():
    notice = (SKILL / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    license_text = (SKILL / "LICENSES" / "CC-BY-NC-4.0.txt").read_text(
        encoding="utf-8"
    )
    profile = (SKILL / "references" / "figures4papers-profile.md").read_text(
        encoding="utf-8"
    )

    for required in ("ChenLiu-1996/figures4papers", EXPECTED_COMMIT, "CC BY-NC 4.0"):
        assert required in notice
    assert "Attribution-NonCommercial 4.0 International" in license_text
    profile_lower = profile.lower()
    for required in (
        "adopt",
        "adapt",
        "reject",
        "reference-only",
        "F4P-BAR-01",
        "F4P-HEAT-02",
        "F4P-RADAR-01",
        "F4P-3D-02",
        "zero baseline",
        "colorblind-safe",
    ):
        assert required.lower() in profile_lower


def test_skill_routes_through_license_first_gate():
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "Step 2.5: Source and License Gate" in skill
    assert "references/figures4papers-profile.md" in skill
    assert "references/figures4papers.lock.json" in skill
    assert "THIRD_PARTY_NOTICES.md" in skill
    assert "This gate overrides every generic" in skill


def test_codex_adapter_generator_preserves_license_resources():
    generator = runpy.run_path(str(SKILL / "scripts" / "generate_adapters.py"))
    generated, generated_instructions = generator["generate_codex_manifest"](
        generator["extract_core_rules"]()
    )
    checked_in = (SKILL / "install" / "codex" / "manifest.yaml").read_text(
        encoding="utf-8"
    )
    checked_in_instructions = (
        SKILL / "install" / "codex" / "instructions.md"
    ).read_text(encoding="utf-8")

    for required in (
        'version: "1.2.0"',
        "  - LICENSE\n",
        "  - THIRD_PARTY_NOTICES.md\n",
        "  - LICENSES/\n",
        "  - ../scientific-figure-making/\n",
    ):
        assert required in generated
        assert required in checked_in

    def normalize_timestamp(text: str) -> str:
        return re.sub(
            r"Auto-generated from academic-figure-skill/SKILL\.md — .* UTC",
            "Auto-generated from academic-figure-skill/SKILL.md — <TIME>",
            re.sub(r"# Generated: .* UTC", "# Generated: <TIME>", text),
        )

    assert normalize_timestamp(generated) == normalize_timestamp(checked_in)
    assert normalize_timestamp(generated_instructions) == normalize_timestamp(
        checked_in_instructions
    )


def test_ci_supports_published_checksums_and_pdf_integration():
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    assert "figures4papers\\.lock\\.json$" in workflow
    assert "texlive-xetex" in workflow
    assert "texlive-fonts-recommended" in workflow
    assert "texlive-lang-chinese" in workflow
    assert "texlive-plain-generic" in workflow
    assert "texlive-science" in workflow
    assert "fonts-texgyre-math" in workflow
    assert "/usr/local/share/fonts/fandol" in workflow
    assert "fc-cache -f" in workflow
