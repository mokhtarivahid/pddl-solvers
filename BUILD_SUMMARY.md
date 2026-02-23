# PDDL Solvers - Build Status

## Status: 11/16 Planners Working (69%)

**Working:** FF, Fast-Downward, MADAGASCAR, CONFORMANT-FF, CONTINGENT-FF, ENHSP, METRIC-FF, OPTIC, TFD, VHPOP, POWERLIFTED, SYMK

**Not Working:** FF-X, PROBABILISTIC-FF, NextFLAP, POPF

## Recent Fixes
- **TFD**: Python symlink issue resolved
- **VHPOP**: Build completed (autotools)  
- **POWERLIFTED/SYMK**: Handler integration added
- **METRIC-FF**: Symbol conflicts fixed (extern declarations)

## Remaining Issues
- **FF-X**: Symbol conflicts (manual source fixes needed)
- **PROBABILISTIC-FF**: C++ compatibility errors
- **NextFLAP**: Modern C++20 template issues  
- **POPF**: Undefined symbols (try different branch)

## Next Steps
1. Manual symbol conflict resolution for FF-X/PROBABILISTIC-FF
2. Try alternative POPF versions/branches
3. Update NextFLAP for modern C++ standards