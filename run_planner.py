#!/usr/bin/env python3
"""
Unified PDDL Planner Runner

This script provides a unified interface to run various PDDL planners
with standardized input (domain and problem files) and consistent output.

Author: PDDL Solvers Suite
License: MIT
"""

import argparse
import os
import sys
import subprocess
import select
import signal
import tempfile
import shutil
import json
import time
import shlex
import re
import textwrap
from contextlib import suppress
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import the PDDL analyzer and planner profiles
from pddl_analyzer import PDDLAnalyzer, PDDLRequirementsParser, PlannerCapabilityDatabase
from planner_profiles import PlannerProfiles


class PlannerRunner:
    """Unified runner for multiple PDDL planners."""
    
    def __init__(self, repo_root: str, spec_file: str = None, live_output: bool = True):
        self.repo_root = Path(repo_root)
        self.planners_dir = self.repo_root / "planners"
        self.temp_dir = None
        self.live_output = live_output
        
        # Initialize PDDL analyzer
        self.analyzer = PDDLAnalyzer(str(self.repo_root))
        
        # Load planner execution profiles
        if spec_file is None:
            spec_file = self.repo_root / "planner_profiles.yaml"
        try:
            self.spec = PlannerProfiles(str(spec_file))
        except Exception as e:
            print(f"Warning: Could not load planner specification: {e}", file=sys.stderr)
            self.spec = None
        
        # Legacy profiles (fallback if spec not available)
        # Fast Downward search profiles
        self.fd_profiles = {
            "optimal-lmcut": "astar(lmcut())",
            "optimal-ff": "astar(ff())",
            "satisficing-ff": "lazy_greedy([ff()], preferred=[ff()])",
            "satisficing-lmcut": "lazy_greedy([lmcut()])",
            "astar-cegar": "astar(cegar())",
            "ehc-ff": "ehc(ff())",
            "seq-sat-lama": "seq-sat-lama-2011",  # Uses alias
            "seq-opt-lama": "seq-opt-lmcut-one",  # Uses alias
            "wa-star-ff": "lazy_wastar([ff()], w=3)",
            "gbfs-ff": "lazy_greedy([ff()], preferred=[ff()])"
        }
        
        # ENHSP search profiles
        self.enhsp_profiles = {
            "sat-hmrp": "sat-hmrp", 
            "opt-hrmax": "opt-hrmax",
            "gbfs-hadd": "gbfs -h hadd",
            "wastar-hadd": "WAStar -h hadd",
            "astar-hadd": "WAStar -h hadd -wh 1.0"
        }
    
    def setup_temp_dir(self) -> Path:
        """Create temporary directory for planner intermediate files."""
        if self.temp_dir is None or not self.temp_dir.exists():
            self.temp_dir = Path(tempfile.mkdtemp(prefix="pddl_planner_"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        return self.temp_dir
    
    def cleanup_temp_dir(self):
        """Clean up temporary directory."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
    
    def print_execution_header(self, domain_file: Path, problem_file: Path, 
                               planner: str, profile: Optional[str], timeout: int,
                               auto_selected: bool = False, 
                               extra_args: Optional[List[str]] = None) -> None:
        """Print header information before planner execution."""
        print("\n" + "="*70)
        print("PDDL Planner Execution")
        print("="*70)
        print(f"Domain file:       {domain_file.name}")
        print(f"Problem file:      {problem_file.name}")
        print(f"Planner:           {planner}")
        if profile:
            if self.spec and self.spec.has_planner(planner):
                print(f"Profile:           {profile}")
                try:
                    desc = self.spec.get_profile_description(planner, profile)
                    if desc:
                        print(f"                   ({desc})")
                except ValueError:
                    pass
            else:
                print(f"Profile:           {profile}")
        if auto_selected:
            print(f"Selection mode:    Auto-selected based on domain requirements")
        print(f"Timeout:           {timeout} seconds")
        if extra_args:
            print(f"Extra arguments:   {' '.join(extra_args)}")
        print("="*70 + "\n")
    
    def validate_inputs(self, domain_file: str, problem_file: str) -> Tuple[Path, Path]:
        """Validate input PDDL files exist and are readable."""
        domain_path = Path(domain_file).resolve()
        problem_path = Path(problem_file).resolve()
        
        if not domain_path.exists():
            raise FileNotFoundError(f"Domain file not found: {domain_path}")
        if not problem_path.exists():
            raise FileNotFoundError(f"Problem file not found: {problem_path}")
        if not domain_path.is_file():
            raise ValueError(f"Domain path is not a file: {domain_path}")
        if not problem_path.is_file():
            raise ValueError(f"Problem path is not a file: {problem_path}")
            
        return domain_path, problem_path

    def format_command(self, cmd: List[str]) -> str:
        """Format a command for display."""
        return shlex.join([str(part) for part in cmd])

    def _decode_timeout_stream(self, stream) -> str:
        """Decode partial subprocess output captured in TimeoutExpired."""
        if stream is None:
            return ""
        if isinstance(stream, bytes):
            return stream.decode(errors="replace")
        return str(stream)

    def _run_subprocess(self, cmd: List[str], cwd: Optional[Path] = None,
                        timeout: Optional[int] = None, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
        """Run command while optionally streaming stdout/stderr live and collecting both."""
        if not self.live_output:
            return subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )

        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )

        out_chunks: List[str] = []
        err_chunks: List[str] = []
        streams = {
            process.stdout.fileno(): (process.stdout, out_chunks, sys.stdout),
            process.stderr.fileno(): (process.stderr, err_chunks, sys.stderr),
        }
        blank_line_runs: Dict[int, int] = {fd: 0 for fd in streams}

        start = time.time()
        while streams:
            if timeout is not None and (time.time() - start) >= timeout:
                process.kill()
                process.wait()
                raise subprocess.TimeoutExpired(
                    cmd=cmd,
                    timeout=timeout,
                    output="".join(out_chunks),
                    stderr="".join(err_chunks),
                )

            poll_timeout = 0.2
            if timeout is not None:
                remaining = max(0.0, timeout - (time.time() - start))
                poll_timeout = min(poll_timeout, remaining)

            ready, _, _ = select.select(list(streams.keys()), [], [], poll_timeout)
            if not ready:
                if process.poll() is not None:
                    break
                continue

            for fd in ready:
                stream, collected, sink = streams[fd]
                line = stream.readline()
                if line == "":
                    del streams[fd]
                    continue
                collected.append(line)

                # Some planners emit long runs of blank/progress lines in live mode.
                # Keep raw output for parsing, but compact terminal rendering.
                if line.strip() == "":
                    blank_line_runs[fd] = blank_line_runs.get(fd, 0) + 1
                else:
                    blank_line_runs[fd] = 0

                if blank_line_runs[fd] > 3:
                    continue

                try:
                    sink.write(line)
                    sink.flush()
                except BrokenPipeError:
                    # Downstream consumer closed (e.g., piping to head).
                    # Keep collecting output without crashing the planner run.
                    pass

        if process.stdout is not None:
            remaining_out = process.stdout.read() or ""
            if remaining_out:
                out_chunks.append(remaining_out)
                try:
                    sys.stdout.write(remaining_out)
                    sys.stdout.flush()
                except BrokenPipeError:
                    pass
        if process.stderr is not None:
            remaining_err = process.stderr.read() or ""
            if remaining_err:
                err_chunks.append(remaining_err)
                try:
                    sys.stderr.write(remaining_err)
                    sys.stderr.flush()
                except BrokenPipeError:
                    pass

        returncode = process.wait()
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=returncode,
            stdout="".join(out_chunks),
            stderr="".join(err_chunks),
        )

    def _compact_blank_runs(self, text: str, max_consecutive_newlines: int = 3) -> str:
        """Reduce excessive blank-line runs in planner output for readability."""
        if not text:
            return text
        if max_consecutive_newlines < 1:
            max_consecutive_newlines = 1
        pattern = r"\n{" + str(max_consecutive_newlines + 1) + r",}"
        replacement = "\n" * max_consecutive_newlines
        return re.sub(pattern, replacement, text)

    def _build_timeout_response(
        self,
        planner: str,
        profile: str,
        timeout: int,
        start_time: float,
        exc: subprocess.TimeoutExpired,
        plan_content: str = "",
        extra_note: str = "",
        stdout_suffix: str = "",
    ) -> Dict:
        """Build a consistent timeout result while preserving partial output."""
        runtime = time.time() - start_time
        partial_stdout = self._decode_timeout_stream(exc.stdout or exc.output).rstrip()
        partial_stderr = self._decode_timeout_stream(exc.stderr).rstrip()

        timeout_note = f"Timeout expired after {timeout}s"
        if extra_note:
            timeout_note = f"{timeout_note}; {extra_note}"

        if stdout_suffix:
            partial_stdout = f"{partial_stdout}{stdout_suffix}".strip()

        merged_stderr = timeout_note
        if partial_stderr:
            merged_stderr = f"{partial_stderr}\n{timeout_note}"

        return {
            "planner": planner,
            "profile": profile,
            "success": bool(plan_content.strip()),
            "runtime": runtime,
            "plan": plan_content,
            "stdout": partial_stdout,
            "stderr": merged_stderr,
            "return_code": 124,
        }

    def _collect_tfd_best_plan(self, solution_file: Path) -> Tuple[str, Optional[Path], List[Path]]:
        """Collect TFD plans and return the best available plan text.

        TFD may emit one or more plan files using the base output path and
        numeric suffixes (e.g., solution.plan.1, solution.plan.2, ...).
        """
        numbered_plans: List[Tuple[int, Path]] = []

        for plan_path in solution_file.parent.glob(f"{solution_file.name}.*"):
            suffix = plan_path.name[len(solution_file.name) + 1:]
            if suffix.isdigit():
                numbered_plans.append((int(suffix), plan_path))

        selected_plan: Optional[Path] = None
        if numbered_plans:
            selected_plan = max(numbered_plans, key=lambda item: item[0])[1]
        elif solution_file.exists():
            selected_plan = solution_file

        plan_content = ""
        if selected_plan is not None:
            with suppress(OSError):
                plan_content = selected_plan.read_text().strip()

        discovered = [p for _, p in sorted(numbered_plans, key=lambda x: x[0])]
        if solution_file.exists() and solution_file not in discovered:
            discovered.append(solution_file)

        return plan_content, selected_plan, discovered

    def _collect_numbered_plan_files(self, base_path: Path) -> List[Tuple[int, Path]]:
        """Collect plan files matching a base path and numeric suffixes."""
        ranked_paths: List[Tuple[int, Path]] = []

        if base_path.exists():
            ranked_paths.append((1, base_path))

        for plan_path in base_path.parent.glob(f"{base_path.name}.*"):
            suffix = plan_path.name[len(base_path.name) + 1:]
            if suffix.isdigit():
                ranked_paths.append((int(suffix), plan_path))

        ranked_paths.sort(key=lambda item: item[0])
        return ranked_paths

    def _cleanup_plan_artifacts(self, base_path: Path) -> None:
        """Remove a base plan file and any numbered siblings if present."""
        for _, plan_path in self._collect_numbered_plan_files(base_path):
            with suppress(OSError):
                plan_path.unlink()

    def _infer_plan_format(self, lines: List[str]) -> str:
        """Infer a coarse plan format from extracted plan lines."""
        if any("TRUESON:" in line or "FALSESON:" in line for line in lines):
            return "policy-tree"
        if any(re.match(r"^STEP\s+\d", line) for line in lines):
            return "parallel-step"
        if any(re.match(r"^\d+(?:\.\d+)?:\s+\(.*\)\s+\[[^\]]+\]$", line) for line in lines):
            return "temporal"
        if any(re.match(r"^\d+:\s+\(.*\)", line) for line in lines):
            return "numbered-sequential"
        if any(re.match(r"^step\s+\d+:", line, re.IGNORECASE) for line in lines):
            return "sequential"
        if lines and all(line.startswith("(") for line in lines if line and not line.startswith(";")):
            return "sequential"
        return "unknown"

    def _extract_plan_metrics(self, text: str) -> Dict[str, Optional[float]]:
        """Extract coarse cost and makespan signals from plan text."""
        cost = None
        makespan = None

        cost_patterns = [
            r";\s*cost\s*=\s*([0-9]+(?:\.[0-9]+)?)",
            r"Plan cost:\s*([0-9]+(?:\.[0-9]+)?)",
            r"Total plan cost:\s*([0-9]+(?:\.[0-9]+)?)",
            r"Metric \(Search\):\s*([0-9]+(?:\.[0-9]+)?)",
            r";\s*Cost:\s*([0-9]+(?:\.[0-9]+)?)",
        ]
        makespan_patterns = [
            r";\s*Makespan:\s*([0-9]+(?:\.[0-9]+)?)",
            r"Elapsed Time:\s*([0-9]+(?:\.[0-9]+)?)",
        ]

        for pattern in cost_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cost = float(match.group(1))
                break

        for pattern in makespan_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                makespan = float(match.group(1))
                break

        return {"cost": cost, "makespan": makespan}

    def _build_plan_entry(
        self,
        planner: str,
        text: str,
        source: str,
        rank: int = 1,
        source_name: Optional[str] = None,
        is_partial: bool = False,
        is_selected: bool = False,
    ) -> Dict[str, Any]:
        """Build a structured plan entry from raw text."""
        normalized_text = text.strip()
        lines = [line.strip() for line in normalized_text.splitlines() if line.strip()]
        metrics = self._extract_plan_metrics(normalized_text)

        return {
            "planner": planner,
            "rank": rank,
            "source": source,
            "source_name": source_name,
            "format": self._infer_plan_format(lines),
            "is_partial": is_partial,
            "is_selected": is_selected,
            "text": normalized_text,
            "actions": lines,
            "action_count": len([line for line in lines if not line.startswith(";")]),
            "cost": metrics["cost"],
            "makespan": metrics["makespan"],
        }

    def _plans_from_text_block(
        self,
        planner: str,
        text: str,
        source: str,
        source_name: Optional[str] = None,
        is_partial: bool = False,
    ) -> List[Dict[str, Any]]:
        """Create a single plan entry from a raw text block when present."""
        normalized_text = text.strip()
        if not normalized_text:
            return []
        return [
            self._build_plan_entry(
                planner,
                normalized_text,
                source,
                rank=1,
                source_name=source_name,
                is_partial=is_partial,
                is_selected=True,
            )
        ]

    def _plans_from_files(
        self,
        planner: str,
        base_path: Path,
        source: str,
        selected_rank: Optional[int] = None,
        prefer_last_as_selected: bool = False,
        is_partial: bool = False,
    ) -> List[Dict[str, Any]]:
        """Create plan entries from numbered plan files."""
        ranked_files = self._collect_numbered_plan_files(base_path)
        if not ranked_files:
            return []

        if selected_rank is None:
            selected_rank = ranked_files[-1][0] if prefer_last_as_selected else ranked_files[0][0]

        plans: List[Dict[str, Any]] = []
        for rank, plan_path in ranked_files:
            with suppress(OSError):
                text = plan_path.read_text().strip()
                if text:
                    plans.append(
                        self._build_plan_entry(
                            planner,
                            text,
                            source,
                            rank=rank,
                            source_name=plan_path.name,
                            is_partial=is_partial,
                            is_selected=(rank == selected_rank),
                        )
                    )

        plans.sort(key=lambda entry: entry["rank"])
        return plans

    def _selected_plan_text(self, plans: List[Dict[str, Any]]) -> str:
        """Return the selected plan text from a plan list."""
        for plan in plans:
            if plan.get("is_selected"):
                return plan["text"]
        return plans[0]["text"] if plans else ""

    def _finalize_result_plans(self, result: Dict[str, Any], plans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Attach structured plans and keep the legacy plan field aligned."""
        result["plans"] = plans
        result["plan"] = self._selected_plan_text(plans)
        result["plan_count"] = len(plans)
        result["selected_plan_rank"] = next(
            (plan["rank"] for plan in plans if plan.get("is_selected")),
            None,
        )
        return result

    def resolve_profile(self, planner: str, profile: Optional[str]) -> str:
        """Resolve the effective profile for a planner."""
        if profile is not None:
            return profile
        if self.spec and self.spec.has_planner(planner):
            return self.spec.get_default_profile(planner)
        if planner == "downward":
            return "optimal-lmcut"
        if planner == "enhsp":
            return "sat-hmrp"
        return "default"

    def _has_passthrough_option(self, extra_args: Optional[List[str]], *options: str) -> bool:
        """Check if extra arguments already specify a given option."""
        if not extra_args:
            return False
        return any(arg in options for arg in extra_args)

    def _get_spec_search(self, planner: str, profile: str) -> Optional[str]:
        """Get search string from specification when available."""
        if not self.spec or not self.spec.has_planner(planner):
            return None
        try:
            return self.spec.get_search_command(planner, profile)
        except ValueError:
            return None

    def _get_spec_args(self, planner: str, profile: str) -> List[str]:
        """Get profile arguments from specification when available."""
        if not self.spec or not self.spec.has_planner(planner):
            return []
        try:
            return self.spec.get_profile_args(planner, profile)
        except ValueError:
            return []

    def _get_spec_executable(self, planner: str, profile: str) -> Optional[str]:
        """Get executable override from specification when available."""
        if not self.spec or not self.spec.has_planner(planner):
            return None
        try:
            return self.spec.get_profile_executable(planner, profile)
        except ValueError:
            return None

    def _prepare_enhsp_inputs(self, domain_file: Path, problem_file: Path) -> Tuple[Path, Path]:
        """Prepare ENHSP-friendly lowercase PDDL copies.

        ENHSP's parser is not consistently case-insensitive on some legacy IPC
        benchmarks. Normalizing the temporary copies to lowercase preserves PDDL
        semantics while avoiding parser failures on uppercase keywords/tokens.
        """
        temp_dir = self.setup_temp_dir()
        enhsp_domain = temp_dir / "enhsp_domain.pddl"
        enhsp_problem = temp_dir / "enhsp_problem.pddl"

        enhsp_domain.write_text(domain_file.read_text().lower())
        enhsp_problem.write_text(problem_file.read_text().lower())

        return enhsp_domain, enhsp_problem

    def prepare_planner_command(self, planner: str, domain_file: Path, problem_file: Path,
                                profile: Optional[str] = None, timeout: int = 300,
                                extra_args: Optional[List[str]] = None) -> Dict:
        """Prepare command metadata for execution or dry-run preview."""
        resolved_profile = self.resolve_profile(planner, profile)

        if planner == "downward":
            downward_dir = self.planners_dir / "downward"
            downward_script = downward_dir / "fast-downward.py"
            if not downward_script.exists():
                raise FileNotFoundError(f"Fast Downward not found at {downward_script}")

            search_profile = self._get_spec_search("downward", resolved_profile) or self.fd_profiles.get(resolved_profile, resolved_profile)
            cmd = [str(downward_script), str(domain_file), str(problem_file)]
            if not self._has_passthrough_option(extra_args, "--search", "--alias"):
                if resolved_profile in ["seq-sat-lama", "seq-opt-lama"]:
                    cmd.extend(["--alias", search_profile])
                else:
                    cmd.extend(["--search", search_profile])
            if extra_args:
                cmd.extend(extra_args)
            return {"profile": resolved_profile, "cmd": cmd, "cwd": str(downward_dir)}

        if planner == "enhsp":
            enhsp_dir = self.planners_dir / "enhsp"
            enhsp_jar = enhsp_dir / "enhsp.jar"
            if not enhsp_jar.exists():
                raise FileNotFoundError(f"ENHSP JAR not found at {enhsp_jar}")

            enhsp_domain, enhsp_problem = self._prepare_enhsp_inputs(domain_file, problem_file)

            cmd = ["java", "-jar", str(enhsp_jar), "-o", str(enhsp_domain), "-f", str(enhsp_problem), "-timeout", str(timeout)]
            search_profile = self._get_spec_search("enhsp", resolved_profile) or self.enhsp_profiles.get(resolved_profile)
            if search_profile:
                if search_profile in ["sat-hmrp", "opt-hrmax"]:
                    cmd.extend(["-planner", search_profile])
                else:
                    cmd.extend(search_profile.split())
            plan_file = self.setup_temp_dir() / "enhsp_plan.txt"
            cmd.extend(["-sp", str(plan_file)])
            if extra_args:
                cmd.extend(extra_args)
            return {"profile": resolved_profile, "cmd": cmd, "cwd": str(enhsp_dir), "plan_file": plan_file}

        if planner == "ff":
            ff_dir = self.planners_dir / "ff"
            ff_executable = ff_dir / "ff"
            if not ff_executable.exists():
                raise FileNotFoundError(f"FF executable not found at {ff_executable}")
            temp_dir = self.setup_temp_dir()
            shutil.copy2(domain_file, temp_dir / "domain.pddl")
            shutil.copy2(problem_file, temp_dir / "problem.pddl")
            cmd = [str(ff_executable), "-p", str(temp_dir) + "/", "-o", "domain.pddl", "-f", "problem.pddl"]
            if extra_args:
                cmd.extend(extra_args)
            return {"profile": resolved_profile, "cmd": cmd, "cwd": str(temp_dir)}

        if planner in ["ff-x", "metric-ff", "conformant-ff", "contingent-ff", "probabilistic-ff"]:
            planner_dir = self.planners_dir / planner
            possible_exes = [planner.replace('-', ''), planner, "ff"]
            executable = None
            for exe_name in possible_exes:
                exe_path = planner_dir / exe_name
                if exe_path.exists() and exe_path.is_file():
                    import stat
                    if exe_path.stat().st_mode & stat.S_IEXEC:
                        executable = exe_path
                        break
            if executable is None:
                raise FileNotFoundError(f"No executable found for {planner}")
            temp_dir = self.setup_temp_dir()
            shutil.copy2(domain_file, temp_dir / "domain.pddl")
            shutil.copy2(problem_file, temp_dir / "problem.pddl")
            cmd = [str(executable), "-p", str(temp_dir) + "/", "-o", "domain.pddl", "-f", "problem.pddl"]
            if extra_args:
                cmd.extend(extra_args)
            return {"profile": resolved_profile, "cmd": cmd, "cwd": str(temp_dir)}

        if planner == "lpg":
            lpg_dir = self.planners_dir / "lpg"
            lpg_exe_name = self._get_spec_executable("lpg", resolved_profile) or "lpg"
            lpg_exe = lpg_dir / lpg_exe_name
            if not lpg_exe.exists():
                raise FileNotFoundError(f"LPG executable not found at {lpg_exe}")
            temp_dir = self.setup_temp_dir()
            shutil.copy2(domain_file, temp_dir / "domain.pddl")
            shutil.copy2(problem_file, temp_dir / "problem.pddl")
            cmd = [str(lpg_exe), "-o", "domain.pddl", "-f", "problem.pddl",
                   "-out", "plan.sol"]
            # Add mode flags from spec or profile name
            spec_args = self._get_spec_args("lpg", resolved_profile)
            if spec_args:
                cmd.extend(spec_args)
            elif resolved_profile == "speed":
                cmd.extend(["-speed"])
            elif resolved_profile == "quality":
                cmd.extend(["-quality"])
            else:
                cmd.extend(["-n", "1"])
            if extra_args:
                cmd.extend(extra_args)
            return {"profile": resolved_profile, "cmd": cmd, "cwd": str(temp_dir)}

        if planner == "madagascar":
            madagascar_dir = self.planners_dir / "madagascar"
            madagascar_exe_name = self._get_spec_executable("madagascar", resolved_profile) or "Mp"
            madagascar_exe = madagascar_dir / madagascar_exe_name
            if not madagascar_exe.exists():
                raise FileNotFoundError(f"MADAGASCAR executable not found at {madagascar_exe}")
            cmd = [str(madagascar_exe), str(domain_file), str(problem_file)]
            spec_args = self._get_spec_args("madagascar", resolved_profile)
            if spec_args:
                cmd.extend(spec_args)
            if extra_args:
                cmd.extend(extra_args)
            return {"profile": resolved_profile, "cmd": cmd, "cwd": str(madagascar_dir)}

        if planner == "vhpop":
            vhpop_dir = self.planners_dir / "vhpop"
            vhpop_exe = vhpop_dir / "vhpop"
            if not vhpop_exe.exists():
                vhpop_exe = vhpop_dir / "ipc3-vhpop"
            if not vhpop_exe.exists():
                raise FileNotFoundError("VHPOP executable not found")
            cmd = [str(vhpop_exe), str(domain_file), str(problem_file)]
            if extra_args:
                cmd.extend(extra_args)
            return {"profile": resolved_profile, "cmd": cmd, "cwd": str(vhpop_dir)}

        if planner == "tfd":
            tfd_dir = self.planners_dir / "tfd"
            tfd_exe = tfd_dir / "downward" / "tfd"
            if not tfd_exe.exists():
                raise FileNotFoundError(f"TFD executable not found at {tfd_exe}")
            solution_file = self.setup_temp_dir() / "tfd_solution.plan"
            cmd = [str(tfd_exe), str(domain_file), str(problem_file), str(solution_file)]
            # TFD's wrapper script accepts a single positional 4th argument: an
            # option string like "y+Y+a+e+r+O+1+C+1+b" (split on '+' internally).
            # When omitted, the wrapper applies its built-in default that enables
            # anytime search ('a'), causing the planner to keep looking for
            # improved plans until killed. We forward profile strings from
            # planner_profiles.yaml so non-anytime behavior is the default.
            spec_args = self._get_spec_args("tfd", resolved_profile)
            if spec_args:
                cmd.extend(spec_args)
            if extra_args:
                cmd.extend(extra_args)
            return {"profile": resolved_profile, "cmd": cmd, "cwd": str(tfd_dir), "solution_file": solution_file}

        if planner == "optic":
            optic_dir = self.planners_dir / "optic"
            optic_exe = optic_dir / "build" / "src" / "optic" / "optic-clp"
            if not optic_exe.exists():
                raise FileNotFoundError(f"OPTIC executable not found at {optic_exe}")
            cmd = [str(optic_exe)]
            cmd.extend(self._get_spec_args("optic", resolved_profile))
            if extra_args:
                cmd.extend(extra_args)
            cmd.extend([str(domain_file), str(problem_file)])
            return {"profile": resolved_profile, "cmd": cmd, "cwd": str(optic_dir)}

        if planner == "popf":
            popf_dir = self.planners_dir / "popf"
            popf_build_dir = popf_dir / "build"
            popf_exe = popf_build_dir / "popf"
            if not popf_exe.exists():
                raise FileNotFoundError(f"POPF executable not found at {popf_exe}")
            cmd = [str(popf_exe)]
            cmd.extend(self._get_spec_args("popf", resolved_profile))
            if extra_args:
                cmd.extend(extra_args)
            cmd.extend([str(domain_file), str(problem_file)])
            env = os.environ.copy()
            local_lib_paths = [str(popf_build_dir), str(popf_dir)]
            existing_ld_path = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = ":".join(local_lib_paths + ([existing_ld_path] if existing_ld_path else []))
            return {"profile": resolved_profile, "cmd": cmd, "cwd": str(popf_build_dir), "env": env}

        if planner == "powerlifted":
            powerlifted_dir = self.planners_dir / "powerlifted"
            powerlifted_exe = powerlifted_dir / "powerlifted.py"
            if not powerlifted_exe.exists():
                raise FileNotFoundError(f"POWERLIFTED executable not found at {powerlifted_exe}")
            cmd = ["python3", str(powerlifted_exe), "-d", str(domain_file), "-i", str(problem_file)]
            if resolved_profile == "bfws1":
                cmd.extend(["-s", "bfws1"])
            elif resolved_profile == "bfws2":
                cmd.extend(["-s", "bfws2"])
            elif resolved_profile == "astar":
                cmd.extend(["-s", "astar"])
            else:
                cmd.extend(["-s", "bfws1"])
            plan_file = self.setup_temp_dir() / "powerlifted_plan"
            if not self._has_passthrough_option(extra_args, "--plan-file"):
                cmd.extend(["--plan-file", str(plan_file)])
            if extra_args:
                cmd.extend(extra_args)
            return {"profile": resolved_profile, "cmd": cmd, "cwd": str(powerlifted_dir), "plan_file": plan_file}

        if planner == "symk":
            symk_dir = self.planners_dir / "symk"
            symk_exe = symk_dir / "fast-downward.py"
            if not symk_exe.exists():
                raise FileNotFoundError(f"SYMK executable not found at {symk_exe}")
            fallback_search = {
                "default": "sym_bd()",
                "optimal-bd": "sym_bd()",
                "optimal-fw": "sym_fw()",
                "optimal-bw": "sym_bw()",
                "topk-3": "symk_bd(plan_selection=top_k(num_plans=3))",
                "topk-5": "symk_bd(plan_selection=top_k(num_plans=5))",
                "topk-10": "symk_bd(plan_selection=top_k(num_plans=10))",
                "topq-3-q1.5": "symq_bd(plan_selection=top_k(num_plans=3), quality=1.5)",
                "topq-5-q2.0": "symq_bd(plan_selection=top_k(num_plans=5), quality=2.0)",
                "loopless-3": "symk_bd(simple=true, plan_selection=top_k(num_plans=3))",
                "unordered-3": "symk_bd(plan_selection=unordered(num_plans=3))"
            }
            search_profile = self._get_spec_search("symk", resolved_profile) or fallback_search.get(resolved_profile, fallback_search["default"])
            cmd = ["python3", str(symk_exe), str(domain_file), str(problem_file)]
            if not self._has_passthrough_option(extra_args, "--search", "--alias"):
                cmd.extend(["--search", search_profile])
            if extra_args:
                cmd.extend(extra_args)
            return {"profile": resolved_profile, "cmd": cmd, "cwd": str(symk_dir)}

        planner_dir = self.planners_dir / planner
        executables = [planner, f"{planner}.jar", f"{planner}.py"]
        executable = None
        for exe_name in executables:
            exe_path = planner_dir / exe_name
            if exe_path.exists():
                executable = exe_path
                break
        if executable is None:
            raise FileNotFoundError(f"No executable found for planner {planner} in planners/{planner}/")
        if executable.suffix == ".jar":
            cmd = ["java", "-jar", str(executable)]
        elif executable.suffix == ".py":
            cmd = ["python3", str(executable)]
        else:
            cmd = [str(executable)]
        cmd.extend([str(domain_file), str(problem_file)])
        if extra_args:
            cmd.extend(extra_args)
        return {"profile": resolved_profile, "cmd": cmd, "cwd": str(executable.parent)}
    
    def get_available_planners(self) -> List[str]:
        """Get list of available planners."""
        planners = []
        
        # Check submodule planners
        submodule_planners = [
            "downward", "enhsp", "nextflap", "optic", "popf", 
            "symk", "tfd", "powerlifted", "vhpop"
        ]
        
        for planner in submodule_planners:
            planner_path = self.planners_dir / planner
            if planner_path.exists():
                planners.append(planner)
        
        # Check direct source planners
        source_planners = [
            "ff", "ff-x", "metric-ff", "conformant-ff",
            "contingent-ff", "probabilistic-ff", "madagascar", "lpg"
        ]
        
        for planner in source_planners:
            planner_path = self.planners_dir / planner
            if planner_path.exists():
                planners.append(planner)
        
        return sorted(planners)
    
    def run_downward(self, domain_file: Path, problem_file: Path, 
                    profile: str = "optimal-lmcut", timeout: int = 300,
                    extra_args: Optional[List[str]] = None) -> Dict:
        """Run Fast Downward planner."""
        bundle = self.prepare_planner_command("downward", domain_file, problem_file, profile, timeout, extra_args)
        cmd = bundle["cmd"]
        downward_dir = bundle["cwd"]
        sas_plan_file = Path(downward_dir) / "sas_plan"
        
        # Fast Downward outputs to sas_plan by default
        # We'll read that file after execution
        
        print(f"Running Fast Downward with command: {self.format_command(cmd)}")
        
        start_time = time.time()
        try:
            result = self._run_subprocess(
                cmd,
                cwd=downward_dir,
                timeout=timeout + 30,
            )
            
            runtime = time.time() - start_time
            
            plans = self._plans_from_files("downward", sas_plan_file, "file", selected_rank=1)
            plan_content = self._selected_plan_text(plans)
            if sas_plan_file.exists():
                sas_plan_file.unlink()

            result_data = {
                "planner": "downward",
                "profile": profile,
                "success": result.returncode == 0 and bool(plan_content),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            return self._finalize_result_plans(result_data, plans)
            
        except subprocess.TimeoutExpired as exc:
            plans = self._plans_from_files("downward", sas_plan_file, "file", selected_rank=1, is_partial=True)
            if sas_plan_file.exists():
                with suppress(OSError):
                    sas_plan_file.unlink()
            timeout_result = self._build_timeout_response(
                "downward", profile, timeout, start_time, exc, self._selected_plan_text(plans)
            )
            return self._finalize_result_plans(timeout_result, plans)
    
    def run_enhsp(self, domain_file: Path, problem_file: Path, 
                  profile: str = "sat-hmrp", timeout: int = 300,
                  extra_args: Optional[List[str]] = None) -> Dict:
        """Run ENHSP planner."""
        bundle = self.prepare_planner_command("enhsp", domain_file, problem_file, profile, timeout, extra_args)
        cmd = bundle["cmd"]
        enhsp_dir = bundle["cwd"]
        plan_file = bundle["plan_file"]
        
        print(f"Running ENHSP with command: {self.format_command(cmd)}")
        
        start_time = time.time()
        try:
            result = self._run_subprocess(
                cmd,
                cwd=enhsp_dir,
                timeout=timeout + 30,
            )
            
            runtime = time.time() - start_time
            
            plans = self._plans_from_files("enhsp", plan_file, "file", selected_rank=1)
            if not plans:
                plans = self._plans_from_text_block("enhsp", self._extract_temporal_plan(result.stdout), "stdout")
            plan_content = self._selected_plan_text(plans)

            result_data = {
                "planner": "enhsp",
                "profile": profile,
                "success": result.returncode == 0 and bool(plan_content),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            return self._finalize_result_plans(result_data, plans)
            
        except subprocess.TimeoutExpired as exc:
            plans = self._plans_from_files("enhsp", plan_file, "file", selected_rank=1, is_partial=True)
            if not plans:
                partial_stdout = self._decode_timeout_stream(exc.stdout or exc.output)
                plans = self._plans_from_text_block("enhsp", self._extract_temporal_plan(partial_stdout), "stdout", is_partial=True)
            timeout_result = self._build_timeout_response(
                "enhsp", profile, timeout, start_time, exc, self._selected_plan_text(plans)
            )
            return self._finalize_result_plans(timeout_result, plans)
    
    def run_ff(self, domain_file: Path, problem_file: Path, 
               profile: str = "default", timeout: int = 300,
               extra_args: Optional[List[str]] = None) -> Dict:
        """Run FF planner."""
        bundle = self.prepare_planner_command("ff", domain_file, problem_file, profile, timeout, extra_args)
        cmd = bundle["cmd"]
        temp_dir = bundle["cwd"]
        
        print(f"Running FF with command: {self.format_command(cmd)}")
        
        start_time = time.time()
        try:
            result = self._run_subprocess(
                cmd,
                cwd=temp_dir,
                timeout=timeout,
            )
            
            runtime = time.time() - start_time
            
            # FF outputs plan directly to stdout
            plan_content = self._extract_ff_plan(result.stdout)
            
            result_data = {
                "planner": "ff", 
                "profile": profile,
                "success": result.returncode == 0 and bool(plan_content),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            return self._finalize_result_plans(result_data, self._plans_from_text_block("ff", plan_content, "stdout"))
            
        except subprocess.TimeoutExpired as exc:
            partial_stdout = self._decode_timeout_stream(exc.stdout or exc.output)
            plan_content = self._extract_ff_plan(partial_stdout)
            timeout_result = self._build_timeout_response(
                "ff", profile, timeout, start_time, exc, plan_content
            )
            return self._finalize_result_plans(timeout_result, self._plans_from_text_block("ff", plan_content, "stdout", is_partial=True))
    
    def _extract_ff_plan(self, stdout: str) -> str:
        """Extract plan from FF output.

        Handles both standard FF sequential plans ("found legal plan as
        follows") and contingent-FF policy trees ("found plan as follows").
        """
        lines = stdout.split('\n')
        in_plan = False
        plan_lines = []

        for line in lines:
            lower = line.lower()
            if "found legal plan as follows" in lower or "found plan as follows" in lower:
                in_plan = True
                continue
            elif in_plan:
                stripped = line.strip()
                if stripped.startswith("time spent:"):
                    break
                if stripped.startswith("statistics:") or stripped.startswith("tree layers"):
                    break
                if stripped:
                    plan_lines.append(stripped)

        return '\n'.join(plan_lines)

    def _extract_temporal_plan(self, stdout: str) -> str:
        """Extract timestamped temporal plan lines from stdout."""
        plan_lines = []

        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if re.match(r"^\d+(?:\.\d+)?:\s+\(.*\)\s+\[[^\]]+\]$", line):
                plan_lines.append(line)

        return '\n'.join(plan_lines)

    def _extract_madagascar_plan(self, stdout: str) -> str:
        """Extract plan lines from MADAGASCAR output."""
        plan_lines = []
        in_plan = False

        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if "PLAN FOUND:" in line.upper():
                in_plan = True
                continue

            if in_plan:
                if line.startswith("STEP "):
                    plan_lines.append(line)
                    continue
                if "actions in the plan" in line.lower() or line.startswith("total time"):
                    break

        return '\n'.join(plan_lines)
    
    # ------------------------------------------------------------------
    # VAL plan validation
    # ------------------------------------------------------------------
    def get_val_executable(self, tool: str = "Validate") -> Optional[Path]:
        """Return the path to a VAL executable if it has been built.

        VAL is configured as a git submodule at ``<repo>/VAL`` and is built
        by ``build_all.sh`` (``mkdir -p build && cmake .. && make``). The
        compiled binaries live under ``VAL/build/bin/``. Common tools:
        ``Validate`` (plan validation) and ``Parser`` (PDDL syntax check).
        """
        candidate = self.repo_root / "VAL" / "build" / "bin" / tool
        return candidate if candidate.exists() and os.access(candidate, os.X_OK) else None

    def validate_plan_with_val(
        self,
        domain_file: Path,
        problem_file: Path,
        plan_text: str,
        timeout: int = 60,
        epsilon: Optional[float] = None,
        val_verbose: bool = False,
    ) -> Dict[str, Any]:
        """Validate a plan using KCL-Planning's VAL ``Validate`` tool.

        Writes ``plan_text`` to a temporary file, invokes
        ``VAL/build/bin/Validate [-v N] [-t EPS] <domain> <problem> <plan>``
        and reports the structured outcome.

        Returns a dict with keys: ``available`` (bool), ``valid`` (Optional[bool]),
        ``return_code`` (Optional[int]), ``stdout``, ``stderr``, ``runtime``,
        ``error`` (Optional[str]), ``plan_file`` (path written).
        """
        result: Dict[str, Any] = {
            "available": False,
            "valid": None,
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "runtime": 0.0,
            "error": None,
            "plan_file": None,
            "command": None,
        }

        validate_exe = self.get_val_executable("Validate")
        if validate_exe is None:
            result["error"] = (
                "VAL 'Validate' executable not found at VAL/build/bin/Validate. "
                "Build VAL with: ./build_all.sh --planner val"
            )
            return result
        result["available"] = True

        if not plan_text or not plan_text.strip():
            result["error"] = "No plan available to validate (planner produced empty plan)."
            return result

        # Auto-detect temporal plans (lines like "0.000: (action) [duration]")
        # and pass a default epsilon tolerance so VAL accepts them.
        is_temporal = bool(
            re.search(r"^\s*\d+(?:\.\d+)?\s*:\s*\(.*\)\s*\[[^\]]+\]\s*$",
                      plan_text, re.MULTILINE)
        )

        temp_dir = self.setup_temp_dir()
        plan_file = temp_dir / "val_plan.txt"
        plan_file.write_text(plan_text.rstrip() + "\n")
        result["plan_file"] = str(plan_file)

        cmd: List[str] = [str(validate_exe)]
        if val_verbose:
            cmd.append("-v")
        if epsilon is None and is_temporal:
            epsilon = 0.001
        if epsilon is not None:
            cmd.extend(["-t", str(epsilon)])
        cmd.extend([str(domain_file), str(problem_file), str(plan_file)])
        result["command"] = self.format_command(cmd)

        start_time = time.time()
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            result["runtime"] = time.time() - start_time
            result["return_code"] = completed.returncode
            result["stdout"] = completed.stdout
            result["stderr"] = completed.stderr
            # VAL prints "Plan valid" on success and "Plan failed" / "Goal not
            # satisfied" / "Bad plan description" on failure. Exit code 0 is
            # the authoritative success signal, but we also consult the text
            # to defend against tools that return 0 on parse-only paths.
            stdout_lower = completed.stdout.lower()
            if completed.returncode == 0 and "plan valid" in stdout_lower:
                result["valid"] = True
            elif completed.returncode == 0 and "plan failed" not in stdout_lower \
                    and "bad plan" not in stdout_lower:
                # Conservative: success exit with no explicit failure phrase.
                result["valid"] = True
            else:
                result["valid"] = False
        except subprocess.TimeoutExpired as exc:
            result["runtime"] = time.time() - start_time
            result["error"] = f"VAL validation timed out after {timeout}s"
            result["stdout"] = self._decode_timeout_stream(exc.stdout)
            result["stderr"] = self._decode_timeout_stream(exc.stderr)
        except OSError as exc:
            result["runtime"] = time.time() - start_time
            result["error"] = f"Failed to execute VAL: {exc}"

        return result

    def print_validation_report(self, validation: Dict[str, Any]) -> None:
        """Print a concise, human-readable VAL validation report."""
        print("\n" + "=" * 70)
        print("VAL Plan Validation")
        print("=" * 70)
        if not validation.get("available"):
            print(f"Status: SKIPPED")
            if validation.get("error"):
                print(f"Reason: {validation['error']}")
            print("=" * 70)
            return

        if validation.get("command"):
            print(f"Command:    {validation['command']}")
        if validation.get("plan_file"):
            print(f"Plan file:  {validation['plan_file']}")
        print(f"Runtime:    {validation.get('runtime', 0.0):.3f}s")
        print(f"Exit code:  {validation.get('return_code')}")

        valid = validation.get("valid")
        if valid is True:
            print(f"Result:     VALID")
        elif valid is False:
            print(f"Result:     INVALID")
        else:
            print(f"Result:     UNKNOWN")

        if validation.get("error"):
            print(f"Error:      {validation['error']}")

        stdout = (validation.get("stdout") or "").strip()
        stderr = (validation.get("stderr") or "").strip()
        if stdout:
            print("\n--- VAL stdout ---")
            print(stdout)
        if stderr:
            print("\n--- VAL stderr ---")
            print(stderr)
        print("=" * 70)

    def run_planner(self, planner: str, domain_file: Path, problem_file: Path,
                    profile: str = None, timeout: int = 300, 
                    extra_args: Optional[List[str]] = None) -> Dict:
        """Run specified planner with given profile.
        
        Args:
            planner: Name of planner to run
            domain_file: Path to domain PDDL file
            problem_file: Path to problem PDDL file
            profile: Profile name (uses planner default if None)
            timeout: Timeout in seconds
            extra_args: Additional planner-specific arguments to pass through
        """
        
        profile = self.resolve_profile(planner, profile)
        
        if planner == "downward":
            return self.run_downward(domain_file, problem_file, profile, timeout, extra_args)
        elif planner == "enhsp":
            return self.run_enhsp(domain_file, problem_file, profile, timeout, extra_args)
        elif planner == "ff":
            return self.run_ff(domain_file, problem_file, profile, timeout, extra_args)
        else:
            # For other planners, provide basic interface
            return self.run_generic_planner(planner, domain_file, problem_file, profile, timeout, extra_args)
    
    def run_generic_planner(self, planner: str, domain_file: Path, problem_file: Path,
                           profile: str, timeout: int,
                           extra_args: Optional[List[str]] = None) -> Dict:
        """Run a generic planner with basic PDDL interface."""
        planner_dir = self.planners_dir / planner
        
        # Handle specific planner cases
        if planner == "madagascar":
            return self.run_madagascar(domain_file, problem_file, profile, timeout, extra_args)
        elif planner == "vhpop":
            return self.run_vhpop(domain_file, problem_file, profile, timeout, extra_args)
        elif planner == "tfd":
            return self.run_tfd(domain_file, problem_file, profile, timeout, extra_args)
        elif planner == "optic":
            return self.run_optic(domain_file, problem_file, profile, timeout, extra_args)
        elif planner == "popf":
            return self.run_popf(domain_file, problem_file, profile, timeout, extra_args)
        elif planner == "powerlifted":
            return self.run_powerlifted(domain_file, problem_file, profile, timeout, extra_args)
        elif planner == "symk":
            return self.run_symk(domain_file, problem_file, profile, timeout, extra_args)
        elif planner in ["ff-x", "metric-ff", "conformant-ff", "contingent-ff", "probabilistic-ff"]:
            return self.run_ff_variant(planner, domain_file, problem_file, profile, timeout, extra_args)
        elif planner == "lpg":
            return self.run_lpg(domain_file, problem_file, profile, timeout, extra_args)
        else:
            # Try common executable names in planner directory
            executables = [planner, f"{planner}.jar", f"{planner}.py"]
            executable = None
            
            # Look for executable in the planner directory
            for exe_name in executables:
                exe_path = planner_dir / exe_name
                if exe_path.exists():
                    executable = exe_path
                    break
            
            if executable is None:
                raise FileNotFoundError(f"No executable found for planner {planner} in planners/{planner}/")
            
            # Construct basic command
            if executable.suffix == ".jar":
                cmd = ["java", "-jar", str(executable)]
            elif executable.suffix == ".py":
                cmd = ["python3", str(executable)]
            else:
                cmd = [str(executable)]
            
            # Add domain and problem files (common patterns)
            cmd.extend([str(domain_file), str(problem_file)])
            if extra_args:
                cmd.extend(extra_args)
            
            print(f"Running {planner} with command: {self.format_command(cmd)}")
            
            start_time = time.time()
            try:
                result = self._run_subprocess(
                    cmd,
                    cwd=executable.parent,  # Use executable's directory as cwd
                    timeout=timeout,
                )
                
                runtime = time.time() - start_time
                
                return {
                    "planner": planner,
                    "profile": profile,
                    "success": result.returncode == 0,
                    "runtime": runtime,
                    "plan": result.stdout,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
                
            except subprocess.TimeoutExpired as exc:
                partial_stdout = self._decode_timeout_stream(exc.stdout or exc.output)
                return self._build_timeout_response(
                    planner, profile, timeout, start_time, exc, partial_stdout.strip()
                )
    
    def run_madagascar(self, domain_file: Path, problem_file: Path, 
                      profile: str, timeout: int,
                      extra_args: Optional[List[str]] = None) -> Dict:
        """Run MADAGASCAR SAT-based planner."""
        bundle = self.prepare_planner_command("madagascar", domain_file, problem_file, profile, timeout, extra_args)
        cmd = bundle["cmd"]
        madagascar_dir = bundle["cwd"]
        
        print(f"Running MADAGASCAR with command: {self.format_command(cmd)}")
        
        start_time = time.time()
        try:
            result = self._run_subprocess(
                cmd,
                cwd=madagascar_dir,
                timeout=timeout,
            )
            
            runtime = time.time() - start_time
            
            plan_content = self._extract_madagascar_plan(result.stdout)
            plans = self._plans_from_text_block("madagascar", plan_content, "stdout")

            result_data = {
                "planner": "madagascar",
                "profile": profile,
                "success": result.returncode == 0 and bool(plan_content.strip()),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            return self._finalize_result_plans(result_data, plans)
            
        except subprocess.TimeoutExpired as exc:
            partial_stdout = self._decode_timeout_stream(exc.stdout or exc.output)
            plan_content = self._extract_madagascar_plan(partial_stdout)
            timeout_result = self._build_timeout_response(
                "madagascar", profile, timeout, start_time, exc, partial_stdout.strip()
            )
            return self._finalize_result_plans(timeout_result, self._plans_from_text_block("madagascar", plan_content, "stdout", is_partial=True))
    
    def run_vhpop(self, domain_file: Path, problem_file: Path,
                  profile: str, timeout: int,
                  extra_args: Optional[List[str]] = None) -> Dict:
        """Run VHPOP planner."""
        bundle = self.prepare_planner_command("vhpop", domain_file, problem_file, profile, timeout, extra_args)
        cmd = bundle["cmd"]
        vhpop_dir = bundle["cwd"]
        
        print(f"Running VHPOP with command: {self.format_command(cmd)}")
        
        start_time = time.time()
        try:
            result = self._run_subprocess(
                cmd,
                cwd=vhpop_dir,
                timeout=timeout,
            )
            
            runtime = time.time() - start_time
            
            plan_content = result.stdout.strip()
            plans = self._plans_from_text_block("vhpop", plan_content, "stdout")

            result_data = {
                "planner": "vhpop",
                "profile": profile,
                "success": result.returncode == 0 and bool(plan_content.strip()),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            return self._finalize_result_plans(result_data, plans)
            
        except subprocess.TimeoutExpired as exc:
            partial_stdout = self._decode_timeout_stream(exc.stdout or exc.output)
            timeout_result = self._build_timeout_response(
                "vhpop", profile, timeout, start_time, exc, partial_stdout.strip()
            )
            return self._finalize_result_plans(timeout_result, self._plans_from_text_block("vhpop", partial_stdout.strip(), "stdout", is_partial=True))
    
    def run_tfd(self, domain_file: Path, problem_file: Path,
                profile: str, timeout: int,
                extra_args: Optional[List[str]] = None) -> Dict:
        """Run Temporal Fast Downward planner."""
        bundle = self.prepare_planner_command("tfd", domain_file, problem_file, profile, timeout, extra_args)
        cmd = bundle["cmd"]
        tfd_dir = bundle["cwd"]
        solution_file = bundle["solution_file"]
        
        print(f"Running TFD with command: {self.format_command(cmd)}")
        
        start_time = time.time()
        try:
            result = self._run_subprocess(
                cmd,
                cwd=tfd_dir,
                timeout=timeout,
            )
            
            runtime = time.time() - start_time
            
            # TFD primarily writes plans to the solution file and improved variants
            # as solution.N. The highest numeric suffix is the newest/best plan.
            plan_content, selected_plan, _ = self._collect_tfd_best_plan(solution_file)
            selected_rank = None
            if selected_plan is not None and selected_plan.name.startswith(f"{solution_file.name}."):
                suffix = selected_plan.name[len(solution_file.name) + 1:]
                if suffix.isdigit():
                    selected_rank = int(suffix)
            plans = self._plans_from_files("tfd", solution_file, "file", selected_rank=selected_rank, prefer_last_as_selected=True)

            result_data = {
                "planner": "tfd",
                "profile": profile,
                "success": result.returncode == 0 and bool(plan_content.strip()),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            return self._finalize_result_plans(result_data, plans)
            
        except subprocess.TimeoutExpired as exc:
            runtime = time.time() - start_time
            partial_stdout = self._decode_timeout_stream(exc.stdout or exc.output)
            partial_stderr = self._decode_timeout_stream(exc.stderr)
            plan_content, selected_plan, discovered_plans = self._collect_tfd_best_plan(solution_file)

            timeout_note = f"Timeout expired after {timeout}s"
            if selected_plan is not None:
                timeout_note += f"; recovered plan from {selected_plan.name}"
            if discovered_plans:
                timeout_note += f"; discovered {len(discovered_plans)} plan file(s)"

            # In passthrough mode, stdout is what the user sees. If the planner
            # timed out but produced a plan file, surface it explicitly.
            recovered_plan_block = ""
            if plan_content:
                recovered_plan_block = f"\n\nRecovered plan (before timeout):\n{plan_content}\n"

            merged_stderr = timeout_note
            if partial_stderr:
                merged_stderr = f"{partial_stderr.rstrip()}\n{timeout_note}"

            timeout_result = {
                "planner": "tfd",
                "profile": profile,
                "success": bool(plan_content.strip()),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": f"{partial_stdout.rstrip()}{recovered_plan_block}".strip(),
                "stderr": merged_stderr,
                "return_code": 124
            }
            selected_rank = None
            if selected_plan is not None and selected_plan.name.startswith(f"{solution_file.name}."):
                suffix = selected_plan.name[len(solution_file.name) + 1:]
                if suffix.isdigit():
                    selected_rank = int(suffix)
            plans = self._plans_from_files("tfd", solution_file, "file", selected_rank=selected_rank, prefer_last_as_selected=True, is_partial=True)
            return self._finalize_result_plans(timeout_result, plans)
    
    def run_optic(self, domain_file: Path, problem_file: Path,
                  profile: str, timeout: int,
                  extra_args: Optional[List[str]] = None) -> Dict:
        """Run OPTIC planner."""
        bundle = self.prepare_planner_command("optic", domain_file, problem_file, profile, timeout, extra_args)
        cmd = bundle["cmd"]
        optic_dir = bundle["cwd"]
        
        print(f"Running OPTIC with command: {self.format_command(cmd)}")
        
        start_time = time.time()
        try:
            result = self._run_subprocess(
                cmd,
                cwd=optic_dir,
                timeout=timeout,
            )
            
            runtime = time.time() - start_time
            normalized_stdout = self._compact_blank_runs(result.stdout)
            
            plan_content = self._extract_optic_plan(result.stdout)
            plans = self._plans_from_text_block("optic", plan_content, "stdout")

            result_data = {
                "planner": "optic",
                "profile": profile,
                "success": result.returncode == 0 and bool(plan_content.strip()),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": normalized_stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            return self._finalize_result_plans(result_data, plans)
            
        except subprocess.TimeoutExpired as exc:
            partial_stdout = self._decode_timeout_stream(exc.stdout or exc.output)
            plan_content = self._extract_optic_plan(partial_stdout)
            normalized_partial_stdout = self._compact_blank_runs(partial_stdout)
            timeout_result = self._build_timeout_response(
                "optic", profile, timeout, start_time, exc, plan_content,
            )
            timeout_result["stdout"] = normalized_partial_stdout
            return self._finalize_result_plans(timeout_result, self._plans_from_text_block("optic", plan_content, "stdout", is_partial=True))
    
    def _extract_optic_plan(self, stdout: str) -> str:
        """Extract plan from OPTIC output."""
        return self._extract_temporal_plan(stdout)
    
    def run_popf(self, domain_file: Path, problem_file: Path,
                 profile: str, timeout: int,
                 extra_args: Optional[List[str]] = None) -> Dict:
        """Run POPF planner."""
        bundle = self.prepare_planner_command("popf", domain_file, problem_file, profile, timeout, extra_args)
        cmd = bundle["cmd"]
        popf_build_dir = bundle["cwd"]
        env = bundle["env"]
        
        print(f"Running POPF with command: {self.format_command(cmd)}")
        
        start_time = time.time()
        try:
            result = self._run_subprocess(
                cmd,
                cwd=popf_build_dir,
                timeout=timeout,
                env=env,
            )
            
            runtime = time.time() - start_time
            
            plan_content = self._extract_popf_plan(result.stdout)
            plans = self._plans_from_text_block("popf", plan_content, "stdout")

            result_data = {
                "planner": "popf",
                "profile": profile,
                "success": result.returncode == 0 and bool(plan_content.strip()),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            return self._finalize_result_plans(result_data, plans)
            
        except subprocess.TimeoutExpired as exc:
            partial_stdout = self._decode_timeout_stream(exc.stdout or exc.output)
            plan_content = self._extract_popf_plan(partial_stdout)
            timeout_result = self._build_timeout_response(
                "popf", profile, timeout, start_time, exc, plan_content
            )
            return self._finalize_result_plans(timeout_result, self._plans_from_text_block("popf", plan_content, "stdout", is_partial=True))
    
    def _extract_popf_plan(self, stdout: str) -> str:
        """Extract plan from POPF output."""
        return self._extract_temporal_plan(stdout)
    
    def run_lpg(self, domain_file: Path, problem_file: Path,
                profile: str, timeout: int,
                extra_args: Optional[List[str]] = None) -> Dict:
        """Run LPG-td planner."""
        bundle = self.prepare_planner_command("lpg", domain_file, problem_file, profile, timeout, extra_args)
        cmd = bundle["cmd"]
        temp_dir = bundle["cwd"]

        print(f"Running LPG with command: {self.format_command(cmd)}")

        start_time = time.time()
        try:
            result = self._run_subprocess(
                cmd,
                cwd=temp_dir,
                timeout=timeout,
            )

            runtime = time.time() - start_time

            # LPG writes plan to plan_<problem_stem>_<n>.SOL in the working directory.
            # Also fall back to parsing stdout if no file is found.
            plan_content = self._collect_lpg_plan(Path(temp_dir), result.stdout)
            plans = self._plans_from_text_block("lpg", plan_content, "stdout") if plan_content else []

            result_data = {
                "planner": "lpg",
                "profile": profile,
                "success": result.returncode == 0 and bool(plan_content.strip()),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            return self._finalize_result_plans(result_data, plans)

        except subprocess.TimeoutExpired as exc:
            partial_stdout = self._decode_timeout_stream(exc.stdout or exc.output)
            plan_content = self._collect_lpg_plan(Path(temp_dir), partial_stdout)
            timeout_result = self._build_timeout_response(
                "lpg", profile, timeout, start_time, exc, plan_content
            )
            plans = self._plans_from_text_block("lpg", plan_content, "stdout", is_partial=True) if plan_content else []
            return self._finalize_result_plans(timeout_result, plans)

    def _collect_lpg_plan(self, work_dir: Path, stdout: str) -> str:
        """Collect LPG plan from .SOL file, falling back to stdout extraction."""
        # LPG names plan files plan_<problem_name>_<n>.SOL
        sol_files = sorted(work_dir.glob("plan_*_*.SOL"))
        if sol_files:
            # Return the last (best quality) solution
            try:
                return sol_files[-1].read_text(errors="replace").strip()
            except OSError:
                pass
        # Fall back: extract from stdout (LPG prints last solution to screen)
        return self._extract_lpg_plan(stdout)

    def _extract_lpg_plan(self, stdout: str) -> str:
        """Extract plan actions from LPG stdout."""
        lines = stdout.split('\n')
        plan_lines = []
        in_plan = False
        for line in lines:
            stripped = line.strip()
            lower = stripped.lower()
            if 'solution found' in lower or 'plan found' in lower:
                in_plan = True
                continue
            if in_plan:
                if not stripped or lower.startswith(';') or 'time' in lower and ':' not in stripped:
                    continue
                # Action lines typically look like: "0.00000: (action ...)" or "(action ...)"
                if '(' in stripped and ')' in stripped:
                    plan_lines.append(stripped)
                elif stripped.startswith('step') or (stripped and stripped[0].isdigit() and ':' in stripped):
                    plan_lines.append(stripped)
        return '\n'.join(plan_lines)

    def run_ff_variant(self, planner: str, domain_file: Path, problem_file: Path,
                      profile: str, timeout: int,
                      extra_args: Optional[List[str]] = None) -> Dict:
        """Run FF-based planners (ff-x, metric-ff, conformant-ff, etc.)."""
        bundle = self.prepare_planner_command(planner, domain_file, problem_file, profile, timeout, extra_args)
        cmd = bundle["cmd"]
        temp_dir = bundle["cwd"]
        
        print(f"Running {planner} with command: {self.format_command(cmd)}")
        
        start_time = time.time()
        try:
            result = self._run_subprocess(
                cmd,
                cwd=temp_dir,
                timeout=timeout,
            )
            
            runtime = time.time() - start_time
            
            # Extract plan from output (similar to FF)
            plan_content = self._extract_ff_plan(result.stdout)
            
            result_data = {
                "planner": planner,
                "profile": profile,
                "success": result.returncode == 0 and bool(plan_content),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            return self._finalize_result_plans(result_data, self._plans_from_text_block(planner, plan_content, "stdout"))
            
        except subprocess.TimeoutExpired as exc:
            partial_stdout = self._decode_timeout_stream(exc.stdout or exc.output)
            plan_content = self._extract_ff_plan(partial_stdout)
            timeout_result = self._build_timeout_response(
                planner, profile, timeout, start_time, exc, plan_content
            )
            return self._finalize_result_plans(timeout_result, self._plans_from_text_block(planner, plan_content, "stdout", is_partial=True))
    
    def run_powerlifted(self, domain_file: Path, problem_file: Path,
                       profile: str, timeout: int,
                       extra_args: Optional[List[str]] = None) -> Dict:
        """Run POWERLIFTED planner."""
        bundle = self.prepare_planner_command("powerlifted", domain_file, problem_file, profile, timeout, extra_args)
        cmd = bundle["cmd"]
        powerlifted_dir = bundle["cwd"]
        plan_file = bundle["plan_file"]
        
        print(f"Running POWERLIFTED with command: {self.format_command(cmd)}")
        
        start_time = time.time()
        try:
            result = self._run_subprocess(
                cmd,
                cwd=powerlifted_dir,
                timeout=timeout,
            )
            
            runtime = time.time() - start_time
            
            plans = self._plans_from_files("powerlifted", plan_file, "file", prefer_last_as_selected=True)
            if not plans:
                plan_content = self._extract_powerlifted_plan(result.stdout)
                plans = self._plans_from_text_block("powerlifted", plan_content, "stdout")
            else:
                plan_content = self._selected_plan_text(plans)
            success = result.returncode == 0 and len(plan_content.strip()) > 0
            
            result_data = {
                "planner": "powerlifted",
                "profile": profile,
                "success": success,
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            return self._finalize_result_plans(result_data, plans)
            
        except subprocess.TimeoutExpired as exc:
            partial_stdout = self._decode_timeout_stream(exc.stdout or exc.output)
            plans = self._plans_from_files("powerlifted", plan_file, "file", prefer_last_as_selected=True, is_partial=True)
            if not plans:
                plan_content = self._extract_powerlifted_plan(partial_stdout)
                plans = self._plans_from_text_block("powerlifted", plan_content, "stdout", is_partial=True)
            else:
                plan_content = self._selected_plan_text(plans)
            timeout_result = self._build_timeout_response(
                "powerlifted", profile, timeout, start_time, exc, plan_content
            )
            return self._finalize_result_plans(timeout_result, plans)
    
    def run_symk(self, domain_file: Path, problem_file: Path,
                profile: str, timeout: int,
                extra_args: Optional[List[str]] = None) -> Dict:
        """Run SYMK planner."""
        bundle = self.prepare_planner_command("symk", domain_file, problem_file, profile, timeout, extra_args)
        cmd = bundle["cmd"]
        symk_dir = bundle["cwd"]
        plan_file = Path(symk_dir) / "sas_plan"

        self._cleanup_plan_artifacts(plan_file)
        
        print(f"Running SYMK with command: {self.format_command(cmd)}")
        
        start_time = time.time()
        try:
            result = self._run_subprocess(
                cmd,
                cwd=symk_dir,
                timeout=timeout,
            )
            
            runtime = time.time() - start_time
            
            plans = self._plans_from_files("symk", plan_file, "file")
            if not plans:
                plan_content = self._extract_symk_plan(result.stdout)
                plans = self._plans_from_text_block("symk", plan_content, "stdout")
            else:
                plan_content = self._selected_plan_text(plans)
            success = result.returncode == 0 and len(plan_content.strip()) > 0
            
            result_data = {
                "planner": "symk",
                "profile": profile,
                "success": success,
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            finalized = self._finalize_result_plans(result_data, plans)
            self._cleanup_plan_artifacts(plan_file)
            return finalized
            
        except subprocess.TimeoutExpired as exc:
            partial_stdout = self._decode_timeout_stream(exc.stdout or exc.output)
            plans = self._plans_from_files("symk", plan_file, "file", is_partial=True)
            if not plans:
                plan_content = self._extract_symk_plan(partial_stdout)
                plans = self._plans_from_text_block("symk", plan_content, "stdout", is_partial=True)
            else:
                plan_content = self._selected_plan_text(plans)
            extra_note = "recovered plan from partial output" if plan_content.strip() else ""
            timeout_result = self._build_timeout_response(
                "symk", profile, timeout, start_time, exc, plan_content, extra_note
            )
            finalized = self._finalize_result_plans(timeout_result, plans)
            self._cleanup_plan_artifacts(plan_file)
            return finalized
    
    def _extract_powerlifted_plan(self, stdout: str) -> str:
        """Extract plan from POWERLIFTED output."""
        lines = stdout.split('\n')
        plan_lines = []
        in_plan = False
        
        for line in lines:
            line = line.strip()
            if "Solution found!" in line or "Plan found" in line:
                in_plan = True
                continue
            elif in_plan and line and not line.startswith(";") and "(" in line and ")" in line:
                plan_lines.append(line)
            elif in_plan and (line == "" or "Time" in line or "Solution" in line):
                break
        
        return '\n'.join(plan_lines)
    
    def _extract_symk_plan(self, stdout: str) -> str:
        """Extract plan from SYMK output."""
        lines = stdout.split('\n')
        plan_lines = []
        in_plan = False

        for raw_line in lines:
            line = raw_line.strip()
            lower_line = line.lower()

            if "best plan:" in lower_line:
                in_plan = True
                continue

            if in_plan:
                if (
                    "plan length:" in lower_line
                    or "plan cost:" in lower_line
                    or "peak memory:" in lower_line
                    or "search exit code:" in lower_line
                ):
                    break

                # SYMK often prefixes log lines with a timestamp like "[t=... ] ".
                if line.startswith("[t=") and "] " in line:
                    line = line.split("] ", 1)[1].strip()

                if line and not line.startswith(";") and "(" in line and ")" in line:
                    plan_lines.append(line)

        return '\n'.join(plan_lines)
    
    def analyze_domain(self, domain_path: str, verbose: bool = False) -> Dict:
        """
        Analyze a PDDL domain and return compatibility information.
        
        Args:
            domain_path: Path to the PDDL domain file
            verbose: Whether to include detailed information
            
        Returns:
            Dictionary with analysis results
        """
        return self.analyzer.analyze_domain(domain_path)
    
    def print_analysis(self, analysis: Dict, verbose: bool = False):
        """Print formatted analysis results."""
        self.analyzer.print_analysis(analysis, verbose)
    
    def get_recommended_planner(self, domain_path: str) -> Optional[str]:
        """
        Get the recommended planner for a domain.
        
        Args:
            domain_path: Path to the PDDL domain file
            
        Returns:
            Recommended planner name or None if no compatible planners
        """
        analysis = self.analyze_domain(domain_path)
        if analysis['analysis_summary']['recommended_planner']:
            return analysis['analysis_summary']['recommended_planner']['system_name']
        return None
    
    def auto_select_planner(self, domain_path: str, prefer_optimal: bool = True) -> Tuple[str, str]:
        """
        Automatically select the best planner and profile for a domain.
        
        Args:
            domain_path: Path to the PDDL domain file
            prefer_optimal: Whether to prefer optimal planners
            
        Returns:
            Tuple of (planner_name, profile) or raises exception if no compatible planners
        """
        analysis = self.analyze_domain(domain_path)
        compatible_planners = analysis['available_compatible_planners']
        relaxed_fallback = False

        if not compatible_planners:
            # Strict compatibility found nothing; try the relaxed set (only extreme
            # incompatibilities excluded) before giving up.
            relaxed = analysis.get('available_relaxed_planners', [])
            if relaxed:
                print(
                    "Warning: No strictly compatible planners found. "
                    "Falling back to planners with partial compatibility "
                    "(soft requirement mismatches only).",
                    file=sys.stderr,
                )
                compatible_planners = relaxed
                relaxed_fallback = True
            else:
                raise ValueError("No compatible planners available for this domain")
        
        # Filter by optimization preference if requested
        if prefer_optimal:
            optimal_planners = [
                (name, planner) for name, planner in compatible_planners
                if planner.optimization
            ]
            if optimal_planners:
                compatible_planners = optimal_planners
        
        # Select the highest ranked planner
        best_planner = compatible_planners[0]
        planner_name = best_planner[0]
        
        # Select appropriate profile based on planner
        if planner_name == 'downward':
            if prefer_optimal:
                profile = 'optimal-lmcut'  # Optimal
            else:
                profile = 'satisficing-ff'  # Satisficing
        elif planner_name == 'enhsp':
            if prefer_optimal:
                profile = 'opt-hrmax'
            else:
                profile = 'sat-hmrp'
        else:
            profile = None  # Use default profile
        
        return planner_name, profile


def main():
    """Main entry point."""
    
    # Get repository root first (needed for choices validation)
    repo_root = Path(__file__).parent.resolve()
    runner = PlannerRunner(str(repo_root))
    
    # Check for -- separator to extract planner-specific arguments
    extra_args = []
    argv = sys.argv[1:]
    if "--" in argv:
        separator_idx = argv.index("--")
        extra_args = argv[separator_idx + 1:]
        argv = argv[:separator_idx]
    
    parser = argparse.ArgumentParser(
        description="Unified PDDL Planner Runner - Flexible interface for multiple PDDL planners",
        formatter_class=argparse.RawDescriptionHelpFormatter,
                epilog=textwrap.dedent("""
                USAGE EXAMPLES:
                    # Basic usage with auto-selected planner
                    %(prog)s domain.pddl problem.pddl

                    # Specific planner with predefined profile
                    %(prog)s domain.pddl problem.pddl -p downward --profile optimal-lmcut
                    %(prog)s domain.pddl problem.pddl -p symk --profile topk-5

                    # With planner-specific arguments (after --)
                    %(prog)s domain.pddl problem.pddl -p optic -- -b
                    %(prog)s domain.pddl problem.pddl -p symk -- --plan-file output.plan

                    # Show available options
                    %(prog)s --list-planners
                    %(prog)s --list-profiles downward
                    %(prog)s --list-profiles symk

                    # Dry run (shows the exact command without executing)
                    %(prog)s domain.pddl problem.pddl -p ff --dry-run

                NOTES:
                    - Profile is optional (uses planner default if not specified)
                    - Pass-through arguments (after --) are sent directly to the planner
                    - Use --list-profiles to see available profiles for each planner
                    - Each planner's output is printed directly to terminal (passthrough mode)
                """)
    )
    
    parser.add_argument("domain", nargs="?",
                       help="Path to PDDL domain file")
    parser.add_argument("problem", nargs="?",
                       help="Path to PDDL problem file")
    
    parser.add_argument("-p", "--planner", 
                       choices=runner.get_available_planners(),
                       help="Planner to use (default: auto-selected based on domain requirements)")
    
    parser.add_argument("-P", "--profile", 
                       help="Planner profile name or planner-specific profile string (optional)")
    
    parser.add_argument("-t", "--timeout", type=int, default=300,
                       help="Timeout in seconds (default: 300)")
    
    parser.add_argument("-o", "--output",
                       help="Output file for results (JSON format, optional)")

    # Planner information options
    parser.add_argument("-l", "--list-planners", action="store_true",
                       help="List all available planners and exit")
    
    parser.add_argument("-L", "--list-profiles", metavar="PLANNER",
                       help="List available profiles for a specific planner")
    
    # Analysis options
    parser.add_argument("-a", "--analyze", action="store_true",
                       help="Analyze domain requirements and show compatible planners")
    
    parser.add_argument("-A", "--auto-planner", action="store_true",
                       help="Auto-select best planner based on domain requirements (default if no --planner)")
    
    parser.add_argument("-O", "--prefer-optimal", action="store_true", default=True,
                       help="Prefer optimal planners when auto-selecting (default)")
    
    parser.add_argument("-F", "--prefer-fast", dest="prefer_optimal", action="store_false",
                       help="Prefer fast (satisficing) planners when auto-selecting")
    
    # Execution options
    parser.add_argument("-d", "--dry-run", action="store_true",
                       help="Show the exact planner command without running it")
    
    parser.add_argument("-f", "--output-format", choices=["passthrough", "compact", "json"], 
                       default="passthrough",
                       help="Output format: passthrough (default), compact, or json")

    parser.add_argument("-q", "--no-live-output", action="store_true",
                       help="Disable live streaming of planner stdout/stderr while running")
    
    # Plan validation options (uses KCL-Planning's VAL submodule)
    parser.add_argument("-V", "--validate", action="store_true",
                       help="Validate the produced plan with VAL (requires VAL built: ./build_all.sh --planner val)")
    parser.add_argument("--val-epsilon", type=float, default=None,
                       help="Epsilon tolerance passed to VAL via -t (auto-set for temporal plans)")
    parser.add_argument("--val-verbose", action="store_true",
                       help="Pass -v to VAL for verbose plan-check reporting")
    parser.add_argument("--val-timeout", type=int, default=60,
                       help="Timeout in seconds for VAL validation (default: 60)")
    
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose domain analysis output")

    args = parser.parse_args(argv)
    runner.live_output = not args.no_live_output

    # In JSON output mode, route all human-readable wrapper output to stderr
    # so that stdout contains only the final JSON document.
    _original_stdout = sys.stdout
    if args.output_format == "json":
        sys.stdout = sys.stderr

    # Handle list commands
    if args.list_planners:
        if runner.spec:
            runner.spec.list_all_planners()
        else:
            print("Available planners:")
            for planner in runner.get_available_planners():
                print(f"  {planner}")
        return 0
    
    if args.list_profiles:
        planner_name = args.list_profiles
        if runner.spec and runner.spec.has_planner(planner_name):
            try:
                runner.spec.list_profiles(planner_name)
            except Exception as e:
                print(f"Error listing profiles: {e}", file=sys.stderr)
                return 1
        elif planner_name == "downward":
            print(f"\n{planner_name} - Available Profiles:\n")
            for profile, search in runner.fd_profiles.items():
                print(f"  {profile:25} {search}")
            print()
        elif planner_name == "enhsp":
            print(f"\n{planner_name} - Available Profiles:\n")
            for profile in runner.enhsp_profiles:
                print(f"  {profile}")
            print()
        else:
            print(f"No profiles found for planner: {planner_name}")
            print(f"Use --list-planners to see available planners")
        return 0
    
    # Validate required arguments for planner execution
    if not args.domain:
        parser.error("Domain file is required")
    
    # For analysis mode, only domain is required
    if args.analyze and not args.problem:
        try:
            analysis = runner.analyze_domain(args.domain)
            runner.print_analysis(analysis, args.verbose)
            return 0
        except Exception as e:
            print(f"Error analyzing domain: {e}", file=sys.stderr)
            return 1
    
    # For planner execution, both domain and problem are required
    if not args.problem:
        parser.error("Problem file is required for planner execution")
    
    try:
        # Validate inputs
        domain_file, problem_file = runner.validate_inputs(args.domain, args.problem)
        
        # Perform domain analysis if requested or if auto-selecting planner
        analysis = None
        if args.analyze or args.auto_planner or not args.planner:
            print("Analyzing domain requirements...")
            analysis = runner.analyze_domain(str(domain_file))
            
            if args.analyze:
                runner.print_analysis(analysis, args.verbose)
                if not args.planner:
                    return 0
        
        # Auto-select planner if not specified or if requested
        planner = args.planner
        profile = args.profile
        
        if args.auto_planner or not planner:
            try:
                planner, auto_profile = runner.auto_select_planner(
                    str(domain_file), 
                    prefer_optimal=args.prefer_optimal
                )
                if not profile:  # Only use auto-profile if user didn't specify one
                    profile = auto_profile
                
                print(f"\nAuto-selected planner: {planner}")
                if profile:
                    print(f"Auto-selected profile: {profile}")
                    
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1

        profile = runner.resolve_profile(planner, profile)
        
        print(f"\nDomain: {domain_file}")
        print(f"Problem: {problem_file}")
        print(f"Planner: {planner}")
        print(f"Profile: {profile or 'default'}")
        print(f"Timeout: {args.timeout}s")
        print("-" * 50)
        
        # Print execution header
        auto_selected = args.auto_planner or (not args.planner)
        runner.print_execution_header(
            domain_file, problem_file, planner, profile, 
            args.timeout, auto_selected, extra_args
        )
        
        # Show command for dry-run
        if args.dry_run:
            bundle = runner.prepare_planner_command(
                planner, domain_file, problem_file, profile, args.timeout, extra_args
            )
            print("Exact command:")
            print(f"  {runner.format_command(bundle['cmd'])}")
            print(f"Working directory: {bundle['cwd']}")
            if bundle.get("env") and bundle["env"].get("LD_LIBRARY_PATH"):
                print(f"LD_LIBRARY_PATH: {bundle['env']['LD_LIBRARY_PATH']}")
            print("(Dry-run mode: not executing)")
            return 0
        
        # Run planner with extra arguments
        result = runner.run_planner(
            planner, domain_file, problem_file, 
            profile, args.timeout, extra_args
        )

        # Optional plan validation with VAL
        validation = None
        if args.validate:
            validation = runner.validate_plan_with_val(
                domain_file,
                problem_file,
                result.get("plan", "") or "",
                timeout=args.val_timeout,
                epsilon=args.val_epsilon,
                val_verbose=args.val_verbose,
            )
            result["validation"] = validation
        
        # Default behavior: passthrough output mode
        # In live-output mode, planner stdout/stderr has already been streamed.
        # Only print captured output when live streaming is disabled.
        if args.output_format == "passthrough":
            if not runner.live_output and result['stdout']:
                print(result['stdout'])
            if not runner.live_output and result['stderr']:
                print(result['stderr'], file=sys.stderr)
            if validation is not None:
                runner.print_validation_report(validation)
        
        # Additional formats for optional processing
        elif args.output_format == "compact":
            if result.get('plans'):
                if result.get('plan_count', 0) == 1:
                    print("\nPlan:")
                    print(result['plan'])
                else:
                    print(f"\nExtracted {result['plan_count']} plans:")
                    for plan in result['plans']:
                        selected_marker = " [selected]" if plan.get('is_selected') else ""
                        source_name = f", {plan['source_name']}" if plan.get('source_name') else ""
                        print(f"\nPlan {plan['rank']}{selected_marker} ({plan['format']}, {plan['source']}{source_name})")
                        print(plan['text'])
            if validation is not None:
                runner.print_validation_report(validation)
        
        elif args.output_format == "json":
            output_data = {
                "planner": result["planner"],
                "profile": result["profile"],
                "success": result["success"],
                "runtime": result["runtime"],
                "plan": result["plan"],
                "plans": result.get("plans", []),
                "plan_count": result.get("plan_count", 0),
                "selected_plan_rank": result.get("selected_plan_rank"),
                "return_code": result["return_code"]
            }
            if validation is not None:
                output_data["validation"] = validation
            print(json.dumps(output_data, indent=2), file=_original_stdout)
        
        # Save full results to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nFull results saved to: {args.output}")
        
        return 0 if result['success'] else 1
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    finally:
        # Cleanup
        runner.cleanup_temp_dir()


if __name__ == "__main__":
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    try:
        sys.exit(main())
    except BrokenPipeError:
        # Graceful exit when output is piped and consumer closes early.
        with suppress(Exception):
            sys.stdout.close()
        sys.exit(141)