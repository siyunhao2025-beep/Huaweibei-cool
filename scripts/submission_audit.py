#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conservative pre-submission audit for a Huawei Cup paper.

The 2026 AI rules are conditional on how AI was used. This script never
treats an absent disclosure as evidence of a violation unless the user
explicitly declares relevant AI use with --ai-used.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


IDENTITY_PAT = re.compile(
    r"(?:学校|学院|实验室|参赛队号|队员姓名|指导教师|学号|邮箱)\s*[:：]|"
    r"\\(?:schoolname|baominghao|member[abc]|makeidentitycover)\b|"
    r"\b(?:school\s*name|team\s*(?:number|id)|member\s*name|"
    r"advisor\s*name|student\s*(?:id|number)|e-?mail)\b|"
    r"C:\\Users\\",
    re.IGNORECASE,
)
AI_MARKER = re.compile(
    r"人工智能工具|人工智能辅助|AI\s*(?:工具|辅助|生成)|"
    r"本程序及代码是在人工智能工具辅助下完成",
    re.IGNORECASE,
)
COVER_MARKERS = ("学校", "参赛队号", "队员姓名")
COVER_FIELDS = ("schoolname", "baominghao", "membera", "memberb", "memberc")


def load_pymupdf():
    try:
        import pymupdf  # type: ignore
    except ImportError:
        import fitz as pymupdf  # type: ignore
    return pymupdf


def count_pdf_pages(pdf: Path) -> int | None:
    try:
        import pypdf  # type: ignore
        with pdf.open("rb") as handle:
            return len(pypdf.PdfReader(handle).pages)
    except Exception:
        pass
    try:
        pymupdf = load_pymupdf()
        with pymupdf.open(pdf) as document:
            return document.page_count
    except Exception:
        return None


def strip_tex_comments(text: str) -> str:
    cleaned = []
    for line in text.splitlines():
        cut = len(line)
        for index, char in enumerate(line):
            if char != "%":
                continue
            backslashes = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                cut = index
                break
        cleaned.append(line[:cut])
    return "\n".join(cleaned)


def extract_pdf_pages(path: Path) -> list[str]:
    try:
        pymupdf = load_pymupdf()
        with pymupdf.open(path) as document:
            return [page.get_text() for page in document]
    except Exception:
        return []


def strip_tex_cover(text: str) -> str:
    """Remove only the officially permitted page-0 identity commands."""
    clean = strip_tex_comments(text)
    for command in COVER_FIELDS:
        clean = re.sub(rf"\\{command}\s*\{{[^{{}}]*\}}", "", clean, flags=re.S)
    return re.sub(r"\\makeidentitycover\b", "", clean)


def tex_cover_present(text: str) -> bool:
    clean = strip_tex_comments(text)
    return bool(re.search(r"\\makeidentitycover\b", clean)) and all(
        re.search(rf"\\{command}\s*\{{", clean) for command in COVER_FIELDS
    )


