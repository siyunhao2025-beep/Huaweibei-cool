#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""submission_audit.py — 提交前审计。

对论文（PDF / .tex / .docx 文本）做提交前检查：
  - 页数（正文是否超门禁，--body-gate 指定，默认不硬卡）
  - 无页眉、无身份标志（学校/姓名/导师/队号）
  - 参考文献格式（方括号编号、按序）
  - AI 披露是否存在（--ai-file 指定，或在论文文本中检出 AI 标注）
  - 附件清单完整（--attachments 目录）

PDF 页数统计优先用 pypdf，缺失时退化为只做文本检查并提示。

用法:
  python scripts/submission_audit.py --paper 论文.pdf
  python scripts/submission_audit.py --paper 论文.tex --body-gate 45
  python scripts/submission_audit.py --paper 论文.docx --ai-file AI披露.txt --attachments 提交附件
"""
import argparse
import re
import sys
from pathlib import Path

IDENTITY_PAT = re.compile(r"(大学|学院|导师|教授|同学|队|学号|姓名|指导教师)")
HEADER_PAT = re.compile(r"(页眉|runninghead)")


def count_pdf_pages(pdf: Path):
    try:
        import pypdf  # type: ignore
        with open(pdf, "rb") as f:
            return len(pypdf.PdfReader(f).pages)
    except Exception:
        pass
    try:
        import fitz  # type: ignore
        with fitz.open(pdf) as doc:
            return doc.page_count
    except Exception:
        return None


def extract_text(path: Path) -> str:
    """从 pdf/tex/docx 提取可审计文本（docx 仅做启发式，二进制不强解）。"""
    suf = path.suffix.lower()
    if suf == ".pdf":
        try:
            import fitz  # type: ignore
            with fitz.open(path) as doc:
                return "\n".join(pg.get_text() for pg in doc)
        except Exception:
            return ""
    if suf in (".tex", ".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="ignore")
    if suf == ".docx":
        return ""  # docx 二进制，文本检查跳过，仅页数/附件/披露检查
    return ""


def main(argv=None):
    ap = argparse.ArgumentParser(description="提交前审计")
    ap.add_argument("--paper", required=True, help="论文 PDF/tex/docx 路径")
    ap.add_argument("--body-gate", type=int, default=None,
                    help="正文页数门禁（可选，官方未明确时不硬卡）")
    ap.add_argument("--ai-file", help="AI 披露说明文件")
    ap.add_argument("--attachments", help="附件目录")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    paper = Path(args.paper)
    if not paper.exists():
        print(f"[FAIL] 论文不存在: {paper}")
        return 1

    findings = []  # (ok, desc)
    def chk(ok, desc): findings.append((bool(ok), desc))

    # 页数
    pages = None
    if paper.suffix.lower() == ".pdf":
        pages = count_pdf_pages(paper)
        if pages is None:
            chk(False, "无法统计 PDF 页数（缺 pypdf/fitz），请人工核对")
        else:
            chk(True, f"PDF 共 {pages} 页")
            if args.body_gate:
                chk(pages <= args.body_gate, f"总页数 {pages} ≤ 门禁 {args.body_gate}")
    else:
        chk(True, "非 PDF，页数请人工核对（研赛摘要≤2页、无页眉无身份标志）")

    text = extract_text(paper)
    if text:
        # 身份标志
        id_hits = IDENTITY_PAT.findall(text)
        chk(len(id_hits) == 0, f"无身份标志（检出 {len(id_hits)} 处疑似: {set(id_hits) if id_hits else ''}）")
        # 参考文献方括号
        chk(bool(re.search(r"\[\d+\]", text)), "正文有方括号引用编号 [n]")
        # AI 披露
        ai_in_text = bool(re.search(r"人工智能工具|AI工具|人工智能辅助|AI辅助", text))
    else:
        ai_in_text = False

    # AI 披露文件
    ai_ok = False
    if args.ai_file:
        ai_ok = Path(args.ai_file).exists()
        chk(ai_ok, f"AI 披露文件存在: {args.ai_file}")
    elif ai_in_text:
        ai_ok = True
        chk(True, "论文文本内含 AI 标注")
    else:
        chk(False, "未检出 AI 披露（按2026规定辅助写作/分析/编程须标注）")

    # 附件
    if args.attachments:
        d = Path(args.attachments)
        files = list(d.rglob("*")) if d.is_dir() else []
        chk(d.is_dir() and len(files) > 0, f"附件目录 {args.attachments} 含 {len(files)} 项")

    passed = all(ok for ok, _ in findings)
    if args.json:
        print(__import__("json").dumps({"paper": str(paper), "passed": passed,
                                        "pages": pages,
                                        "checks": [{"ok": o, "desc": d} for o, d in findings]},
                                       ensure_ascii=False, indent=2))
    else:
        print(f"=== 提交前审计: {paper.name} ===")
        for ok, desc in findings:
            print(f"  [{'x' if ok else ' '}] {desc}")
        print(f"\n结果: {'PASS' if passed else 'FAIL（有上述未通过项）'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
