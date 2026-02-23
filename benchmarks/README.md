# PDDL Benchmarks Collection

This directory contains organized collections of PDDL benchmark domains from various sources.

## Directory Structure

### `ipc-domains/`
**Source**: [plaans/tyr-ipc-domains](https://github.com/plaans/tyr-ipc-domains)

Extended collection of International Planning Competition (IPC) domains including:
- IPC-1998 through IPC-2023 domains
- Additional community-contributed domains
- Enhanced problem sets with additional test cases

This is a comprehensive fork of the original PDDL instances with expanded coverage.

### `temporal-domains/`
**Source**: [neighthan/tfd](https://github.com/neighthan/tfd) (benchmarks subdirectory only)

Specialized collection of temporal planning benchmarks including:
- Temporal domains from the TFD (Temporal Fast Downward) project
- Numeric temporal planning problems
- Research-grade temporal benchmark instances

*Note: Only the benchmarks are included here to avoid duplication with the TFD planner in `planners/tfd/`*

## Usage

### With run_planner.py
```bash
# Classical planning with IPC domains
./run_planner.py --planner ff -d benchmarks/ipc-domains/ipc-2000/blocks/domain.pddl -p benchmarks/ipc-domains/ipc-2000/blocks/instances/instance-1.pddl

# Temporal planning with TFD benchmarks  
./run_planner.py --planner tfd -d benchmarks/temporal-domains/modeltrain-numeric/domain.pddl -p benchmarks/temporal-domains/modeltrain-numeric/p01.pddl
```

### Domain Discovery
```bash
# List available IPC domains
find benchmarks/ipc-domains/ -name "domain.pddl" | head -10

# List temporal domains
find benchmarks/temporal-domains/ -name "domain.pddl" | head -10
```

## Adding More Benchmarks

This structure allows for easy expansion:
```
benchmarks/
├── ipc-domains/          # Main IPC competition domains
├── temporal-domains/     # Temporal planning benchmarks
├── custom-domains/       # (future) Custom domain collections
├── research-sets/        # (future) Research-specific benchmarks
└── validation-tests/     # (future) Validation and testing sets
```

To add new benchmark collections, use git submodules in organized subdirectories:
```bash
git submodule add <repository-url> benchmarks/new-collection/
```

## Notes

- Each subdirectory is an independent git submodule
- Benchmarks are organized by source and domain type for easy navigation
- Path structure designed for compatibility with existing planner scripts
- All domains maintain their original file structure and naming conventions