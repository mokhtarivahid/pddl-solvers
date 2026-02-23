#!/usr/bin/env python3
"""
PDDL Planners Test Suite

This script runs comprehensive tests on various planners using benchmark problems
from the International Planning Competitions (IPC).

Author: PDDL Solvers Suite
License: MIT
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import subprocess


class PlannerTestSuite:
    """Test suite for PDDL planners."""
    
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.benchmarks_dir = self.repo_root / "benchmarks" 
        self.runner_script = self.repo_root / "run_planner.py"
        self.results_dir = self.repo_root / "tests" / "results"
        
        # Ensure results directory exists
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Test configurations
        self.test_domains = [
            ("ipc-1998", "gripper-round-1-strips", ["instance-1.pddl", "instance-2.pddl"]),
            ("ipc-1998", "logistics-round-1-strips", ["instance-1.pddl"]),
            ("ipc-2000", "logistics-strips", ["instance-1.pddl"]),
            ("ipc-2002", "depots-strips", ["instance-1.pddl"]),
        ]
        
        self.planner_configs = {
            "downward": [
                "astar-lmcut", "astar-ff", "lazy-greedy-ff", 
                "ehc-ff", "wa-star-ff"
            ],
            "enhsp": ["sat-hmrp", "gbfs-hadd"],
            "ff": ["default"],
            "ff-x": ["default"],
            "metric-ff": ["default"],
            "conformant-ff": ["default"],
            "contingent-ff": ["default"],
            "probabilistic-ff": ["default"],
            "madagascar": ["default"],
            "nextflap": ["default"],
            "optic": ["default"],
            "popf": ["default"],
            "powerlifted": ["default"],
            "symk": ["default"],
            "tfd": ["default"],
            "vhpop": ["default"]
        }
    
    def find_available_test_cases(self) -> List[Tuple[str, str, str, str]]:
        """Find available test cases from benchmark directory."""
        test_cases = []
        
        if not self.benchmarks_dir.exists():
            print("Warning: Benchmarks directory not found. Run with submodule initialized.")
            return test_cases
        
        # Define a set of simple test cases that should work with most planners
        simple_cases = [
            ("ipc-domains/ipc-1998/domains/gripper-round-1-strips", ["instance-1.pddl", "instance-2.pddl"]),
            ("ipc-domains/ipc-1998/domains/logistics-round-1-strips", ["instance-1.pddl"]),
        ]
        
        for domain_path, instances in simple_cases:
            full_domain_path = self.benchmarks_dir / domain_path
            if full_domain_path.exists():
                domain_file = full_domain_path / "domain.pddl"
                instances_dir = full_domain_path / "instances"
                
                if domain_file.exists() and instances_dir.exists():
                    for instance_name in instances:
                        instance_file = instances_dir / instance_name
                        if instance_file.exists():
                            test_cases.append((
                                str(domain_path),
                                str(domain_file),
                                str(instance_file), 
                                instance_name
                            ))
        
        return test_cases
    
    def run_single_test(self, planner: str, config: str, domain_file: str, 
                       problem_file: str, timeout: int = 60) -> Dict:
        """Run a single test case."""
        
        cmd = [
            "python3", str(self.runner_script),
            "--domain", domain_file,
            "--problem", problem_file, 
            "--planner", planner,
            "--timeout", str(timeout)
        ]
        
        if config != "default":
            cmd.extend(["--config", config])
        
        print(f"  Running: {planner} ({config}) on {Path(problem_file).name}...")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 10,
                cwd=str(self.repo_root)
            )
            
            runtime = time.time() - start_time
            
            # Parse the output to determine success
            success = result.returncode == 0 and "Success: True" in result.stdout
            
            return {
                "planner": planner,
                "config": config, 
                "domain": domain_file,
                "problem": problem_file,
                "success": success,
                "runtime": runtime,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "planner": planner,
                "config": config,
                "domain": domain_file, 
                "problem": problem_file,
                "success": False,
                "runtime": timeout,
                "return_code": -1,
                "stdout": "",
                "stderr": "Test timeout expired"
            }
    
    def run_planner_tests(self, planners: List[str] = None, 
                         timeout: int = 60) -> Dict[str, List[Dict]]:
        """Run tests for specified planners."""
        
        test_cases = self.find_available_test_cases()
        if not test_cases:
            print("No test cases found. Make sure benchmarks are available.")
            return {}
        
        print(f"Found {len(test_cases)} test cases")
        
        # Get available planners
        try:
            result = subprocess.run(
                ["python3", str(self.runner_script), "--list-planners"],
                capture_output=True, text=True, cwd=str(self.repo_root)
            )
            available_planners = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('Available planners:'):
                    available_planners.append(line)
        except:
            available_planners = ["downward", "enhsp", "ff"]  # Fallback
        
        if planners is None:
            planners = available_planners  # Test all available planners by default
        
        # Filter planners to only test ones that are available
        planners = [p for p in planners if p in available_planners]
        
        print(f"Testing planners: {', '.join(planners)}")
        
        all_results = {}
        
        for planner in planners:
            print(f"\nTesting planner: {planner}")
            planner_results = []
            
            configs = self.planner_configs.get(planner, ["default"])
            
            for config in configs:
                print(f"  Configuration: {config}")
                
                for domain_path, domain_file, problem_file, instance_name in test_cases:
                    result = self.run_single_test(
                        planner, config, domain_file, problem_file, timeout
                    )
                    
                    result["domain_path"] = domain_path
                    result["instance_name"] = instance_name
                    planner_results.append(result)
                    
                    # Print summary
                    status = "PASS" if result["success"] else "FAIL"
                    print(f"    {status} {instance_name} ({result['runtime']:.1f}s)")
            
            all_results[planner] = planner_results
        
        return all_results
    
    def generate_report(self, results: Dict[str, List[Dict]], 
                       output_file: str = None) -> str:
        """Generate a test report."""
        
        report_lines = []
        report_lines.append("# PDDL Planners Test Report")
        report_lines.append(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Summary statistics
        total_tests = sum(len(planner_results) for planner_results in results.values())
        total_success = sum(
            sum(1 for test in planner_results if test["success"])
            for planner_results in results.values()
        )
        
        report_lines.append(f"## Summary")
        report_lines.append(f"- Total tests: {total_tests}")
        report_lines.append(f"- Successful: {total_success}")
        report_lines.append(f"- Success rate: {total_success/total_tests*100:.1f}%")
        report_lines.append("")
        
        # Per-planner results
        for planner, planner_results in results.items():
            success_count = sum(1 for test in planner_results if test["success"])
            total_count = len(planner_results)
            avg_runtime = sum(test["runtime"] for test in planner_results) / total_count
            
            report_lines.append(f"## {planner.upper()}")
            report_lines.append(f"- Tests: {success_count}/{total_count}")
            report_lines.append(f"- Success rate: {success_count/total_count*100:.1f}%")
            report_lines.append(f"- Avg runtime: {avg_runtime:.1f}s")
            report_lines.append("")
            
            # Detailed results table
            report_lines.append("| Config | Domain | Instance | Success | Runtime |")
            report_lines.append("|--------|---------|----------|---------|----------|")
            
            for test in planner_results:
                domain_name = Path(test["domain_path"]).name
                status = "PASS" if test["success"] else "FAIL"
                report_lines.append(
                    f"| {test['config']} | {domain_name} | {test['instance_name']} | "
                    f"{status} | {test['runtime']:.1f}s |"
                )
            
            report_lines.append("")
        
        report_text = '\n'.join(report_lines)
        
        # Save to file if specified
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(report_text)
            print(f"Report saved to: {output_path}")
        
        return report_text
    
    def save_detailed_results(self, results: Dict[str, List[Dict]], 
                            filename: str = None) -> str:
        """Save detailed results in JSON format."""
        
        if filename is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"test_results_{timestamp}.json"
        
        output_path = self.results_dir / filename
        
        output_data = {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "total_tests": sum(len(planner_results) for planner_results in results.values()),
            "results": results
        }
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"Detailed results saved to: {output_path}")
        return str(output_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PDDL Planners Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--planners", nargs="+", 
                       help="Planners to test (default: all available planners)")
    parser.add_argument("--timeout", type=int, default=60,
                       help="Timeout per test in seconds (default: 60)")
    parser.add_argument("--output-report", 
                       help="Output file for markdown report")
    parser.add_argument("--output-json",
                       help="Output file for detailed JSON results")
    parser.add_argument("--quick", action="store_true",
                       help="Run only quick tests (fewer configurations)")
    
    args = parser.parse_args()
    
    # Get repository root
    repo_root = Path(__file__).parent.parent.resolve()
    test_suite = PlannerTestSuite(str(repo_root))
    
    # Adjust configurations for quick test
    if args.quick:
        test_suite.planner_configs = {
            "downward": ["astar-lmcut"],
            "enhsp": ["sat-hmrp"], 
            "ff": ["default"],
            "ff-x": ["default"],
            "metric-ff": ["default"],
            "conformant-ff": ["default"],
            "contingent-ff": ["default"],
            "probabilistic-ff": ["default"],
            "madagascar": ["default"],
            "nextflap": ["default"],
            "optic": ["default"],
            "popf": ["default"],
            "powerlifted": ["default"],
            "symk": ["default"],
            "tfd": ["default"],
            "vhpop": ["default"]
        }
    
    print("PDDL Planners Test Suite")
    print("=" * 50)
    
    # Run tests
    planners = args.planners or None  # Test all available planners by default
    results = test_suite.run_planner_tests(planners, args.timeout)
    
    if not results:
        print("No results to report.")
        return 1
    
    # Generate report
    report_file = args.output_report or str(test_suite.results_dir / "test_report.md")
    report = test_suite.generate_report(results, report_file)
    
    # Save detailed results
    json_file = args.output_json
    test_suite.save_detailed_results(results, json_file)
    
    # Print summary
    print("\n" + "=" * 50)
    print("Test completed!")
    
    # Show brief summary
    total_tests = sum(len(planner_results) for planner_results in results.values())
    total_success = sum(
        sum(1 for test in planner_results if test["success"])
        for planner_results in results.values()
    )
    
    print(f"Summary: {total_success}/{total_tests} tests passed ({total_success/total_tests*100:.1f}%)")
    
    return 0 if total_success > 0 else 1


if __name__ == "__main__":
    sys.exit(main())