#!/bin/bash
#
# PDDL Solvers Build Script
# Automatically downloads, initializes, and compiles all planners in the collection
# 
# Usage: ./build_all.sh [options]
#   -v, --verbose    Enable verbose output
#   -c, --clean      Clean before building
#   -C, --clean-only Clean selected planners and exit
#   -p, --planner    Build/clean only specific planner(s), comma-separated or repeated
#   -h, --help       Show this help message
#

set -e  # Exit on error for the main script, but we'll handle individual planner errors

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VERBOSE=false
CLEAN=false
CLEAN_ONLY=false
BUILD_LOG="build_results.log"
SUCCESS_COUNT=0
FAILURE_COUNT=0
SKIPPED_COUNT=0

declare -a SELECTED_PLANNERS=()
declare -a ALL_PLANNERS=(
    "downward" "symk" "enhsp" "optic" "powerlifted" "popf" "nextflap" "tfd" "vhpop" "madagascar"
    "ff" "ff-x" "metric-ff" "conformant-ff" "contingent-ff" "probabilistic-ff" "lpg"
    "val"
)

# Arrays to track results
declare -a SUCCESS_LIST=()
declare -a FAILURE_LIST=()
declare -a SKIPPED_LIST=()

is_valid_planner() {
    local candidate=$1
    local planner
    for planner in "${ALL_PLANNERS[@]}"; do
        if [[ "$planner" == "$candidate" ]]; then
            return 0
        fi
    done
    return 1
}

append_selected_planners() {
    local raw=$1
    local item
    IFS=',' read -r -a _items <<< "$raw"
    for item in "${_items[@]}"; do
        item="${item// /}"
        [[ -z "$item" ]] && continue
        if ! is_valid_planner "$item"; then
            echo "Unknown planner for --planner: $item"
            echo "Valid planners: ${ALL_PLANNERS[*]}"
            exit 1
        fi
        SELECTED_PLANNERS+=("$item")
    done
}

is_selected_planner() {
    local planner=$1
    if [[ ${#SELECTED_PLANNERS[@]} -eq 0 ]]; then
        return 0
    fi
    local selected
    for selected in "${SELECTED_PLANNERS[@]}"; do
        if [[ "$selected" == "$planner" ]]; then
            return 0
        fi
    done
    return 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -C|--clean-only)
            CLEAN=true
            CLEAN_ONLY=true
            shift
            ;;
        -p|--planner)
            if [[ -z "$2" ]]; then
                echo "Missing value for $1"
                exit 1
            fi
            append_selected_planners "$2"
            shift 2
            ;;
        -h|--help)
            echo "PDDL Solvers Build Script"
            echo "Usage: $0 [options]"
            echo "  -v, --verbose    Enable verbose output"
            echo "  -c, --clean      Clean before building"
            echo "  -C, --clean-only Clean selected planners and exit"
            echo "  -p, --planner    Build/clean only planner(s): comma-separated or repeated"
            echo "                  Valid planners: ${ALL_PLANNERS[*]}"
            echo "  -h, --help       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --clean"
            echo "  $0 --clean --planner optic"
            echo "  $0 --clean --planner ff,metric-ff --planner downward"
            echo "  $0 --clean-only --planner popf"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Utility functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1" >> "$BUILD_LOG"
}

