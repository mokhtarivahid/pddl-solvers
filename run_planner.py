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
import tempfile
import shutil
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class PlannerRunner:
    """Unified runner for multiple PDDL planners."""
    
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.planners_dir = self.repo_root / "planners"
        self.temp_dir = None
        
        # Fast Downward search configurations
        self.fd_configs = {
            "astar-lmcut": "astar(lmcut())",
            "astar-ff": "astar(ff())",
            "astar-cegar": "astar(cegar())",
            "lazy-greedy-ff": "lazy_greedy([ff()], preferred=[ff()])",
            "lazy-greedy-lmcut": "lazy_greedy([lmcut()])",
            "ehc-ff": "ehc(ff())",
            "seq-sat-lama": "seq-sat-lama-2011",  # Uses alias
            "seq-opt-lama": "seq-opt-lmcut-one",  # Uses alias
            "wa-star-ff": "lazy_wastar([ff()], w=3)",
            "gbfs-ff": "lazy_greedy([ff()], preferred=[ff()])"
        }
        
        # ENHSP search configurations
        self.enhsp_configs = {
            "sat-hmrp": "sat-hmrp", 
            "opt-hrmax": "opt-hrmax",
            "gbfs-hadd": "gbfs -h hadd",
            "wastar-hadd": "WAStar -h hadd",
            "astar-hadd": "WAStar -h hadd -wh 1.0"
        }
    
    def setup_temp_dir(self) -> Path:
        """Create temporary directory for planner intermediate files."""
        if self.temp_dir is None:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="pddl_planner_"))
        return self.temp_dir
    
    def cleanup_temp_dir(self):
        """Clean up temporary directory."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
    
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
            "contingent-ff", "probabilistic-ff", "madagascar"
        ]
        
        for planner in source_planners:
            planner_path = self.planners_dir / planner
            if planner_path.exists():
                planners.append(planner)
        
        return sorted(planners)
    
    def run_downward(self, domain_file: Path, problem_file: Path, 
                    config: str = "astar-lmcut", timeout: int = 300) -> Dict:
        """Run Fast Downward planner."""
        downward_dir = self.planners_dir / "downward"
        downward_script = downward_dir / "fast-downward.py"
        
        if not downward_script.exists():
            raise FileNotFoundError(f"Fast Downward not found at {downward_script}")
        
        # Set up search configuration
        search_config = self.fd_configs.get(config, config)
        
        cmd = [
            str(downward_script),
            str(domain_file),
            str(problem_file)
        ]
        
        # Add search configuration
        if config in ["seq-sat-lama", "seq-opt-lama"]:
            cmd.extend(["--alias", search_config])
        else:
            cmd.extend(["--search", search_config])
        
        # Fast Downward outputs to sas_plan by default
        # We'll read that file after execution
        
        print(f"Running Fast Downward with command: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd, 
                cwd=str(downward_dir),
                capture_output=True, 
                text=True, 
                timeout=timeout + 30
            )
            
            runtime = time.time() - start_time
            
            # Check if plan was found (look in current working directory for sas_plan)
            plan_content = ""
            sas_plan_file = Path(downward_dir) / "sas_plan"
            if sas_plan_file.exists():
                with open(sas_plan_file, 'r') as f:
                    plan_content = f.read().strip()
                # Remove the plan file to avoid conflicts
                sas_plan_file.unlink()
            
            return {
                "planner": "downward",
                "config": config,
                "success": result.returncode == 0 and bool(plan_content),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "planner": "downward",
                "config": config,
                "success": False,
                "runtime": timeout,
                "plan": "",
                "stdout": "",
                "stderr": "Timeout expired",
                "return_code": -1
            }
    
    def run_enhsp(self, domain_file: Path, problem_file: Path, 
                  config: str = "sat-hmrp", timeout: int = 300) -> Dict:
        """Run ENHSP planner."""
        enhsp_dir = self.planners_dir / "enhsp"
        enhsp_jar = enhsp_dir / "enhsp.jar"
        
        if not enhsp_jar.exists():
            raise FileNotFoundError(f"ENHSP JAR not found at {enhsp_jar}")
        
        # Set up command
        cmd = [
            "java", "-jar", str(enhsp_jar),
            "-o", str(domain_file),
            "-f", str(problem_file),
            "-timeout", str(timeout)
        ]
        
        # Add planner configuration
        if config in self.enhsp_configs:
            if config in ["sat-hmrp", "opt-hrmax"]:
                cmd.extend(["-planner", config])
            else:
                # Parse manual config (e.g., "gbfs -h hadd")
                parts = self.enhsp_configs[config].split()
                for part in parts:
                    cmd.append(part)
        
        # Set plan output
        temp_dir = self.setup_temp_dir()
        plan_file = temp_dir / "enhsp_plan.txt"
        cmd.extend(["-sp", str(plan_file)])
        
        print(f"Running ENHSP with command: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=str(enhsp_dir),
                capture_output=True,
                text=True,
                timeout=timeout + 30
            )
            
            runtime = time.time() - start_time
            
            # Check if plan was found
            plan_content = ""
            if plan_file.exists():
                with open(plan_file, 'r') as f:
                    plan_content = f.read().strip()
            
            return {
                "planner": "enhsp",
                "config": config,
                "success": result.returncode == 0 and bool(plan_content),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "planner": "enhsp",
                "config": config,
                "success": False,
                "runtime": timeout,
                "plan": "",
                "stdout": "",
                "stderr": "Timeout expired",
                "return_code": -1
            }
    
    def run_ff(self, domain_file: Path, problem_file: Path, 
               config: str = "default", timeout: int = 300) -> Dict:
        """Run FF planner."""
        ff_dir = self.planners_dir / "ff"
        ff_executable = ff_dir / "ff"
        
        if not ff_executable.exists():
            raise FileNotFoundError(f"FF executable not found at {ff_executable}")
        
        # FF uses a special format - needs domain and problem in same directory
        temp_dir = self.setup_temp_dir()
        temp_domain = temp_dir / "domain.pddl"
        temp_problem = temp_dir / "problem.pddl"
        
        # Copy files to temp directory
        shutil.copy2(domain_file, temp_domain)
        shutil.copy2(problem_file, temp_problem)
        
        cmd = [
            str(ff_executable),
            "-p", str(temp_dir) + "/",
            "-o", "domain.pddl",
            "-f", "problem.pddl"
        ]
        
        print(f"Running FF with command: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=str(temp_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            runtime = time.time() - start_time
            
            # FF outputs plan directly to stdout
            plan_content = self._extract_ff_plan(result.stdout)
            
            return {
                "planner": "ff", 
                "config": config,
                "success": result.returncode == 0 and bool(plan_content),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "planner": "ff",
                "config": config,
                "success": False,
                "runtime": timeout,
                "plan": "",
                "stdout": "",
                "stderr": "Timeout expired",
                "return_code": -1
            }
    
    def _extract_ff_plan(self, stdout: str) -> str:
        """Extract plan from FF output."""
        lines = stdout.split('\n')
        in_plan = False
        plan_lines = []
        
        for line in lines:
            if "found legal plan as follows" in line.lower():
                in_plan = True
                continue
            elif in_plan:
                if line.strip() and not line.startswith("time spent:"):
                    if line.strip() != "":
                        plan_lines.append(line.strip())
                elif line.startswith("time spent:"):
                    break
        
        return '\n'.join(plan_lines)
    
    def run_planner(self, planner: str, domain_file: Path, problem_file: Path,
                    config: str = None, timeout: int = 300) -> Dict:
        """Run specified planner with given configuration."""
        
        # Set default configs
        if config is None:
            if planner == "downward":
                config = "astar-lmcut"
            elif planner == "enhsp":
                config = "sat-hmrp"
            else:
                config = "default"
        
        if planner == "downward":
            return self.run_downward(domain_file, problem_file, config, timeout)
        elif planner == "enhsp":
            return self.run_enhsp(domain_file, problem_file, config, timeout)
        elif planner == "ff":
            return self.run_ff(domain_file, problem_file, config, timeout)
        else:
            # For other planners, provide basic interface
            return self.run_generic_planner(planner, domain_file, problem_file, config, timeout)
    
    def run_generic_planner(self, planner: str, domain_file: Path, problem_file: Path,
                           config: str, timeout: int) -> Dict:
        """Run a generic planner with basic PDDL interface."""
        planner_dir = self.planners_dir / planner
        
        # Handle specific planner cases
        if planner == "madagascar":
            return self.run_madagascar(domain_file, problem_file, config, timeout)
        elif planner == "vhpop":
            return self.run_vhpop(domain_file, problem_file, config, timeout)
        elif planner == "tfd":
            return self.run_tfd(domain_file, problem_file, config, timeout)
        elif planner == "optic":
            return self.run_optic(domain_file, problem_file, config, timeout)
        elif planner == "popf":
            return self.run_popf(domain_file, problem_file, config, timeout)
        elif planner == "powerlifted":
            return self.run_powerlifted(domain_file, problem_file, config, timeout)
        elif planner == "symk":
            return self.run_symk(domain_file, problem_file, config, timeout)
        elif planner in ["ff-x", "metric-ff", "conformant-ff", "contingent-ff", "probabilistic-ff"]:
            return self.run_ff_variant(planner, domain_file, problem_file, config, timeout)
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
            
            print(f"Running {planner} with command: {' '.join(cmd)}")
            
            start_time = time.time()
            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(executable.parent),  # Use executable's directory as cwd
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                runtime = time.time() - start_time
                
                return {
                    "planner": planner,
                    "config": config,
                    "success": result.returncode == 0,
                    "runtime": runtime,
                    "plan": result.stdout,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
                
            except subprocess.TimeoutExpired:
                return {
                    "planner": planner,
                    "config": config,
                    "success": False,
                    "runtime": timeout,
                    "plan": "",
                    "stdout": "",
                    "stderr": "Timeout expired",
                    "return_code": -1
                }
    
    def run_madagascar(self, domain_file: Path, problem_file: Path, 
                      config: str, timeout: int) -> Dict:
        """Run MADAGASCAR SAT-based planner."""
        madagascar_dir = self.planners_dir / "madagascar"
        madagascar_exe = madagascar_dir / "Mp"
        
        if not madagascar_exe.exists():
            raise FileNotFoundError(f"MADAGASCAR executable not found at {madagascar_exe}")
        
        cmd = [str(madagascar_exe), str(domain_file), str(problem_file)]
        
        print(f"Running MADAGASCAR with command: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=str(madagascar_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            runtime = time.time() - start_time
            
            # MADAGASCAR outputs plan to stdout
            plan_content = result.stdout
            
            return {
                "planner": "madagascar",
                "config": config,
                "success": result.returncode == 0 and bool(plan_content.strip()),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "planner": "madagascar",
                "config": config,
                "success": False,
                "runtime": timeout,
                "plan": "",
                "stdout": "",
                "stderr": "Timeout expired",
                "return_code": -1
            }
    
    def run_vhpop(self, domain_file: Path, problem_file: Path,
                  config: str, timeout: int) -> Dict:
        """Run VHPOP planner."""
        vhpop_dir = self.planners_dir / "vhpop"
        vhpop_exe = vhpop_dir / "vhpop"
        
        # Try alternative executable name
        if not vhpop_exe.exists():
            vhpop_exe = vhpop_dir / "ipc3-vhpop"
        
        if not vhpop_exe.exists():
            raise FileNotFoundError(f"VHPOP executable not found")
        
        cmd = [str(vhpop_exe), str(domain_file), str(problem_file)]
        
        print(f"Running VHPOP with command: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=str(vhpop_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            runtime = time.time() - start_time
            
            # VHPOP outputs plan to stdout
            plan_content = result.stdout
            
            return {
                "planner": "vhpop",
                "config": config,
                "success": result.returncode == 0 and bool(plan_content.strip()),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "planner": "vhpop",
                "config": config,
                "success": False,
                "runtime": timeout,
                "plan": "",
                "stdout": "",
                "stderr": "Timeout expired", 
                "return_code": -1
            }
    
    def run_tfd(self, domain_file: Path, problem_file: Path,
                config: str, timeout: int) -> Dict:
        """Run Temporal Fast Downward planner."""
        tfd_dir = self.planners_dir / "tfd"
        tfd_exe = tfd_dir / "downward" / "tfd"
        
        if not tfd_exe.exists():
            raise FileNotFoundError(f"TFD executable not found at {tfd_exe}")
        
        cmd = [str(tfd_exe), str(domain_file), str(problem_file)]
        
        print(f"Running TFD with command: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=str(tfd_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            runtime = time.time() - start_time
            
            # TFD outputs plan to stdout or file
            plan_content = result.stdout
            
            return {
                "planner": "tfd",
                "config": config,
                "success": result.returncode == 0 and bool(plan_content.strip()),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "planner": "tfd",
                "config": config,
                "success": False,
                "runtime": timeout,
                "plan": "",
                "stdout": "",
                "stderr": "Timeout expired",
                "return_code": -1
            }
    
    def run_optic(self, domain_file: Path, problem_file: Path,
                  config: str, timeout: int) -> Dict:
        """Run OPTIC planner."""
        optic_dir = self.planners_dir / "optic"
        optic_exe = optic_dir / "build" / "src" / "optic" / "optic-clp"
        
        if not optic_exe.exists():
            raise FileNotFoundError(f"OPTIC executable not found at {optic_exe}")
        
        cmd = [str(optic_exe), str(domain_file), str(problem_file)]
        
        print(f"Running OPTIC with command: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=str(optic_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            runtime = time.time() - start_time
            
            # OPTIC outputs plan to stdout
            plan_content = self._extract_optic_plan(result.stdout)
            
            return {
                "planner": "optic",
                "config": config,
                "success": result.returncode == 0 and bool(plan_content.strip()),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "planner": "optic",
                "config": config,
                "success": False,
                "runtime": timeout,
                "plan": "",
                "stdout": "",
                "stderr": "Timeout expired",
                "return_code": -1
            }
    
    def _extract_optic_plan(self, stdout: str) -> str:
        """Extract plan from OPTIC output."""
        lines = stdout.split('\n')
        plan_lines = []
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('(') or ':' in line) and not line.startswith(';'):
                # Filter out comments and extract action lines
                plan_lines.append(line)
        
        return '\n'.join(plan_lines)
    
    def run_popf(self, domain_file: Path, problem_file: Path,
                 config: str, timeout: int) -> Dict:
        """Run POPF planner."""
        popf_dir = self.planners_dir / "popf"
        popf_exe = popf_dir / "build" / "popf"
        
        if not popf_exe.exists():
            raise FileNotFoundError(f"POPF executable not found at {popf_exe}")
        
        cmd = [str(popf_exe), str(domain_file), str(problem_file)]
        
        print(f"Running POPF with command: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=str(popf_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            runtime = time.time() - start_time
            
            # POPF outputs plan to stdout
            plan_content = self._extract_popf_plan(result.stdout)
            
            return {
                "planner": "popf",
                "config": config,
                "success": result.returncode == 0 and bool(plan_content.strip()),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "planner": "popf",
                "config": config,
                "success": False,
                "runtime": timeout,
                "plan": "",
                "stdout": "",
                "stderr": "Timeout expired",
                "return_code": -1
            }
    
    def _extract_popf_plan(self, stdout: str) -> str:
        """Extract plan from POPF output."""
        lines = stdout.split('\n')
        plan_lines = []
        
        for line in lines:
            line = line.strip()
            if line and line.startswith('(') and ')' in line and not line.startswith(';'):
                # Filter out comments and extract action lines
                plan_lines.append(line)
        
        return '\n'.join(plan_lines)
    
    def run_ff_variant(self, planner: str, domain_file: Path, problem_file: Path,
                      config: str, timeout: int) -> Dict:
        """Run FF-based planners (ff-x, metric-ff, conformant-ff, etc.)."""
        planner_dir = self.planners_dir / planner
        
        # Look for compiled executable
        possible_exes = [planner.replace('-', ''), planner, "ff"]
        executable = None
        
        for exe_name in possible_exes:
            exe_path = planner_dir / exe_name
            if exe_path.exists() and exe_path.is_file():
                # Check if it's executable
                import stat
                if exe_path.stat().st_mode & stat.S_IEXEC:
                    executable = exe_path
                    break
        
        if executable is None:
            raise FileNotFoundError(f"No executable found for {planner}")
        
        # FF-based planners need files in same directory
        temp_dir = self.setup_temp_dir()
        temp_domain = temp_dir / "domain.pddl"
        temp_problem = temp_dir / "problem.pddl"
        
        # Copy files to temp directory
        shutil.copy2(domain_file, temp_domain)
        shutil.copy2(problem_file, temp_problem)
        
        cmd = [
            str(executable),
            "-p", str(temp_dir) + "/",
            "-o", "domain.pddl",
            "-f", "problem.pddl"
        ]
        
        print(f"Running {planner} with command: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=str(temp_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            runtime = time.time() - start_time
            
            # Extract plan from output (similar to FF)
            plan_content = self._extract_ff_plan(result.stdout)
            
            return {
                "planner": planner,
                "config": config,
                "success": result.returncode == 0 and bool(plan_content),
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "planner": planner,
                "config": config,
                "success": False,
                "runtime": timeout,
                "plan": "",
                "stdout": "",
                "stderr": "Timeout expired",
                "return_code": -1
            }
    
    def run_powerlifted(self, domain_file: Path, problem_file: Path,
                       config: str, timeout: int) -> Dict:
        """Run POWERLIFTED planner."""
        powerlifted_dir = self.planners_dir / "powerlifted"
        powerlifted_exe = powerlifted_dir / "powerlifted.py"
        
        if not powerlifted_exe.exists():
            raise FileNotFoundError(f"POWERLIFTED executable not found at {powerlifted_exe}")
        
        cmd = [
            "python3", str(powerlifted_exe),
            "-d", str(domain_file),
            "-i", str(problem_file)
        ]
        
        # Add search algorithm based on config
        if config == "bfws1":
            cmd.extend(["-s", "bfws1"])
        elif config == "bfws2":
            cmd.extend(["-s", "bfws2"])
        elif config == "astar":
            cmd.extend(["-s", "astar"])
        else:
            cmd.extend(["-s", "bfws1"])  # Default search
        
        print(f"Running POWERLIFTED with command: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=str(powerlifted_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            runtime = time.time() - start_time
            
            plan_content = self._extract_powerlifted_plan(result.stdout)
            success = result.returncode == 0 and len(plan_content.strip()) > 0
            
            return {
                "planner": "powerlifted",
                "config": config,
                "success": success,
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "planner": "powerlifted",
                "config": config,
                "success": False,
                "runtime": timeout,
                "plan": "",
                "stdout": "",
                "stderr": "Timeout expired",
                "return_code": -1
            }
    
    def run_symk(self, domain_file: Path, problem_file: Path,
                config: str, timeout: int) -> Dict:
        """Run SYMK planner."""
        symk_dir = self.planners_dir / "symk"
        symk_exe = symk_dir / "fast-downward.py"
        
        if not symk_exe.exists():
            raise FileNotFoundError(f"SYMK executable not found at {symk_exe}")
        
        # SYMK search configurations similar to Fast Downward
        symk_configs = {
            "astar-lmcut": "astar(lmcut())",
            "astar-ff": "astar(ff())",
            "lazy-greedy-ff": "lazy_greedy([ff()], preferred=[ff()])",
            "lazy-greedy-lmcut": "lazy_greedy([lmcut()])",
            "gbfs-ff": "lazy_greedy([ff()], preferred=[ff()])",
            "default": "astar(lmcut())"  # Default to optimal search
        }
        
        search_config = symk_configs.get(config, symk_configs["default"])
        
        cmd = [
            "python3", str(symk_exe),
            str(domain_file), str(problem_file),
            "--search", search_config
        ]
        
        print(f"Running SYMK with command: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=str(symk_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            runtime = time.time() - start_time
            
            plan_content = self._extract_symk_plan(result.stdout)
            success = result.returncode == 0 and len(plan_content.strip()) > 0
            
            return {
                "planner": "symk",
                "config": config,
                "success": success,
                "runtime": runtime,
                "plan": plan_content,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "planner": "symk",
                "config": config,
                "success": False,
                "runtime": timeout,
                "plan": "",
                "stdout": "",
                "stderr": "Timeout expired",
                "return_code": -1
            }
    
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
        """Extract plan from SYMK output (similar to Fast Downward)."""
        lines = stdout.split('\n')
        plan_lines = []
        in_plan = False
        
        for line in lines:
            line = line.strip()
            if line.startswith("Solution found!") or line == "Solution found.":
                in_plan = True
                continue
            elif in_plan and line and not line.startswith(";") and "(" in line:
                plan_lines.append(line)
            elif in_plan and line == "":
                break
        
        return '\n'.join(plan_lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified PDDL Planner Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -d domain.pddl -p problem.pddl --planner downward
  %(prog)s -d domain.pddl -p problem.pddl --planner enhsp --config sat-hmrp
  %(prog)s -d domain.pddl -p problem.pddl --planner ff
  %(prog)s -d domain.pddl -p problem.pddl --planner downward --config astar-ff --timeout 600

Fast Downward configurations:
  astar-lmcut, astar-ff, astar-cegar, lazy-greedy-ff, lazy-greedy-lmcut,
  ehc-ff, seq-sat-lama, seq-opt-lama, wa-star-ff, gbfs-ff

ENHSP configurations:
  sat-hmrp, opt-hrmax, gbfs-hadd, wastar-hadd, astar-hadd
        """
    )
    
    # Get repository root
    repo_root = Path(__file__).parent.resolve()
    runner = PlannerRunner(str(repo_root))
    
    parser.add_argument("-d", "--domain",
                       help="Path to PDDL domain file")
    parser.add_argument("-p", "--problem",
                       help="Path to PDDL problem file")
    parser.add_argument("--planner", default="downward",
                       choices=runner.get_available_planners(),
                       help="Planner to use (default: downward)")
    parser.add_argument("--config", 
                       help="Planner configuration/algorithm (see examples)")
    parser.add_argument("--timeout", type=int, default=300,
                       help="Timeout in seconds (default: 300)")
    parser.add_argument("--output", "-o",
                       help="Output file for results (JSON format)")
    parser.add_argument("--list-planners", action="store_true",
                       help="List available planners and exit")
    parser.add_argument("--list-configs", 
                       help="List available configurations for specified planner")
    
    args = parser.parse_args()
    
    # Handle list commands
    if args.list_planners:
        print("Available planners:")
        for planner in runner.get_available_planners():
            print(f"  {planner}")
        return 0
    
    if args.list_configs:
        if args.list_configs == "downward":
            print("Fast Downward configurations:")
            for config in runner.fd_configs:
                print(f"  {config}: {runner.fd_configs[config]}")
        elif args.list_configs == "enhsp":
            print("ENHSP configurations:")
            for config in runner.enhsp_configs:
                print(f"  {config}")
        else:
            print(f"No specific configurations defined for {args.list_configs}")
        return 0
    
    # Validate required arguments for main operation
    if not args.domain or not args.problem:
        parser.error("Domain (-d/--domain) and problem (-p/--problem) files are required for planner execution")
    
    try:
        # Validate inputs
        domain_file, problem_file = runner.validate_inputs(args.domain, args.problem)
        
        print(f"Domain: {domain_file}")
        print(f"Problem: {problem_file}")
        print(f"Planner: {args.planner}")
        print(f"Config: {args.config or 'default'}")
        print(f"Timeout: {args.timeout}s")
        print("-" * 50)
        
        # Run planner
        result = runner.run_planner(
            args.planner, domain_file, problem_file, 
            args.config, args.timeout
        )
        
        # Print results
        print(f"\nResults:")
        print(f"Success: {result['success']}")
        print(f"Runtime: {result['runtime']:.2f}s")
        if result['plan']:
            print(f"Plan found with {len(result['plan'].split('\n'))} steps")
        else:
            print("No plan found")
        
        if result['success'] and result['plan']:
            print(f"\nPlan:")
            print(result['plan'])
        
        if result['stderr']:
            print(f"\nErrors/Warnings:")
            print(result['stderr'])
        
        # Save to file if requested
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
    sys.exit(main())