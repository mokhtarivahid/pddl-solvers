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
        
        # Test profiles
        self.test_domains = [
            ("ipc-1998", "gripper-round-1-strips", ["instance-1.pddl", "instance-2.pddl"]),
            ("ipc-1998", "logistics-round-1-strips", ["instance-1.pddl"]),
            ("ipc-2000", "logistics-strips", ["instance-1.pddl"]),
            ("ipc-2002", "depots-strips", ["instance-1.pddl"]),
        ]
        
        # Benchmark categories. Each category lists (domain_relpath, [instances]).
        # Instances must live under `<domain>/instances/` (IPC layout) or
        # alongside `domain.pddl` (temporal-domains layout); both are handled
        # by `find_test_cases_for_category`.
        self.benchmark_categories = {
            "classical": [
                ("ipc-domains/ipc-1998/domains/gripper-round-1-strips",
                 ["instance-1.pddl", "instance-2.pddl"]),
                ("ipc-domains/ipc-1998/domains/logistics-round-1-strips",
                 ["instance-1.pddl"]),
            ],
            "numeric": [
                ("ipc-domains/ipc-2023/domains/counters-numeric",
                 ["instance-1.pddl", "instance-2.pddl"]),
            ],
            "temporal": [
                ("temporal-domains/crewplanning-strips",
                 ["p01.pddl", "p02.pddl"]),
            ],
            # Specialist dialects: tiny hand-written PDDL benchmarks under
            # `tests/benchmarks/` chosen to solve in well under a second so
            # that every planner is exercised end-to-end on each run.
            "conformant": [
                ("tests/benchmarks/conformant", ["problem.pddl"]),
            ],
            "contingent": [
                ("tests/benchmarks/contingent", ["problem.pddl"]),
            ],
            "probabilistic": [
                ("tests/benchmarks/probabilistic", ["problem.pddl"]),
            ],
            "partial-order": [
                ("planners/vhpop/examples",
                 [("gripper-domain.pddl", "gripper-2.pddl")]),
            ],
        }

        # Per-planner: which profiles to test and which benchmark
        # categories the planner can solve. Every planner has at least one
        # category; if the corresponding domain/problem cannot be found, or
        # the planner binary is not built, the test runner reports a generic
        # SKIP without any planner-specific carve-out.
        self.planner_profiles = {
            "downward":         {"profiles": ["default", "satisficing-ff", "satisficing-lmcut"], "categories": ["classical"]},
            "symk":             {"profiles": ["default"],                                       "categories": ["classical"]},
            "ff":               {"profiles": ["default"],                                       "categories": ["classical"]},
            "ff-x":             {"profiles": ["default"],                                       "categories": ["classical"]},
            "madagascar":       {"profiles": ["default"],                                       "categories": ["classical"]},
            "powerlifted":      {"profiles": ["default"],                                       "categories": ["classical"]},
            "metric-ff":        {"profiles": ["default"],                                       "categories": ["classical", "numeric"]},
            "enhsp":            {"profiles": ["default", "satisficing-hmrp"],                   "categories": ["classical", "numeric"]},
            "optic":            {"profiles": ["default"],                                       "categories": ["temporal"]},
            "popf":             {"profiles": ["default"],                                       "categories": ["temporal"]},
            "tfd":              {"profiles": ["default"],                                       "categories": ["temporal"]},
            "lpg":              {"profiles": ["default"],                                       "categories": ["classical"]},
            "nextflap":         {"profiles": ["default"],                                       "categories": ["temporal"]},
            "conformant-ff":    {"profiles": ["default"],                                       "categories": ["conformant"]},
            "contingent-ff":    {"profiles": ["default"],                                       "categories": ["contingent"]},
            "probabilistic-ff": {"profiles": ["default"],                                       "categories": ["probabilistic"]},
            "vhpop":            {"profiles": ["default"],                                       "categories": ["partial-order"]},
        }

    def find_test_cases_for_category(self, category: str) -> List[Tuple[str, str, str, str]]:
        """Resolve benchmark entries for `category` to concrete (domain_path, domain_file, problem_file, instance_name) tuples.

        Each entry's directory may be given relative to ``benchmarks/`` (the
        IPC layout) or relative to the repository root (e.g.
        ``tests/benchmarks/...`` or ``planners/<planner>/examples`` for
        bespoke per-planner inputs). Instance entries are either a plain
        problem filename (paired with a sibling ``domain.pddl``) or an
        explicit ``(domain_filename, problem_filename)`` tuple.
        """
        cases: List[Tuple[str, str, str, str]] = []
        for domain_path, instances in self.benchmark_categories.get(category, []):
            # Allow repo-root-relative paths (tests/..., planners/...) so
            # specialist planners can ship their own tiny benchmarks without
            # polluting the IPC benchmarks tree.
            repo_relative = self.repo_root / domain_path
            full_domain_path = repo_relative if repo_relative.exists() else self.benchmarks_dir / domain_path
            default_domain_file = full_domain_path / "domain.pddl"
            # Instances may live in `instances/` (IPC layout) or in the
            # domain directory itself (temporal-domains layout).
            search_dirs = [full_domain_path / "instances", full_domain_path]
            for instance_entry in instances:
                if isinstance(instance_entry, tuple):
                    domain_name, instance_name = instance_entry
                else:
                    domain_name, instance_name = "domain.pddl", instance_entry
                for search_dir in search_dirs:
                    instance_file = search_dir / instance_name
                    domain_file = search_dir / domain_name if domain_name != "domain.pddl" else default_domain_file
                    if instance_file.exists() and domain_file.exists():
                        cases.append((str(domain_path), str(domain_file), str(instance_file), instance_name))
                        break
        return cases

    def find_available_test_cases(self) -> List[Tuple[str, str, str, str]]:
        """Return all available test cases across every benchmark category."""
        if not self.benchmarks_dir.exists():
            print("Warning: Benchmarks directory not found. Run with submodule initialized.")
            return []
        all_cases: List[Tuple[str, str, str, str]] = []
        for category in self.benchmark_categories:
            all_cases.extend(self.find_test_cases_for_category(category))
        return all_cases
    
    def run_single_test(self, planner: str, profile: str, domain_file: str, 
                       problem_file: str, timeout: int = 60) -> Dict:
        """Run a single test case."""
        
        cmd = [
            "python3", str(self.runner_script),
            "--planner", planner,
            "--profile", profile,
            "--timeout", str(timeout),
            "--no-live-output",
            "--output-format", "json",
            domain_file,
            problem_file,
        ]

        print(f"  Running: {planner} ({profile}) on {Path(problem_file).name}...")

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

            # Use the structured JSON report from run_planner.py; many planners
            # exit 0 even on failure/timeout, so exit code alone is unreliable.
            success = False
            executable_missing = False
            try:
                report = json.loads(result.stdout)
                success = bool(report.get("success"))
            except (json.JSONDecodeError, ValueError):
                # Non-JSON output usually means the runner aborted before
                # invoking the planner (e.g. binary not built).
                combined = (result.stdout or "") + (result.stderr or "")
                lowered = combined.lower()
                if ("executable not found" in lowered
                        or "no executable found" in lowered):
                    executable_missing = True
                else:
                    success = result.returncode == 0
            
            return {
                "planner": planner,
                "profile": profile, 
                "domain": domain_file,
                "problem": problem_file,
                "success": success,
                "executable_missing": executable_missing,
                "runtime": runtime,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "planner": planner,
                "profile": profile,
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

        if not self.benchmarks_dir.exists():
            print("No test cases found. Make sure benchmarks are available.")
            return {}

        # Get available planners (parse `--list-planners` output;
        # planner rows start at column 2 with the bare name, followed by
        # indented `Capabilities:` lines that must be ignored).
        try:
            result = subprocess.run(
                ["python3", str(self.runner_script), "--list-planners"],
                capture_output=True, text=True, cwd=str(self.repo_root)
            )
            available_planners = []
            for line in result.stdout.split('\n'):
                stripped = line.strip()
                if not stripped or stripped.startswith("Available") or stripped.startswith("Capabilities:"):
                    continue
                token = stripped.split()[0]
                # Planner names are lowercase identifiers (letters/digits/dash).
                if token and all(c.isalnum() or c == '-' for c in token) and token == token.lower():
                    available_planners.append(token)
        except Exception:
            available_planners = ["downward", "enhsp", "ff"]  # Fallback

        # Default: every planner declared in `planner_profiles`.
        if planners is None:
            planners = list(self.planner_profiles.keys())

        # Filter to planners that are both available and have profiles defined.
        planners = [p for p in planners if p in available_planners and p in self.planner_profiles]

        print(f"Testing planners: {', '.join(planners)}")

        all_results = {}

        for planner in planners:
            print(f"\nTesting planner: {planner}")
            planner_spec = self.planner_profiles[planner]
            categories = planner_spec["categories"]
            profiles = planner_spec["profiles"]

            # Collect benchmark cases compatible with this planner's capabilities.
            test_cases: List[Tuple[str, str, str, str]] = []
            for category in categories:
                test_cases.extend(self.find_test_cases_for_category(category))

            if not test_cases:
                reason = "no available domain/problem"
                print(f"  SKIP - {reason}")
                all_results[planner] = []
                continue

            planner_results = []
            missing_binary = False
            for profile in profiles:
                if missing_binary:
                    break
                print(f"  Profile: {profile}")
                for domain_path, domain_file, problem_file, instance_name in test_cases:
                    result = self.run_single_test(
                        planner, profile, domain_file, problem_file, timeout
                    )

                    result["domain_path"] = domain_path
                    result["instance_name"] = instance_name

                    if result.get("executable_missing"):
                        print(f"    SKIP {instance_name} - no binary available")
                        missing_binary = True
                        break

                    planner_results.append(result)
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
        rate = (total_success / total_tests * 100) if total_tests else 0.0
        report_lines.append(f"- Success rate: {rate:.1f}%")
        report_lines.append("")

        # Per-planner results
        for planner, planner_results in results.items():
            total_count = len(planner_results)
            if total_count == 0:
                report_lines.append(f"## {planner.upper()}")
                report_lines.append("- SKIPPED (no available domain/problem)")
                report_lines.append("")
                continue

            success_count = sum(1 for test in planner_results if test["success"])
            avg_runtime = sum(test["runtime"] for test in planner_results) / total_count

            report_lines.append(f"## {planner.upper()}")
            report_lines.append(f"- Tests: {success_count}/{total_count}")
            report_lines.append(f"- Success rate: {success_count/total_count*100:.1f}%")
            report_lines.append(f"- Avg runtime: {avg_runtime:.1f}s")
            report_lines.append("")
            
            # Detailed results table
            report_lines.append("| Profile | Domain | Instance | Success | Runtime |")
            report_lines.append("|--------|---------|----------|---------|----------|")
            
            for test in planner_results:
                domain_name = Path(test["domain_path"]).name
                status = "PASS" if test["success"] else "FAIL"
                report_lines.append(
                    f"| {test['profile']} | {domain_name} | {test['instance_name']} | "
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
                       help="Run only quick tests (fewer profiles)")
    
    args = parser.parse_args()
    
    # Get repository root
    repo_root = Path(__file__).parent.parent.resolve()
    test_suite = PlannerTestSuite(str(repo_root))
    
    # Quick mode: keep all planners but reduce to a single profile each.
    if args.quick:
        for planner, spec in test_suite.planner_profiles.items():
            spec["profiles"] = spec["profiles"][:1]
    
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
    
    skipped = [p for p, r in results.items() if not r]
    rate = (total_success / total_tests * 100) if total_tests else 0.0
    print(f"Summary: {total_success}/{total_tests} tests passed ({rate:.1f}%)")
    if skipped:
        print(f"Skipped (no available domain/problem or no binary): {', '.join(skipped)}")

    return 0 if total_tests and total_success == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())