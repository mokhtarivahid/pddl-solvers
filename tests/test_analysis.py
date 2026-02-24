#!/usr/bin/env python3
"""
PDDL Requirements Analysis Test Suite

Tests for the PDDL analyzer, planner compatibility matching, and auto-selection features.

Author: PDDL Solvers Suite  
License: MIT
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pddl_analyzer import PDDLAnalyzer, PDDLRequirementsParser, PlannerCapabilityDatabase
except ImportError as e:
    print(f"Error importing analyzer modules: {e}")
    print("Make sure pddl_analyzer.py is in the project root directory")
    sys.exit(1)


class AnalysisTestSuite:
    """Test suite for PDDL requirements analysis and planner selection."""
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.benchmarks_dir = repo_root / "benchmarks"
        self.results_dir = repo_root / "tests" / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.analyzer = PDDLAnalyzer(str(repo_root))
        
        # Test domains with different characteristics
        self.test_domains = [
            {
                "name": "Classical Planning",
                "path": "benchmarks/ipc-domains/ipc-2023/domains/counters-numeric/domain.pddl",
                "expected_type": "Classical Planning",
                "expected_planners": ["downward", "ff"]
            },
            {
                "name": "Numeric Planning", 
                "path": "benchmarks/ipc-domains/ipc-2023/domains/settlers-numeric/domain.pddl",
                "expected_type": "Numeric Planning",
                "expected_planners": ["downward", "metric-ff", "enhsp"]
            },
            {
                "name": "Temporal Planning",
                "path": "benchmarks/temporal-domains/elevators-strips/domain.pddl", 
                "expected_type": "Temporal Planning",
                "expected_planners": ["optic", "enhsp", "popf", "tfd"]
            }
        ]
    
    def test_basic_imports(self) -> bool:
        """Test that all required modules can be imported."""
        print("Testing Basic Imports...")
        
        try:
            # Test parser
            parser = PDDLRequirementsParser()
            print("PASS: PDDLRequirementsParser imported successfully")
            
            # Test database
            db = PlannerCapabilityDatabase()
            print(f"PASS: PlannerCapabilityDatabase with {len(db.planners)} planners loaded")
            
            # Test analyzer
            analyzer = PDDLAnalyzer()
            print("PASS: PDDLAnalyzer created successfully")
            
            return True
            
        except Exception as e:
            print(f"FAIL: Import test failed: {e}")
            return False
    
    def test_domain_parsing(self) -> bool:
        """Test PDDL domain parsing functionality."""
        print("\nTesting Domain Parsing...")
        
        test_count = 0
        passed_count = 0
        
        for test_case in self.test_domains:
            test_count += 1
            domain_path = self.repo_root / test_case["path"]
            
            print(f"\n  Testing {test_case['name']}: {domain_path.name}")
            
            if not domain_path.exists():
                print(f"    WARNING: Domain file not found: {domain_path}")
                continue
            
            try:
                # Test parsing
                analysis = self.analyzer.analyze_domain(str(domain_path))
                
                # Verify structure
                required_keys = ['domain_info', 'compatible_planners', 'available_compatible_planners', 'analysis_summary']
                for key in required_keys:
                    if key not in analysis:
                        raise ValueError(f"Missing key in analysis: {key}")
                
                domain_info = analysis['domain_info']
                summary = analysis['analysis_summary']
                
                print(f"    PASS: Parsed domain: {domain_info['domain_name']}")
                print(f"    PASS: Requirements: {len(domain_info['requirements'])} ({', '.join(domain_info['requirements'][:3])}{'...' if len(domain_info['requirements']) > 3 else ''})")
                print(f"    PASS: Planning approach: {summary['planning_approach']}")
                print(f"    PASS: Compatible planners: {len(analysis['available_compatible_planners'])}")
                
                # Check expected planning type
                if summary['planning_approach'] == test_case['expected_type']:
                    print(f"    PASS: Expected planning type matched")
                else:
                    print(f"    ! Planning type mismatch: expected {test_case['expected_type']}, got {summary['planning_approach']}")
                
                # Check some expected planners are present
                compatible_names = [name for name, _, _ in analysis['available_compatible_planners']]
                found_expected = any(planner in compatible_names for planner in test_case['expected_planners'])
                if found_expected:
                    print(f"    PASS: Found expected planners")
                else:
                    print(f"    ! No expected planners found. Available: {compatible_names[:3]}")
                
                passed_count += 1
                
            except Exception as e:
                print(f"    FAIL: Parsing failed: {e}")
        
        success_rate = (passed_count / test_count * 100) if test_count > 0 else 0
        print(f"\nDomain Parsing: {passed_count}/{test_count} passed ({success_rate:.1f}%)")
        return success_rate >= 80
    
    def test_planner_matching(self) -> bool:
        """Test planner compatibility matching."""
        print("\nTesting Planner Compatibility Matching...")
        
        # Test with known requirements
        test_cases = [
            {
                "requirements": ["strips", "typing"],
                "expected_compatible": ["downward", "ff"],
                "description": "Basic classical planning"
            },
            {
                "requirements": ["numeric-fluents", "typing"],
                "expected_compatible": ["downward", "metric-ff", "enhsp"],
                "description": "Numeric planning"
            },
            {
                "requirements": ["durative-actions", "typing"],
                "expected_compatible": ["optic", "popf", "enhsp", "tfd"],
                "description": "Temporal planning"
            }
        ]
        
        passed_tests = 0
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n  Test {i}: {test_case['description']}")
            print(f"    Requirements: {test_case['requirements']}")
            
            try:
                compatible = self.analyzer.planner_db.get_compatible_planners(test_case['requirements'])
                compatible_names = [name for name, _, _ in compatible]
                
                print(f"    Compatible planners: {len(compatible)} ({compatible_names[:5]}{'...' if len(compatible_names) > 5 else ''})")
                
                # Check if expected planners are found
                found_expected = [planner for planner in test_case['expected_compatible'] if planner in compatible_names]
                
                if found_expected:
                    print(f"    PASS: Found expected planners: {found_expected}")
                    passed_tests += 1
                else:
                    print(f"    FAIL: No expected planners found")
                    
            except Exception as e:
                print(f"    FAIL: Matching failed: {e}")
        
        success_rate = (passed_tests / len(test_cases) * 100)
        print(f"\nPlanner Matching: {passed_tests}/{len(test_cases)} passed ({success_rate:.1f}%)")
        return success_rate >= 80
    
    def test_cli_integration(self) -> bool:
        """Test command-line integration."""
        print("\nTesting CLI Integration...")
        
        # Test analyze-only mode
        test_domain = None
        for test_case in self.test_domains:
            domain_path = self.repo_root / test_case["path"]
            if domain_path.exists():
                test_domain = domain_path
                break
        
        if not test_domain:
            print("    WARNING: No test domain available for CLI testing")
            return True
        
        try:
            # Test analyze-only command
            cmd = [
                "python3", str(self.repo_root / "run_planner.py"),
                "--analyze-only", "-d", str(test_domain)
            ]
            
            print(f"    Testing command: {' '.join(cmd[-3:])}")
            result = subprocess.run(cmd, cwd=str(self.repo_root), capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                if "PDDL DOMAIN ANALYSIS" in result.stdout and "Compatible Planners" in result.stdout:
                    print("    PASS: Analysis command works correctly")
                    return True
                else:
                    print("    FAIL: Analysis output missing expected content")
                    return False
            else:
                print(f"    FAIL: Analysis command failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("    FAIL: Analysis command timed out")
            return False
        except Exception as e:
            print(f"    FAIL: CLI integration test failed: {e}")
            return False
    
    def test_requirement_coverage(self) -> bool:
        """Test coverage of PDDL requirements."""
        print("\nTesting PDDL Requirements Coverage...")
        
        parser = PDDLRequirementsParser()
        db = PlannerCapabilityDatabase()
        
        print(f"    PASS: Parser knows {len(parser.known_requirements)} PDDL requirements")
        print(f"    PASS: Database has {len(db.planners)} planners")
        
        # Check requirement coverage
        all_supported_reqs = set()
        for planner in db.planners.values():
            all_supported_reqs.update(planner.supported_requirements)
        
        coverage = len(all_supported_reqs & parser.known_requirements) / len(parser.known_requirements) * 100
        print(f"    PASS: Requirement coverage: {coverage:.1f}% ({len(all_supported_reqs & parser.known_requirements)}/{len(parser.known_requirements)})")
        
        return coverage >= 50  # At least 50% coverage expected
    
    def run_comprehensive_demo(self) -> bool:
        """Run a comprehensive demonstration of the analysis system."""
        print("\nRunning Comprehensive Demo...")
        
        demo_successes = 0
        demo_tests = 0
        
        for test_case in self.test_domains:
            domain_path = self.repo_root / test_case["path"]
            if not domain_path.exists():
                continue
                
            demo_tests += 1
            print(f"\n  Demo {demo_tests}: {test_case['name']}")
            print(f"    Domain: {domain_path.relative_to(self.repo_root)}")
            
            try:
                analysis = self.analyzer.analyze_domain(str(domain_path))
                
                domain_info = analysis['domain_info']
                summary = analysis['analysis_summary']
                
                print(f"    → Domain: {domain_info['domain_name']}")
                print(f"    → PDDL Version: {summary['pddl_version']}")
                print(f"    → Approach: {summary['planning_approach']}")
                print(f"    → Requirements: {len(domain_info['requirements'])}")
                print(f"    → Compatible Planners: {len(analysis['available_compatible_planners'])}")
                
                if summary['recommended_planner']:
                    rec = summary['recommended_planner']
                    print(f"    → Recommended: {rec['name']} ({rec['compatibility_score']:.1%} match)")
                
                demo_successes += 1
                
            except Exception as e:
                print(f"    FAIL: Demo failed: {e}")
        
        success_rate = (demo_successes / demo_tests * 100) if demo_tests > 0 else 0
        print(f"\nDemo Results: {demo_successes}/{demo_tests} successful ({success_rate:.1f}%)")
        return success_rate >= 80
    
    def generate_report(self, results: Dict[str, bool]) -> str:
        """Generate a test report."""
        
        report_lines = [
            "# PDDL Requirements Analysis Test Report",
            f"Generated: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}",
            "",
            "## Test Results Summary",
            ""
        ]
        
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        
        for test_name, passed in results.items():
            status = "PASS" if passed else "FAIL"
            report_lines.append(f"- {test_name}: {status}")
        
        report_lines.extend([
            "",
            f"**Overall: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)**",
            "",
            "## System Information",
            f"- Repository: {self.repo_root}",
            f"- Available planners: {len(self.analyzer.planner_db.planners)}",
            f"- Benchmarks available: {'Yes' if self.benchmarks_dir.exists() else 'No'}",
            ""
        ])
        
        return "\n".join(report_lines)


def main():
    """Run the analysis test suite."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PDDL Requirements Analysis Test Suite")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--output-report", help="Generate markdown test report")
    parser.add_argument("--output-json", help="Generate JSON test results")
    
    args = parser.parse_args()
    
    # Get repository root
    repo_root = Path(__file__).parent.parent
    test_suite = AnalysisTestSuite(repo_root)
    
    print("="*60)
    print("PDDL Requirements Analysis Test Suite")
    print("="*60)
    
    # Define test sequence
    tests = [
        ("Basic Imports", test_suite.test_basic_imports),
        ("Requirement Coverage", test_suite.test_requirement_coverage),
        ("Domain Parsing", test_suite.test_domain_parsing),
        ("Planner Matching", test_suite.test_planner_matching),
        ("CLI Integration", test_suite.test_cli_integration)
    ]
    
    if not args.quick:
        tests.append(("Comprehensive Demo", test_suite.run_comprehensive_demo))
    
    # Run tests
    results = {}
    overall_success = True
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            success = test_func()
            results[test_name] = success
            
            if not success:
                overall_success = False
                
        except Exception as e:
            print(f"\nFAIL: Test '{test_name}' failed with exception: {e}")
            results[test_name] = False
            overall_success = False
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"{test_name:<25} {status}")
    
    print(f"\nOverall Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if overall_success:
        print("All tests passed! PDDL analysis system is working correctly.")
    else:
        print("Some tests failed. Check the output above for details.")
    
    # Generate reports if requested
    if args.output_report or args.output_json:
        report_content = test_suite.generate_report(results)
        
        if args.output_report:
            with open(args.output_report, 'w') as f:
                f.write(report_content)
            print(f"\nMarkdown report saved to: {args.output_report}")
        
        if args.output_json:
            json_results = {
                'timestamp': subprocess.run(['date', '+%Y-%m-%d %H:%M:%S'], capture_output=True, text=True).stdout.strip(),
                'overall_success': overall_success,
                'results': results,
                'summary': {
                    'total_tests': total,
                    'passed_tests': passed,
                    'success_rate': passed/total*100
                }
            }
            
            with open(args.output_json, 'w') as f:
                json.dump(json_results, f, indent=2)
            print(f"JSON results saved to: {args.output_json}")
    
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())