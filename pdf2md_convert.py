#!/usr/bin/env python3
"""
pdf2md_convert.py — PDF conversion helper for pdf2md CLI.
Called by the bash wrapper; handles all conversion logic.

Usage:
  pdf2md_convert.py <input.pdf> <output_file> <fmt> <math:true|false> <vision_url|"">
"""

import sys
import os
import re
import hashlib


# ── Artifact cleaner ──────────────────────────────────────────────────────────

def clean_artifacts(text):
    """
    Remove common OCR noise patterns from markdown/plain-text output.

    Targets:
    - ~~XX~~ strikethrough fragments produced by Tesseract on image noise
    - Lone lines of pure non-alphanumeric symbols (decorative rules, etc.)
    - Excessive blank lines (3+ → 2)
    """
    # Strikethrough OCR artifacts: ~~anything up to 15 chars~~
    text = re.sub(r'~~[^~\n]{1,15}~~', '', text)

    # Collapse multiple spaces to one (but not in code/math blocks)
    lines = text.split('\n')
    cleaned = []
    in_code_block = False

    for line in lines:
        # Track fenced code/math blocks – don't touch their contents
        stripped = line.strip()
        if stripped.startswith('```') or stripped.startswith('$$'):
            in_code_block = not in_code_block
            cleaned.append(line)
            continue

        if in_code_block:
            cleaned.append(line)
            continue

        if stripped:
            # Count letters / digits (Cyrillic + Latin + digits + common math)
            meaningful = len(re.findall(
                r'[а-яёА-ЯЁa-zA-Z0-9\U0001D400-\U0001D7FF⋯⋮⋱⋰+\-=/*^()[\]{}]',
                stripped
            ))
            total = len(stripped)
            # Drop short lines with <10% meaningful chars (but keep markdown syntax)
            if total > 3 and meaningful / total < 0.10:
                if not stripped[0] in ('#', '-', '*', '|', '!', '[', '>'):
                    continue

        cleaned.append(line)

    text = '\n'.join(cleaned)
    # Collapse 3+ consecutive blank lines → 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


# ── Image extractor ───────────────────────────────────────────────────────────

def extract_images(pdf_path, images_dir):
    """
    Extract every embedded image from the PDF, one file per unique image.

    Returns list of dicts:
        { "page": int, "order": int, "width": int, "height": int, "filename": str }

    Images are saved to images_dir. Tiny images (<10×10 px) are skipped.
    """
    import pymupdf

    doc = pymupdf.open(pdf_path)
    os.makedirs(images_dir, exist_ok=True)

    seen_hashes = {}   # hash -> filename  (dedup across pages)
    extracted = []     # ordered list for placeholder matching

    for page_idx, page in enumerate(doc):
        img_list = page.get_images(full=True)
        page_order = 0

        for img_info in img_list:
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                img_bytes = base_image["image"]
                ext       = base_image.get("ext", "png")
                width     = base_image.get("width", 0)
                height    = base_image.get("height", 0)

                # Skip tiny decorative images
                if width < 10 or height < 10:
                    continue

                img_hash = hashlib.md5(img_bytes).hexdigest()[:8]

                # Reuse filename if we already extracted this exact image
                if img_hash in seen_hashes:
                    filename = seen_hashes[img_hash]
                else:
                    filename = f"img_p{page_idx + 1}_{page_order + 1}_{img_hash}.{ext}"
                    save_path = os.path.join(images_dir, filename)
                    with open(save_path, 'wb') as f:
                        f.write(img_bytes)
                    seen_hashes[img_hash] = filename

                extracted.append({
                    "page":     page_idx,
                    "order":    page_order,
                    "width":    width,
                    "height":   height,
                    "filename": filename,
                })
                page_order += 1

            except Exception:
                pass

    return extracted


# ── Placeholder replacer ──────────────────────────────────────────────────────

