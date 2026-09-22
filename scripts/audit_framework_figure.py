#!/usr/bin/env python3
"""Audit the recorded QA contract for a paper-primary framework figure.

Raster OCR cannot reliably prove font size, collisions, or Chinese glyph
correctness.  This gate therefore validates a hash-bound visual-QA record
instead of pretending to infer those facts from pixels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path


MIN_PT = {
    "macro_group": 11.0,
    "node": 10.0,
    "edge_or_port": 9.0,
    "internal_micro": 9.0,
    "legend": 9.0,
}
MIN_INK_MM = {
    "macro_group": 3.0,
    "node": 2.5,
    "edge_or_port": 2.0,
    "internal_micro": 2.0,
    "legend": 2.2,
}
ZERO_VIOLATIONS = (
    "text_text_collisions",
    "text_connector_collisions",
    "boundary_overflows",
    "clipped_elements",
    "garbled_cjk_glyphs",
    "semantic_mismatches",
)
GRAPHICS_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".svg", ".eps")
MIN_VECTOR_VISUAL_SIMILARITY = 0.97


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def png_dimensions(path: Path) -> tuple[int, int] | None:
    """Read PNG dimensions without silently trusting metadata in the binding."""
    try:
        with path.open("rb") as stream:
            header = stream.read(24)
    except OSError:
        return None
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", header[16:24])


def uncommented_tex(path: Path) -> str:
    lines = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        lines.append(re.sub(r"(?<!\\)%.*$", "", line))
    return "\n".join(lines)


def balanced_brace(text: str, opening: int) -> tuple[str, int] | None:
    """Return one TeX brace group's content and exclusive end position."""
    if opening >= len(text) or text[opening] != "{":
        return None
    depth = 0
    for position in range(opening, len(text)):
        if text[position] == "{" and (position == 0 or text[position - 1] != "\\"):
            depth += 1
        elif text[position] == "}" and (position == 0 or text[position - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return text[opening + 1:position], position + 1
    return None


def expanded_graphics_arguments(text: str) -> list[str]:
    r"""Expand only simple newcommand wrappers around includegraphics.

    This is deliberately not a TeX interpreter.  It supports the common,
    auditable pattern ``\newcommand{\name}[N]{...#1...}`` (and renewcommand)
    followed by N mandatory brace arguments.
    """
    definition_pattern = re.compile(
        r"\\(?:re)?newcommand\*?\s*\{\\([A-Za-z@]+)\}\s*"
        r"(?:\[(\d+)\])?\s*(\{)",
    )
    definitions: list[tuple[str, int, list[str], tuple[int, int]]] = []
    for match in definition_pattern.finditer(text):
        body_group = balanced_brace(text, match.start(3))
        if body_group is None:
            continue
        body, end = body_group
        argument_count = int(match.group(2) or 0)
        templates = re.findall(
            r"\\includegraphics\s*(?:\[[^\]]*\]\s*)?\{([^{}]+)\}", body,
            flags=re.DOTALL,
        )
        if argument_count and templates:
            definitions.append(
                (match.group(1), argument_count, templates, (match.start(), end))
            )

    expanded: list[str] = []
    definition_ranges = [item[3] for item in definitions]
    for name in {item[0] for item in definitions}:
        invocation_pattern = re.compile(rf"\\{re.escape(name)}(?![A-Za-z@])")
        for match in invocation_pattern.finditer(text):
            if any(start <= match.start() < end for start, end in definition_ranges):
                continue
            active = [
                item for item in definitions
                if item[0] == name and item[3][1] <= match.start()
            ]
            if not active:
                continue
            _, argument_count, templates, _ = max(active, key=lambda item: item[3][1])
            cursor = match.end()
            arguments: list[str] = []
            for _index in range(argument_count):
                while cursor < len(text) and text[cursor].isspace():
                    cursor += 1
                group = balanced_brace(text, cursor)
                if group is None:
                    arguments = []
                    break
                value, cursor = group
                arguments.append(value)
            if len(arguments) != argument_count:
                continue
            for template in templates:
                value = template
                for index, argument in enumerate(arguments, start=1):
                    value = value.replace(f"#{index}", argument)
                if "#" not in value:
                    expanded.append(value)
    return expanded


def tex_references_target(main_tex: Path, target: Path, project_root: Path) -> tuple[bool, list[str]]:
    """Require an active includegraphics command that resolves to the bound file.

    A stem search is insufficient: prose, a comment, or ``F01-old.png`` can all
    contain the expected stem without including the audited asset.
    """
    text = uncommented_tex(main_tex)
    direct_includes = re.findall(
        r"\\includegraphics\s*(?:\[[^\]]*\]\s*)?\{([^{}]+)\}", text,
        flags=re.DOTALL,
    )
    includes = direct_includes + expanded_graphics_arguments(text)
    graphicspath_blocks = re.findall(
        r"\\graphicspath\s*\{((?:\s*\{[^{}]*\}\s*)+)\}", text,
        flags=re.DOTALL,
    )
    graphics_dirs = [
        item.strip()
        for block in graphicspath_blocks
        for item in re.findall(r"\{([^{}]*)\}", block)
        if item.strip()
    ]
    roots = [main_tex.parent, project_root]
    roots.extend(main_tex.parent / Path(item.replace("/", str(Path('/')))) for item in graphics_dirs)
    roots.extend(project_root / Path(item.replace("/", str(Path('/')))) for item in graphics_dirs)

    expected = target.resolve()
    for raw in includes:
        argument = raw.strip()
        if not argument or "\\" in argument or "#" in argument:
            continue
        relative = Path(argument.replace("/", str(Path('/'))))
        if relative.is_absolute():
            continue
        for root in roots:
            candidate = root / relative
            variants = [candidate]
            if not candidate.suffix:
                variants = [candidate.with_suffix(ext) for ext in GRAPHICS_EXTENSIONS]
            if any(item.resolve() == expected for item in variants):
                return True, includes
    return False, includes


def pixmap_fingerprint(pixmap: object) -> tuple[str, int, int, int, bool]:
    """Hash decoded pixels, not file bytes or dimensions."""
    import pymupdf

    pix = pixmap
    if pix.colorspace is None or pix.colorspace.n != 3:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    payload = (
        f"{pix.width}x{pix.height}:{pix.n}:{int(bool(pix.alpha))}:".encode("ascii")
        + bytes(pix.samples)
    )
    return (
        hashlib.sha256(payload).hexdigest().upper(),
        pix.width,
        pix.height,
        pix.n,
        bool(pix.alpha),
    )


def raster_file_fingerprint(path: Path) -> tuple[str, int, int, int, bool]:
    import pymupdf

    # Byte input avoids filename-encoding surprises on Chinese Windows paths.
    return pixmap_fingerprint(pymupdf.Pixmap(path.read_bytes()))


def page_contains_raster(page: object, document: object, expected: tuple) -> tuple[bool, int]:
    """Match a displayed PDF image by decoded pixel content.

    ``get_image_info`` excludes unused/dead XObjects.  The soft-mask lookup is
    needed to reconstruct transparent PNGs before comparing their pixels.
    """
    import pymupdf

    soft_masks = {item[0]: item[1] for item in page.get_images(full=True)}
    examined = 0
    for info in page.get_image_info(xrefs=True):
        xref = info.get("xref", 0)
        if not isinstance(xref, int) or xref <= 0:
            continue
        try:
            pix = pymupdf.Pixmap(document, xref)
            mask_xref = soft_masks.get(xref, 0)
            if mask_xref:
                pix = pymupdf.Pixmap(pix, pymupdf.Pixmap(document, mask_xref))
            actual = pixmap_fingerprint(pix)
        except (RuntimeError, ValueError):
            continue
        examined += 1
        if actual == expected:
            return True, examined
    return False, examined


def valid_page_bbox(raw: object, page_rect: object) -> tuple[float, float, float, float] | None:
    if not isinstance(raw, list) or len(raw) != 4:
        return None
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in raw):
        return None
    x0, y0, x1, y1 = map(float, raw)
    if not (x0 < x1 and y0 < y1):
        return None
    if x0 < page_rect.x0 or y0 < page_rect.y0 or x1 > page_rect.x1 or y1 > page_rect.y1:
        return None
    return x0, y0, x1, y1


def vector_visual_match(target: Path, compiled_page: object, bbox: tuple[float, ...]) -> dict:
    """Compare the hash-bound vector asset with its declared final-page region."""
    import pymupdf

    filetype = target.suffix.lower().lstrip(".")
    source_doc = pymupdf.open(stream=target.read_bytes(), filetype=filetype)
    with source_doc:
        if source_doc.page_count < 1:
            raise ValueError("vector asset has no page")
        source_page = source_doc[0]
        source_rect = source_page.rect
        crop_rect = pymupdf.Rect(*bbox)
        source_aspect = source_rect.width / source_rect.height
        crop_aspect = crop_rect.width / crop_rect.height
        aspect_delta = abs(source_aspect - crop_aspect) / source_aspect

        width = 1000
        height = max(1, round(width / source_aspect))
        if height > 1600:
            height = 1600
            width = max(1, round(height * source_aspect))
        source_pix = source_page.get_pixmap(
            matrix=pymupdf.Matrix(width / source_rect.width, height / source_rect.height),
            clip=source_rect, colorspace=pymupdf.csRGB, alpha=False,
        )
        crop_pix = compiled_page.get_pixmap(
            matrix=pymupdf.Matrix(width / crop_rect.width, height / crop_rect.height),
            clip=crop_rect, colorspace=pymupdf.csRGB, alpha=False,
        )
        if (source_pix.width, source_pix.height) != (crop_pix.width, crop_pix.height):
            return {"match": False, "similarity": None, "aspect_delta": aspect_delta,
                    "ink_fraction": None}
        source_samples = bytes(source_pix.samples)
        crop_samples = bytes(crop_pix.samples)
        difference = sum(abs(left - right) for left, right in zip(source_samples, crop_samples))
        similarity = 1.0 - difference / (255.0 * len(source_samples))
        source_mask = bytearray(
            min(source_samples[offset:offset + 3]) < 250
            for offset in range(0, len(source_samples), 3)
        )
        crop_mask = bytearray(
            min(crop_samples[offset:offset + 3]) < 250
            for offset in range(0, len(crop_samples), 3)
        )
        source_ink = sum(source_mask)
        crop_ink = sum(crop_mask)
        intersection = sum(left and right for left, right in zip(source_mask, crop_mask))
        union = source_ink + crop_ink - intersection
        foreground_iou = intersection / union if union else 0.0

        def tolerant_coverage(subject: bytearray, reference: bytearray) -> float:
            subject_points = [index for index, present in enumerate(subject) if present]
            if not subject_points:
                return 0.0
            matched = 0
            image_width = source_pix.width
            image_height = source_pix.height
            for index in subject_points:
                y, x = divmod(index, image_width)
                if any(
                    reference[row * image_width + column]
                    for row in range(max(0, y - 1), min(image_height, y + 2))
                    for column in range(max(0, x - 1), min(image_width, x + 2))
                ):
                    matched += 1
            return matched / len(subject_points)

        source_coverage = tolerant_coverage(source_mask, crop_mask)
        crop_coverage = tolerant_coverage(crop_mask, source_mask)
        ink_fraction = source_ink / (source_pix.width * source_pix.height)
        return {
            "match": (
                aspect_delta <= 0.01
                and ink_fraction >= 0.001
                and similarity >= MIN_VECTOR_VISUAL_SIMILARITY
                and foreground_iou >= 0.50
                and source_coverage >= 0.90
                and crop_coverage >= 0.90
            ),
            "similarity": similarity,
            "aspect_delta": aspect_delta,
            "ink_fraction": ink_fraction,
            "foreground_iou": foreground_iou,
            "source_foreground_coverage": source_coverage,
            "crop_foreground_coverage": crop_coverage,
        }


def resolve_project_file(project_root: Path, raw: object) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    candidate = Path(raw)
    if candidate.is_absolute():
        return None
    resolved = (project_root / candidate).resolve()
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError:
        return None
    return resolved


def audit(binding_path: Path, project_root: Path, stage: str = "render") -> dict:
    binding = json.loads(binding_path.read_text(encoding="utf-8-sig"))
    checks: list[dict] = []

    def add(code: str, ok: bool, **details: object) -> None:
        checks.append({"code": code, "ok": bool(ok), **details})

    required = {
        "schema_version", "figure_id", "role", "document_language",
        "localization_mode", "localization_origin", "source_terminal_stage",
        "selected_source", "selected_source_sha256", "latex_target",
        "latex_target_sha256", "label", "main_tex", "framework_text_qa",
    }
    add("framework_binding_fields_present", not (required - binding.keys()),
        missing=sorted(required - binding.keys()))
    add("framework_figure_is_f01", binding.get("figure_id") == "F01",
        actual=binding.get("figure_id"))
    add("framework_role_valid",
        binding.get("role") == "complex_multi_question_framework",
        actual=binding.get("role"))
    add("framework_terminal_stage_is_s5",
        binding.get("source_terminal_stage") == "S5-CANDIDATE-IMAGE",
        actual=binding.get("source_terminal_stage"))
    add("framework_no_s6_stage", "S6-" not in json.dumps(binding, ensure_ascii=False))

    source = resolve_project_file(project_root, binding.get("selected_source"))
    target = resolve_project_file(project_root, binding.get("latex_target"))
    add("framework_source_path_is_project_relative", source is not None)
    add("framework_target_path_is_project_relative", target is not None)
    source_ok = bool(source and source.is_file())
    target_ok = bool(target and target.is_file())
    add("framework_selected_source_exists", source_ok,
        path=str(source) if source else None)
    add("framework_latex_target_exists", target_ok,
        path=str(target) if target else None)
    source_hash = sha256(source) if source_ok else None
    target_hash = sha256(target) if target_ok else None
    add("framework_selected_source_hash_matches",
        source_hash == str(binding.get("selected_source_sha256", "")).upper(),
        actual=source_hash, expected=binding.get("selected_source_sha256"))
    add("framework_latex_target_hash_matches",
        target_hash == str(binding.get("latex_target_sha256", "")).upper(),
        actual=target_hash, expected=binding.get("latex_target_sha256"))
    add("framework_bound_asset_matches_selected_source",
        source_hash is not None and source_hash == target_hash,
        selected_source_sha256=source_hash, latex_target_sha256=target_hash)
    add("framework_label_valid", str(binding.get("label", "")).startswith("fig:"),
        actual=binding.get("label"))

    main_tex = resolve_project_file(project_root, binding.get("main_tex"))
    main_ok = bool(main_tex and main_tex.is_file())
    add("framework_main_tex_exists", main_ok,
        path=str(main_tex) if main_tex else None)
    exact_reference, include_arguments = (
        tex_references_target(main_tex, target, project_root)
        if main_ok and target is not None else (False, [])
    )
    add("framework_main_tex_references_bound_asset",
        exact_reference, includegraphics=include_arguments,
        expected=str(target) if target else None,
        path=str(main_tex) if main_tex else None)

    language = binding.get("document_language")
    localization_mode = binding.get("localization_mode")
    if language == "zh-CN":
        add("framework_chinese_language_mode",
            localization_mode == "zh_primary_preserve_exact_tokens",
            actual=localization_mode)
        ledger = resolve_project_file(project_root, binding.get("label_ledger"))
        add("framework_label_ledger_exists", bool(ledger and ledger.is_file()),
            path=str(ledger) if ledger else None)
        ledger_data = None
        if ledger and ledger.is_file():
            try:
                ledger_data = json.loads(ledger.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                ledger_data = None
        add("framework_label_ledger_is_structured",
            isinstance(ledger_data, dict)
            and isinstance(ledger_data.get("labels"), list)
            and bool(ledger_data.get("labels")))
        tokens = binding.get("retained_technical_tokens", [])
        add("framework_technical_tokens_registered",
            isinstance(tokens, list) and bool(tokens) and all(isinstance(x, str) and x for x in tokens))
        ledger_tokens = ledger_data.get("retained_technical_tokens", []) if isinstance(ledger_data, dict) else []
        add("framework_binding_tokens_match_ledger",
            isinstance(tokens, list) and set(tokens) == set(ledger_tokens),
            binding_tokens=tokens, ledger_tokens=ledger_tokens)
        add("framework_no_unregistered_latin_prose",
            binding.get("unregistered_latin_prose_count") == 0,
            actual=binding.get("unregistered_latin_prose_count"))
        add("framework_latin_font_policy",
            binding.get("latin_font_policy") == "times_new_roman_or_math_font",
            actual=binding.get("latin_font_policy"))
    else:
        add("framework_source_language_mode",
            localization_mode == "source_language", actual=localization_mode)

    origin = binding.get("localization_origin")
    add("framework_localization_origin_valid",
        origin in {"s1_s4_visible_text_contract", "explicit_post_s5_consumer_adaptation"},
        actual=origin)
    if origin == "s1_s4_visible_text_contract":
        for key in ("s1_visible_text_contract", "s4_visible_text_contract"):
            contract = resolve_project_file(project_root, binding.get(key))
            add(f"framework_{key}_exists", bool(contract and contract.is_file()),
                path=str(contract) if contract else None)
    elif origin == "explicit_post_s5_consumer_adaptation":
        add("framework_consumer_adaptation_authorized",
            bool(str(binding.get("user_authorization_record", "")).strip()))
        directory = resolve_project_file(project_root, binding.get("consumer_adaptation_directory"))
        add("framework_consumer_adaptation_recorded",
            bool(directory and directory.is_dir()), path=str(directory) if directory else None)
        upstream = resolve_project_file(project_root, binding.get("upstream_s5_source"))
        upstream_ok = bool(upstream and upstream.is_file())
        upstream_hash = sha256(upstream) if upstream_ok else None
        add("framework_upstream_s5_source_exists", upstream_ok,
            path=str(upstream) if upstream else None)
        add("framework_upstream_s5_hash_matches",
            upstream_hash == str(binding.get("upstream_s5_sha256", "")).upper(),
            actual=upstream_hash, expected=binding.get("upstream_s5_sha256"))
        for field in ("adaptation_record", "localization_prompt_record"):
            record = resolve_project_file(project_root, binding.get(field))
            record_ok = bool(record and record.is_file())
            record_hash = sha256(record) if record_ok else None
            add(f"framework_{field}_exists", record_ok,
                path=str(record) if record else None)
            add(f"framework_{field}_hash_matches",
                record_hash == str(binding.get(f"{field}_sha256", "")).upper(),
                actual=record_hash, expected=binding.get(f"{field}_sha256"))

    qa = binding.get("framework_text_qa", {})
    qa_is_object = isinstance(qa, dict)
    add("framework_text_qa_is_object", qa_is_object)
    if not qa_is_object:
        qa = {}
    add("framework_target_insert_width_recorded",
        isinstance(qa.get("target_insert_width_mm"), (int, float))
        and qa.get("target_insert_width_mm", 0) > 0,
        actual=qa.get("target_insert_width_mm"))
    asset_kind = qa.get("asset_kind")
    add("framework_text_asset_kind_valid",
        asset_kind in {"vector_text", "raster"}, actual=asset_kind)
    dimensions = png_dimensions(source) if source_ok else None
    width_mm = qa.get("target_insert_width_mm")
    if asset_kind == "vector_text":
        effective = qa.get("minimum_effective_pt", {})
        for role, minimum in MIN_PT.items():
            actual = effective.get(role) if isinstance(effective, dict) else None
            add(f"framework_minimum_{role}_pt",
                isinstance(actual, (int, float)) and actual >= minimum,
                actual=actual, required=minimum)
    elif asset_kind == "raster":
        add("framework_raster_dimensions_readable", dimensions is not None,
            dimensions=dimensions)
        measured = qa.get("minimum_ink_height_px", {})
        density = (
            dimensions[0] / float(width_mm)
            if dimensions and isinstance(width_mm, (int, float)) and width_mm > 0
            else None
        )
        for role, minimum_mm in MIN_INK_MM.items():
            required_px = math.ceil(minimum_mm * density) if density else None
            actual = measured.get(role) if isinstance(measured, dict) else None
            add(f"framework_minimum_{role}_ink_height",
                isinstance(actual, (int, float))
                and isinstance(required_px, int) and actual >= required_px,
                actual_px=actual, required_px=required_px, minimum_mm=minimum_mm)
        add("framework_raster_measurement_method_recorded",
            qa.get("measurement_method") == "native_pixel_component_measurement",
            actual=qa.get("measurement_method"))
        evidence = resolve_project_file(project_root, qa.get("measurement_evidence"))
        evidence_ok = bool(evidence and evidence.is_file())
        evidence_hash = sha256(evidence) if evidence_ok else None
        add("framework_raster_measurement_evidence_exists", evidence_ok,
            path=str(evidence) if evidence else None)
        add("framework_raster_measurement_evidence_hash_matches",
            evidence_hash == str(qa.get("measurement_evidence_sha256", "")).upper(),
            actual=evidence_hash, expected=qa.get("measurement_evidence_sha256"))
        actual_ppi = (
            dimensions[0] / (float(width_mm) / 25.4)
            if dimensions and isinstance(width_mm, (int, float)) and width_mm > 0
            else None
        )
        recorded_ppi = qa.get("effective_ppi")
        add("framework_effective_ppi_matches_asset",
            isinstance(recorded_ppi, (int, float)) and actual_ppi is not None
            and abs(float(recorded_ppi) - actual_ppi) <= 1.0,
            actual=actual_ppi, recorded=recorded_ppi)
        add("framework_raster_resolution_policy",
            actual_ppi is not None and (
                actual_ppi >= 300
                or bool(str(qa.get("resolution_exception", "")).strip())
            ), actual_ppi=actual_ppi,
            resolution_exception=qa.get("resolution_exception"))
    violations = qa.get("violations", {})
    for key in ZERO_VIOLATIONS:
        actual = violations.get(key) if isinstance(violations, dict) else None
        add(f"framework_zero_{key}", actual == 0, actual=actual)
    reviewed_hash = str(qa.get("reviewed_asset_sha256", "")).upper()
    add("framework_visual_qa_hash_is_current",
        source_hash is not None and reviewed_hash == source_hash,
        actual=reviewed_hash, expected=source_hash)

    if stage == "paper":
        add("framework_body_reference_before_figure",
            binding.get("body_reference_before_figure") is True)
        add("framework_caption_complete", binding.get("caption_complete") is True)
        add("framework_post_figure_interpretation",
            binding.get("post_figure_interpretation") is True)
        add("framework_compiled_pdf_visible", binding.get("compiled_pdf_visible") is True)
        add("framework_compiled_pdf_page_recorded",
            isinstance(binding.get("compiled_pdf_page"), int)
            and binding.get("compiled_pdf_page", 0) > 0,
            actual=binding.get("compiled_pdf_page"))
        compiled_pdf = resolve_project_file(project_root, binding.get("compiled_pdf"))
        pdf_ok = bool(compiled_pdf and compiled_pdf.is_file())
        pdf_hash = sha256(compiled_pdf) if pdf_ok else None
        add("framework_compiled_pdf_exists", pdf_ok,
            path=str(compiled_pdf) if compiled_pdf else None)
        add("framework_compiled_pdf_hash_matches",
            pdf_hash == str(binding.get("compiled_pdf_sha256", "")).upper(),
            actual=pdf_hash, expected=binding.get("compiled_pdf_sha256"))
        add("framework_compiled_pdf_not_stale",
            bool(pdf_ok and target_ok and compiled_pdf.stat().st_mtime >= target.stat().st_mtime),
            pdf_mtime=compiled_pdf.stat().st_mtime if pdf_ok else None,
            target_mtime=target.stat().st_mtime if target_ok else None)
        page_contains_asset = False
        page_count = None
        verification = None
        page_number = binding.get("compiled_pdf_page")
        if pdf_ok and isinstance(page_number, int) and page_number > 0:
            try:
                import pymupdf
                with pymupdf.open(compiled_pdf) as document:
                    page_count = document.page_count
                    if page_number <= page_count:
                        page = document[page_number - 1]
                        if asset_kind == "raster" and target_ok:
                            expected_pixels = raster_file_fingerprint(target)
                            page_contains_asset, examined = page_contains_raster(
                                page, document, expected_pixels
                            )
                            verification = {
                                "method": "decoded_pixel_sha256",
                                "expected_pixel_sha256": expected_pixels[0],
                                "displayed_images_examined": examined,
                            }
                        elif asset_kind == "vector_text" and target_ok:
                            bbox = valid_page_bbox(
                                binding.get("compiled_pdf_figure_bbox_pt"), page.rect
                            )
                            add("framework_compiled_pdf_vector_bbox_valid", bbox is not None,
                                actual=binding.get("compiled_pdf_figure_bbox_pt"))
                            if bbox is not None:
                                verification = {
                                    "method": "vector_region_render_similarity",
                                    **vector_visual_match(target, page, bbox),
                                }
                                page_contains_asset = bool(verification["match"])
            except (ImportError, OSError, RuntimeError, ValueError):
                page_contains_asset = False
        add("framework_compiled_pdf_page_in_range",
            isinstance(page_number, int) and page_count is not None
            and 0 < page_number <= page_count,
            page=page_number, page_count=page_count)
        add("framework_compiled_pdf_page_contains_bound_asset",
            page_contains_asset, page=page_number, verification=verification)

    failures = [item for item in checks if not item["ok"]]
    return {
        "status": "PASS" if not failures else "FAIL",
        "stage": stage,
        "binding": str(binding_path),
        "checks": checks,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("render", "paper"), default="render")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = audit(args.binding.resolve(), args.project_root.resolve(), args.stage)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
