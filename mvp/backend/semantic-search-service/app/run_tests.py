#!/usr/bin/env python3
"""
Test runner script for the semantic search service.

This script provides various options for running tests with different configurations.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=False)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run tests for semantic search service"
    )
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--api", action="store_true", help="Run only API tests")
    parser.add_argument(
        "--integration", action="store_true", help="Run only integration tests"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Run tests with coverage report"
    )
    parser.add_argument(
        "--html", action="store_true", help="Generate HTML coverage report"
    )
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--fast", action="store_true", help="Run fast tests only (skip slow ones)"
    )
    parser.add_argument("--file", type=str, help="Run specific test file")
    parser.add_argument("--pattern", type=str, help="Run tests matching pattern")

    args = parser.parse_args()

    # Set environment variables for testing
    os.environ["TESTING"] = "true"
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

    # Base pytest command
    cmd_parts = ["python", "-m", "pytest"]

    # Add test markers based on arguments
    if args.unit:
        cmd_parts.extend(["-m", "unit"])
    elif args.api:
        cmd_parts.extend(["-m", "api"])
    elif args.integration:
        cmd_parts.extend(["-m", "integration"])

    # Add specific file or pattern
    if args.file:
        cmd_parts.append(args.file)
    elif args.pattern:
        cmd_parts.extend(["-k", args.pattern])

    # Add coverage options
    if args.coverage or args.html:
        cmd_parts.extend(["--cov=.", "--cov-report=term-missing"])
        if args.html:
            cmd_parts.append("--cov-report=html")

    # Add parallel execution
    if args.parallel:
        cmd_parts.extend(["-n", "auto"])

    # Add verbosity
    if args.verbose:
        cmd_parts.append("-v")
    else:
        cmd_parts.append("-q")

    # Skip slow tests if fast mode
    if args.fast:
        cmd_parts.extend(["-m", "not slow"])

    # Build final command
    command = " ".join(cmd_parts)

    # Run the tests
    success = run_command(command, "Test execution")

    if success:
        print(f"\n🎉 All tests passed!")
        if args.html:
            html_report = Path("htmlcov/index.html")
            if html_report.exists():
                print(f"📊 Coverage report generated: {html_report.absolute()}")
    else:
        print(f"\n💥 Some tests failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
