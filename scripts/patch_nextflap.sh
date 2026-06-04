#!/usr/bin/env bash
# patch_nextflap.sh -- Local-only preparation of the NextFLAP submodule so
# it compiles cleanly with modern toolchains (gcc 13+, C++20) on a fresh
# `git clone --recursive` of pddl-solvers.
#
# Upstream policy
# ---------------
# We do NOT modify the upstream NextFLAP repo (github.com/ossaver/NextFLAP).
# All fixups live here in pddl-solvers and are applied in-place to the
# checked-out submodule working tree before each build. The submodule is
# declared with `ignore = dirty` in .gitmodules, so these local edits do
# not affect the parent repo's `git status`.
#
# What this script does
# ---------------------
# 1. Add a missing `#include <algorithm>` to sas/sasTask.cpp.
#    sasTask.cpp calls `std::find(...)` in several places but only
#    includes <limits>, <time.h> and sasTask.h (which itself pulls in
#    <vector>, <unordered_map>, etc. but never <algorithm>). With
#    libstdc++ 13 the <algorithm> header is no longer transitively
#    included and the build fails with
#       "no matching function for call to 'find(...)'".
#    The aiplan4eu/up-nextflap fork applies the same fix.
#
# 2. (Reserved) place for future modern-toolchain fixups; the script is
#    structured so additional patches can be appended idempotently.
#
# Idempotency
# -----------
# Each patch uses a marker comment so subsequent invocations are no-ops.
#
# Usage:  scripts/patch_nextflap.sh [nextflap_dir]
# Default nextflap_dir is planners/nextflap relative to the current
# working directory (which build_all.sh sets to the repo root).

set -euo pipefail

NEXTFLAP_DIR="${1:-planners/nextflap}"

if [[ ! -d "$NEXTFLAP_DIR" ]]; then
    echo "[patch_nextflap] ERROR: '$NEXTFLAP_DIR' not found." >&2
    exit 1
fi

# --- Step 1: add missing <algorithm> include to sas/sasTask.cpp --------------
SAS_TASK_CPP="$NEXTFLAP_DIR/sas/sasTask.cpp"
MARKER="// pddl-solvers: added <algorithm> for std::find on libstdc++ 13+"

if [[ ! -f "$SAS_TASK_CPP" ]]; then
    echo "[patch_nextflap] ERROR: '$SAS_TASK_CPP' not found." >&2
    exit 1
fi

if grep -qF "$MARKER" "$SAS_TASK_CPP"; then
    echo "[patch_nextflap] $SAS_TASK_CPP already patched, skipping."
elif grep -qE '^[[:space:]]*#include[[:space:]]*<algorithm>' "$SAS_TASK_CPP"; then
    echo "[patch_nextflap] $SAS_TASK_CPP already includes <algorithm>, skipping."
else
    # Insert the include right after the existing #include "sasTask.h" line so
    # it comes after all upstream headers but before any function definitions.
    tmp="$(mktemp)"
    awk -v marker="$MARKER" '
        BEGIN { inserted = 0 }
        {
            print $0
            if (!inserted && $0 ~ /^[[:space:]]*#include[[:space:]]*"sasTask\.h"/) {
                print marker
                print "#include <algorithm>"
                inserted = 1
            }
        }
        END {
            if (!inserted) {
                # Fallback: append at end of file (still valid, just less tidy).
                print marker
                print "#include <algorithm>"
            }
        }
    ' "$SAS_TASK_CPP" > "$tmp"
    mv "$tmp" "$SAS_TASK_CPP"
    echo "[patch_nextflap] Inserted <algorithm> include into $SAS_TASK_CPP."
fi

echo "[patch_nextflap] Done."
