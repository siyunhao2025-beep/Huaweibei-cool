#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
corpus_build.py — 华为杯研赛获奖论文语料全量勘察与抽文脚本（Wave0）。

功能：
  1. 递归扫描获奖论文语料根下全部 PDF（默认 729 篇）。
  2. 用 PyMuPDF 抽全文文本，写入 corpus/text/<年>/<安全文件名>.txt（UTF-8）。
  3. 记录页数、字符数、抽文状态（ok / low_text / scanned / failed）。
  4. 字符数 < 500 视为 low_text：渲染前 3 页 PNG 到 corpus/text/<年>/_rendered/，
     供后续 Wave1 多模态读封面（Wave0 只渲染并标记，不识别）。
  5. 从文件名/首页正则推断赛道字母、学校、队号、论文题目、奖级（含置信度）。
  6. 清洗“加微 anjia”等广告水印：只在文本中打标记，绝不修改原始 PDF。
  7. 断点续跑：已存在且状态 ok 的 txt 跳过抽文只更新索引；--rescan 强制重跑。
  8. 输出 corpus/papers_index.json 与 corpus/papers_index.csv，并打印统计。

设计原则：
  - 语料根只读，绝不删除/移动/重命名任何用户文件。
  - 数字、奖级、方法归属拿不准一律标“待确认”与低置信度，禁止脑补。

用法（在仓库根目录运行）：
  python scripts/corpus_build.py --corpus-root "D:\某语料根"
  python scripts/corpus_build.py --corpus-root "D:\某语料根" --rescan
  python scripts/corpus_build.py --corpus-root "D:\某语料根" --repo-root .
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# 路径配置。公开仓库不得绑定某位使用者的桌面目录。
# ---------------------------------------------------------------------------
DEFAULT_CORPUS_ROOT = os.environ.get("HUAWEI_CORPUS_ROOT")
# 仓库根（默认：本脚本所在目录的上一级）
DEFAULT_REPO_ROOT = Path(__file__).resolve().parent.parent

# low_text 阈值：抽文字符数低于此值视为可能是扫描件
LOW_TEXT_THRESHOLD = 500
# 每篇 low_text 最多渲染的页数
RENDER_MAX_PAGES = 3
# 广告水印正则（命中即在 notes 标记，不改原文）
AD_WATERMARK_RE = re.compile(r"(加微|加[VvＶ]|微信|vx|VX|anjia|公众号|关注|有偿|代写|代充|\d{5,}[\u4e00-\u9fa5]{0,4}号)")
# 赛道字母：文件名首字母 A-F，后接数字（如 A24102940057）
TRACK_RE = re.compile(r"^([A-F])(?=[0-9])", re.IGNORECASE)
# 队号：文件名里的连续数字（8-11 位常见）
TEAM_NUM_RE = re.compile(r"(\d{7,12})")
# 学校名：首页/前几页中“XX大学/学院/学校”
SCHOOL_RE = re.compile(r"([\u4e00-\u9fa5]{2,16}?(?:大学|学院|学校|理工大学|科技大学))")
# 奖级关键词
AWARD_PATTERNS = [
    (re.compile(r"全国一等奖|国家一等奖|全国\s*一\s*等\s*奖"), "全国一等奖", "high"),
    (re.compile(r"全国二等奖|国家二等奖|全国\s*二\s*等\s*奖"), "全国二等奖", "high"),
    (re.compile(r"一\s*等\s*奖"), "一等奖", "medium"),
    (re.compile(r"二\s*等\s*奖"), "二等奖", "medium"),
    (re.compile(r"优\s*秀\s*论\s*文"), "优秀论文", "medium"),
]


def safe_name(name: str) -> str:
    """把文件名转成安全的磁盘名（保留扩展名，去掉非法字符）。"""
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    return name[:120] or "untitled"


