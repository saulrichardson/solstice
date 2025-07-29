#!/usr/bin/env python3
"""Verify the refactoring changes are correct."""

import ast
import sys
from pathlib import Path

# Files to check
files_to_verify = [
    "src/fact_check/evidence_extractor.py",
    "src/fact_check/agents/supporting_evidence_extractor.py", 
    "src/fact_check/agents/evidence_critic.py",
    "src/fact_check/agents/completeness_checker.py"
]

def check_no_context_field(file_path):
    """Check that file doesn't use context field."""
    content = Path(file_path).read_text()
    
    issues = []
    
    # Check for context field in snippets
    if "snippet.context" in content or "snippet['context']" in content or 'snippet["context"]' in content:
        issues.append("Found reference to snippet.context")
    
    # Check for context in data structures
    if '"context":' in content and "# The FactCheckInterface" not in content:
        # Count occurrences
        count = content.count('"context":')
        if count > 0:
            issues.append(f"Found {count} occurrences of 'context' field in data structures")
    
    # Check for context parameter in critique function
    if "def _critique_snippet" in content and ", context:" in content:
        issues.append("Found context parameter in _critique_snippet method")
    
    return issues

def check_prompt_updates(file_path):
    """Check that prompts have been updated."""
    content = Path(file_path).read_text()
    
    issues = []
    
    # Check for ellipsis instruction
    if "DO NOT use ellipsis (...)" in content or "No ellipsis (...)" in content:
        print(f"  ✓ Found updated prompt without ellipsis")
    elif "evidence_extractor.py" in file_path and "prompt = " in content:
        # Check if it's the extraction prompt
        if "Extract VERBATIM quotes" in content:
            print(f"  ✓ Found simplified verbatim extraction prompt")
        else:
            issues.append("Extraction prompt may not be updated")
    
    return issues

def main():
    print("Verifying refactoring changes...\n")
    
    all_good = True
    
    for file_path in files_to_verify:
        print(f"Checking {file_path}:")
        
        if not Path(file_path).exists():
            print(f"  ❌ File not found!")
            all_good = False
            continue
        
        # Check for context field usage
        context_issues = check_no_context_field(file_path)
        if context_issues:
            for issue in context_issues:
                print(f"  ❌ {issue}")
                all_good = False
        else:
            print(f"  ✓ No context field usage found")
        
        # Check prompt updates
        prompt_issues = check_prompt_updates(file_path)
        if prompt_issues:
            for issue in prompt_issues:
                print(f"  ❌ {issue}")
                all_good = False
        
        print()
    
    # Check SupportingSnippet model
    print("Checking SupportingSnippet model:")
    extractor_content = Path("src/fact_check/evidence_extractor.py").read_text()
    
    # Find the model definition
    if "class SupportingSnippet" in extractor_content:
        model_start = extractor_content.find("class SupportingSnippet")
        model_end = extractor_content.find("\n\nclass", model_start)
        if model_end == -1:
            model_end = extractor_content.find("\n\ndef", model_start)
        
        model_def = extractor_content[model_start:model_end]
        
        if "context: Optional[str]" in model_def:
            print("  ❌ Context field still in SupportingSnippet model")
            all_good = False
        else:
            print("  ✓ Context field removed from SupportingSnippet model")
    
    print("\n" + "="*50)
    if all_good:
        print("✅ All refactoring changes verified successfully!")
    else:
        print("❌ Some issues found in refactoring")
        sys.exit(1)

if __name__ == "__main__":
    main()