#!/usr/bin/env bash
# install.sh — set up pdf2md dependencies and install the CLI
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${CYAN}[install]${NC} $*"; }
success() { echo -e "${GREEN}[install]${NC} $*"; }
warn()    { echo -e "${YELLOW}[install]${NC} $*"; }
error()   { echo -e "${RED}[install] ERROR:${NC} $*" >&2; exit 1; }

BIN_DIR="/usr/local/bin"
LIB_DIR="/usr/local/lib/pdf2md"
OS="$(uname -s)"

# ── Pick pip that is not restricted by PEP 668 ───────────────────────────────
find_pip() {
  for candidate in \
      "/Library/Frameworks/Python.framework/Versions/3.12/bin/pip3" \
      "/Library/Frameworks/Python.framework/Versions/3.11/bin/pip3" \
      "$(which pip3 2>/dev/null || true)"; do
    if [[ -x "$candidate" ]]; then
      PIP="$candidate"
      return
    fi
  done
  error "pip3 not found. Install Python 3.10+ from python.org"
}

# ── macOS ─────────────────────────────────────────────────────────────────────
install_deps_macos() {
  command -v brew >/dev/null 2>&1 || error "Homebrew not found. Install from https://brew.sh"

  info "Installing tesseract + language packs..."
  brew install tesseract tesseract-lang

  info "Installing ocrmypdf..."
  brew install ocrmypdf

  find_pip
  info "Installing pymupdf4llm via $PIP..."
  "$PIP" install --upgrade pymupdf4llm
}

# ── Linux ─────────────────────────────────────────────────────────────────────
install_deps_linux() {
  info "Installing tesseract + ocrmypdf..."
  sudo apt-get update -q
  sudo apt-get install -y tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng ocrmypdf

  find_pip
  info "Installing pymupdf4llm via $PIP..."
  "$PIP" install --upgrade pymupdf4llm
}

# ── Copy CLI files ────────────────────────────────────────────────────────────
install_cli() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  # Resolve target bin/lib dirs (fall back to ~/bin and ~/.local/lib if no write access)
  local bin_target="$BIN_DIR"
  local lib_target="$LIB_DIR"

  if [[ ! -w "$BIN_DIR" ]]; then
    bin_target="$HOME/bin"
    lib_target="$HOME/.local/lib/pdf2md"
    mkdir -p "$bin_target" "$lib_target"

    # Add ~/bin to PATH in shell rc if needed
    local shell_rc=""
    if [[ "$SHELL" == *"zsh"* ]]; then
      shell_rc="$HOME/.zshrc"
    else
      shell_rc="$HOME/.bashrc"
    fi
    if ! grep -q '"$HOME/bin"' "$shell_rc" 2>/dev/null; then
      echo 'export PATH="$HOME/bin:$PATH"' >> "$shell_rc"
      info "Added ~/bin to PATH in $shell_rc"
      warn "Run: source $shell_rc  (or open a new terminal)"
    fi
  fi

  info "Installing pdf2md to $bin_target..."
  cp "$script_dir/pdf2md" "$bin_target/pdf2md"
  chmod +x "$bin_target/pdf2md"

  info "Installing pdf2md_convert.py to $lib_target..."
  cp "$script_dir/pdf2md_convert.py" "$lib_target/pdf2md_convert.py"
  chmod +x "$lib_target/pdf2md_convert.py"
}

# ── Main ──────────────────────────────────────────────────────────────────────
echo -e "${BOLD}pdf2md v2.0.0 installer${NC}"
echo ""

case "$OS" in
  Darwin) install_deps_macos ;;
  Linux)  install_deps_linux ;;
  *)      error "Unsupported OS: $OS" ;;
esac

install_cli

echo ""
success "Installation complete!"
echo ""
echo "Usage:"
echo "  pdf2md document.pdf                          # text-based PDF → .md"
echo "  pdf2md --ocr scanned.pdf                     # scanned PDF → .md"
echo "  pdf2md --math textbook.pdf                   # extract formula images"
echo "  pdf2md --math --vision-url http://localhost:11434 textbook.pdf"
echo "  pdf2md --ocr --math --lang rus lecture.pdf"
echo ""
echo "Run 'pdf2md --help' for full options."
