
        // Document search functionality
        class DocumentSearch {
            constructor() {
                this.searchIndex = null;
                this.loadSearchIndex();
                this.setupEventListeners();
            }
            
            async loadSearchIndex() {
                try {
                    const response = await fetch('../search-index.json');
                    this.searchIndex = await response.json();
                } catch (error) {
                    console.error('Failed to load search index:', error);
                }
            }
            
            setupEventListeners() {
                const searchInput = document.getElementById('search-input');
                if (searchInput) {
                    searchInput.addEventListener('input', (e) => this.handleSearch(e.target.value));
                }
            }
            
            handleSearch(query) {
                if (!query || query.length < 2) {
                    this.hideResults();
                    return;
                }
                
                const results = this.search(query);
                this.displayResults(results);
            }
            
            search(query) {
                if (!this.searchIndex) return [];
                
                const lowerQuery = query.toLowerCase();
                const results = [];
                
                for (const item of this.searchIndex) {
                    if (item.text.toLowerCase().includes(lowerQuery)) {
                        results.push({
                            ...item,
                            preview: this.getPreview(item.text, query)
                        });
                    }
                }
                
                return results.slice(0, 20); // Limit to 20 results
            }
            
            getPreview(text, query) {
                const index = text.toLowerCase().indexOf(query.toLowerCase());
                if (index === -1) return text.substring(0, 100) + '...';
                
                const start = Math.max(0, index - 50);
                const end = Math.min(text.length, index + query.length + 50);
                
                let preview = text.substring(start, end);
                if (start > 0) preview = '...' + preview;
                if (end < text.length) preview = preview + '...';
                
                // Highlight the match
                const regex = new RegExp(query, 'gi');
                preview = preview.replace(regex, '<strong>$&</strong>');
                
                return preview;
            }
            
            displayResults(results) {
                const resultsContainer = document.getElementById('search-results');
                if (!resultsContainer) return;
                
                if (results.length === 0) {
                    resultsContainer.innerHTML = '<div class="search-result">No results found</div>';
                } else {
                    resultsContainer.innerHTML = results.map(result => `
                        <div class="search-result" onclick="navigateToResult('${result.document}', '${result.block_id}')">
                            <div class="search-result-doc">${result.document} - Page ${result.page + 1}</div>
                            <div class="search-result-preview">${result.preview}</div>
                        </div>
                    `).join('');
                }
                
                resultsContainer.style.display = 'block';
            }
            
            hideResults() {
                const resultsContainer = document.getElementById('search-results');
                if (resultsContainer) {
                    resultsContainer.style.display = 'none';
                }
            }
        }
        
        // Navigation function
        function navigateToResult(document, blockId) {
            window.location.href = `documents/${document}.html#block-${blockId}`;
        }
        
        // Initialize search on page load
        document.addEventListener('DOMContentLoaded', () => {
            new DocumentSearch();
        });
        