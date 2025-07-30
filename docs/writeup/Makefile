# Solstice Technical Documentation Build

# Directory structure
SRC_DIR = src
BUILD_DIR = build
OUTPUT_DIR = output
ASSETS_DIR = assets

# Main tex file
MAIN_TEX = solstice.tex

# Default target
.PHONY: all
all: writeup

# Build the writeup
.PHONY: writeup
writeup:
	@mkdir -p $(BUILD_DIR) $(OUTPUT_DIR)
	@echo "Building Solstice writeup..."
	@cd $(BUILD_DIR) && pdflatex -interaction=nonstopmode ../$(SRC_DIR)/$(MAIN_TEX)
	@cd $(BUILD_DIR) && pdflatex -interaction=nonstopmode ../$(SRC_DIR)/$(MAIN_TEX)
	@cp $(BUILD_DIR)/solstice.pdf $(OUTPUT_DIR)/
	@echo "Done! PDF available at: $(OUTPUT_DIR)/solstice.pdf"

# Clean build artifacts (but keep output)
.PHONY: clean
clean:
	@rm -rf $(BUILD_DIR)
	@echo "Build artifacts removed"

# Clean everything including output
.PHONY: distclean
distclean: clean
	@rm -rf $(OUTPUT_DIR)/*.pdf
	@echo "All artifacts and output removed"

# Build stats document
.PHONY: stats
stats:
	@mkdir -p $(BUILD_DIR) $(OUTPUT_DIR)
	@echo "Building stats document..."
	@cd $(BUILD_DIR) && pdflatex -interaction=nonstopmode ../$(SRC_DIR)/stats.tex
	@cp $(BUILD_DIR)/stats.pdf $(OUTPUT_DIR)/
	@echo "Stats PDF available at: $(OUTPUT_DIR)/stats.pdf"

# View the PDF (macOS)
.PHONY: view
view:
	@open $(OUTPUT_DIR)/solstice.pdf 2>/dev/null || echo "PDF not found. Run 'make writeup' first."