def infer_year(year_folder: Path) -> int:
    """从年份文件夹名开头解析 4 位年份。"""
    m = re.search(r"(20\d{2}|19\d{2})", year_folder.name)
    return int(m.group(1)) if m else -1


def infer_track(pdf_path: Path, year: int) -> tuple[str, str]:
    """从文件名首字母推断赛道，返回 (track, confidence)。"""
    m = TRACK_RE.match(pdf_path.stem)
    if m:
        return m.group(1).upper(), "high"
    # 尝试父目录名（如 A/B/C 子目录、2010A、1001007B、9000208-D）
    parent = pdf_path.parent.name.upper()
    m2 = re.search(r"([A-F])(?=$|题|[\s\-_）)])", parent)
    if m2:
        return m2.group(1), "medium"
    return "", "unknown"


def infer_team_number(pdf_path: Path) -> str:
    m = TEAM_NUM_RE.search(pdf_path.stem)
    return m.group(1) if m else ""


def parse_first_pages(first_text: str) -> dict:
    """从首页/前几页文本做保守正则识别，拿不准就留空并标待确认。"""
    info = {"school": "", "title": "", "award_level": "", "award_confidence": "unknown"}

    # 学校
    sm = SCHOOL_RE.search(first_text)
    if sm:
        info["school"] = sm.group(1).strip()

    # 奖级：按优先级匹配
    for rx, label, conf in AWARD_PATTERNS:
        if rx.search(first_text):
            info["award_level"] = label
            info["award_confidence"] = conf
            break
    if not info["award_level"]:
        info["award_level"] = "待确认"
        info["award_confidence"] = "low"

    # 题目：启发式——取首页较长的中文行（不含队号/学校/指导教师字样），置信度低
    title = ""
    for line in first_text.splitlines():
        line = line.strip()
        if not line or len(line) < 8 or len(line) > 60:
            continue
        if re.search(r"队号|学校|学院|指导|教师|队员|学号|摘要|关键词|参考文献", line):
            continue
        if re.fullmatch(r"[\d\s\-_]+", line):
            continue
        # 广告水印行（“有偿…加微 anjia…”）不得作为题目
        if AD_WATERMARK_RE.search(line):
            continue
        title = line
        break
    info["title"] = title or "待确认"
    return info


def extract_one(pdf_path: Path, out_txt: Path, render_dir: Path) -> dict:
    """抽单篇 PDF，返回该篇的元数据 dict（不含路径/年份等外层字段）。"""
    meta = {
        "page_count": 0,
        "char_count": 0,
        "extract_status": "failed",
        "rendered_pages": [],
        "notes": [],
    }
    text = ""
    used_backup = False
    try:
        import pymupdf  # 延迟导入，--help 时不依赖
        with pymupdf.open(pdf_path) as doc:
            meta["page_count"] = doc.page_count
            parts = []
            for page in doc:
                parts.append(page.get_text("text", sort=True))
            text = "\n".join(parts)
    except Exception as e:  # noqa: BLE001 —— 兜底用 pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(pdf_path))
            meta["page_count"] = len(reader.pages)
            parts = []
            for pg in reader.pages:
                parts.append(pg.extract_text() or "")
            text = "\n".join(parts)
            used_backup = True
            meta["notes"].append(f"pymupdf失败({type(e).__name__})，pypdf兜底成功")
        except Exception as e2:  # noqa: BLE001
            meta["notes"].append(f"pymupdf与pypdf均失败: {type(e2).__name__}: {e2}")
            return meta

    char_count = len(text.strip())
    meta["char_count"] = char_count

    # 广告水印标记
    if AD_WATERMARK_RE.search(text):
        meta["notes"].append("检测到广告/联系方式水印（未修改原文）")

    # 写 txt
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text(text, encoding="utf-8")

    # 状态判定
    if char_count < LOW_TEXT_THRESHOLD:
        meta["extract_status"] = "low_text"
        # 渲染前 3 页 PNG
        try:
            import pymupdf
            render_dir.mkdir(parents=True, exist_ok=True)
            with pymupdf.open(pdf_path) as doc:
                n = min(RENDER_MAX_PAGES, doc.page_count)
                stem = safe_name(pdf_path.stem)
                for i in range(n):
                    pix = doc[i].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                    png = render_dir / f"{stem}_p{i+1}.png"
                    pix.save(png)
                    meta["rendered_pages"].append(str(png.name))
            meta["notes"].append(f"low_text({char_count}字)，已渲染前{n}页供多模态读封面")
        except Exception as e:  # noqa: BLE001
            meta["notes"].append(f"渲染PNG失败: {type(e).__name__}: {e}")
    else:
        meta["extract_status"] = "scanned" if used_backup and char_count < 2000 else "ok"
        if used_backup:
            meta["extract_status"] = "ok"  # pypdf 兜底且文本量正常仍算 ok

    return meta