clean_planner_artifacts() {
    local planner_key=$1
    local planner_dir="planners/$planner_key"

    # VAL is a validation tool, not a planner; it lives at the repo root.
    if [[ "$planner_key" == "val" ]]; then
        planner_dir="VAL"
    fi

    if [[ ! -d "$planner_dir" ]]; then
        log_warning "$planner_key directory not found for cleaning: $planner_dir"
        return 1
    fi

    log_info "Cleaning $planner_key..."

    pushd "$planner_dir" >/dev/null || return 1

    # Generic cleanup for Make-based projects.
    if [[ -f Makefile || -f makefile ]]; then
        make clean >/dev/null 2>&1 || true
    fi

    case "$planner_key" in
        downward|symk)
            rm -rf builds build >/dev/null 2>&1 || true
            ;;
        optic|popf)
            rm -rf build CMakeFiles CMakeCache.txt cmake_install.cmake >/dev/null 2>&1 || true
            ;;
        enhsp)
            rm -rf build target enhsp-dist out >/dev/null 2>&1 || true
            rm -f enhsp.jar >/dev/null 2>&1 || true
            ;;
        madagascar)
            rm -f M Mp MpC >/dev/null 2>&1 || true
            ;;
        tfd)
            rm -f downward/tfd downward/preprocess downward/search/downward >/dev/null 2>&1 || true
            ;;
        lpg)
            rm -f lpg lpg-probing >/dev/null 2>&1 || true
            ;;
        powerlifted)
            rm -rf __pycache__ build dist >/dev/null 2>&1 || true
            ;;
        nextflap)
            rm -rf build out target >/dev/null 2>&1 || true
            ;;
        vhpop)
            rm -f vhpop ipc3-vhpop >/dev/null 2>&1 || true
            ;;
        ff|ff-x|metric-ff|conformant-ff|contingent-ff|probabilistic-ff)
            rm -f ff >/dev/null 2>&1 || true
            ;;
        val)
            rm -rf build >/dev/null 2>&1 || true
            ;;
    esac

    popd >/dev/null || true
    log_success "Cleaned $planner_key"
    return 0
}

