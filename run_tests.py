#!/usr/bin/env python
"""Run the test suite with various options."""
import subprocess
import sys

def run_tests():
    """Run the test suite."""
    print("Running gateway tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/", 
        "-v",
        "--tb=short"
    ])
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed.")
        
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())