"""Convert extracted tables to LLM-friendly formats.

This module provides utilities to convert table extraction results
into formats optimized for LLM processing and understanding.
"""

from typing import Dict, Any, List, Optional, Union
import pandas as pd
import json
from textwrap import dedent


class TableToLLMFormatter:
    """Format extracted tables for LLM consumption."""
    
    def __init__(self, max_cell_length: int = 100, include_metadata: bool = True):
        """Initialize formatter.
        
        Args:
            max_cell_length: Maximum characters per cell (truncate if longer)
            include_metadata: Whether to include table metadata in output
        """
        self.max_cell_length = max_cell_length
        self.include_metadata = include_metadata
    
    def format_for_llm(
        self,
        extraction_result: Dict[str, Any],
        format_type: str = "markdown",
        context: Optional[str] = None
    ) -> str:
        """Format extraction result for LLM processing.
        
        Args:
            extraction_result: Result from TableExtractor
            format_type: Output format ('markdown', 'json', 'natural', 'structured')
            context: Optional context about the table
            
        Returns:
            Formatted string ready for LLM
        """
        if 'error' in extraction_result:
            return f"Table extraction failed: {extraction_result['error']}"
        
        # Get DataFrame
        df = extraction_result.get('dataframe')
        if df is None or df.empty:
            return "No table data extracted."
        
        # Clean data
        df = self._clean_dataframe(df)
        
        # Format based on type
        formatters = {
            'markdown': self._format_as_markdown,
            'json': self._format_as_json,
            'natural': self._format_as_natural_language,
            'structured': self._format_as_structured_text,
            'csv': self._format_as_csv,
            'xml': self._format_as_xml
        }
        
        formatter = formatters.get(format_type, self._format_as_markdown)
        formatted = formatter(df, extraction_result, context)
        
        return formatted
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean DataFrame for LLM processing."""
        # Make a copy
        df = df.copy()
        
        # Truncate long cells
        for col in df.columns:
            df[col] = df[col].astype(str).apply(
                lambda x: x[:self.max_cell_length] + '...' if len(x) > self.max_cell_length else x
            )
        
        # Replace None/NaN with empty string
        df = df.fillna('')
        
        # Strip whitespace
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        
        return df
    
    def _format_as_markdown(
        self, 
        df: pd.DataFrame, 
        result: Dict[str, Any], 
        context: Optional[str]
    ) -> str:
        """Format as Markdown table."""
        output = []
        
        if context:
            output.append(f"**Context**: {context}\n")
        
        if self.include_metadata:
            output.append(f"**Table Info**:")
            output.append(f"- Shape: {df.shape[0]} rows × {df.shape[1]} columns")
            output.append(f"- Extraction method: {result.get('method', 'unknown')}")
            if result.get('accuracy'):
                output.append(f"- Accuracy: {result['accuracy']:.1f}%")
            output.append("")
        
        # Convert to markdown
        output.append(df.to_markdown(index=False))
        
        return '\n'.join(output)
    
    def _format_as_json(
        self, 
        df: pd.DataFrame, 
        result: Dict[str, Any], 
        context: Optional[str]
    ) -> str:
        """Format as JSON for structured processing."""
        data = {
            "table": df.to_dict('records'),
            "metadata": {
                "rows": df.shape[0],
                "columns": df.shape[1],
                "extraction_method": result.get('method', 'unknown'),
                "accuracy": result.get('accuracy'),
                "column_names": df.columns.tolist()
            }
        }
        
        if context:
            data["context"] = context
        
        return json.dumps(data, indent=2)
    
    def _format_as_natural_language(
        self, 
        df: pd.DataFrame, 
        result: Dict[str, Any], 
        context: Optional[str]
    ) -> str:
        """Format as natural language description."""
        output = []
        
        if context:
            output.append(f"This table is about {context}.")
        
        output.append(f"The table has {df.shape[0]} rows and {df.shape[1]} columns.")
        
        # Describe columns
        cols_desc = ", ".join([f"'{col}'" for col in df.columns])
        output.append(f"The columns are: {cols_desc}.")
        
        # Sample data description
        if len(df) > 0:
            output.append("\nHere are the first few rows:")
            for idx, row in df.head(3).iterrows():
                row_desc = []
                for col, val in row.items():
                    if val:  # Only include non-empty values
                        row_desc.append(f"{col}: {val}")
                output.append(f"- Row {idx + 1}: {', '.join(row_desc)}")
        
        return '\n'.join(output)
    
    def _format_as_structured_text(
        self, 
        df: pd.DataFrame, 
        result: Dict[str, Any], 
        context: Optional[str]
    ) -> str:
        """Format as structured text with clear delimiters."""
        output = []
        
        output.append("=== TABLE START ===")
        
        if context:
            output.append(f"CONTEXT: {context}")
        
        output.append(f"DIMENSIONS: {df.shape[0]} rows × {df.shape[1]} columns")
        output.append(f"COLUMNS: {' | '.join(str(col) for col in df.columns)}")
        output.append("---")
        
        # Data rows
        for idx, row in df.iterrows():
            row_values = [str(val) for val in row.values]
            output.append(' | '.join(row_values))
        
        output.append("=== TABLE END ===")
        
        return '\n'.join(output)
    
    def _format_as_csv(
        self, 
        df: pd.DataFrame, 
        result: Dict[str, Any], 
        context: Optional[str]
    ) -> str:
        """Format as CSV."""
        output = []
        
        if context:
            output.append(f"# Context: {context}")
        
        output.append(df.to_csv(index=False))
        
        return '\n'.join(output)
    
    def _format_as_xml(
        self, 
        df: pd.DataFrame, 
        result: Dict[str, Any], 
        context: Optional[str]
    ) -> str:
        """Format as XML for structured processing."""
        output = ['<table>']
        
        if context:
            output.append(f'  <context>{context}</context>')
        
        output.append(f'  <metadata>')
        output.append(f'    <rows>{df.shape[0]}</rows>')
        output.append(f'    <columns>{df.shape[1]}</columns>')
        output.append(f'    <method>{result.get("method", "unknown")}</method>')
        output.append(f'  </metadata>')
        
        output.append('  <data>')
        for idx, row in df.iterrows():
            output.append('    <row>')
            for col, val in row.items():
                safe_col = str(col).replace(' ', '_').replace('/', '_')
                output.append(f'      <{safe_col}>{val}</{safe_col}>')
            output.append('    </row>')
        output.append('  </data>')
        
        output.append('</table>')
        
        return '\n'.join(output)
    
    def create_llm_prompt(
        self,
        extraction_result: Dict[str, Any],
        task: str = "summarize",
        format_type: str = "markdown"
    ) -> str:
        """Create a complete LLM prompt with table data.
        
        Args:
            extraction_result: Result from TableExtractor
            task: Task for LLM ('summarize', 'analyze', 'extract', 'qa')
            format_type: Table format to use
            
        Returns:
            Complete prompt ready for LLM
        """
        # Format table
        table_formatted = self.format_for_llm(extraction_result, format_type)
        
        # Task-specific prompts
        task_prompts = {
            'summarize': dedent("""
                Please summarize the key information from this table.
                Focus on the main findings, trends, or important data points.
                
                {table}
                
                Summary:
            """),
            
            'analyze': dedent("""
                Analyze this table and provide insights about:
                1. Key patterns or trends
                2. Notable outliers or exceptions
                3. Relationships between different columns
                4. Overall conclusions
                
                {table}
                
                Analysis:
            """),
            
            'extract': dedent("""
                Extract and list all important facts from this table.
                Present each fact as a clear, standalone statement.
                
                {table}
                
                Extracted Facts:
            """),
            
            'qa': dedent("""
                You have access to the following table data.
                Please answer questions based on this information.
                
                {table}
                
                I'm ready to answer questions about this table.
            """),
            
            'structured_extraction': dedent("""
                Extract information from this table into the following JSON structure:
                {{
                    "main_topic": "...",
                    "key_metrics": [
                        {{"name": "...", "value": "...", "unit": "..."}}
                    ],
                    "categories": ["..."],
                    "summary": "..."
                }}
                
                {table}
                
                JSON Output:
            """)
        }
        
        prompt_template = task_prompts.get(task, task_prompts['summarize'])
        return prompt_template.format(table=table_formatted)


def create_multi_table_prompt(
    tables: List[Dict[str, Any]],
    task: str = "compare",
    formatter: Optional[TableToLLMFormatter] = None
) -> str:
    """Create prompt for multiple tables.
    
    Args:
        tables: List of extraction results
        task: Task type ('compare', 'combine', 'relate')
        formatter: Optional formatter instance
        
    Returns:
        Complete prompt for multiple tables
    """
    if formatter is None:
        formatter = TableToLLMFormatter()
    
    formatted_tables = []
    for i, table in enumerate(tables):
        formatted = formatter.format_for_llm(table, format_type="markdown")
        formatted_tables.append(f"### Table {i+1}\n{formatted}")
    
    all_tables = "\n\n".join(formatted_tables)
    
    task_prompts = {
        'compare': dedent("""
            Compare and contrast the following tables.
            Identify similarities, differences, and relationships between them.
            
            {tables}
            
            Comparison:
        """),
        
        'combine': dedent("""
            Combine information from these tables into a unified summary.
            Identify how the data relates and create a cohesive narrative.
            
            {tables}
            
            Combined Summary:
        """),
        
        'relate': dedent("""
            Analyze the relationships between these tables.
            How does the data in one table relate to or support the data in others?
            
            {tables}
            
            Relationships:
        """)
    }
    
    prompt_template = task_prompts.get(task, task_prompts['compare'])
    return prompt_template.format(tables=all_tables)


# Example usage functions
def example_table_to_llm_pipeline():
    """Example of complete table to LLM pipeline."""
    
    # Simulated extraction result
    extraction_result = {
        'dataframe': pd.DataFrame({
            'Method': ['BERT', 'GPT-3', 'T5'],
            'Accuracy': [92.5, 94.8, 91.2],
            'Speed (ms)': [45, 120, 78],
            'Memory (GB)': [1.2, 8.5, 2.1]
        }),
        'method': 'camelot',
        'accuracy': 99.2,
        'shape': (3, 4)
    }
    
    formatter = TableToLLMFormatter()
    
    # Different format examples
    print("=== MARKDOWN FORMAT ===")
    print(formatter.format_for_llm(
        extraction_result, 
        format_type="markdown",
        context="ML model performance comparison"
    ))
    
    print("\n=== JSON FORMAT ===")
    print(formatter.format_for_llm(
        extraction_result,
        format_type="json"
    ))
    
    print("\n=== NATURAL LANGUAGE FORMAT ===")
    print(formatter.format_for_llm(
        extraction_result,
        format_type="natural"
    ))
    
    print("\n=== LLM PROMPT EXAMPLE ===")
    print(formatter.create_llm_prompt(
        extraction_result,
        task="analyze"
    ))


if __name__ == "__main__":
    example_table_to_llm_pipeline()