#!/usr/bin/env bash
# patch_vhpop.sh -- Local-only preparation of the VHPOP submodule so it
# compiles cleanly with modern toolchains (gcc 13+, C++17 mode) on a
# fresh `git clone --recursive` of pddl-solvers.
#
# Upstream policy
# ---------------
# We do NOT modify the upstream VHPOP repo (github.com/hlsyounes/vhpop).
# All fixups live here in pddl-solvers and are applied in-place to the
# checked-out submodule working tree before each build. The submodule is
# declared with `ignore = dirty` in .gitmodules, so these local edits do
# not affect the parent repo's `git status`.
#
# What this script does
# ---------------------
# 1. autoreconf -fi
#    Upstream does NOT ship `configure`, `Makefile.in`, `ltmain.sh`,
#    `aclocal.m4`, etc. On a truly fresh clone those files do not exist
#    and `./configure && make` would fail with "No such file". Running
#    `autoreconf -fi` at the top level regenerates them for both vhpop
#    and the bundled gtest subproject (which otherwise also fails with
#    "cannot find required auxiliary files: ltmain.sh").
#
# 2. Relax -Werror for std::binary_function deprecation
#    Upstream sets `AM_CXXFLAGS = -Wall -Werror` and inherits from
#    `std::binary_function`, which is deprecated in C++17 and removed
#    in C++20. On gcc 13 this triggers
#    `-Werror=deprecated-declarations` and aborts the build. We append
#    `-Wno-error=deprecated-declarations` so the warning is still shown
#    but no longer fatal. All other `-Werror` checks remain enforced.
#
# Idempotency
# -----------
# Both steps are safe to re-run. The patch step uses a marker comment
# so subsequent invocations are no-ops. autoreconf is also idempotent.
#
# Usage:  scripts/patch_vhpop.sh [vhpop_dir]
# Default vhpop_dir is planners/vhpop relative to the current working
# directory (which build_all.sh sets to the repo root).

set -euo pipefail

VHPOP_DIR="${1:-planners/vhpop}"

if [[ ! -d "$VHPOP_DIR" ]]; then
    echo "[patch_vhpop] ERROR: '$VHPOP_DIR' not found." >&2
    exit 1
fi

# --- Step 1: regenerate autotools files if missing ---------------------------
if [[ ! -f "$VHPOP_DIR/configure" || ! -f "$VHPOP_DIR/Makefile.in" ]]; then
    if ! command -v autoreconf >/dev/null 2>&1; then
        echo "[patch_vhpop] ERROR: autoreconf not found. Install autoconf, automake, libtool." >&2
        exit 1
    fi
    echo "[patch_vhpop] Regenerating autotools files via autoreconf -fi..."
    ( cd "$VHPOP_DIR" && autoreconf -fi ) >/dev/null
    echo "[patch_vhpop] autoreconf complete."
else
    echo "[patch_vhpop] autotools files already present, skipping autoreconf."
fi

# --- Step 2: relax -Werror for the binary_function deprecation ---------------
MARKER="# pddl-solvers: relaxed -Werror for std::binary_function deprecation"
ORIGINAL_LINE="AM_CXXFLAGS = -Wall -Werror"
PATCHED_LINE="AM_CXXFLAGS = -Wall -Werror -Wno-error=deprecated-declarations"

patch_file() {
    local f="$1"
    if [[ ! -f "$f" ]]; then
        return 0
    fi
    if grep -qF "$MARKER" "$f"; then
        echo "[patch_vhpop] $f already patched, skipping."
        return 0
    fi
    if ! grep -qxF "$ORIGINAL_LINE" "$f"; then
        echo "[patch_vhpop] $f has no exact '$ORIGINAL_LINE' line, skipping."
        return 0
    fi
    # awk avoids sed delimiter / escaping pitfalls.
    local tmp="${f}.patch.tmp"
    awk -v orig="$ORIGINAL_LINE" -v marker="$MARKER" -v patched="$PATCHED_LINE" '
        $0 == orig {
            print marker
            print patched
            next
        }
        { print }
    ' "$f" > "$tmp"
    mv "$tmp" "$f"
    echo "[patch_vhpop] Patched $f"
}

# Makefile.am is the autotools input; Makefile.in is what ./configure reads to
# generate Makefile; the in-tree Makefile (if any) is patched too so a bare
# `make` after a stale configure also picks up the fix.
patch_file "$VHPOP_DIR/Makefile.am"
patch_file "$VHPOP_DIR/Makefile.in"
patch_file "$VHPOP_DIR/Makefile"

echo "[patch_vhpop] Done."
