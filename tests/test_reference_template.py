import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "assets" / "paper-template" / "reference-23rd-latex"
MANIFEST = REFERENCE / "source-manifest.json"


def test_user_reference_manifest_and_optional_local_hashes():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["local_skill_loaded"] is True
    assert manifest["git_distribution"] is False
    assert len(manifest["files"]) == 6
    for item in manifest["files"]:
        assert item["local_loaded"] is True
        assert item["git_distributed"] is False
        assert len(item["sha256"]) == 64
        path = REFERENCE / item["path"]
        if path.is_file():
            assert path.stat().st_size == item["bytes"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
            assert digest == item["sha256"]


def test_production_template_never_imports_reference_package():
    template = ROOT / "assets" / "paper-template"
    production_files = [
        template / "example.tex",
        template / "example-with-identity-cover.tex",
        template / "gmcmthesis.cls",
        ROOT / "scripts" / "build_latex.py",
    ]
    for path in production_files:
        text = path.read_text(encoding="utf-8")
        assert "reference-23rd-latex" not in text
        assert "第二十二届" not in text
    assert "\\tableofcontents" not in (template / "example.tex").read_text(encoding="utf-8")


def test_2026_page_gate_is_off_until_an_official_limit_exists():
    contest = json.loads((ROOT / "config" / "contest.json").read_text(encoding="utf-8"))
    targets = json.loads((ROOT / "assets" / "paper-template" / "page_targets.json").read_text(encoding="utf-8"))
    gate = contest["paper"]["body_page_gate"]
    assert gate["mode"] == "off"
    assert gate["minimum"] == 0
    assert gate["maximum"] is None
    assert contest["paper"]["role_windows_enabled"] is False
    assert targets["body_page_gate_mode"] == "off"
    assert targets["required_body_pages"] == 0
    assert targets["role_windows_enabled"] is False

    official = (ROOT / "docs" / "OFFICIAL_FORMAT_2026.md").read_text(encoding="utf-8")
    assert "没有给出正文页数上限、全文总页数上限或正文最低页数" in official


def test_times_family_and_abstract_emphasis_rules_are_built_in():
    template = ROOT / "assets" / "paper-template"
    cls = (template / "gmcmthesis.cls").read_text(encoding="utf-8")
    abstract_fragment = (template / "章节模板" / "摘要模板.tex").read_text(encoding="utf-8")
    abstract_guide = (ROOT / "modules" / "abstract.md").read_text(encoding="utf-8")

    assert "\\setmainfont{Times New Roman}" in cls
    assert "\\setsansfont{Times New Roman}" in cls
    assert "texgyretermes" in cls
    assert "texgyreheros" not in cls
    assert "\\setmathfont{TeX Gyre Termes Math}" in cls
    assert "\\urlstyle{same}" in cls
    assert "\\textbf{【主要模型/算法】}" in abstract_fragment
    assert "年份、题号" in abstract_guide
    assert "不机械加粗" in abstract_guide
    assert "整句、整段加粗" in abstract_guide
