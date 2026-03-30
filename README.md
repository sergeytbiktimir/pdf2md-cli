# pdf2md

CLI tool to convert PDF files to Markdown optimized for AI/LLM context (RAG, Cursor, ChatGPT, Claude, etc.).

Built on [pymupdf4llm](https://github.com/pymupdf/pymupdf4llm), [ocrmypdf](https://github.com/ocrmypdf/OCRmyPDF), and Tesseract. No heavy ML models required. Fits within a 500MB footprint.

---

## Features

| Feature | Flag | Description |
|---------|------|-------------|
| Text-based PDF → Markdown | *(default)* | Preserves headings, bold, structure |
| Scanned PDF → OCR → Markdown | `--ocr` | Via Tesseract + ocrmypdf |
| Formula images extraction | `--math` | Saves formula images, embeds `![...](path)` in MD |
| OCR artifact cleanup | `--math` | Removes `~~OO~~`-style noise from OCR output |
| LaTeX via vision model | `--vision-url` | Sends images to Ollama/LM Studio, replaces with `$$LaTeX$$` |
| Plain text output | `--format txt` | Raw text without Markdown syntax |
| Batch folder processing | *(folder path)* | Converts all PDFs in a directory |

---

## Requirements

- macOS or Linux
- Python 3.10+
- Homebrew (macOS) or apt (Linux)

---

## Install

```bash
git clone https://github.com/sergeytbiktimir/pdf2md-cli.git
cd pdf2md-cli
chmod +x install.sh
./install.sh
```

`install.sh` installs:
- `tesseract` + language packs
- `ocrmypdf`
- `pymupdf4llm` (pip)
- `pdf2md` CLI + `pdf2md_convert.py` helper

---

## Usage

```bash
pdf2md [OPTIONS] <file.pdf | folder/>
```

### Options

| Flag | Description |
|------|-------------|
| `-o`, `--ocr` | Enable OCR (for scanned PDFs) |
| `-l`, `--lang <langs>` | OCR language(s), default: `rus+eng` |
| `-d`, `--output-dir <dir>` | Output directory for files |
| `--format md\|txt` | Output format, default: `md` |
| `-m`, `--math` | Math mode: extract images + clean artifacts |
| `--vision-url <url>` | Vision model endpoint (enables `--math` automatically) |
| `-f`, `--force` | Overwrite existing output files |
| `-v`, `--version` | Show version |
| `-h`, `--help` | Show help |

---

## Examples

### Text-based PDF → Markdown

```bash
pdf2md document.pdf
# → document.md
```

**Output:**
```markdown
## **Физическая культура**

**Бег на короткие дистанции. Прыжок в длину с места**

## **Глоссарий**

**Бег** – один из способов передвижения человека...
```

---

### Scanned PDF → OCR → Markdown

```bash
pdf2md --ocr --lang rus scan.pdf
# → scan.md
```

---

### Math document (formulas, matrices)

```bash
pdf2md --math textbook.pdf
# → textbook.md
# → textbook_images/img_p1_1_abc123.png  (formula images)
#   textbook_images/img_p2_1_def456.png
```

**Without `--math`** — formulas embedded as images are lost:
```markdown
**==> picture [285 x 37] intentionally omitted <==**
```

**With `--math`** — formula images are extracted and embedded:
```markdown
![Рисунок](textbook_images/img_p2_1_def456.png)
```

---

### Math + Vision model (LaTeX extraction)

Requires a running vision model (Ollama with `llava`, or LM Studio):

```bash
# Ollama
pdf2md --math --vision-url http://localhost:11434 textbook.pdf

# LM Studio
pdf2md --math --vision-url http://localhost:1234 textbook.pdf
```

**Output with `--vision-url`** — images replaced by LaTeX:
```markdown
$$
A_{m \times n} = \begin{pmatrix} a_{11} & a_{12} & \cdots & a_{1n} \\ a_{21} & a_{22} & \cdots & a_{2n} \\ \vdots & \vdots & \ddots & \vdots \\ a_{m1} & a_{m2} & \cdots & a_{mn} \end{pmatrix}
$$
```

---

### Batch folder

```bash
# All PDFs → .md files in same directory
pdf2md ./docs/

# Math mode, output to ./output/
pdf2md --math --output-dir ./output/ ./docs/

# OCR + math, plain text output
pdf2md --ocr --math --format txt ./scans/
```

---

## How it works

```
PDF (text layer)  ────────────────────────────────► pymupdf4llm ──► output.md
PDF (scanned)     ──► ocrmypdf (Tesseract OCR) ──► pymupdf4llm ──► output.md

With --math:
  ├── Extract embedded images ──► output_images/*.png
  ├── Clean OCR artifacts (~~noise~~)
  ├── Replace "intentionally omitted" placeholders with ![img](path)
  └── (optional) --vision-url ──► replace images with $$ LaTeX $$
```

---

## Disk footprint

| Component | Size |
|---|---|
| pymupdf4llm | ~10 MB |
| ocrmypdf | ~42 MB |
| tesseract + tesseract-lang | ~130 MB |
| **Total** | **~182 MB** |

---

## License

MIT