def build_index(corpus_root: Path, repo_root: Path, rescan: bool) -> list[dict]:
    text_dir = repo_root / "corpus" / "text"
    year_dirs = sorted([d for d in corpus_root.iterdir() if d.is_dir()])
    papers: list[dict] = []
    total_pdf = 0

    for ydir in year_dirs:
        year = infer_year(ydir)
        pdfs = sorted(ydir.rglob("*.pdf"))
        total_pdf += len(pdfs)
        for idx, pdf in enumerate(pdfs, 1):
            rel_to_year_root = pdf.relative_to(corpus_root)
            track, track_conf = infer_track(pdf, year)
            team = infer_team_number(pdf)
            # 安全文件名 + 相对路径短哈希，保证跨目录同名（如多个“论文.pdf”）不碰撞
            raw_stem = safe_name(pdf.stem)
            # Compatibility-only short identifier, never a security digest.
            h8 = hashlib.md5(
                str(rel_to_year_root).encode("utf-8"), usedforsecurity=False
            ).hexdigest()[:8]
            stem = f"{raw_stem}_{h8}" if len(raw_stem) < 12 else raw_stem
            out_txt = text_dir / str(year) / f"{stem}.txt"
            render_dir = text_dir / str(year) / "_rendered"

            # paper_id：年份_赛道_文件名（去扩展名），同名时带短哈希
            paper_id = f"{year}_{track or 'X'}_{stem}"

            entry = {
                "paper_id": paper_id,
                "year": year,
                "track": track,
                "track_confidence": track_conf,
                "team_number": team,
                "school": "",
                "title": "",
                "award_level": "",
                "award_confidence": "unknown",
                "page_count": 0,
                "char_count": 0,
                "extract_status": "failed",
                "file_relpath": str(rel_to_year_root).replace("\\", "/"),
                "file_size": pdf.stat().st_size,
                "rendered_pages": [],
                "notes": [],
            }

            # 断点续跑：已存在且 ok 的 txt 直接读元数据
            if (not rescan) and out_txt.exists():
                existing = out_txt.read_text(encoding="utf-8", errors="ignore")
                cc = len(existing.strip())
                entry["char_count"] = cc
                entry["extract_status"] = "ok" if cc >= LOW_TEXT_THRESHOLD else "low_text"
                # 前两页文本用于正则识别
                head = existing[:4000]
                info = parse_first_pages(head)
                entry.update({k: info[k] for k in ("school", "title", "award_level", "award_confidence")})
                papers.append(entry)
                continue

            meta = extract_one(pdf, out_txt, render_dir)
            entry["page_count"] = meta["page_count"]
            entry["char_count"] = meta["char_count"]
            entry["extract_status"] = meta["extract_status"]
            entry["rendered_pages"] = meta["rendered_pages"]
            entry["notes"] = meta["notes"]

            # 首页文本正则识别
            head = ""
            if out_txt.exists():
                head = out_txt.read_text(encoding="utf-8", errors="ignore")[:4000]
            info = parse_first_pages(head)
            entry["school"] = info["school"]
            entry["title"] = info["title"]
            entry["award_level"] = info["award_level"]
            entry["award_confidence"] = info["award_confidence"]

            papers.append(entry)
            if idx % 50 == 0:
                print(f"  [{year}] 进度 {idx}/{len(pdfs)} 累计{len(papers)}", flush=True)

    return papers