def replace_placeholders(md_text, images, images_dir_basename):
    """
    Replace pymupdf4llm placeholder strings:
        **==> picture [W x H] intentionally omitted <==**
    with actual Markdown image references, matched by exact pixel dimensions.
    """
    pattern = re.compile(
        r'\*\*==> picture \[(\d+) x (\d+)\] intentionally omitted <==\*\*'
    )

    # Index images by (width, height) keeping insertion order per key
    img_by_dims: dict[tuple, list[str]] = {}
    for img in images:
        key = (img["width"], img["height"])
        img_by_dims.setdefault(key, []).append(img["filename"])

    usage: dict[tuple, int] = {}

    def replace_one(match):
        w, h = int(match.group(1)), int(match.group(2))
        key = (w, h)
        idx = usage.get(key, 0)
        candidates = img_by_dims.get(key, [])
        if idx < len(candidates):
            usage[key] = idx + 1
            rel = f"{images_dir_basename}/{candidates[idx]}"
            return f"![Рисунок]({rel})"
        # Dimensions didn't match exactly — keep original placeholder
        return match.group(0)

    return pattern.sub(replace_one, md_text)


# ── Vision model integration ──────────────────────────────────────────────────

def call_vision_model(img_path, vision_url):
    """
    Send an image to a vision model (Ollama or LM Studio / OpenAI-compatible).
    Returns LaTeX string or None on failure.

    Tries:
    1. OpenAI-compatible  POST /v1/chat/completions
    2. Ollama native      POST /api/generate  (model: llava)
    """
    import base64
    import json
    import urllib.request

    with open(img_path, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode()

    prompt = (
        "This image shows a mathematical matrix or formula from a university textbook. "
        "Transcribe it exactly in LaTeX notation. "
        "Output only the raw LaTeX code (no explanation, no code fences)."
    )

    base_url = vision_url.rstrip('/')

    # ── Attempt 1: OpenAI-compatible (LM Studio, Ollama /v1) ──────────────────
    try:
        payload = {
            "model": "local-model",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{img_b64}"
                    }},
                ],
            }],
            "max_tokens": 512,
            "temperature": 0.1,
        }
        req = urllib.request.Request(
            f"{base_url}/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            result = json.loads(resp.read())
        if "choices" in result:
            content = result["choices"][0]["message"]["content"].strip()
            # Strip any fences the model may have added
            content = re.sub(r'^```(?:latex|math|tex)?\s*', '', content, flags=re.IGNORECASE)
            content = re.sub(r'\s*```$', '', content)
            return content.strip()
    except Exception:
        pass

    # ── Attempt 2: Ollama native format ───────────────────────────────────────
    try:
        payload = {
            "model": "llava",
            "prompt": prompt,
            "images": [img_b64],
            "stream": False,
        }
        req = urllib.request.Request(
            f"{base_url}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            result = json.loads(resp.read())
        if "response" in result:
            return result["response"].strip()
    except Exception:
        pass

    return None


def describe_images_with_vision(md_text, images_dir, images_dir_basename, vision_url):
    """
    For each ![...](images_dir_basename/...) reference in the markdown,
    call the vision model and replace the image tag with a $$ LaTeX $$ block.
    Falls back to keeping the original image tag on any error.
    """
    img_pattern = re.compile(
        r'!\[([^\]]*)\]\((' + re.escape(images_dir_basename) + r'/[^)]+)\)'
    )

    def replace_with_latex(match):
        img_rel = match.group(2)
        img_filename = img_rel[len(images_dir_basename):].lstrip('/')
        img_full = os.path.join(images_dir, img_filename)

        if not os.path.exists(img_full):
            return match.group(0)

        print(f"    [vision] {img_filename} ...", file=sys.stderr)
        latex = call_vision_model(img_full, vision_url)

        if latex:
            return f"\n$$\n{latex}\n$$\n"
        return match.group(0)   # keep image if model failed

    return img_pattern.sub(replace_with_latex, md_text)


# ── Main conversion ───────────────────────────────────────────────────────────

def convert(input_pdf, output_file, fmt, math_mode, vision_url):
    import pymupdf4llm
    import pymupdf

    # ── Plain-text output ─────────────────────────────────────────────────────
    if fmt == 'txt':
        doc = pymupdf.open(input_pdf)
        text = "\n\n".join(page.get_text() for page in doc)
        if math_mode:
            text = clean_artifacts(text)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
        return

    # ── Markdown output ───────────────────────────────────────────────────────
    if math_mode:
        import shutil
        import tempfile

        base          = os.path.splitext(output_file)[0]
        images_dir    = os.path.abspath(base + '_images')
        images_dir_bn = os.path.basename(base) + '_images'

        # pymupdf4llm replaces spaces in image_path with underscores — workaround:
        # use a space-free temp dir, then move images to the real target.
        tmp_img_dir = tempfile.mkdtemp(prefix='pdf2md_imgs_')
        try:
            # 1. Convert with write_images=True
            md = pymupdf4llm.to_markdown(
                input_pdf,
                write_images=True,
                image_path=tmp_img_dir + '/',
                image_format='png',
            )

            # 2. Move extracted images from temp → real images_dir
            os.makedirs(images_dir, exist_ok=True)
            img_files = [f for f in os.listdir(tmp_img_dir) if not f.startswith('.')]
            for fname in img_files:
                shutil.move(
                    os.path.join(tmp_img_dir, fname),
                    os.path.join(images_dir, fname),
                )
        finally:
            shutil.rmtree(tmp_img_dir, ignore_errors=True)

        n_imgs = len([f for f in os.listdir(images_dir) if not f.startswith('.')])
        if n_imgs:
            print(f"  → Saved {n_imgs} formula image(s) to {images_dir_bn}/",
                  file=sys.stderr)

        # 3. Rewrite absolute image paths → relative paths
        #    pymupdf4llm writes: ![](<tmp_img_dir>/filename.png)
        #    We want:            ![Формула](images_dir_bn/filename.png)
        tmp_prefix = re.escape(tmp_img_dir)
        md = re.sub(
            r'!\[([^\]]*)\]\(' + tmp_prefix + r'/?([^)]+)\)',
            lambda m: f'![Формула]({images_dir_bn}/{os.path.basename(m.group(2))})',
            md,
        )
        # Also rewrite any remaining absolute paths that pymupdf4llm may have used
        # (it sometimes writes the path without trailing slash)
        md = re.sub(
            r'!\[([^\]]*)\]\([^)]*/' + re.escape(os.path.basename(tmp_img_dir)) + r'/([^)]+)\)',
            lambda m: f'![Формула]({images_dir_bn}/{os.path.basename(m.group(2))})',
            md,
        )

        # 3. Clean OCR artifacts (~~OO~~, ~~pT~~ etc.)
        md = clean_artifacts(md)

        # 4. Optional: send images to vision model for LaTeX description
        if vision_url and n_imgs:
            print(f"  → Vision mode: {n_imgs} image(s) → {vision_url}",
                  file=sys.stderr)
            md = describe_images_with_vision(md, images_dir, images_dir_bn, vision_url)

    else:
        # Standard mode — just clean artifacts
        md = pymupdf4llm.to_markdown(input_pdf)
        md = clean_artifacts(md)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) != 6:
        print(
            "Usage: pdf2md_convert.py <input.pdf> <output> <fmt> <math:true|false> <vision_url|>",
            file=sys.stderr
        )
        sys.exit(1)

    _, input_pdf, output_file, fmt, math_flag, vision_url_arg = sys.argv

    math_mode  = math_flag.lower() == 'true'
    vision_url = vision_url_arg if vision_url_arg else None

    try:
        convert(input_pdf, output_file, fmt, math_mode, vision_url)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
