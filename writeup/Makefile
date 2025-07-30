# Makefile for building LaTeX documents

TEX = pdflatex
PYTHON = python3

# Document versions
MAIN = solstice

.PHONY: all clean view

# Build main document
all: $(MAIN).pdf

# Build rules
$(MAIN).pdf: $(MAIN).tex
	$(TEX) $(MAIN)
	$(TEX) $(MAIN)  # Run twice for references

# Clean auxiliary files (but keep PDFs)
clean:
	rm -f *.aux *.log *.out *.toc *.bbl *.blg

# Clean everything including PDFs
cleanall: clean
	rm -f *.pdf

# View document
view: $(MAIN).pdf
	open $(MAIN).pdf  # macOS

# Quick build
quick: $(MAIN).tex
	$(TEX) $(MAIN)