def extract_text(path: Path) -> str:
    """Extract enough text for conservative content checks."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            pymupdf = load_pymupdf()
            with pymupdf.open(path) as document:
                return "\n".join(page.get_text() for page in document)
        except Exception:
            return ""
    if suffix in {".tex", ".txt", ".md"}:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            return ""
        return strip_tex_comments(text) if suffix == ".tex" else text
    if suffix == ".docx":
        try:
            from docx import Document  # type: ignore
            document = Document(str(path))
            blocks = [paragraph.text for paragraph in document.paragraphs]
            blocks.extend(cell.text for table in document.tables for row in table.rows for cell in row.cells)
            for section in document.sections:
                blocks.extend(paragraph.text for paragraph in section.header.paragraphs)
                blocks.extend(paragraph.text for paragraph in section.footer.paragraphs)
            return "\n".join(blocks)
        except Exception:
            return ""
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="华为杯提交前审计")
    parser.add_argument("--paper", required=True, help="论文 PDF / tex / docx 路径")
    parser.add_argument(
        "--max-total-pages", "--body-gate", dest="max_total_pages", type=int,
        help="总页数上限（仅在当届官方明确时使用；--body-gate 为兼容别名）",
    )
    parser.add_argument(
        "--ai-used", choices=("unknown", "none", "writing", "analysis", "programming", "mixed"),
        default="unknown", help="实际 AI 使用方式；默认 unknown 不将未披露误判为违规",
    )
    parser.add_argument("--ai-file", help="AI 使用/标注说明文件（声明使用 AI 时的审计证据）")
    parser.add_argument("--attachments", help="提交附件目录")
    parser.add_argument(
        "--cover-policy", choices=("required", "forbidden"), default="required",
        help="2026 正式提交默认 required；纯匿名内部审阅稿使用 forbidden",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    paper = Path(args.paper)
    if not paper.is_file():
        print(f"[FAIL] 论文不存在: {paper}", file=sys.stderr)
        return 1

    checks: list[dict] = []
    warnings: list[str] = []

    def check(ok: bool, desc: str) -> None:
        checks.append({"ok": bool(ok), "desc": desc})

    pages = None
    if paper.suffix.lower() == ".pdf":
        pages = count_pdf_pages(paper)
        check(pages is not None, "PDF 页数可读取")
        if pages is not None:
            check(True, f"PDF 共 {pages} 页")
            if args.max_total_pages is not None:
                check(
                    pages <= args.max_total_pages,
                    f"总页数 {pages} ≤ 官方上限 {args.max_total_pages}",
                )
    else:
        warnings.append("非 PDF 文件未统计页数；请以最终 PDF 人工核对摘要页、页码和版式。")

    suffix = paper.suffix.lower()
    supported_suffix = suffix in {".pdf", ".tex", ".txt", ".md", ".docx"}
    check(supported_suffix, f"文件类型受支持: {suffix or '(无扩展名)'}")
    text = extract_text(paper) if supported_suffix else ""
    check(bool(text.strip()), "正文文本可读取，匿名与披露检查可执行")
    cover_present = False
    anonymous_text = text
    can_separate_cover = False
    if suffix == ".pdf":
        page_texts = extract_pdf_pages(paper)
        if page_texts:
            cover_compact = re.sub(r"\s+", "", page_texts[0])
            cover_present = all(marker in cover_compact for marker in COVER_MARKERS)
            anonymous_text = "\n".join(page_texts[1:])
            can_separate_cover = len(page_texts) >= 2
    elif suffix == ".tex":
        cover_present = tex_cover_present(text)
        anonymous_text = strip_tex_cover(text)
        can_separate_cover = True
    elif suffix == ".docx":
        compact = re.sub(r"\s+", "", text)
        cover_present = all(marker in compact for marker in COVER_MARKERS)
        warnings.append("DOCX 无法可靠按页分离封皮；封皮后的匿名性须以最终 PDF 再审计。")

    if args.cover_policy == "required":
        check(cover_present, "2026 正式提交含第 0 页官方参赛信息封皮")
        warnings.append("人工核对：封皮四个官方 logo 未删除、替换或变形。")
        if can_separate_cover and anonymous_text:
            hits = sorted(set(IDENTITY_PAT.findall(anonymous_text)))
            check(not hits, f"封皮之后无身份标志（检出 {len(hits)} 处疑似项：{hits[:10]}）")
        elif not can_separate_cover:
            warnings.append("未能可靠分离封皮与正文，封皮后的身份信息需人工复核。")
    else:
        check(not cover_present, "内部纯匿名审阅稿不含参赛信息封皮")
        if text:
            hits = sorted(set(IDENTITY_PAT.findall(text)))
            check(not hits, f"纯匿名稿无身份标志（检出 {len(hits)} 处疑似项：{hits[:10]}）")
        else:
            warnings.append("未能抽取正文文本，身份信息需人工复核。")

    # Public sources and borrowed programs need formal references. A template
    # need not manufacture a citation, so this is a review reminder, not a
    # false automated failure.
    check(True, "引用格式：如使用公开资料或程序，正文应按 [n] 引用并列完整参考文献。")

    disclosure_exists = bool(
        args.ai_file
        and Path(args.ai_file).is_file()
        and Path(args.ai_file).stat().st_size > 0
    )
    marker_exists = bool(text and AI_MARKER.search(text))
    if args.ai_used == "none":
        check(True, "AI 使用声明为 none；不要求附加 AI 标注。")
    elif args.ai_used == "unknown":
        warnings.append("尚未声明是否使用 AI；提交前须人工确认 --ai-used=none 或相应使用方式。")
    else:
        check(
            disclosure_exists or marker_exists,
            "已声明使用 AI，且存在 AI 使用/标注证据（说明文件或论文内标注）。",
        )
        if args.ai_used in {"analysis", "mixed"}:
            warnings.append("人工核对：AI 辅助数据分析的结果前后须标明工具、版本、开发者和发布日期。")
        if args.ai_used in {"programming", "mixed"}:
            warnings.append("人工核对：AI 辅助代码开头须有规定的工具信息注释。")
        if args.ai_used in {"writing", "mixed"}:
            warnings.append("人工核对：最终文字须经队伍理解并用自己的语言表述。")

    if args.ai_file:
        check(disclosure_exists, f"AI 说明文件存在: {args.ai_file}")

    if args.attachments:
        attachment_dir = Path(args.attachments)
        files = [item for item in attachment_dir.rglob("*") if item.is_file()] if attachment_dir.is_dir() else []
        check(attachment_dir.is_dir() and bool(files), f"附件目录含 {len(files)} 个文件")

    passed = all(item["ok"] for item in checks)
    payload = {
        "paper": str(paper),
        "passed": passed,
        "pages": pages,
        "ai_used": args.ai_used,
        "cover_policy": args.cover_policy,
        "checks": checks,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"=== 提交前审计：{paper.name} ===")
        for item in checks:
            print(f"  [{'x' if item['ok'] else ' '}] {item['desc']}")
        for warning in warnings:
            print(f"  [!] {warning}")
        print(f"\n结果: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
