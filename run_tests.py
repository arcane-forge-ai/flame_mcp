#!/usr/bin/env python3
"""
Simple test runner for Flame Documentation Processing Pipeline
"""

import subprocess
import sys
from pathlib import Path

def run_tests():
    """Run the test suite with appropriate options."""
    print("🧪 Running Flame Docs Processing Tests")
    print("=" * 50)
    
    # Ensure we're in the right directory
    if not Path("tests").exists():
        print("❌ Tests directory not found. Make sure you're in the project root.")
        return 1
    
    # Run pytest with verbose output
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/",
        "-v",
        "--tb=short",
        "-ra"
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        if result.returncode == 0:
            print("\n✅ All tests passed!")
        else:
            print(f"\n❌ Tests failed with return code {result.returncode}")
        return result.returncode
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

def run_specific_test(test_name):
    """Run a specific test or test class."""
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/",
        "-v",
        "-k", test_name
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return 1

def run_test_file(test_file):
    """Run a specific test file."""
    test_path = f"tests/{test_file}"
    if not test_file.startswith("test_"):
        test_path = f"tests/test_{test_file}"
    if not test_path.endswith(".py"):
        test_path += ".py"
    
    cmd = [
        sys.executable, "-m", "pytest", 
        test_path,
        "-v"
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except Exception as e:
        print(f"❌ Error running test file: {e}")
        return 1

def show_help():
    """Show usage help."""
    print("""
🧪 Flame Docs Test Runner

Usage:
  python run_tests.py                    # Run all tests
  python run_tests.py chunking           # Run tests matching 'chunking'
  python run_tests.py --file chunking    # Run tests/test_chunking.py
  python run_tests.py --help             # Show this help

Available test files:
  - chunking      (document chunking tests)
  - embeddings    (embedding creation tests)
  - metadata      (metadata extraction tests)
  - utils         (utility function tests)
  - qdrant        (Qdrant storage tests)
  - integration   (integration tests)
""")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg in ["--help", "-h"]:
            show_help()
            sys.exit(0)
        elif arg == "--file" and len(sys.argv) > 2:
            # Run specific test file
            test_file = sys.argv[2]
            print(f"🧪 Running test file: {test_file}")
            exit_code = run_test_file(test_file)
        else:
            # Run specific test pattern
            test_name = arg
            print(f"🧪 Running tests matching: {test_name}")
            exit_code = run_specific_test(test_name)
    else:
        # Run all tests
        exit_code = run_tests()
    
    sys.exit(exit_code) 