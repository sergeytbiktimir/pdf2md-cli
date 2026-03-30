# pdf2md

CLI tool to convert PDF files to Markdown optimized for AI/LLM context (RAG, Cursor, ChatGPT, Claude, etc.).

Built on top of [pymupdf4llm](https://github.com/pymupdf/pymupdf4llm) and [ocrmypdf](https://github.com/ocrmypdf/OCRmyPDF). No heavy ML models required. Fits within a 500MB footprint.

---

## Features

- **Variant 1** — text-based PDF → Markdown (preserves headings, bold, structure)
- **Variant 2** — scanned PDF → OCR → Markdown (via Tesseract + ocrmypdf)
- Batch processing of entire folders
- Language flag for OCR (`--lang rus`, `--lang eng`, `--lang rus+eng`)
- Custom output directory (`--output-dir`)

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

`install.sh` will:
1. Install `tesseract` + language packs
2. Install `ocrmypdf`
3. Install `pymupdf4llm` via pip
4. Copy `pdf2md` to `/usr/local/bin`

---

## Usage

```bash
pdf2md [OPTIONS] <file.pdf | folder/>
```

### Options

| Flag | Description |
|------|-------------|
| `-o`, `--ocr` | Enable OCR mode (for scanned PDFs) |
| `-l`, `--lang <langs>` | OCR language(s), default: `rus+eng` |
| `-d`, `--output-dir <dir>` | Output directory for `.md` files |
| `-f`, `--force` | Overwrite existing `.md` files |
| `-v`, `--version` | Show version |
| `-h`, `--help` | Show help |

---

## Examples

### Single file — text-based PDF (Variant 1)

```bash
pdf2md document.pdf
```

**Output** (`document.md`):
```markdown
## **Физическая культура**

**Бег на короткие дистанции. Прыжок в длину с места**

## **Глоссарий**

**Бег** – один из способов передвижения человека, в котором присутствует
фаза полёта за счет скоординированных действий мышц скелета, рук и ног.

**Дистанция (спортивная)** – расстояние от старта до финиша, которое
спортсмен должен преодолеть за максимально короткое время.
```

---

### Single file — scanned PDF with OCR (Variant 2)

```bash
pdf2md --ocr --lang rus scan.pdf
```

**Output** (`scan.md`):
```markdown
Физическая культура

## Глоссарий

Бег — один из способов передвижения человека, в котором присутствует
фаза полёта за счет скоординированных действий мышц скелета, рук и ног.

Дистанция (спортивная) — расстояние от старта до финиша, которое
спортсмен должен преодолеть за максимально короткое время.
```

---

### Batch — entire folder

```bash
# All PDFs in ./docs/ → .md files saved next to originals
pdf2md ./docs/

# All PDFs with OCR → .md files saved in ./output/
pdf2md --ocr --output-dir ./output/ ./docs/
```

---

## How it works

```
PDF (text layer)  ──────────────────────────► pymupdf4llm ──► output.md
PDF (scanned)     ──► ocrmypdf (Tesseract) ──► pymupdf4llm ──► output.md
```

---

## Disk footprint

| Component | Size |
|---|---|
| pymupdf4llm | ~10 MB |
| ocrmypdf | ~42 MB |
| tesseract + tesseract-lang | ~130 MB |
| **Total** | **~180 MB** |

Well within a 500 MB project limit.

---

## License

MIT
