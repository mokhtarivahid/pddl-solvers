#!/bin/bash
#
# PDDL Solvers Build Script
# Automatically downloads, initializes, and compiles all planners in the collection
# 
# Usage: ./build_all.sh [options]
#   -v, --verbose    Enable verbose output
#   -c, --clean      Clean before building
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
BUILD_LOG="build_results.log"
SUCCESS_COUNT=0
FAILURE_COUNT=0
SKIPPED_COUNT=0

# Arrays to track results
declare -a SUCCESS_LIST=()
declare -a FAILURE_LIST=()
declare -a SKIPPED_LIST=()

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
        -h|--help)
            echo "PDDL Solvers Build Script"
            echo "Usage: $0 [options]"
            echo "  -v, --verbose    Enable verbose output"
            echo "  -c, --clean      Clean before building"
            echo "  -h, --help       Show this help message"
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
    
    log_info "Building $planner_name..."
    
    if [ ! -d "$planner_dir" ]; then
        log_warning "$planner_name directory not found: $planner_dir"
        SKIPPED_LIST+=("$planner_name (directory not found)")
        ((SKIPPED_COUNT++))
        return 1
    fi
    
    cd "$planner_dir"
    
    # Clean if requested
    if [ "$CLEAN" = true ] && [ -f "Makefile" ]; then
        make clean >/dev/null 2>&1 || true
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
        ((SUCCESS_COUNT++))
        return 0
    elif [ $exit_code -eq 124 ]; then
        log_error "$planner_name build timed out (>10 minutes)"
        FAILURE_LIST+=("$planner_name (timeout)")
        ((FAILURE_COUNT++))
        return 1
    else
        log_error "$planner_name build failed (exit code: $exit_code)"
        FAILURE_LIST+=("$planner_name (build error)")
        ((FAILURE_COUNT++))
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
    build_planner "POPF" "planners/popf" "mkdir -p build && cd build && cmake .. && make"
}

build_nextflap() {
    # NextFLAP is Java-based, check if it has a build script
    if [ -f "planners/nextflap/compile.sh" ]; then
        build_planner "NextFLAP" "planners/nextflap" "./compile.sh"
    elif [ -f "planners/nextflap/build.xml" ]; then
        build_planner "NextFLAP" "planners/nextflap" "ant"
    else
        log_warning "NextFLAP: No known build method found"
        SKIPPED_LIST+=("NextFLAP (no build method)")
        ((SKIPPED_COUNT++))
    fi
}

build_tfd() {
    build_planner "TFD" "planners/tfd" "./build"
}

build_vhpop() {
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
            ((madagascar_success++))
        else
            log_error "MADAGASCAR $variant build failed"
        fi
        
        cd - >/dev/null
    done
    
    if [ $madagascar_success -gt 0 ]; then
        SUCCESS_LIST+=("MADAGASCAR ($madagascar_success variants)")
        ((SUCCESS_COUNT++))
    else
        FAILURE_LIST+=("MADAGASCAR (all variants failed)")
        ((FAILURE_COUNT++))
    fi
}

build_ff_planners() {
    local ff_planners=("ff" "ff-x" "metric-ff" "conformant-ff" "contingent-ff" "probabilistic-ff")
    
    for planner in "${ff_planners[@]}"; do
        build_planner "FF-$planner" "planners/$planner" "make"
    done
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
    
    # Check dependencies
    check_dependencies
    
    # Initialize submodules
    initialize_submodules
    
    # Download direct source planners
    download_madagascar
    
    # Build all planners (continue on failure to build as many as possible)
    build_fast_downward || true
    build_symk || true  
    build_enhsp || true
    build_optic || true
    build_powerlifted || true
    build_popf || true
    build_nextflap || true
    build_tfd || true
    build_vhpop || true
    build_madagascar || true
    build_ff_planners || true
    
    # Generate final report
    generate_report
}

# Run main function
main "$@"