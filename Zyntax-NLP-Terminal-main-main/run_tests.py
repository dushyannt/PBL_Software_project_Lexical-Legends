#!/usr/bin/env python3
"""
File: run_tests.py
Description: Script to run all tests for the Zyntax project with various options
             for coverage reporting and verbosity levels.
"""

import os
import sys
import unittest
import argparse
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored terminal output
init()

def run_tests(verbosity=1, pattern="test_*.py", coverage=False):
    """Run all tests matching the pattern with optional coverage reporting"""
    # If coverage reporting is requested, check if the module is available
    if coverage:
        try:
            import coverage
            cov = coverage.Coverage(
                source=['nlp_engine', 'command_executor', 'interface'],
                omit=['*/tests/*', '*/venv/*', '*/env/*']
            )
            cov.start()
            use_coverage = True
        except ImportError:
            print(f"{Fore.YELLOW}Warning: coverage module not found. Running without coverage.{Style.RESET_ALL}")
            use_coverage = False
    else:
        use_coverage = False
    
    # Print header
    print(f"\n{Fore.CYAN}============================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}            ZYNTAX TEST SUITE            {Style.RESET_ALL}")
    print(f"{Fore.CYAN}============================================{Style.RESET_ALL}\n")
    
    # Discover and run tests
    print(f"{Fore.WHITE}Discovering tests...{Style.RESET_ALL}")
    tests_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests')
    
    loader = unittest.TestLoader()
    suite = loader.discover(tests_dir, pattern=pattern)
    
    print(f"{Fore.WHITE}Running {suite.countTestCases()} tests...{Style.RESET_ALL}\n")
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{Fore.CYAN}============================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}               TEST SUMMARY              {Style.RESET_ALL}")
    print(f"{Fore.CYAN}============================================{Style.RESET_ALL}")
    
    if result.wasSuccessful():
        print(f"{Fore.GREEN}✓ All tests passed!{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}✗ Some tests failed.{Style.RESET_ALL}")
    
    print(f"{Fore.WHITE}Ran {result.testsRun} tests with:")
    print(f"  {Fore.GREEN}{len(result.successes) if hasattr(result, 'successes') else result.testsRun - len(result.failures) - len(result.errors)} passed{Style.RESET_ALL}")
    print(f"  {Fore.RED}{len(result.failures)} failed{Style.RESET_ALL}")
    print(f"  {Fore.YELLOW}{len(result.errors)} errors{Style.RESET_ALL}")
    print(f"  {Fore.YELLOW}{len(result.skipped) if hasattr(result, 'skipped') else 0} skipped{Style.RESET_ALL}")
    
    # Generate coverage report if requested
    if use_coverage:
        print(f"\n{Fore.CYAN}============================================{Style.RESET_ALL}")
        print(f"{Fore.CYAN}            COVERAGE REPORT              {Style.RESET_ALL}")
        print(f"{Fore.CYAN}============================================{Style.RESET_ALL}")
        
        cov.stop()
        cov.save()
        
        print(f"\n{Fore.WHITE}Coverage Summary:{Style.RESET_ALL}")
        cov.report()
        
        # Generate HTML report
        html_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coverage_html')
        cov.html_report(directory=html_dir)
        print(f"\n{Fore.WHITE}HTML report generated at: {html_dir}{Style.RESET_ALL}")
    
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Zyntax tests")
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-p', '--pattern', default="test_*.py", help='Pattern to match test files')
    parser.add_argument('-c', '--coverage', action='store_true', help='Generate coverage report')
    args = parser.parse_args()
    
    verbosity = 2 if args.verbose else 1
    sys.exit(run_tests(verbosity, args.pattern, args.coverage))