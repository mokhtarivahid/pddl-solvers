# PDDL Solvers Collection

A comprehensive collection of Planning Domain Definition Language (PDDL) planners and solvers for easy access and compilation.

## Overview

This repository provides a curated collection of state-of-the-art PDDL planners, each specialized for different types of planning problems. All planners are included as Git submodules in the `planners/` directory.

## Curated PDDL Planners & Solvers Reference

<div style="font-size: 0.85em;">

| Category | Planner Name | GitHub Link | Best For... |
| --- | --- | --- | --- |
| **Classical** | **Fast-Downward** | [aibasel/downward](https://github.com/aibasel/downward) | The industry and research "gold standard" for discrete, deterministic planning. |
| **Classical (Legacy)** | **FF** | [FF-v2.3](https://fai.cs.uni-saarland.de/hoffmann/ff.html) | Fast forward chaining heuristic search; foundational classical planner with excellent performance on STRIPS domains. |
| **Classical (ADL)** | **FF-X** | [FF-X](https://fai.cs.uni-saarland.de/hoffmann/ff.html) | Extension of FF handling PDDL 2.1 derived predicates (axioms) for complex logical planning. |
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

</div>

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

## Automated Build

Use the included build script to automatically download, initialize, and compile all planners:

```bash
# Make script executable (if needed)
chmod +x build_all.sh

# Build all planners
./build_all.sh

# Build with verbose output
./build_all.sh --verbose

# Clean and rebuild
./build_all.sh --clean
```

The build script will:
- Check system dependencies
- Initialize git submodules
- Download direct source planners (MADAGASCAR, etc.)
- Attempt to build each planner individually
- Skip failed builds and continue with others
- Generate comprehensive build report

## Quick Start

### Option 1: Automated Build (Recommended)

1. Clone this repository:
   ```bash
   git clone --recursive https://github.com/mokhtarivahid/pddl-solvers.git
   cd pddl-solvers
   ```

2. Install system dependencies (see [System Requirements](#system-requirements--dependencies) above)

3. Run the automated build script:
   ```bash
   ./build_all.sh
   ```
   
   The script will automatically:
   - Initialize all git submodules
   - Download direct source planners (MADAGASCAR)
   - Compile all planners with proper error handling
   - Generate a comprehensive build report

4. **Run any planner with the unified interface:**
   ```bash
   # List available planners
   ./run_planner.py --list-planners
   
   # Run FF planner
   ./run_planner.py -d benchmarks/ipc-1998/domains/gripper-round-1-strips/domain.pddl \
                     -p benchmarks/ipc-1998/domains/gripper-round-1-strips/instances/instance-1.pddl \
                     --planner ff
   
   # Run Fast Downward with A* + LM-cut
   ./run_planner.py -d domain.pddl -p problem.pddl --planner downward --config astar-lmcut
   ```

## Unified Planner Interface

The repository includes `run_planner.py` - a unified Python script that provides a consistent interface to run any planner:

### Basic Usage

```bash
./run_planner.py -d <domain.pddl> -p <problem.pddl> --planner <planner_name> [options]
```

### List Available Planners

```bash
./run_planner.py --list-planners
```

Available: `conformant-ff`, `contingent-ff`, `downward`, `enhsp`, `ff`, `ff-x`, `madagascar`, `metric-ff`, `nextflap`, `optic`, `popf`, `powerlifted`, `probabilistic-ff`, `symk`, `tfd`, `vhpop`

### Build Status

| Planner | Status | Notes |
|---------|--------| ----- |
| **FF** | Working | Classic STRIPS planner |
| **Fast Downward** | Working | Multiple search algorithms |
| **MADAGASCAR** | Working | SAT-based planner |
| **CONFORMANT-FF** | Working | Conformant planning |
| **ENHSP** | Working | Numeric planning (some domains) |
| **OPTIC** | Working | Temporal planning |
| **CONTINGENT-FF** | Partial | Builds but output parsing issues |
| **FF-X** | Build Issues | Linker symbol conflicts |
| **METRIC-FF** | Build Issues | Linker symbol conflicts |
| **TFD** | Config Issue | Requires python symlink |
| **VHPOP** | Incomplete | Missing vhpop executable |
| **POPF** | Link Issues | Undefined symbols |
| **NextFLAP** | Build Issues | C++20 compatibility |
| **Others** | Not Built | Require investigation |

### Planner Configurations

**Fast Downward** search algorithms:
```bash
./run_planner.py --list-configs downward
```
- `astar-lmcut` - A* with LM-cut heuristic (optimal)
- `astar-ff` - A* with FF heuristic  
- `lazy-greedy-ff` - Greedy best-first with FF heuristic
- `seq-sat-lama` - LAMA satisficing configuration
- `seq-opt-lama` - LAMA optimal configuration
- And more...

**ENHSP** configurations:
```bash
./run_planner.py --list-configs enhsp
```
- `sat-hmrp` - Satisficing planning with HMRP heuristic
- `opt-hrmax` - Optimal planning with HRMax heuristic
- `gbfs-hadd` - Greedy best-first with additive heuristic

### PDDL Requirements Analysis & Auto-Selection

The system includes intelligent domain analysis and automatic planner selection:

```bash
# Analyze domain requirements and show compatible planners
./run_planner.py --analyze-only -d domain.pddl

# Auto-select best planner for a domain
./run_planner.py --auto-planner -d domain.pddl -p problem.pddl

# Prefer fast satisficing planners over optimal ones
./run_planner.py --auto-planner --prefer-fast -d domain.pddl -p problem.pddl

# Standalone analyzer with detailed output
./pddl_analyzer.py domain.pddl --verbose
```

**Supported Analysis:**
- PDDL version detection (1.2, 2.1, 2.2, 3.0+)
- Requirements parsing (25+ requirement types)
- Planner compatibility matching
- Automatic optimal/satisficing selection

### Examples

```bash
# Classical planning with FF
./run_planner.py -d domain.pddl -p problem.pddl --planner ff

# Optimal planning with Fast Downward
./run_planner.py -d domain.pddl -p problem.pddl --planner downward --config astar-lmcut

# Numeric planning with ENHSP  
./run_planner.py -d domain.pddl -p problem.pddl --planner enhsp --config sat-hmrp

# With timeout and JSON output
./run_planner.py -d domain.pddl -p problem.pddl --planner downward \
                  --config lazy-greedy-ff --timeout 300 --output results.json
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
   
   # OPTIC / POPF
   cd planners/optic && mkdir build && cd build && cmake .. && make
   
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

2. **TFD: `/usr/bin/env: 'python': No such file or directory`**
   ```bash
   # Create python symlink
   sudo ln -sf /usr/bin/python3 /usr/bin/python
   ```

3. **OPTIC: GSL library not found**
   ```bash
   # Install GSL development library
   sudo apt install libgsl-dev
   ```

4. **POPF: Undefined symbols during linking**
   ```
   Solution: Try clean rebuild or use different POPF repository
   Status: Known linking issue in some POPF forks
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
./run_planner.py -d benchmarks/ipc-1998/domains/gripper-round-1-strips/domain.pddl \
                  -p benchmarks/ipc-1998/domains/gripper-round-1-strips/instances/instance-1.pddl \
                  --planner ff

# Run test suite on working planners only
./tests/run_tests.py --planners ff downward madagascar conformant-ff enhsp optic
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
../../../run_planner.py -d domain.pddl -p p01.pddl --planner tfd
```

## Usage

Each planner has its own compilation and usage instructions. Refer to the individual planner repositories for detailed documentation.

## Contributing

Contributions are welcome! If you know of other high-quality PDDL planners that should be included, please open an issue or submit a pull request.

## License

This repository is a collection of existing planners, each with their own licenses. Please refer to the individual planner repositories for their specific licensing terms.