# Solstice Technical Documentation Build

BUILD_DIR = build
DOCS_DIR = docs

# Build the writeup
.PHONY: writeup
writeup:
	@mkdir -p $(BUILD_DIR) $(DOCS_DIR)
	@echo "Building Solstice writeup..."
	@pdflatex -interaction=nonstopmode -output-directory=$(BUILD_DIR) solstice.tex
	@pdflatex -interaction=nonstopmode -output-directory=$(BUILD_DIR) solstice.tex
	@mv $(BUILD_DIR)/solstice.pdf $(DOCS_DIR)/
	@echo "Done! PDF available at: $(DOCS_DIR)/solstice.pdf"

# Clean writeup build artifacts
.PHONY: clean-writeup
clean-writeup:
	@rm -rf $(BUILD_DIR) $(DOCS_DIR)
	@echo "Writeup artifacts and PDF removed"