def write_outputs(papers: list[dict], repo_root: Path) -> None:
    corpus_dir = repo_root / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    json_path = corpus_dir / "papers_index.json"
    csv_path = corpus_dir / "papers_index.csv"

    # JSON
    payload = {
        "generated_by": "scripts/corpus_build.py",
        "total": len(papers),
        "papers": papers,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV
    fields = [
        "paper_id", "year", "track", "team_number", "school", "title",
        "award_level", "award_confidence", "page_count", "char_count",
        "extract_status", "file_relpath", "rendered_pages", "notes",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for p in papers:
            row = dict(p)
            row["rendered_pages"] = ";".join(p.get("rendered_pages", []))
            row["notes"] = ";".join(p.get("notes", []))
            w.writerow(row)

    # 统计
    from collections import Counter
    status_cnt = Counter(p["extract_status"] for p in papers)
    year_cnt = Counter(p["year"] for p in papers)
    track_cnt = Counter(p["track"] or "(空)" for p in papers)
    award_cnt = Counter(p["award_level"] for p in papers)

    print("\n========== 语料勘察统计 ==========")
    print(f"总篇数: {len(papers)}")
    print(f"抽文状态: {dict(status_cnt)}")
    print(f"各年篇数: {dict(sorted(year_cnt.items()))}")
    print(f"赛道分布: {dict(sorted(track_cnt.items()))}")
    print(f"奖级分布: {dict(sorted(award_cnt.items()))}")

    low = [p for p in papers if p["extract_status"] in ("low_text", "scanned")]
    failed = [p for p in papers if p["extract_status"] == "failed"]
    print(f"\nlow_text/scanned 清单（{len(low)}篇）:")
    for p in low:
        print(f"  - {p['paper_id']}  [{p['extract_status']}] {p['char_count']}字  {p['file_relpath']}")
    print(f"\nfailed 清单（{len(failed)}篇）:")
    for p in failed:
        print(f"  - {p['paper_id']}  {p['file_relpath']}  notes={p['notes']}")
    print(f"\n索引已写出: {json_path}")
    print(f"索引已写出: {csv_path}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="华为杯研赛获奖论文语料全量勘察与抽文（Wave0）。语料根只读。"
    )
    ap.add_argument(
        "--corpus-root", default=DEFAULT_CORPUS_ROOT,
        help="获奖论文语料根（只读）；也可设置 HUAWEI_CORPUS_ROOT。",
    )
    ap.add_argument(
        "--repo-root", default=str(DEFAULT_REPO_ROOT),
        help="目标仓库根目录，默认本脚本上一级。",
    )
    ap.add_argument(
        "--rescan", action="store_true",
        help="强制重跑抽文，忽略已存在的 txt。",
    )
    args = ap.parse_args()

    if not args.corpus_root:
        ap.error("请用 --corpus-root 指定只读语料根，或设置 HUAWEI_CORPUS_ROOT")

    corpus_root = Path(args.corpus_root).expanduser().resolve()
    repo_root = Path(args.repo_root)
    if not corpus_root.is_dir():
        print(f"错误：语料根不存在: {corpus_root}", file=sys.stderr)
        sys.exit(1)

    t0 = time.time()
    print(f"语料根: {corpus_root}")
    print(f"仓库根: {repo_root}")
    print(f"重扫模式: {args.rescan}")
    papers = build_index(corpus_root, repo_root, args.rescan)
    write_outputs(papers, repo_root)
    print(f"\n用时 {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
