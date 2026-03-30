#!/usr/bin/env bash
# install.sh — set up pdf2md dependencies and install the CLI
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${CYAN}[install]${NC} $*"; }
success() { echo -e "${GREEN}[install]${NC} $*"; }
error()   { echo -e "${RED}[install] ERROR:${NC} $*" >&2; exit 1; }

INSTALL_DIR="/usr/local/bin"

# ── macOS / Linux detection ───────────────────────────────────────────────────
OS="$(uname -s)"

install_deps_macos() {
  command -v brew >/dev/null 2>&1 || error "Homebrew not found. Install from https://brew.sh"

  info "Installing tesseract + language packs..."
  brew install tesseract tesseract-lang

  info "Installing ocrmypdf..."
  brew install ocrmypdf

  info "Installing pymupdf4llm (Python)..."
  # Try system Python first (avoids brew PEP 668 restriction)
  local pip_cmd=""
  for candidate in \
      "/Library/Frameworks/Python.framework/Versions/3.12/bin/pip3" \
      "/Library/Frameworks/Python.framework/Versions/3.11/bin/pip3" \
      "$(which pip3 2>/dev/null || true)"; do
    if [[ -x "$candidate" ]]; then
      pip_cmd="$candidate"
      break
    fi
  done

  if [[ -n "$pip_cmd" ]]; then
    "$pip_cmd" install --upgrade pymupdf4llm
  else
    pip3 install --upgrade --break-system-packages pymupdf4llm
  fi
}

install_deps_linux() {
  info "Installing tesseract..."
  sudo apt-get update -q
  sudo apt-get install -y tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng ocrmypdf

  info "Installing pymupdf4llm (Python)..."
  pip3 install --upgrade pymupdf4llm
}

# ── Install CLI script ────────────────────────────────────────────────────────
install_cli() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  # Prefer /usr/local/bin if writable, otherwise fall back to ~/bin
  if [[ -w "$INSTALL_DIR" ]]; then
    cp "$script_dir/pdf2md" "$INSTALL_DIR/pdf2md"
    chmod +x "$INSTALL_DIR/pdf2md"
    info "Installed to $INSTALL_DIR/pdf2md"
  else
    local user_bin="$HOME/bin"
    mkdir -p "$user_bin"
    cp "$script_dir/pdf2md" "$user_bin/pdf2md"
    chmod +x "$user_bin/pdf2md"
    info "Installed to $user_bin/pdf2md"
    # Add ~/bin to PATH if not already there
    local shell_rc=""
    if [[ "$SHELL" == *"zsh"* ]]; then
      shell_rc="$HOME/.zshrc"
    else
      shell_rc="$HOME/.bashrc"
    fi
    if ! grep -q 'export PATH="$HOME/bin:$PATH"' "$shell_rc" 2>/dev/null; then
      echo 'export PATH="$HOME/bin:$PATH"' >> "$shell_rc"
      info "Added ~/bin to PATH in $shell_rc"
      warn "Run: source $shell_rc  (or open a new terminal)"
    fi
  fi
}

# ── Main ──────────────────────────────────────────────────────────────────────
echo -e "${BOLD}pdf2md installer${NC}"
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
echo "  pdf2md document.pdf"
echo "  pdf2md --ocr scanned.pdf"
echo "  pdf2md --ocr --lang rus folder/"
echo ""
echo "Run 'pdf2md --help' for full options."
