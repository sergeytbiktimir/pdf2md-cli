---
name: python-doc-conversion
description: Python document format conversion: PDF, DOCX, HTML, Markdown, plain text, OCR, math/formula extraction, vision API integration, LLM-ready output. Use when working with document conversion pipelines, extracting text/structure from files, handling scanned PDFs, or preparing content for AI/LLM consumption.
---

# Python Document Conversion

## Library Quick Reference

| Source → Target | Preferred library |
|-----------------|-------------------|
| PDF → Markdown (LLM-ready) | `pymupdf4llm.to_markdown()` |
| PDF → plain text | `pymupdf` (`page.get_text()`) |
| PDF → structured data | `pdfplumber` |
| DOCX → text/Markdown | `python-docx` |
| HTML → Markdown | `markdownify` |
| Any → Any (complex) | `pandoc` via `subprocess` |
| Scanned PDF (OCR) | `ocrmypdf` + Tesseract |
| Images with formulas | Vision API (OpenAI-compatible) |

## Core Patterns

### PDF → Markdown (standard)
```python
import pymupdf4llm

md = pymupdf4llm.to_markdown("file.pdf")
```

### PDF → Markdown with image extraction
```python
md = pymupdf4llm.to_markdown(
    "file.pdf",
    write_images=True,
    image_path="output_images/",
    image_format="png",
)
```

### PDF → plain text
```python
import pymupdf

doc = pymupdf.open("file.pdf")
text = "\n".join(page.get_text() for page in doc)
```

### DOCX → plain text
```python
from docx import Document

doc = Document("file.docx")
text = "\n".join(p.text for p in doc.paragraphs)
```

### HTML → Markdown
```python
import markdownify

md = markdownify.markdownify(html, heading_style="ATX")
```

### OCR pre-pass (scanned PDFs)
```python
import subprocess, tempfile, os

with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
    subprocess.run(
        ["ocrmypdf", "--force-ocr", "-l", "rus+eng", "input.pdf", tmp.name],
        check=True,
    )
    # proceed with tmp.name
```

### Vision API for formulas/images
```python
import base64, urllib.request, json

def image_to_latex(image_path: str, api_url: str, model: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Convert this formula to LaTeX. Return only LaTeX, no explanation."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]}],
    }
    req = urllib.request.Request(
        f"{api_url}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp["choices"][0]["message"]["content"].strip()
```

## Output Cleaning (LLM-ready)

Common noise to strip after conversion:

```python
import re

def clean_artifacts(text: str) -> str:
    # Collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove lines that are only punctuation/symbols (OCR noise)
    text = re.sub(r"(?m)^[^\w\s]{1,5}$", "", text)
    return text.strip()
```

When writing cleaners, respect fenced blocks — skip lines inside ` ``` ` and `$$...$$ ` fences.

## This Project (pdf2md-cli)

- Entry point: `pdf2md` (bash) → `pdf2md_convert.py` (Python)
- Pipeline: OCR pre-pass (optional) → `pymupdf4llm.to_markdown()` → image path rewriting → `clean_artifacts()` → vision API per image (optional)
- Install: `install.sh` (no pyproject.toml — deps via pip in the script)
- CLI contract: `python pdf2md_convert.py <input> <output> <fmt> <math:true|false> <vision_url> [vision_model]`

## Common Pitfalls

- **Spaces in paths**: `pymupdf4llm` breaks on paths with spaces — write images to a temp dir, then move.
- **OCR language**: always pass explicit `-l` to ocrmypdf; default is English only.
- **Vision model output**: strip surrounding code fences (` ```latex ` … ` ``` `) before using LaTeX output.
- **Absolute vs relative image paths**: after extraction, rewrite to relative paths for portable Markdown.
