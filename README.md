# pdf2md

CLI tool to convert PDF files to Markdown optimized for AI/LLM context (RAG, Cursor, ChatGPT, Claude, etc.).

Built on [pymupdf4llm](https://github.com/pymupdf/pymupdf4llm), [ocrmypdf](https://github.com/ocrmypdf/OCRmyPDF), and Tesseract. No heavy ML models required on the main machine. Fits within a 500MB footprint.

---

## Features

| Feature | Flag | Description |
|---------|------|-------------|
| Text-based PDF → Markdown | *(default)* | Preserves headings, bold, structure |
| Scanned PDF → OCR → Markdown | `--ocr` | Via Tesseract + ocrmypdf |
| Plain text output | `--format txt` | Raw text without Markdown syntax |
| Formula/matrix image extraction | `--math` | Saves formula images, embeds `![...](path)` in MD |
| OCR artifact cleanup | `--math` | Removes `~~OO~~`-style noise automatically |
| LaTeX via vision model | `--vision-url` + `--vision-model` | Sends images to remote Ollama/LM Studio, replaces with `$$ LaTeX $$` |
| Batch folder processing | *(folder path)* | Converts all PDFs in a directory |

---

## Requirements

- macOS or Linux
- Python 3.10+
- Homebrew (macOS) or apt (Linux)
- *(optional)* Remote Ollama server with a vision model for LaTeX extraction

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
- `pdf2md` CLI + `pdf2md_convert.py` helper → `~/bin/` or `/usr/local/bin/`

---

## Usage

```bash
pdf2md [OPTIONS] <file.pdf | folder/>
```

### Options

| Flag | Description |
|------|-------------|
| `-o`, `--ocr` | Enable OCR (for scanned PDFs without text layer) |
| `-l`, `--lang <langs>` | OCR language(s), default: `rus+eng` |
| `-d`, `--output-dir <dir>` | Output directory for files |
| `--format md\|txt` | Output format, default: `md` |
| `-m`, `--math` | Math mode: extract formula images + clean OCR artifacts |
| `--vision-url <url>` | Vision model endpoint — enables `--math` automatically |
| `--vision-model <name>` | Vision model name, default: `glm-ocr` |
| `-f`, `--force` | Overwrite existing output files |
| `-v`, `--version` | Show version |
| `-h`, `--help` | Show help |

---

## Examples

### Text-based PDF → Markdown (Variant 1)

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

### Scanned PDF → OCR → plain text (Variant 2)

```bash
pdf2md --ocr --format txt --lang rus scan.pdf
# → scan.txt
```

---

### Math document — extract formula images

```bash
pdf2md --math textbook.pdf
# → textbook.md          (with embedded image refs)
# → textbook_images/     (formula PNG files)
```

**Without `--math`** — formulas are silently dropped:
```
**==> picture [285 x 37] intentionally omitted <==**
```

**With `--math`** — formula images preserved in Markdown:
```markdown
![Формула](textbook_images/konspekt_1.pdf-0002-03.png)
```

---

### Math + Vision model → LaTeX text

Requires a running **Ollama** or **LM Studio** instance (can be on a remote server).

#### Recommended model: GLM-OCR

[GLM-OCR](https://ollama.com/library/glm-ocr) is a 0.9B model specialized for document OCR and formula recognition. Ranked #1 on OmniDocBench v1.5. Only **2.2 GB**, runs without GPU.

```bash
# On the server
ollama pull glm-ocr
```

```bash
# Convert with LaTeX extraction
pdf2md --math --vision-url http://<server-ip>:11434 --vision-model glm-ocr textbook.pdf
```

**Output — formulas become LaTeX blocks:**
```markdown
## Вопрос 2. Линейные операции над матрицами

$$
\begin{bmatrix}
1 & -3 & 4 \\
0.5 & 9 & -2
\end{bmatrix}
$$

Квадратная матрица Аn называется треугольной...

$$
A = \begin{bmatrix}
a_{11} & a_{12} & \cdots & a_{1n} \\
0      & a_{22} & \cdots & a_{2n} \\
\vdots & \vdots & \ddots & \vdots \\
0      & 0      & \cdots & a_{nn}
\end{bmatrix}
$$
```

#### Other supported models

| Model | Pull command | Size | Notes |
|-------|-------------|------|-------|
| `glm-ocr` | `ollama pull glm-ocr` | 2.2 GB | **Recommended** — specialized formula OCR |
| `olmocr2` | `ollama pull richardyoung/olmocr2:7b-q8` | 9.5 GB | Higher accuracy, needs 10+ GB RAM |
| `qwen2.5vl:7b` | `ollama pull qwen2.5vl:7b` | ~5 GB | General vision, decent on formulas |
| `llava` | `ollama pull llava` | ~4 GB | Basic vision, weak on math |

For **LM Studio** (OpenAI-compatible endpoint):
```bash
pdf2md --math --vision-url http://localhost:1234 --vision-model olmocr2 textbook.pdf
```

---

### Batch folder

```bash
# All PDFs in ./docs/ → .md (same directory)
pdf2md ./docs/

# Math mode with LaTeX, output to ./output/
pdf2md --math --vision-url http://192.168.1.74:11434 --output-dir ./output/ ./docs/

# OCR + plain text
pdf2md --ocr --format txt --lang rus ./scans/
```

---

## How it works

```
PDF (text layer)  ──────────────────────────────────► pymupdf4llm ──► output.md
PDF (scanned)     ──► ocrmypdf (Tesseract) ─────────► pymupdf4llm ──► output.md

With --math:
  ├── pymupdf4llm write_images=True ──► output_images/*.png
  ├── Clean OCR artifacts (~~noise~~)
  ├── Rewrite absolute paths → relative refs in Markdown
  └── (optional) --vision-url ──► GLM-OCR/olmOCR-2 ──► $$ LaTeX $$
```

---

## Disk footprint (local machine)

| Component | Size |
|---|---|
| pymupdf4llm | ~10 MB |
| ocrmypdf | ~42 MB |
| tesseract + tesseract-lang | ~130 MB |
| **Total** | **~182 MB** |

Vision model runs on a **remote server** — zero weight on the local machine.

---

## Version history

| Version | Changes |
|---------|---------|
| v2.1.0 | Add `--vision-model` flag; GLM-OCR format support (image in system message); fix double `$$` wrapping |
| v2.0.0 | Add `--math` mode; `--vision-url`; OCR artifact cleanup; Python helper `pdf2md_convert.py` |
| v1.1.0 | Add `--format txt`; fix install.sh for non-writable `/usr/local/bin` |
| v1.0.0 | Initial release: text PDF → MD, OCR mode, batch processing |

---

## License

MIT