clean_selected_planners() {
    local cleaned=0
    local planner

    for planner in "${ALL_PLANNERS[@]}"; do
        if is_selected_planner "$planner"; then
            clean_planner_artifacts "$planner" || true
            cleaned=$((cleaned + 1))
        fi
    done

    if [[ $cleaned -eq 0 ]]; then
        log_warning "No planners selected for cleaning"
    else
        log_info "Cleaned planner targets: $cleaned"
    fi
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1" >> "$BUILD_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1" >> "$BUILD_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "$BUILD_LOG"
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check system dependencies
check_dependencies() {
    log_info "Checking system dependencies..."
    
    local missing_deps=()
    
    # Essential build tools
    if ! command_exists gcc; then missing_deps+=("gcc"); fi
    if ! command_exists g++; then missing_deps+=("g++"); fi
    if ! command_exists make; then missing_deps+=("make"); fi
    if ! command_exists cmake; then missing_deps+=("cmake"); fi
    if ! command_exists python3; then missing_deps+=("python3"); fi
    if ! command_exists java; then missing_deps+=("java (JDK 8+)"); fi
    if ! command_exists flex; then missing_deps+=("flex"); fi
    if ! command_exists bison; then missing_deps+=("bison"); fi
    if ! command_exists git; then missing_deps+=("git"); fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install these dependencies before running the build script."
        log_error "See README.md for detailed installation instructions."
        exit 1
    fi
    
    log_success "All required dependencies found"
}

# Initialize git submodules
initialize_submodules() {
    log_info "Initializing and updating git submodules..."
    
    # Check if .gitmodules exists and has content
    if [[ ! -f .gitmodules ]] || [[ ! -s .gitmodules ]]; then
        log_info "No submodules configured in .gitmodules"
        return 0
    fi
    
    # Initialize only configured submodules
    local failed_submodules=()
    
    # Get list of configured submodules from .gitmodules
    local configured_submodules=($(git config --file .gitmodules --get-regexp path | awk '{print $2}'))
    
    if [[ ${#configured_submodules[@]} -eq 0 ]]; then
        log_info "No submodule paths found in .gitmodules"
        return 0
    fi
    
    log_info "Found ${#configured_submodules[@]} configured submodules"
    
    # Initialize each submodule individually
    for submodule_path in "${configured_submodules[@]}"; do
        if [[ $VERBOSE == true ]]; then
            echo "  Initializing submodule: $submodule_path"
        fi
        
        if git submodule update --init --recursive "$submodule_path"; then
            if [[ $VERBOSE == true ]]; then
                echo "    $submodule_path initialized successfully"
            fi
        else
            log_info "  Warning: Failed to initialize submodule: $submodule_path"
            failed_submodules+=("$submodule_path")
        fi
    done
    
    if [[ ${#failed_submodules[@]} -eq 0 ]]; then
        log_success "All git submodules initialized successfully"
    else
        log_info "Some submodules failed to initialize: ${failed_submodules[*]}"
        log_info "Continuing with available submodules..."
    fi
}

# Configure local ignore rules inside submodules for generated artifacts.
# These patterns are intentionally local to each submodule repository.
configure_submodule_ignores() {
    log_info "Configuring submodule local ignore rules for build artifacts..."

    local configured=0

    add_submodule_exclude() {
        local repo_path=$1
        local pattern=$2

        if [[ ! -d "$repo_path" ]]; then
            return 0
        fi

        local exclude_file
        exclude_file=$(git -C "$repo_path" rev-parse --git-path info/exclude 2>/dev/null || true)
        if [[ -z "$exclude_file" ]]; then
            return 0
        fi

        mkdir -p "$(dirname "$exclude_file")"
        touch "$exclude_file"

        if ! grep -Fxq "$pattern" "$exclude_file"; then
            echo "$pattern" >> "$exclude_file"
            configured=$((configured + 1))
            if [[ $VERBOSE == true ]]; then
                echo "  added $repo_path -> $pattern"
            fi
        fi
    }

    # Get all configured submodules from .gitmodules.
    local configured_submodules=($(git config --file .gitmodules --get-regexp path | awk '{print $2}'))
    if [[ ${#configured_submodules[@]} -eq 0 ]]; then
        log_info "No submodules found for ignore configuration"
        return 0
    fi

    # Common generated artifacts to ignore in all submodules.
    local common_patterns=(
        "*.o"
        "*.obj"
        "*.so"
        "*.a"
        "*.dylib"
        "*.pyc"
        "__pycache__/"
        "build/"
        "dist/"
        "target/"
        "bin/"
        "obj/"
        "CMakeFiles/"
        "CMakeCache.txt"
        "cmake_install.cmake"
        "config.log"
        "config.status"
        "confdefs.h"
        "autom4te.cache/"
        ".deps/"
        ".libs/"
        "*.tmp"
        "*.log"
        "gmon.out"
    )

    local submodule_path
    local pattern
    for submodule_path in "${configured_submodules[@]}"; do
        for pattern in "${common_patterns[@]}"; do
            add_submodule_exclude "$submodule_path" "$pattern"
        done
    done

    # Planner-specific generated outputs not covered by common patterns.
    add_submodule_exclude "planners/enhsp" "enhsp-dist/"
    add_submodule_exclude "planners/enhsp" "*.jar"

    # VAL-specific generated outputs (CMake build artifacts).
    add_submodule_exclude "VAL" "build/"
    add_submodule_exclude "VAL" "bin/"

    if [[ $configured -gt 0 ]]; then
        log_success "Configured $configured new local submodule ignore rule(s) across all submodules"
    else
        log_info "Submodule local ignore rules already configured"
    fi
}

# Mark tracked generated files as skip-worktree locally so clean/rebuild cycles
# do not appear as deletions in git status.
configure_local_skip_worktree() {
    log_info "Configuring local skip-worktree rules for generated planner files..."

    local configured=0
    local rel_path
    local tracked_state

    local skip_files=(
        "planners/ff/lex.fct_pddl.c"
        "planners/ff/lex.ops_pddl.c"
        "planners/ff/scan-fct_pddl.tab.c"
        "planners/ff/scan-ops_pddl.tab.c"
        "planners/ff-x/lex.fct_pddl.c"
        "planners/ff-x/lex.ops_pddl.c"
        "planners/ff-x/scan-fct_pddl.tab.c"
        "planners/ff-x/scan-ops_pddl.tab.c"
        "planners/metric-ff/lex.fct_pddl.c"
        "planners/metric-ff/lex.ops_pddl.c"
        "planners/metric-ff/scan-fct_pddl.tab.c"
        "planners/metric-ff/scan-ops_pddl.tab.c"
        "planners/conformant-ff/lex.fct_pddl.c"
        "planners/conformant-ff/lex.ops_pddl.c"
        "planners/conformant-ff/scan-fct_pddl.tab.c"
        "planners/conformant-ff/scan-ops_pddl.tab.c"
        "planners/contingent-ff/lex.fct_pddl.c"
        "planners/contingent-ff/lex.ops_pddl.c"
        "planners/contingent-ff/scan-fct_pddl.tab.c"
        "planners/contingent-ff/scan-ops_pddl.tab.c"
        "planners/probabilistic-ff/lex.fct_pddl.c"
        "planners/probabilistic-ff/lex.ops_pddl.c"
        "planners/probabilistic-ff/scan-fct_pddl.tab.c"
        "planners/probabilistic-ff/scan-ops_pddl.tab.c"
        "planners/madagascar/parser.tab.c"
        "planners/madagascar/parser.tab.h"
    )

    for rel_path in "${skip_files[@]}"; do
        if ! git ls-files --error-unmatch "$rel_path" >/dev/null 2>&1; then
            continue
        fi

        tracked_state=$(git ls-files -v -- "$rel_path" 2>/dev/null | awk '{print $1}')
        if [[ "$tracked_state" != "S" ]]; then
            git update-index --skip-worktree "$rel_path" >/dev/null 2>&1 || true
            configured=$((configured + 1))
            if [[ $VERBOSE == true ]]; then
                echo "  marked skip-worktree: $rel_path"
            fi
        fi
    done

    if [[ $configured -gt 0 ]]; then
        log_success "Configured $configured local skip-worktree rule(s) for generated files"
    else
        log_info "Local skip-worktree rules already configured"
    fi
}

# Download MADAGASCAR if not present
download_madagascar() {
    if [ ! -d "planners/madagascar" ]; then
        log_info "Downloading MADAGASCAR planner..."
        mkdir -p planners/madagascar
        
        if wget -q https://users.aalto.fi/~rintanj1/downloads/MADAGASCAR.TAR -O /tmp/MADAGASCAR.TAR; then
            tar -xf /tmp/MADAGASCAR.TAR -C planners/madagascar
            rm -f /tmp/MADAGASCAR.TAR
            log_success "MADAGASCAR downloaded successfully"
        else
            log_error "Failed to download MADAGASCAR"
            return 1
        fi
    else
        log_info "MADAGASCAR already present"
    fi
}

# Generic build function with error handling
build_planner() {
    local planner_name=$1
    local planner_dir=$2
    local build_command=$3
    local planner_key
    planner_key=$(basename "$planner_dir")
    
    log_info "Building $planner_name..."
    
    if [ ! -d "$planner_dir" ]; then
        log_warning "$planner_name directory not found: $planner_dir"
        SKIPPED_LIST+=("$planner_name (directory not found)")
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        return 1
    fi
    
    cd "$planner_dir"
    
    # Clean if requested
    if [ "$CLEAN" = true ]; then
        cd - >/dev/null
        clean_planner_artifacts "$planner_key" || true
        cd "$planner_dir"
    fi
    
    # Execute build command with timeout (10 minutes max)
    if [ "$VERBOSE" = true ]; then
        timeout 600 bash -c "$build_command"
        local exit_code=$?
    else
        timeout 600 bash -c "$build_command" >/dev/null 2>&1
        local exit_code=$?
    fi
    
    cd - >/dev/null
    
    if [ $exit_code -eq 0 ]; then
        log_success "$planner_name built successfully"
        SUCCESS_LIST+=("$planner_name")
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        return 0
    elif [ $exit_code -eq 124 ]; then
        log_error "$planner_name build timed out (>10 minutes)"
        FAILURE_LIST+=("$planner_name (timeout)")
        FAILURE_COUNT=$((FAILURE_COUNT + 1))
        return 1
    else
        log_error "$planner_name build failed (exit code: $exit_code)"
        FAILURE_LIST+=("$planner_name (build error)")
        FAILURE_COUNT=$((FAILURE_COUNT + 1))
        return 1
    fi
}

# Build individual planners
build_fast_downward() {
    build_planner "Fast-Downward" "planners/downward" "./build.py"
}

build_symk() {
    build_planner "SymK" "planners/symk" "./build.py"
}

build_enhsp() {
    build_planner "ENHSP" "planners/enhsp" "./compile"
}

build_optic() {
    build_planner "OPTIC" "planners/optic" "mkdir -p build && cd build && cmake .. && make"
}

build_powerlifted() {
    build_planner "PowerLifted" "planners/powerlifted" "./build.py"
}

build_popf() {
    build_planner "POPF" "planners/popf" "mkdir -p build && cd build && cmake -DCMAKE_BUILD_RPATH='$ORIGIN' -DCMAKE_INSTALL_RPATH='$ORIGIN' .. && make"
}

build_nextflap() {
    # NextFLAP is a C++ planner (despite the historic Java-build probe
    # that used to live here). It ships its own GNU `makefile` and a
    # bundled libz3.so under planners/nextflap/z3/lib/. On modern
    # toolchains (gcc 13+, libstdc++ 13 in C++20 mode) the build fails
    # because sas/sasTask.cpp calls std::find without including
    # <algorithm>; scripts/patch_nextflap.sh adds that include in-place
    # without modifying the upstream submodule beyond a working-tree fix.
    if [ ! -f "planners/nextflap/makefile" ]; then
        log_warning "NextFLAP: makefile not found"
        SKIPPED_LIST+=("NextFLAP (no makefile)")
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        return
    fi
    if [ -x "scripts/patch_nextflap.sh" ]; then
        scripts/patch_nextflap.sh planners/nextflap >/dev/null 2>&1 \
            || log_warning "NextFLAP: patch_nextflap.sh failed; trying build anyway"
    fi
    build_planner "NextFLAP" "planners/nextflap" "make"
}

build_tfd() {
    build_planner "TFD" "planners/tfd" "./build"
}

build_vhpop() {
    # Upstream VHPOP does not ship configure/Makefile.in and uses -Werror,
    # which fails on modern GCC (std::binary_function deprecation).
    # scripts/patch_vhpop.sh runs autoreconf and relaxes that one warning,
    # all in the local working tree (submodule has ignore=dirty in .gitmodules).
    if [[ -x scripts/patch_vhpop.sh ]]; then
        log_info "Preparing VHPOP (autoreconf + local patch)..."
        if ! scripts/patch_vhpop.sh planners/vhpop >/dev/null 2>&1; then
            log_warning "scripts/patch_vhpop.sh failed; VHPOP build will likely fail."
        fi
    fi
    build_planner "VHPOP" "planners/vhpop" "./configure && make"
}

build_madagascar() {
    # Build all three variants
    local variants=("Mp" "MpC" "M")
    local madagascar_success=0
    
    for variant in "${variants[@]}"; do
        log_info "Building MADAGASCAR variant: $variant"
        cd "planners/madagascar"
        
        # Modify Makefile for this variant
        case $variant in
            "Mp")
                sed -i 's/^#*VERSION = .*/VERSION = -DMPDOWNLOAD/' Makefile
                sed -i 's/^#*EXECUTABLE=.*/EXECUTABLE=Mp/' Makefile
                ;;
            "MpC")
                sed -i 's/^#*VERSION = .*/VERSION = -DCMPDOWNLOAD/' Makefile
                sed -i 's/^#*EXECUTABLE=.*/EXECUTABLE=MpC/' Makefile
                ;;
            "M")
                sed -i 's/^#*VERSION = .*/VERSION = -DVSIDS/' Makefile
                sed -i 's/^#*EXECUTABLE=.*/EXECUTABLE=M/' Makefile
                ;;
        esac
        
        if [ "$CLEAN" = true ]; then
            make clean >/dev/null 2>&1 || true
        fi
        
        if [ "$VERBOSE" = true ]; then
            make
        else
            make >/dev/null 2>&1
        fi
        
        if [ $? -eq 0 ]; then
            log_success "MADAGASCAR $variant built successfully"
            madagascar_success=$((madagascar_success + 1))
        else
            log_error "MADAGASCAR $variant build failed"
        fi
        
        cd - >/dev/null
    done
    
    if [ $madagascar_success -gt 0 ]; then
        SUCCESS_LIST+=("MADAGASCAR ($madagascar_success variants)")
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        FAILURE_LIST+=("MADAGASCAR (all variants failed)")
        FAILURE_COUNT=$((FAILURE_COUNT + 1))
    fi
}

build_ff_planners() {
    local ff_planners=("ff" "ff-x" "metric-ff" "conformant-ff" "contingent-ff" "probabilistic-ff")
    
    for planner in "${ff_planners[@]}"; do
        if ! is_selected_planner "$planner"; then
            continue
        fi
        build_planner "FF-$planner" "planners/$planner" "make"
    done
}

build_lpg() {
    local lpg_success=0

    if build_planner "LPG-td (lpg)" "planners/lpg" "./configure >/dev/null 2>&1"; then
        lpg_success=$((lpg_success + 1))
    fi
    if build_planner "LPG-td (lpg-probing)" "planners/lpg" "./configure -probing >/dev/null 2>&1"; then
        lpg_success=$((lpg_success + 1))
    fi

    if [ -d "planners/lpg" ]; then
        (cd "planners/lpg" && ./configure >/dev/null 2>&1) || true
    fi

    if [ $lpg_success -eq 2 ]; then
        return 0
    fi
    return 1
}

# Build VAL (KCL-Planning plan validation tool).
# VAL is a CMake project that produces several executables under build/bin/,
# most importantly:
#   - VAL/build/bin/Validate : plan validation (used by run_planner.py --validate)
#   - VAL/build/bin/Parser   : PDDL parser / syntax checker
# Standard build: mkdir -p build && cd build && cmake .. && make
build_val() {
    build_planner "VAL" "VAL" "mkdir -p build && cd build && cmake -DCMAKE_BUILD_TYPE=Release .. && make -j"
}

# Generate final report
generate_report() {
    log_info "Build Summary:"
    log_info "=============="
    log_success "Successful builds: $SUCCESS_COUNT"
    log_error "Failed builds: $FAILURE_COUNT"
    log_warning "Skipped builds: $SKIPPED_COUNT"
    
    if [ ${#SUCCESS_LIST[@]} -gt 0 ]; then
        log_success "Successfully built planners:"
        for planner in "${SUCCESS_LIST[@]}"; do
            echo "  $planner"
        done
    fi
    
    if [ ${#FAILURE_LIST[@]} -gt 0 ]; then
        log_error "Failed to build planners:"
        for planner in "${FAILURE_LIST[@]}"; do
            echo "  Failed: $planner"
        done
    fi
    
    if [ ${#SKIPPED_LIST[@]} -gt 0 ]; then
        log_warning "Skipped planners:"
        for planner in "${SKIPPED_LIST[@]}"; do
            echo "  - $planner"
        done
    fi
    
    log_info "Detailed build log saved to: $BUILD_LOG"
    
    if [ $FAILURE_COUNT -eq 0 ] && [ $SKIPPED_COUNT -eq 0 ]; then
        log_success "All planners built successfully!"
        exit 0
    else
        log_warning "Some planners failed to build or were skipped."
        exit 1
    fi
}

# Main execution
main() {
    log_info "PDDL Solvers Build Script Starting..."
    echo "Build log: $BUILD_LOG" > "$BUILD_LOG"

    if [[ ${#SELECTED_PLANNERS[@]} -gt 0 ]]; then
        log_info "Selected planners: ${SELECTED_PLANNERS[*]}"
    else
        log_info "Selected planners: all"
    fi

    if [[ "$CLEAN_ONLY" == true ]]; then
        clean_selected_planners
        log_success "Clean-only mode completed"
        exit 0
    fi
    
    # Check dependencies
    check_dependencies
    
    # Initialize submodules
    initialize_submodules

    # Configure local submodule ignore patterns for generated build artifacts
    configure_submodule_ignores

    # Configure local skip-worktree rules for tracked generated files
    configure_local_skip_worktree
    
    # Download direct source planners
    download_madagascar
    
    # Build all planners (continue on failure to build as many as possible)
    is_selected_planner "downward" && build_fast_downward || true
    is_selected_planner "symk" && build_symk || true
    is_selected_planner "enhsp" && build_enhsp || true
    is_selected_planner "optic" && build_optic || true
    is_selected_planner "powerlifted" && build_powerlifted || true
    is_selected_planner "popf" && build_popf || true
    is_selected_planner "nextflap" && build_nextflap || true
    is_selected_planner "tfd" && build_tfd || true
    is_selected_planner "vhpop" && build_vhpop || true
    is_selected_planner "madagascar" && build_madagascar || true

    if is_selected_planner "ff" || is_selected_planner "ff-x" || is_selected_planner "metric-ff" || is_selected_planner "conformant-ff" || is_selected_planner "contingent-ff" || is_selected_planner "probabilistic-ff"; then
        build_ff_planners || true
    fi

    is_selected_planner "lpg" && build_lpg || true

    # Build VAL plan validation tool (optional companion to the planners)
    is_selected_planner "val" && build_val || true

    # Generate final report
    generate_report
}

# Run main function
main "$@"