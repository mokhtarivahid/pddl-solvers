# PDDL Solvers Collection

A comprehensive collection of Planning Domain Definition Language (PDDL) planners and solvers for easy access and compilation.

## Overview

This repository provides a curated collection of state-of-the-art PDDL planners, each specialized for different types of planning problems. All planners are included as Git submodules in the `planners/` directory.

## Curated PDDL Planners & Solvers Reference

| Category | Planner Name | GitHub Link | Best For... |
| --- | --- | --- | --- |
| **Classical** | **Fast-Downward** | [aibasel/downward](https://github.com/aibasel/downward) | The industry and research "gold standard" for discrete, deterministic planning. |
| **Classical (Legacy)** | **FF** | [FF-v2.3](https://fai.cs.uni-saarland.de/hoffmann/ff.html) | Fast forward chaining heuristic search; foundational classical planner with excellent performance on STRIPS domains. |
| **Classical (ADL)** | **FF-X** | [FF-X](https://fai.cs.uni-saarland.de/hoffmann/ff.html) | Extension of FF handling PDDL 2.1 derived predicates (axioms) for complex logical planning. |
| **Temporal/Numeric (PDDL 2.2)** | **LPG-td** | [LPG](https://lpg.ing.unibs.it/) | Local search on planning graphs; IPC 3 & 4 award winner; supports PDDL 2.2 (durative actions, numeric fluents, timed initial literals, derived predicates). |
| **Optimal/Top-K** | **SymK** | [speckdavid/symk](https://github.com/speckdavid/symk) | Finding optimal plans or a set of diverse "top-k" alternatives using symbolic search. |
| **Numeric** | **ENHSP** | [hstairs/enhsp](https://github.com/hstairs/enhsp) | Advanced numeric planning, including non-linear effects and global constraints. |
| **Numeric (Legacy)** | **Metric-FF** | [Metric-FF](https://fai.cs.uni-saarland.de/hoffmann/metric-ff.html) | Extension of FF to numerical state variables; top performer in PDDL 2.1 level 2 numeric planning. |
| **Temporal** | **OPTIC** | [KavrakiLab/optic](https://github.com/KavrakiLab/optic) | Temporal planning that requires reasoning over continuous numeric fluents and durative actions. |
| **Lifted** | **PowerLifted** | [abcorrea/powerlifted](https://github.com/abcorrea/powerlifted) | Problems with massive object counts where grounding the domain would consume too much memory. |
| **Temporal (PO)** | **POPF** | [fmrico/popf](https://github.com/fmrico/popf) | Partial Order Planning; excellent for durative actions and widely integrated into ROS 2 (PlanSys2). |
| **Expressive Hybrid** | **NextFLAP** | [ossaver/NextFLAP](https://github.com/ossaver/NextFLAP) | Handling complex numeric structures, non-linear conditions, and disjunctive preconditions. |
| **Temporal (Heuristic)** | **Temporal Fast Downward** | [neighthan/tfd](https://github.com/neighthan/tfd) | Bridging the Fast Downward heuristic approach with temporal state space search. |
| **Partial Order** | **VHPOP** | [hlsyounes/vhpop](https://github.com/hlsyounes/vhpop) | Versatile heuristic partial order planner with ground/lifted actions, multiple search algorithms (A*, IDA*, hill climbing), and flexible flaw selection strategies. |
| **SAT-based** | **MADAGASCAR** | [MADAGASCAR](https://users.aalto.fi/~rintanj1/satplan.html) | Efficient SAT-based planner with variants M, Mp, MpC; placed 2nd and 3rd in 2014 competition agile track, component of 1st/2nd place portfolio planners. |
| **Conformant** | **Conformant-FF** | [Conformant-FF](https://fai.cs.uni-saarland.de/hoffmann/cff.html) | Planning under initial state uncertainty using CNF formulas; handles incomplete initial knowledge. |
| **Contingent** | **Contingent-FF** | [Contingent-FF](https://fai.cs.uni-saarland.de/hoffmann/cff.html) | Partial observability planning; generates tree-shaped plans with observation branches. |  
| **Probabilistic** | **Probabilistic-FF** | [Probabilistic-FF](https://fai.cs.uni-saarland.de/hoffmann/cff.html) | Probabilistic planning with Bayesian initial states and stochastic action effects. |
| **Partial Order** | **VHPOP** | [hlsyounes/vhpop](https://github.com/hlsyounes/vhpop) | Versatile heuristic partial order planner with ground/lifted actions, multiple search algorithms (A*, IDA*, hill climbing), and flexible flaw selection strategies. |

## System Requirements & Dependencies

Before building the planners, ensure your system has all required dependencies installed:

### Core Build Tools
- **C/C++ Compiler**: GCC 9+ or Clang 12+ (required for C++20 support)
- **Build Systems**: Make, CMake 3.16+, Autotools (autoconf, automake, libtool)
- **Version Control**: Git
- **Parser Generators**: Flex 2.6+, Bison 3.0+

### Language Runtimes
- **Python**: 3.8+ (with python3-dev for headers)
- **Java**: JDK 11+ (OpenJDK recommended)

### Scientific Libraries
- **GSL**: GNU Scientific Library (required for OPTIC planner)
- **Linear Algebra**: BLAS, LAPACK (for numeric planners)
- **LP Solvers**: CLP, CBC (for optimization planners)

### Installation (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Essential build tools and compilers
sudo apt install -y build-essential cmake git autoconf automake libtool

# Parser generators and development tools
sudo apt install -y flex bison pkg-config

# Python development (ensure both python3 and python symlink)
sudo apt install -y python3 python3-pip python3-dev
sudo ln -sf /usr/bin/python3 /usr/bin/python  # For planners requiring 'python'

# Java development kit
sudo apt install -y openjdk-11-jdk

# Scientific and optimization libraries
sudo apt install -y libgsl-dev libblas-dev liblapack-dev
sudo apt install -y coinor-libclp-dev coinor-libcbc-dev coinor-libcgl-dev coinor-libosi-dev coinor-libcoinutils-dev

# Additional system libraries
sudo apt install -y libboost-all-dev zlib1g-dev
```

### Optional Dependencies
Some planners require additional libraries:
- **Z3 Solver**: For constraint-based planners (NextFLAP)
- **MiniSat**: SAT solver (bundled with probabilistic-ff)
- **Commercial Solvers**: CPLEX, Gurobi (optional for advanced optimization)

### Validation
Verify your installation:
```bash
# Check compiler versions
gcc --version    # Should be 9.0+
g++ --version    # Should be 9.0+
cmake --version  # Should be 3.16+

# Check language runtimes
python3 --version  # Should be 3.8+
java -version      # Should be 11+

# Check scientific libraries
pkg-config --modversion gsl  # Should be present
```

## Build Instructions

### Option 1: Automated Build (Recommended)

1. Clone this repository with all submodules:
   ```bash
   git clone --recursive https://github.com/mokhtarivahid/pddl-solvers.git
   cd pddl-solvers
   ```

2. Install system dependencies (see [System Requirements](#system-requirements--dependencies) above)

3. Run the automated build script:
   ```bash
   # Make script executable (if needed)
   chmod +x build_all.sh
   
   # Build all planners
   ./build_all.sh
   
   # Build with verbose output
   ./build_all.sh --verbose
   
   # Clean and rebuild
   ./build_all.sh --clean

  # Clean and rebuild a single planner
  ./build_all.sh --clean --planner optic

  # Clean only (no build), can target one or more planners
  ./build_all.sh --clean-only --planner popf
  ./build_all.sh --clean-only --planner ff,metric-ff
   ```

The build script will:
- Check system dependencies
- Initialize git submodules
- Auto-configure local submodule ignore rules for generated build artifacts
- Download direct source planners (MADAGASCAR, etc.)
- Attempt to build each planner individually
- Skip failed builds and continue with others
- Generate comprehensive build report

**Note:** planner repositories under `planners/` are external git submodules with their own history. When `./build_all.sh` runs, it now applies a common local ignore baseline (object files, build directories, CMake/autotools outputs, logs, caches, etc.) to all configured submodules via each submodule's `info/exclude`, plus planner-specific patterns where needed (for example ENHSP `enhsp-dist/` and JAR files). This keeps `git status` and VS Code Source Control clean across cloned environments without modifying upstream submodule history.

### Option 2: Manual Build

1. Clone this repository with all submodules:
   ```bash
   git clone --recursive https://github.com/your-username/pddl-solvers.git
   cd pddl-solvers
   ```

2. If you've already cloned without submodules, initialize them:
   ```bash
   git submodule update --init --recursive
   ```

3. Build individual planners manually:

   **Modern Planners (Git Submodules):**
   ```bash
   # Fast Downward / SymK / PowerLifted
   cd planners/downward && ./build.py
   
   # ENHSP
   cd planners/enhsp && ./compile
   
   # OPTIC
   cd planners/optic && mkdir build && cd build && cmake .. && make

   # POPF (build with local-origin RPATH for robust shared-library resolution)
   cd planners/popf && mkdir -p build && cd build && cmake -DCMAKE_BUILD_RPATH='$ORIGIN' -DCMAKE_INSTALL_RPATH='$ORIGIN' .. && make
   
   # TFD
   cd planners/tfd && ./build
   
   # VHPOP
   cd planners/vhpop && ./configure && make
   ```

   **Legacy Planners (Direct Source):**
   ```bash
   # FF-family planners
   cd planners/ff && make
   cd planners/conformant-ff && make
   # ... (see individual directories for specific instructions)
   
   # MADAGASCAR (build Mp variant)
   cd planners/madagascar && make
   ```

## Quick Start

1. **Build the planners** (see [Build Instructions](#build-instructions) above)

2. **List available planners:**
   ```bash
   ./run_planner.py --list-planners
   ```

3. **Run a planner:**
   ```bash
   # Run FF planner on a benchmark
  ./run_planner.py benchmarks/ipc-1998/domains/gripper-round-1-strips/domain.pddl \
              benchmarks/ipc-1998/domains/gripper-round-1-strips/instances/instance-1.pddl \
              -p ff
   
   # Run Fast Downward with A* + LM-cut
  ./run_planner.py domain.pddl problem.pddl -p downward --config optimal-lmcut
   
   # Show available configurations for a planner
   ./run_planner.py --list-configs symk
   ```

## Unified Planner Interface (`run_planner.py`)

The repository includes `run_planner.py` - a unified Python script that provides a consistent interface to run any planner while preserving access to each planner's unique capabilities.

### Design Philosophy

- **Beginner-Friendly**: Simple commands for common use cases (`./run_planner.py domain.pddl problem.pddl`)
- **Expert-Friendly**: Full access to all planner parameters via pass-through arguments and configuration files
- **Transparent Output**: Direct planner output to terminal by default (no forced processing)
- **Configuration-Driven**: `planner_configurations.yaml` documents planner execution configurations
- **Flexible**: Predefined configurations for common scenarios + custom parameter support

### Planner Specifications

Planner execution options are documented in `planner_configurations.yaml`:
```yaml
planners:
  symk:
    description: "SymK - Symbolic optimal and top-k planner"
    configurations:
      optimal-bd:
        description: "Single optimal, bidirectional search"
        search: "sym_bd()"
      topk-5:
        description: "Top 5 best plans"
        search: "symk_bd(plan_selection=top_k(num_plans=5))"
      # ... more configurations
    parameters:
      --plan-file: "Output file for plans"
      # ... more parameters documented
```

View the full specification:
```bash
# List all planners with descriptions
./run_planner.py --list-planners

# Show all configurations for a specific planner
./run_planner.py --list-configs symk
./run_planner.py --list-configs downward
```

### Basic Usage

```bash
# Simplest form - uses defaults
./run_planner.py <domain.pddl> <problem.pddl>

# Specify planner and configuration
./run_planner.py <domain.pddl> <problem.pddl> -p <name> --config <config>

# Auto-select best planner for domain
./run_planner.py <domain.pddl> <problem.pddl> --auto-planner
```

### Build Status

| Planner | Status | Notes |
|---------|--------| ----- |
| **Fast Downward** | Working | Multiple search algorithms |
| **FF** | Working | Classic STRIPS planner |
| **CONFORMANT-FF** | Working | Conformant planning |
| **CONTINGENT-FF** | Working | Contingent planning |
| **METRIC-FF** | Working | Numeric planning (subset of PDDL 2.1 level 2) |
| **FF-X** | Working | PDDL 2.1 derived predicates |
| **PROBABILISTIC-FF** | Working | Planning under uncertainty |
| **LPG-td** | Working | PDDL 2.2 temporal, numeric, timed initial literals, derived predicates |
| **ENHSP** | Working | Numeric planning (some domains) |
| **SymK** | Working | Optimal and top-k planning with symbolic search |
| **MADAGASCAR** | Working | SAT-based planner |
| **OPTIC** | Working | Temporal planning |
| **POPF** | Working | Temporal planning |
| **TFD** | Working | Temporal planning (only on temporal domains) |
| **VHPOP** | Incomplete | Missing vhpop executable |
| **NextFLAP** | Build Issues | C++20 compatibility |
| **PowerLifted** | Working | Lifted-clause planning |

### Key Features

#### 1. **Predefined Configurations** (Recommended for Most Users)

Each planner has carefully defined configurations accessible via `--config`:

```bash
# Fast Downward - optimal planning
./run_planner.py domain.pddl problem.pddl -p downward --config optimal-lmcut

# SymK - top-k planning (find 5 diverse best plans)
./run_planner.py domain.pddl problem.pddl -p symk --config topk-5

# SymK - top-q planning (plans within 1.5x optimal cost)
./run_planner.py domain.pddl problem.pddl -p symk --config topq-3-q1.5

# SymK - loopless planning (no state revisit)
./run_planner.py domain.pddl problem.pddl -p symk --config loopless-3

# OPTIC - first solution (stop after first plan found)
./run_planner.py domain.pddl problem.pddl -p optic --config first-solution

# ENHSP - numeric optimal planning
./run_planner.py domain.pddl problem.pddl -p enhsp --config optimal-hrmax
```

List all available configurations for a planner:
```bash
./run_planner.py --list-configs symk
./run_planner.py --list-configs downward
./run_planner.py --list-configs enhsp
```

#### 2. **Pass-Through Arguments** (For Advanced Users)

Send planner-specific parameters directly by using `--` separator:

```bash
# OPTIC: stop at first solution
./run_planner.py domain.pddl problem.pddl -p optic -- -b

# OPTIC: use greedy FF heuristic
./run_planner.py domain.pddl problem.pddl -p optic -- -g

# SymK: specify output file
./run_planner.py domain.pddl problem.pddl -p symk -- --plan-file plans.out

# SymK: custom search command (overrides --config)
./run_planner.py domain.pddl problem.pddl -p symk -- \
  --search "symk_bw(simple=true, plan_selection=top_k(num_plans=3))"
```

The `--` separator tells run_planner where your arguments end and the planner's arguments begin.

#### 3. **Output Modes** (Optional Processing)

By default, planner output goes directly to terminal (passthrough mode):

```bash
# Passthrough mode (default) - full planner output
./run_planner.py domain.pddl problem.pddl -p downward

# Compact mode - selected plan for single-plan runs, all extracted plans for multi-plan runs
./run_planner.py domain.pddl problem.pddl -p downward --output-format compact

# JSON mode - structured selected plan plus extracted plan metadata
./run_planner.py domain.pddl problem.pddl -p downward --output-format json

# Multi-plan compact output (e.g. SymK top-k)
./run_planner.py domain.pddl problem.pddl -p symk --config topk-5 --output-format compact

# Save full results to file (JSON)
./run_planner.py domain.pddl problem.pddl -p downward -o results.json
```

`run_planner.py` now separates raw planner execution from extracted plan reporting:

- `passthrough`: prints planner stdout/stderr directly, with no plan post-processing.
- `compact`: prints the selected plan for single-plan planners, or all extracted plans when a planner naturally returns multiple solutions.
- `json`: returns the legacy `plan` field for the selected plan plus structured multi-plan data in `plans`, `plan_count`, and `selected_plan_rank`.

The extractor is representation-driven rather than planner-name-only. It can now recover plans from both stdout and generated plan files, including:

- sequential stdout plans from FF-family planners
- timestamped temporal plans from OPTIC and POPF
- numbered `sas_plan.N` files from SymK top-k/top-q runs
- explicit plan files from PowerLifted
- improving `solution.plan.N` files from TFD
- step-grouped output from Madagascar

Each extracted plan entry in JSON includes these fields:

```json
{
  "rank": 1,
  "source": "stdout",
  "source_name": null,
  "format": "temporal",
  "is_partial": false,
  "is_selected": true,
  "text": "0.000: (action ...) [60.000]",
  "actions": ["0.000: (action ...) [60.000]"],
  "action_count": 1,
  "cost": null,
  "makespan": null
}
```

Current `format` values are coarse output-family labels such as `sequential`, `numbered-sequential`, `temporal`, `parallel-step`, and `policy-tree`.

#### 4. **Dry-Run Mode** (Preview Commands)

Show the exact planner command without running it:

```bash
# Dry-run prints the exact subprocess command and working directory
./run_planner.py domain.pddl problem.pddl -p symk --config topk-5 --dry-run
```

#### 5. **Domain Analysis & Auto-Selection**

Automatically select the best planner for a domain:

```bash
# Analyze domain requirements
./run_planner.py domain.pddl --analyze

# Auto-select and run
./run_planner.py domain.pddl problem.pddl --auto-planner

# Prefer fast satisficing over optimal
./run_planner.py domain.pddl problem.pddl --auto-planner --prefer-fast
```

The analyzer now uses a transparent YAML capability file at `planner_capabilities.yaml`.
You can tune strictness, requirement aliases, planner feature support, and ordered
priority lists without changing Python code.

```bash
# Inspect transparent output including catalog info and per-planner compatibility trace
./pddl_analyzer.py domain.pddl --json
```

Catalog examples:
- Strict mode: set `compatibility.mode` to `all-missing` to require zero missing requirements.
- Relaxed mode: set `compatibility.mode` to `critical-only` so only critical requirements block strict compatibility.
- Established priority: edit `priority.established_order`.
- Approach-specific priority: edit `priority.approach_order`.
- Planner capabilities: edit `planners.<planner>.supported_requirements` and metadata.

### Comprehensive Examples

#### Classical Planning
```bash
# FF - classic forward-chaining planner
./run_planner.py domain.pddl problem.pddl -p ff

# Fast Downward - modern optimal planning
./run_planner.py domain.pddl problem.pddl -p downward --config optimal-lmcut

# Fast Downward - satisficing (faster)
./run_planner.py domain.pddl problem.pddl -p downward --config satisficing-ff
```

#### Optimal & Top-K Planning (SymK)
```bash
# Single optimal plan
./run_planner.py domain.pddl problem.pddl -p symk

# Top 5 diverse best plans
./run_planner.py domain.pddl problem.pddl -p symk --config topk-5

# Top 5 diverse best plans with extracted compact output
./run_planner.py domain.pddl problem.pddl -p symk --config topk-5 --output-format compact

# Top 3 plans within 1.5x optimal cost
./run_planner.py domain.pddl problem.pddl -p symk --config topq-3-q1.5

# Top 3 loopless plans (no state revisit)
./run_planner.py domain.pddl problem.pddl -p symk --config loopless-3

# Backward search instead of bidirectional
./run_planner.py domain.pddl problem.pddl -p symk -- --search "sym_bw()"

# Custom search with unordered selector
./run_planner.py domain.pddl problem.pddl -p symk -- \
  --search "symk_bd(plan_selection=unordered(num_plans=10))"
```

#### Temporal Planning
```bash
# OPTIC - optimal temporal planning
./run_planner.py domain.pddl problem.pddl -p optic

# OPTIC - first feasible solution (faster)
./run_planner.py domain.pddl problem.pddl -p optic --config first-solution

# POPF - satisficing temporal planning (widely used in ROS)
./run_planner.py domain.pddl problem.pddl -p popf

# TFD - temporal planning with heuristics
./run_planner.py domain.pddl problem.pddl -p tfd
```

#### Numeric Planning
```bash
# ENHSP - numeric satisficing
./run_planner.py domain.pddl problem.pddl -p enhsp --config satisficing-hmrp

# ENHSP - numeric optimal
./run_planner.py domain.pddl problem.pddl -p enhsp --config optimal-hrmax

# Metric-FF - numeric STRIPS planning
./run_planner.py domain.pddl problem.pddl -p metric-ff
```

#### Special Features
```bash
# Conformant planning (incomplete information)
./run_planner.py domain.pddl problem.pddl -p conformant-ff

# Contingent planning (with sensing)
./run_planner.py domain.pddl problem.pddl -p contingent-ff

# Lifted planning (large object domains)
./run_planner.py domain.pddl problem.pddl -p powerlifted

# SAT-based planning
./run_planner.py domain.pddl problem.pddl -p madagascar
```

### Complete Command Reference

```
REQUIRED ARGUMENTS:
  domain FILE                 Domain PDDL file (required for analysis/execution)
  problem FILE                Problem PDDL file (required for planner execution)

PLANNER SELECTION (optional, uses auto-select if not provided):
  -p, --planner NAME          Specific planner to use
  -A, --auto-planner          Auto-select best planner based on domain
  -O, --prefer-optimal        Prefer optimal planners (default for auto-select)
  -F, --prefer-fast           Prefer satisficing planners for auto-select

CONFIGURATION (optional, uses planner default if not provided):
  -c, --config NAME           Predefined configuration (e.g., optimal-bd, topk-5)
  -L, --list-configs PLANNER  Show all configs for a planner

PLANNER-SPECIFIC ARGUMENTS:
  -- ARGS                     Pass arguments directly to the planner
                              Example: ./run_planner.py ... -- -b --flag

EXECUTION OPTIONS:
  -t, --timeout INT           Timeout in seconds (default: 300)
  -d, --dry-run               Show the exact planner command without running it
  -o, --output FILE           Save JSON results to file

OUTPUT HANDLING:
  -f, --output-format FORMAT  passthrough (default), compact, or json
                              compact/json use extracted plans from stdout and plan files when available
  -q, --no-live-output        Disable live streaming while planner runs
  --verbose, -v               Verbose domain analysis output

INFORMATION:
  -l, --list-planners         Show all available planners
  -a, --analyze               Analyze domain requirements and show compatible planners
  --help, -h                  Show this help message

EXAMPLES:
  # Simple usage
  ./run_planner.py domain.pddl problem.pddl

  # Short-form aliases for common options
  ./run_planner.py domain.pddl problem.pddl -p symk -c topk-5 -t 120

  # With specific configuration
  ./run_planner.py domain.pddl problem.pddl -p symk --config topk-5

  # With planner-specific arguments
  ./run_planner.py domain.pddl problem.pddl -p optic -- -b

  # Auto-select and show the exact command without running
  ./run_planner.py domain.pddl problem.pddl --auto-planner --dry-run
```

### Understanding Planner Output

By default, `run_planner.py` prints the planner's raw output directly to your terminal, along with a header showing:
- Domain and problem files used
- Selected planner and configuration
- Timeout value
- Auto-selection information (if applicable)
- Any pass-through arguments

This allows you to:
- See exactly what the planner is doing
- Understand errors and debug issues
- Process output with standard Unix tools (`grep`, `awk`, `sed`, etc.)
- Parse custom output formats from each planner

Example output header:
```
======================================================================
PDDL Planner Execution
======================================================================
Domain file:       gripper.pddl
Problem file:      p01.pddl
Planner:           symk
Configuration:     topk-5
                   (Top 5 best plans, bidirectional)
Timeout:           300 seconds
======================================================================
```

### Advanced Usage

#### Adding Custom Configurations

Edit `planner_configurations.yaml` to add new configurations:

```yaml
planners:
  symk:
    configurations:
      my-custom:
        description: "My custom search strategy"
        search: "symq_bd(plan_selection=top_k(num_plans=10), quality=3.0)"
```

Then use it:
```bash
./run_planner.py domain.pddl problem.pddl -p symk --config my-custom
```

#### Batch Testing

```bash
# Test a planner on multiple problems
for problem in benchmarks/*/p*.pddl; do
  echo "Testing: $problem"
  ./run_planner.py benchmarks/domain.pddl "$problem" -p downward
done

# Parse results with --output-format json
./run_planner.py domain.pddl problem.pddl -p symk --output-format json -o result.json
jq '.plan' result.json                  # Selected plan text
jq '.plan_count' result.json            # Number of extracted plans
jq '.plans[0].actions' result.json     # First extracted plan as action lines
```

#### Integration with Scripts

```bash
#!/bin/bash
# Collect statistics across multiple planners

for planner in ff downward symk optic; do
  ./run_planner.py domain.pddl problem.pddl -p "$planner" \
    --output-format json -o "result_$planner.json"
  
  success=$(jq '.success' "result_$planner.json")
  runtime=$(jq '.runtime' "result_$planner.json")
  echo "$planner: success=$success, runtime=$runtime"
done
```

## Testing Framework

Run automated tests on multiple planners using benchmark problems:

```bash
# Quick planner test (recommended first run)
./tests/run_tests.py --quick

# Test specific planners
./tests/run_tests.py --planners ff downward enhsp

# Full planner test suite with custom timeout
./tests/run_tests.py --timeout 120

# Generate reports
./tests/run_tests.py --output-report test_report.md --output-json results.json
```

**PDDL Analysis System Tests:**

```bash
# Test PDDL requirements analysis and planner matching
./tests/test_analysis.py

# Quick analysis tests only
./tests/test_analysis.py --quick

# Generate analysis test reports
./tests/test_analysis.py --output-report analysis_report.md --output-json analysis_results.json
```

Test results include:
- Success/failure rates per planner
- PDDL requirements parsing validation
- Planner compatibility matching verification
- Auto-selection functionality testing
- Runtime statistics  
- Markdown and JSON reports
- Coverage across different domain types

## Compilation Notes

- **Git Submodule Planners**: Modern planners (Fast-Downward, SymK, ENHSP, OPTIC, PowerLifted, POPF, NextFLAP, TFD) should compile without issues on modern systems.
- **FF Family Planners**: Legacy FF-based planners may require compiler fixes due to their age. The source code is available and can be modified to resolve compilation issues on modern gcc versions.

## Troubleshooting

### Common Build Issues

1. **FF-X/Metric-FF: Multiple symbol definition errors**
   ```
   Solution: Symbol conflicts in C code - requires manual code fixes
   Status: Known issue with modern GCC versions
   ```

2. **TFD: Requires `solutionFile` argument when called directly**
   ```
   TFD native usage: downward/tfd <domainFile> <problemFile> <solutionFile> [config]
  Repository behavior: `run_planner.py -p tfd` passes a temp solution file automatically
   Plan extraction: when TFD emits multiple plan files (.1, .2, ...), the latest numeric file is selected
   ```

3. **OPTIC: GSL library not found**
   ```bash
   # Install GSL development library
   sudo apt install libgsl-dev
   ```

4. **POPF: Symbol lookup error when ROS is installed (for example `/opt/ros/jazzy/lib/libpopfCommon.so`)**
   ```
   Root cause: system/ROS `LD_LIBRARY_PATH` can override POPF's local shared libs
   Repository fix: `run_planner.py` prepends `planners/popf/build` to `LD_LIBRARY_PATH`
   Build hardening: POPF is configured with `RPATH=$ORIGIN` in `build_all.sh`
   ```

5. **NextFLAP: C++20 template compilation errors**
   ```
   Solution: Requires GCC 10+ or code modifications for older compilers
   Status: Modern C++ compatibility issue
   ```

6. **VHPOP: Missing executable after build**
   ```bash
   # Build complete VHPOP (not just libraries)
   cd planners/vhpop && autoreconf -i && ./configure && make
   ```

### Testing Individual Planners

```bash
# Test a specific planner
./run_planner.py benchmarks/ipc-1998/domains/gripper-round-1-strips/domain.pddl \
                 benchmarks/ipc-1998/domains/gripper-round-1-strips/instances/instance-1.pddl \
                 -p ff

# Run test suite on working planners only
./tests/run_tests.py --planners ff downward madagascar conformant-ff enhsp optic tfd
```

## Repository Structure

```
pddl-solvers/
├── README.md           # Complete documentation
├── build_all.sh        # Automated build script for all planners
├── .gitignore          # Excludes compilation artifacts
├── benchmarks/         # PDDL benchmark instances (IPC 1998-2014)
└── planners/           # All PDDL planners collection
    ├── downward/       # Classical planner (Fast-Downward)
    ├── symk/           # Optimal/Top-K planner (SymK)
    ├── enhsp/          # Numeric planner (ENHSP)
    ├── optic/          # Temporal planner (OPTIC)
    ├── powerlifted/    # Lifted planner (PowerLifted)
    ├── popf/           # Temporal PO planner (POPF)
    ├── nextflap/       # Expressive Hybrid planner (NextFLAP)
    ├── tfd/            # Temporal Heuristic planner (TFD)
    ├── vhpop/          # Partial Order planner (VHPOP)
    ├── madagascar/     # SAT-based planner (MADAGASCAR)
    ├── ff/             # Classical FF planner
    ├── ff-x/           # FF with axioms support
    ├── metric-ff/      # Numeric FF planner
    ├── conformant-ff/  # Conformant planning
    ├── contingent-ff/  # Contingent planning
    └── probabilistic-ff/ # Probabilistic planning
```

## Build Script Features

The `build_all.sh` script provides:

- **Dependency Checking**: Verifies all required tools are installed
- **Robust Error Handling**: Continues building other planners if one fails
- **Progress Reporting**: Real-time status updates and final summary
- **Multiple Variants**: Builds all MADAGASCAR variants (M, Mp, MpC)
- **Clean Builds**: Optional cleaning before compilation
- **Detailed Logging**: Comprehensive build log saved to `build_results.log`
- **Timeout Protection**: Prevents builds from hanging indefinitely

## PDDL Benchmark Instances

This repository includes a comprehensive collection of **PDDL benchmark instances** from the International Planning Competitions (IPC):

### Classical Benchmarks (Submodule)
- **IPC 1998-2014**: Available via `benchmarks/ipc-domains/` submodule
- **Source**: [plaans/tyr-ipc-domains](https://github.com/plaans/tyr-ipc-domains) - Comprehensive PDDL benchmark collection

### Temporal Benchmarks (Via TFD Submodule)  
- **Temporal Planning Domains**: Available via `planners/tfd/benchmarks/`
- **Source**: [neighthan/tfd](https://github.com/neighthan/tfd) - Temporal Fast Downward with benchmarks
- **Domains**: crewplanning-strips, elevators (numeric/strips), modeltrain-numeric, openstacks variants, parcprinter-strips, pegsol-strips, sokoban-strips, transport-numeric, woodworking-numeric

### Benchmark Structure
Each domain follows a consistent structure:
- `domain.pddl` - Domain definition file
- `instances/` - Directory containing problem instances (`instance-1.pddl`, `instance-2.pddl`, etc.)
- `README.md` - Informal description of the domain

### Usage Examples
```bash
# Test Fast-Downward on Classical Benchmarks
cd benchmarks/ipc-domains/ipc-1998/domains/gripper
../../../../planners/downward/fast-downward.py domain.pddl instances/instance-1.pddl --search "astar(blind())"

# Test FF on Classical Logistics  
cd benchmarks/ipc-domains/ipc-2000/domains/logistics
../../../../planners/ff/ff -o domain.pddl -f instances/instance-1.pddl

# Test TFD on Temporal Benchmarks
cd planners/tfd/benchmarks/elevators-strips
../../../run_planner.py domain.pddl p01.pddl -p tfd

# Optional: pass native TFD config string (solution path is still internal)
../../../run_planner.py domain.pddl p01.pddl -p tfd --config "y+Y+a+e+r+O+1+C+1+b"
```

## Usage

Each planner has its own compilation and usage instructions. Refer to the individual planner repositories for detailed documentation.

## Contributing

Contributions are welcome! If you know of other high-quality PDDL planners that should be included, please open an issue or submit a pull request.

## License

This repository is a collection of existing planners, each with their own licenses. Please refer to the individual planner repositories for their specific licensing terms.