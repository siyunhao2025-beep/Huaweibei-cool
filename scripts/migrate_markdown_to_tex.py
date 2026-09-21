#!/usr/bin/env python3
# [来源] 移植自 v2.1 华为杯_论文规范模板/tools/，相对路径已改为 CLI 参数驱动，Wave3 验证编译链路。
"""One-time migration of legacy Markdown chapters to real LaTeX fragments.

This script is intentionally a migration utility, not a paper-writing
pipeline.  After migration, the generated ``.tex`` files are the source of
truth and the old Markdown files must be moved to a legacy archive.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}
TOKEN_RE = re.compile(r"(`[^`]*`|\$\$[^$]*\$\$|\$[^$]+\$|\*\*[^*]+\*\*|\*[^*]+\*)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
IMAGE_RE = re.compile(r"^!\[([^]]*)\]\(([^)]+)\)\s*$")
ORDERED_RE = re.compile(r"^\s*\d+[.)]\s+(.+)$")
UNORDERED_RE = re.compile(r"^\s*[-*+]\s+(.+)$")
REFERENCE_RE = re.compile(r"^\s*\[(\d+)\]\s+(.+)$")
TABLE_SEPARATOR_RE = re.compile(r"^\s*:?-{2,}:?\s*$")


def tex_escape(text: str) -> str:
    return "".join(SPECIALS.get(char, char) for char in text)


def tex_escape_path(path: str) -> str:
    # Paths are expanded by graphicx.  Escape only characters that are
    # special in a filename argument while retaining directory separators.
    return path.replace("#", r"\#").replace("%", r"\%").replace("&", r"\&").replace(" ", r"\ ")


def render_inline(text: str) -> str:
    parts: list[str] = []
    cursor = 0
    for match in TOKEN_RE.finditer(text):
        parts.append(tex_escape(text[cursor : match.start()]))
        token = match.group(0)
        if token.startswith("$$"):
            parts.append(r"\[" + token[2:-2] + r"\]")
        elif token.startswith("$"):
            parts.append(r"\(" + token[1:-1] + r"\)")
        elif token.startswith("`"):
            parts.append(r"\texttt{" + tex_escape(token[1:-1]) + "}")
        elif token.startswith("**"):
            parts.append(r"\textbf{" + tex_escape(token[2:-2]) + "}")
        else:
            parts.append(r"\emph{" + tex_escape(token[1:-1]) + "}")
        cursor = match.end()
    parts.append(tex_escape(text[cursor:]))
    return "".join(parts)


def normalized_heading(text: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*\s*", "", text.strip())


def strip_heading_number(text: str) -> str:
    return normalized_heading(text)


def split_table(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw in lines:
        cells = [cell.strip() for cell in raw.strip().strip("|").split("|")]
        if cells and all(TABLE_SEPARATOR_RE.fullmatch(cell) for cell in cells):
            continue
        rows.append(cells)
    width = max((len(row) for row in rows), default=0)
    return [row + [""] * (width - len(row)) for row in rows]


def render_table(lines: list[str], table_number: int, label_prefix: str) -> list[str]:
    rows = split_table(lines)
    if not rows:
        return []
    width = len(rows[0])
    columns = "".join(r">{\raggedright\arraybackslash}X" for _ in range(width))
    output = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\small",
        r"\caption{数据汇总表}",
        rf"\label{{tab:{label_prefix}-{table_number}}}",
        rf"\begin{{tabularx}}{{\textwidth}}{{{columns}}}",
        r"\toprule",
    ]
    for row_number, row in enumerate(rows):
        cells = [render_inline(cell) for cell in row]
        output.append(" & ".join(cells) + r" \\")
        if row_number == 0:
            output.append(r"\midrule")
    output.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}", ""])
    return output


def render_image(caption: str, raw_path: str, figure_number: int, label_prefix: str) -> list[str]:
    path = tex_escape_path(raw_path.strip())
    caption_tex = render_inline(caption.strip() or "结果图")
    return [
        r"\begin{figure}[htbp]",
        r"\centering",
        rf"\includegraphics[width=0.92\textwidth]{{{path}}}",
        rf"\caption{{{caption_tex}}}",
        rf"\label{{fig:{label_prefix}-{figure_number}}}",
        r"\end{figure}",
        "",
    ]


def render_list(lines: list[str], ordered: bool) -> list[str]:
    env = "enumerate" if ordered else "itemize"
    output = [rf"\begin{{{env}}}"]
    for line in lines:
        match = ORDERED_RE.fullmatch(line) if ordered else UNORDERED_RE.fullmatch(line)
        if match:
            output.append(r"\item " + render_inline(match.group(1)))
    output.extend([rf"\end{{{env}}}", ""])
    return output


def convert_fragment(markdown: str, title: str | None = None, role: str | None = None, label_prefix: str = "fragment") -> str:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    output: list[str] = ["% Generated from the legacy Markdown source; edit this TeX file directly thereafter."]
    if title:
        output.extend([rf"\section{{{render_inline(title)}}}", ""])
    title_consumed = False

    paragraph: list[str] = []
    table_number = 0
    figure_number = 0
    list_mode: str | None = None
    reference_open = False

    def flush_paragraph() -> None:
        if paragraph:
            output.append(render_inline(" ".join(item.strip() for item in paragraph)))
            output.append("")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_mode
        if list_mode:
            output.append(rf"\end{{{list_mode}}}")
            output.append("")
            list_mode = None

    def close_references() -> None:
        nonlocal reference_open
        if reference_open:
            output.extend([r"\end{thebibliography}", ""])
            reference_open = False

    index = 0
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if not stripped:
            flush_paragraph()
            close_list()
            index += 1
            continue

        image = IMAGE_RE.fullmatch(stripped)
        if image:
            flush_paragraph()
            close_list()
            close_references()
            figure_number += 1
            output.extend(render_image(image.group(1), image.group(2), figure_number, label_prefix))
            index += 1
            continue

        if stripped.startswith("|") and "|" in stripped:
            flush_paragraph()
            close_list()
            close_references()
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            table_number += 1
            output.extend(render_table(table_lines, table_number, label_prefix))
            continue

        heading = HEADING_RE.fullmatch(stripped)
        if heading:
            flush_paragraph()
            close_list()
            close_references()
            heading_text = strip_heading_number(heading.group(2))
            if title and not title_consumed and normalized_heading(heading_text) == normalized_heading(title):
                title_consumed = True
                index += 1
                continue
            level = min(len(heading.group(1)), 3)
            command = {1: "section", 2: "subsection", 3: "subsubsection"}[level]
            output.extend([rf"\{command}{{{render_inline(heading_text)}}}", ""])
            index += 1
            continue

        if role == "references":
            reference = REFERENCE_RE.fullmatch(stripped)
            if reference:
                flush_paragraph()
                close_list()
                if not reference_open:
                    output.extend([r"\begin{thebibliography}{99}"])
                    reference_open = True
                output.append(rf"\bibitem{{ref{reference.group(1)}}} {render_inline(reference.group(2))}")
                index += 1
                continue
            close_references()

        ordered = ORDERED_RE.fullmatch(stripped)
        unordered = UNORDERED_RE.fullmatch(stripped)
        if ordered or unordered:
            flush_paragraph()
            close_references()
            wanted = "enumerate" if ordered else "itemize"
            if list_mode != wanted:
                close_list()
                list_mode = wanted
                output.append(rf"\begin{{{list_mode}}}")
            output.append(r"\item " + render_inline((ordered or unordered).group(1)))
            index += 1
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            close_list()
            close_references()
            output.extend([r"\begin{quote}", render_inline(stripped[1:].strip()), r"\end{quote}", ""])
            index += 1
            continue

        # Fenced code is retained as a verbatim block in the TeX output.
        if stripped.startswith(chr(96) * 3):
            flush_paragraph()
            close_list()
            close_references()
            index += 1
            code_lines: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith(chr(96) * 3):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            output.extend([r"\begin{verbatim}", *code_lines, r"\end{verbatim}", ""])
            continue

        paragraph.append(raw)
        index += 1

    flush_paragraph()
    close_list()
    close_references()
    return "\n".join(output).rstrip() + "\n"


def migrate(input_path: Path, source_dir: Path, output_dir: Path) -> dict:
    project_root = input_path.parent.resolve()
    source_root = source_dir.resolve()
    output_root = output_dir.resolve()
    try:
        source_root.relative_to(project_root)
        output_root.relative_to(project_root)
    except ValueError as exc:
        raise ValueError("--source-dir 与 --output-dir 必须位于旧 manifest 所在项目目录内") from exc

    data = json.loads(input_path.read_text(encoding="utf-8-sig"))
    if "abstract" not in data or not str(data["abstract"]).strip():
        raise ValueError("旧 manifest 的 abstract 必须是非空文本")
    chapters_data = data.get("chapters")
    if not isinstance(chapters_data, list) or not chapters_data:
        raise ValueError("旧 manifest 的 chapters 必须是非空列表")

    resolved_sources: list[tuple[dict, Path]] = []
    target_names: set[str] = set()
    for index, chapter in enumerate(chapters_data, start=1):
        if not isinstance(chapter, dict) or "content_file" not in chapter or "title" not in chapter:
            raise ValueError(f"第 {index} 个章节缺少 title/content_file")
        source = (source_root / str(chapter["content_file"])).resolve()
        try:
            source.relative_to(source_root)
        except ValueError as exc:
            raise ValueError(f"章节源文件必须位于 --source-dir 内: {chapter['content_file']}") from exc
        if source.suffix.lower() != ".md":
            raise ValueError(f"迁移输入必须是旧 Markdown 文件: {source}")
        if not source.is_file():
            raise FileNotFoundError(f"章节源文件不存在: {source}")
        target_name = f"{source.stem}.tex"
        if target_name.casefold() in target_names:
            raise ValueError(f"章节输出文件名冲突: {target_name}")
        target_names.add(target_name.casefold())
        resolved_sources.append((chapter, source))

    output_root.mkdir(parents=True, exist_ok=True)
    abstract_path = output_root / "00_摘要.tex"
    abstract_path.write_text(convert_fragment(str(data["abstract"])), encoding="utf-8")
    chapters = []
    for chapter, source in resolved_sources:
        target = output_root / f"{source.stem}.tex"
        content = source.read_text(encoding="utf-8-sig")
        target.write_text(
            convert_fragment(
                content,
                title=str(chapter["title"]),
                role=str(chapter.get("role", "")),
                label_prefix=re.sub(r"[^A-Za-z0-9-]+", "-", source.stem).strip("-").lower() or "chapter",
            ),
            encoding="utf-8",
        )
        chapters.append({
            "title": chapter["title"],
            "role": chapter.get("role", "problem"),
            "level": chapter.get("level", 1),
            "source_md": str(source.relative_to(project_root)).replace("\\", "/"),
            "tex_path": str(target.relative_to(project_root)).replace("\\", "/"),
        })
    return {
        "abstract_tex_path": str(abstract_path.relative_to(project_root)).replace("\\", "/"),
        "chapters": chapters,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = migrate(args.input.resolve(), args.source_dir.resolve(), args.output_dir.resolve())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
