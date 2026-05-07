#!/usr/bin/env python3
"""
PDDL Requirements Analyzer

This module analyzes PDDL domain files to extract requirements and identify
which planners can solve the problems based on their supported features.

Author: PDDL Solvers Suite
License: MIT
"""

import re
import os
from pathlib import Path
from typing import Any, Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
import json
from planner_capabilities import PlannerCapabilitiesCatalog, PlannerCapabilities


@dataclass
class PlannerCapability:
    """Represents a planner's capabilities and supported PDDL features."""
    name: str
    supported_requirements: Set[str]
    pddl_version: str
    description: str
    notes: str = ""
    performance_category: str = "medium"  # low, medium, high
    optimization: bool = False  # True if supports optimization
    temporal: bool = False  # True if supports temporal planning
    approach_tags: Set[str] = field(default_factory=set)  # classical, adl, numeric, temporal, lifted, uncertainty, probabilistic
    temporal_only: bool = False  # True if planner should only be used for temporal domains
    reliability: str = "medium"  # low, medium, high - used for prioritizing stable planners


class PDDLRequirementsParser:
    """Parser for extracting requirements from PDDL domain files."""
    
    def __init__(self):
        # Standard PDDL requirements from PDDL 1.2, 2.1, 2.2, 3.0, etc.
        self.known_requirements = {
            # PDDL 1.2 (Basic)
            'strips', 'typing', 'disjunctive-preconditions', 'equality',
            'existential-preconditions', 'universal-preconditions',
            'quantified-preconditions', 'conditional-effects',
            'action-expansions', 'foreach-expansions', 'dag-expansions',
            'domain-axioms', 'subgoals-through-axioms', 'safety-constraints',
            'expression-evaluation', 'fluents', 'open-world', 'true-negation',
            'adl', 'ucpop',
            
            # PDDL 2.1 (Numeric and Temporal)
            'numeric-fluents', 'durative-actions', 'durative-inequalities',
            'continuous-effects', 'negative-preconditions',
            
            # PDDL 2.2 (Extensions)
            'derived-predicates', 'timed-initial-literals',
            
            # PDDL 3.0 (Preferences)
            'preferences', 'constraints',

            # PPDDL / Probabilistic planning
            'probabilistic-effects',
            
            # Common aliases and variations
            'fluents', 'metrics', 'object-fluents'
        }
    
    def parse_domain_file(self, domain_path: str) -> Dict:
        """
        Parse a PDDL domain file and extract information including requirements.
        
        Args:
            domain_path: Path to the PDDL domain file
            
        Returns:
            Dictionary containing domain information and requirements
        """
        domain_path = Path(domain_path)
        if not domain_path.exists():
            raise FileNotFoundError(f"Domain file not found: {domain_path}")
        
        with open(domain_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove comments
        content = re.sub(r';[^\n]*', '', content)
        
        result = {
            'file_path': str(domain_path),
            'domain_name': self._extract_domain_name(content),
            'requirements': self._extract_requirements(content),
            'types': self._extract_types(content),
            'predicates': self._extract_predicates(content),
            'functions': self._extract_functions(content),
            'actions': self._extract_actions(content),
            'durative_actions': self._extract_durative_actions(content),
            'derived_predicates': self._extract_derived_predicates(content),
            'pddl_version': self._infer_pddl_version(content)
        }
        
        return result
    
    def _extract_domain_name(self, content: str) -> str:
        """Extract domain name from PDDL content."""
        match = re.search(r'\(define\s*\(\s*domain\s+([^)]+)\s*\)', content, re.IGNORECASE)
        return match.group(1).strip() if match else "unknown"
    
    def _extract_requirements(self, content: str) -> List[str]:
        """Extract requirements from PDDL domain content."""
        # Find requirements section
        req_match = re.search(r'\(\s*:requirements\s+([^)]+)\)', content, re.IGNORECASE | re.DOTALL)
        
        if not req_match:
            return []
        
        req_text = req_match.group(1)
        
        # Extract individual requirements (they start with :)
        requirements = re.findall(r':([a-zA-Z0-9_-]+)', req_text)
        
        # Filter known requirements and normalize
        normalized_reqs = []
        for req in requirements:
            req_normalized = req.lower().replace('_', '-')
            if req_normalized in self.known_requirements:
                normalized_reqs.append(req_normalized)
            else:
                # Keep unknown requirements for completeness
                normalized_reqs.append(req_normalized)
        
        return normalized_reqs
    
    def _extract_types(self, content: str) -> List[str]:
        """Extract type definitions from domain."""
        type_match = re.search(r'\(\s*:types\s+([^)]+)\)', content, re.IGNORECASE | re.DOTALL)
        if not type_match:
            return []
        
        types_text = type_match.group(1)
        # Basic extraction - could be improved for hierarchical types
        types = re.findall(r'([a-zA-Z0-9_-]+)', types_text)
        return [t for t in types if t not in ['-', 'object']]
    
    def _extract_predicates(self, content: str) -> int:
        """Count predicate definitions."""
        pred_matches = re.findall(r'\(\s*([a-zA-Z0-9_-]+)\s+[^)]*\)', 
                                  re.search(r'\(\s*:predicates\s+([^)]+(?:\([^)]*\))*[^)]*)\)', 
                                           content, re.IGNORECASE | re.DOTALL).group(1) 
                                  if re.search(r'\(\s*:predicates\s+', content, re.IGNORECASE) else "")
        return len(pred_matches)
    
    def _extract_functions(self, content: str) -> int:
        """Count function definitions (numeric fluents)."""
        func_match = re.search(r'\(\s*:functions\s+([^)]+(?:\([^)]*\))*[^)]*)\)', content, re.IGNORECASE | re.DOTALL)
        if not func_match:
            return 0
        
        func_text = func_match.group(1)
        func_matches = re.findall(r'\(\s*([a-zA-Z0-9_-]+)', func_text)
        return len(func_matches)
    
    def _extract_actions(self, content: str) -> int:
        """Count regular action definitions."""
        action_matches = re.findall(r'\(\s*:action\s+', content, re.IGNORECASE)
        return len(action_matches)
    
    def _extract_durative_actions(self, content: str) -> int:
        """Count durative action definitions."""
        durative_matches = re.findall(r'\(\s*:durative-action\s+', content, re.IGNORECASE)
        return len(durative_matches)
    
    def _extract_derived_predicates(self, content: str) -> int:
        """Count derived predicate definitions."""
        derived_matches = re.findall(r'\(\s*:derived\s+', content, re.IGNORECASE)
        return len(derived_matches)
    
    def _infer_pddl_version(self, content: str) -> str:
        """Infer PDDL version based on features used."""
        content_lower = content.lower()
        
        # Check for version-specific features
        if ':durative-action' in content_lower or ':numeric-fluents' in content_lower:
            if ':derived' in content_lower or ':timed-initial-literals' in content_lower:
                return "PDDL 2.2+"
            return "PDDL 2.1+"
        elif ':preferences' in content_lower or ':constraints' in content_lower:
            return "PDDL 3.0+"
        elif any(feature in content_lower for feature in [':adl', ':conditional-effects', ':quantified-preconditions']):
            return "PDDL 1.2+"
        else:
            return "PDDL 1.2"


class PlannerCapabilityDatabase:
    """Database of planner capabilities and supported PDDL features."""
    
    def __init__(self, catalog: Optional[PlannerCapabilitiesCatalog] = None, planner_entries: Optional[Dict[str, Any]] = None):
        self.catalog = catalog or PlannerCapabilitiesCatalog.default()
        if planner_entries:
            self.planners = self._load_planners_from_yaml_entries(planner_entries)
        else:
            self.planners = self._initialize_planner_database()
        self._apply_catalog_overrides()

    def _load_planners_from_yaml_entries(self, planner_entries: Dict[str, Any]) -> Dict[str, PlannerCapability]:
        planners: Dict[str, PlannerCapability] = {}
        for name, entry in planner_entries.items():
            if not isinstance(entry, dict):
                continue
            planners[name] = PlannerCapability(
                name=entry.get('name', name),
                supported_requirements=set(entry.get('supported_requirements', [])),
                pddl_version=entry.get('pddl_version', 'PDDL 1.2'),
                description=entry.get('description', ''),
                notes=entry.get('notes', ''),
                performance_category=entry.get('performance_category', 'medium'),
                optimization=bool(entry.get('optimization', False)),
                temporal=bool(entry.get('temporal', False)),
                approach_tags=set(entry.get('approach_tags', [])),
                temporal_only=bool(entry.get('temporal_only', False)),
                reliability=entry.get('reliability', 'medium'),
            )
        return planners

    def _apply_catalog_overrides(self):
        """Apply runtime behavior flag overrides (optimization, temporal, temporal_only).
        
        Note: To modify planner capabilities (add/remove requirements),
        edit the planner entry directly in planner_capabilities.yaml.
        This method only handles runtime behavior flags.
        """
        for planner_name, overrides in self.catalog.planner_overrides.items():
            planner = self.planners.get(planner_name)
            if planner is None:
                continue

            # Apply only simple flag overrides
            if 'optimization' in overrides:
                planner.optimization = bool(overrides['optimization'])
            if 'temporal' in overrides:
                planner.temporal = bool(overrides['temporal'])
            if 'temporal_only' in overrides:
                planner.temporal_only = bool(overrides['temporal_only'])
    
    def _initialize_planner_database(self) -> Dict[str, PlannerCapability]:
        """Initialize the database with known planner capabilities."""
        
        # Basic PDDL 1.2 requirements
        basic_reqs = {'strips', 'typing', 'negative-preconditions'}
        adl_reqs = basic_reqs | {'disjunctive-preconditions', 'equality', 
                                'existential-preconditions', 'universal-preconditions',
                                'quantified-preconditions', 'conditional-effects', 'adl'}
        
        # Numeric planning requirements  
        numeric_reqs = basic_reqs | {'numeric-fluents', 'fluents'}
        
        # Temporal planning requirements
        temporal_reqs = basic_reqs | {'durative-actions', 'durative-inequalities', 'numeric-fluents'}
        
        planners = {
            # Fast Downward - Excellent PDDL support
            'downward': PlannerCapability(
                name='Fast Downward',
                supported_requirements=adl_reqs | numeric_reqs | {'derived-predicates'},
                pddl_version='PDDL 2.2',
                description='State-of-the-art classical planner with excellent performance',
                performance_category='high',
                optimization=True,
                temporal=False,
                approach_tags={'classical', 'adl', 'numeric', 'optimal', 'satisficing'},
                notes='Supports most PDDL 1.2 and 2.1 features except temporal planning'
            ),
            
            # FF Family - Classical planning
            'ff': PlannerCapability(
                name='FF (Fast Forward)',
                supported_requirements=basic_reqs | {'conditional-effects'},
                pddl_version='PDDL 1.2',
                description='Classic heuristic search planner, fast and reliable',
                performance_category='high',
                optimization=False,
                temporal=False,
                approach_tags={'classical', 'adl-lite', 'satisficing'},
                notes='Good for basic STRIPS and ADL planning'
            ),
            
            'metric-ff': PlannerCapability(
                name='Metric-FF',
                supported_requirements=numeric_reqs | {'conditional-effects'},
                pddl_version='PDDL 2.1',
                description='Extension of FF with numeric fluent support',
                performance_category='medium',
                optimization=True,
                temporal=False,
                approach_tags={'numeric', 'classical', 'optimal', 'satisficing'},
                notes='Handles numeric planning problems'
            ),
            
            # Temporal Planners
            'optic': PlannerCapability(
                name='OPTIC',
                supported_requirements=temporal_reqs | {'continuous-effects', 'preferences'},
                pddl_version='PDDL 2.1+',
                description='Advanced temporal planner with continuous effects',
                performance_category='high',
                optimization=True,
                temporal=True,
                approach_tags={'temporal', 'numeric', 'optimal', 'satisficing'},
                notes='Excellent for temporal and numeric planning'
            ),
            
            'popf': PlannerCapability(
                name='POPF',
                supported_requirements=temporal_reqs,
                pddl_version='PDDL 2.1',
                description='Temporal planner, predecessor to OPTIC',
                performance_category='medium',
                optimization=False,
                temporal=True,
                approach_tags={'temporal', 'numeric', 'satisficing'},
                notes='Good for basic temporal planning'
            ),
            
            # Numeric and Hybrid Planners
            'enhsp': PlannerCapability(
                name='ENHSP',
                supported_requirements=numeric_reqs | {'continuous-effects', 'constraints'},
                pddl_version='PDDL 2.1+',
                description='Heuristic search planner for expressive numeric domains',
                performance_category='high',
                optimization=True,
                temporal=False,
                approach_tags={'numeric', 'optimal', 'satisficing', 'constraints'},
                notes='Specialized in numeric planning; does not reliably support durative actions'
            ),
            
            # Lifted Planning
            'powerlifted': PlannerCapability(
                name='PowerLifted',
                supported_requirements=basic_reqs | {'equality'},
                pddl_version='PDDL 1.2+',
                description='Lifted classical planner using first-order representations',
                performance_category='medium',
                optimization=True,
                temporal=False,
                approach_tags={'classical', 'lifted', 'satisficing', 'optimal'},
                notes='Lifted STRIPS-like planning; no conditional effects, quantifiers, or axioms'
            ),
            
            # Symbolic Planners
            'symk': PlannerCapability(
                name='SymK',
                supported_requirements=adl_reqs | {'derived-predicates'},
                pddl_version='PDDL 1.2',
                description='Symbolic planner using binary decision diagrams',
                performance_category='medium',
                optimization=True,
                temporal=False,
                approach_tags={'classical', 'adl', 'optimal', 'topk'},
                notes='Supports top-k/top-q planning; supports conditional effects and derived predicates'
            ),
            
            # Partial Order Planners
            'vhpop': PlannerCapability(
                name='VHPOP', 
                supported_requirements=adl_reqs,
                pddl_version='PDDL 1.2+',
                description='Partial-order causal-link planner',
                performance_category='low',
                optimization=True,
                temporal=False,
                approach_tags={'classical', 'adl', 'partial-order', 'optimal'},
                notes='Academic planner, good for small problems'
            ),
            
            # Conformant and Contingent Planning
            'conformant-ff': PlannerCapability(
                name='Conformant-FF',
                supported_requirements=basic_reqs,
                pddl_version='PDDL 1.2',
                description='Planner for conformant (uncertainty) planning',
                performance_category='low',
                optimization=False,
                temporal=False,
                approach_tags={'classical', 'uncertainty', 'conformant'},
                notes='Specialized for planning under uncertainty'
            ),
            
            'contingent-ff': PlannerCapability(
                name='Contingent-FF',
                supported_requirements=basic_reqs,
                pddl_version='PDDL 1.2',
                description='Planner for contingent planning with observations',
                performance_category='low',
                optimization=False,
                temporal=False,
                approach_tags={'classical', 'uncertainty', 'contingent'},
                notes='Handles conditional planning with observations'
            ),
            
            # Probabilistic Planning
            'probabilistic-ff': PlannerCapability(
                name='Probabilistic-FF',
                supported_requirements=adl_reqs | {'probabilistic-effects'},
                pddl_version='PDDL 1.2+ / PPDDL extensions',
                description='Probabilistic planning with weighted model counting',
                performance_category='low',
                optimization=False,
                temporal=False,
                approach_tags={'probabilistic', 'uncertainty', 'adl'},
                notes='Supports probabilistic initial belief states and probabilistic effects'
            ),
            
            # Additional planners
            'tfd': PlannerCapability(
                name='TFD (Temporal Fast Downward)',
                supported_requirements=temporal_reqs,
                pddl_version='PDDL 2.1',
                description='Temporal extension of Fast Downward',
                performance_category='medium',
                optimization=True,
                temporal=True,
                approach_tags={'temporal', 'numeric', 'optimal', 'satisficing'},
                temporal_only=True,
                notes='Temporal planning based on Fast Downward'
            ),
            
            'madagascar': PlannerCapability(
                name='Madagascar',
                supported_requirements=basic_reqs | {'conditional-effects'},
                pddl_version='PDDL 1.2',
                description='SAT-based planner using compilation to SAT',
                performance_category='medium',
                optimization=True,
                temporal=False,
                approach_tags={'classical', 'sat', 'optimal', 'satisficing'},
                notes='Uses SAT solvers for planning'
            ),
            
            'nextflap': PlannerCapability(
                name='NextFLAP',
                supported_requirements=basic_reqs,
                pddl_version='PDDL 1.2',
                description='Learning-based planner',
                performance_category='medium',
                optimization=False,
                temporal=False,
                approach_tags={'classical', 'hybrid'},
                notes='Experimental learning-based approach'
            ),
            
            'ff-x': PlannerCapability(
                name='FF-X',
                supported_requirements=adl_reqs | {'derived-predicates'},
                pddl_version='PDDL 2.1 (derived predicates)',
                description='FF variant with support for derived predicates (axioms)',
                performance_category='medium',
                optimization=False,
                temporal=False,
                approach_tags={'classical', 'adl', 'derived-predicates', 'satisficing'},
                notes='Handles ADL and PDDL 2.1 derived predicates (axioms)'
            ),

            # PDDL 2.2 Local Search Planner
            'lpg': PlannerCapability(
                name='LPG-td',
                supported_requirements=temporal_reqs | adl_reqs | {'derived-predicates', 'timed-initial-literals'},
                pddl_version='PDDL 2.2',
                description='Local search planner supporting temporal, numeric, derived predicates and timed initial literals',
                performance_category='medium',
                optimization=False,
                temporal=True,
                approach_tags={'temporal', 'numeric', 'classical', 'adl', 'satisficing', 'local-search'},
                notes='IPC 3/4 award-winning local search on planning graphs; handles PDDL 2.2 (timed-initial-literals, derived-predicates)'
            )
        }
        
        return planners
    
    def get_compatible_planners(self, requirements: List[str]) -> List[Tuple[str, PlannerCapability]]:
        """
        Get planners compatible with the given requirements.
        
        Args:
            requirements: List of PDDL requirements
            
        Returns:
            List of tuples: (planner_name, capability)
        """
        compatible = []
        
        for name, planner in self.planners.items():
            eval_info = self.evaluate_planner_compatibility(name, requirements)
            if eval_info['strict_compatible']:
                compatible.append((name, planner))

        compatible.sort(key=lambda x: self._base_priority_key(x[0]))
        
        return compatible

    def _normalize_requirements(self, missing_reqs: Set[str], supported_reqs: Set[str]) -> Set[str]:
        """Normalize and handle requirement aliases and implications."""
        normalized_missing = missing_reqs.copy()
        
        # Handle aliases and implications
        aliases = self.catalog.aliases
        
        # ADL implications
        if 'adl' in supported_reqs:
            normalized_missing -= self.catalog.adl_implied_requirements
        
        # Apply aliases
        for missing in list(normalized_missing):
            if missing in aliases and aliases[missing] in supported_reqs:
                normalized_missing.remove(missing)
        
        return normalized_missing
    
    def _get_critical_missing_requirements(self, missing_reqs: Set[str]) -> Set[str]:
        """Identify which missing requirements are critical (planner cannot handle)."""
        # These requirements are considered critical and cannot be easily worked around
        return missing_reqs & self.catalog.critical_requirements

    def _base_priority_key(self, planner_name: str) -> Tuple[int, int, str]:
        if planner_name in self.catalog.established_priority:
            return (0, self.catalog.established_priority.index(planner_name), planner_name)
        return (1, 0, planner_name)

    def evaluate_planner_compatibility(self, planner_name: str, requirements: List[str]) -> Dict[str, Any]:
        """Return transparent compatibility diagnostics for one planner."""
        planner = self.planners.get(planner_name)
        if planner is None:
            return {
                'planner': planner_name,
                'strict_compatible': False,
                'relaxed_compatible': False,
                'extreme_incompatibility': False,
                'extreme_reasons': ['planner-not-found'],
                'raw_missing': [],
                'normalized_missing': [],
                'critical_missing': [],
                'compatibility_mode': self.catalog.compatibility_mode,
            }

        req_set = set(req.lower().replace('_', '-') for req in requirements)
        raw_missing = req_set - planner.supported_requirements
        normalized_missing = self._normalize_requirements(raw_missing, planner.supported_requirements)
        critical_missing = self._get_critical_missing_requirements(normalized_missing)

        extreme_reasons = []
        is_temporal_domain = 'durative-actions' in req_set
        if 'probabilistic-effects' in req_set and 'probabilistic-effects' not in planner.supported_requirements:
            extreme_reasons.append('missing-probabilistic-effects')
        if is_temporal_domain and not planner.temporal:
            extreme_reasons.append('temporal-domain-but-planner-not-temporal')
        if planner.temporal_only and not is_temporal_domain:
            extreme_reasons.append('planner-temporal-only-but-domain-classical')

        extreme_incompatibility = bool(extreme_reasons)
        if self.catalog.compatibility_mode == 'all-missing':
            strict_compatible = (not extreme_incompatibility) and (not normalized_missing)
        else:
            strict_compatible = (not extreme_incompatibility) and (not critical_missing)
        relaxed_compatible = not extreme_incompatibility

        return {
            'planner': planner_name,
            'strict_compatible': strict_compatible,
            'relaxed_compatible': relaxed_compatible,
            'extreme_incompatibility': extreme_incompatibility,
            'extreme_reasons': extreme_reasons,
            'raw_missing': sorted(raw_missing),
            'normalized_missing': sorted(normalized_missing),
            'critical_missing': sorted(critical_missing),
            'compatibility_mode': self.catalog.compatibility_mode,
        }

    def get_relaxed_compatible_planners(self, requirements: List[str]) -> List[Tuple[str, 'PlannerCapability']]:
        """
        Return planners that pass only the extreme-incompatibility check.

        This is a lenient fallback: planners that lack soft requirements (ADL
        features, equality, derived-predicates, etc.) are included because many
        planners handle them in practice.  Only fundamentally impossible pairings
        (non-temporal planner vs temporal domain, temporal-only vs classical) are
        excluded.
        """
        compatible = [
            (name, planner)
            for name, planner in self.planners.items()
            if self.evaluate_planner_compatibility(name, requirements)['relaxed_compatible']
        ]
        compatible.sort(key=lambda x: self._base_priority_key(x[0]))
        return compatible

    def is_extreme_incompatibility(self, planner_name: str, requirements: List[str]) -> bool:
        """
        Check if there is an extreme (fundamental) incompatibility between a planner
        and domain requirements that would make planning impossible.

        Extreme incompatibilities:
        - A non-temporal planner (temporal=False) used on a domain with durative-actions
        - A temporal-only planner (temporal_only=True) used on a non-temporal domain

        Soft mismatches (missing ADL features, equality, derived-predicates, etc.)
        are NOT extreme — the planner may still handle the domain in practice.
        """
        info = self.evaluate_planner_compatibility(planner_name, requirements)
        return info['extreme_incompatibility']


class PDDLAnalyzer:
    """Main analyzer that combines parsing and planner matching."""
    
    def __init__(self, repo_root: str = None):
        self.parser = PDDLRequirementsParser()
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.capability_configuration_path = self.repo_root / "planner_capabilities.yaml"
        self.capability_configuration, planner_entries = self._load_capability_configuration(self.capability_configuration_path)
        # Backward-compatible attribute alias used across existing logic.
        self.capability_catalog = self.capability_configuration
        self.planner_db = PlannerCapabilityDatabase(self.capability_catalog, planner_entries)
        self.planners_dir = self.repo_root / "planners"
        # Keep in sync with README Build Status "Working" planners.
        self.working_planners = {
            'downward', 'ff', 'conformant-ff', 'contingent-ff', 'metric-ff',
            'ff-x', 'probabilistic-ff', 'lpg',
            'enhsp', 'symk', 'madagascar', 'optic', 'popf', 'tfd', 'powerlifted'
        }

    def _load_capability_configuration(self, config_path: Path) -> Tuple[PlannerCapabilitiesCatalog, Dict[str, Any]]:
        """Load compatibility and planner capability entries from YAML."""
        spec = PlannerCapabilities(str(config_path))
        catalog, planner_entries, warning = spec.load()
        if warning:
            print(f"Warning: {warning}")
        return catalog, planner_entries

    def _priority_key(self, planner_name: str, planning_approach: str) -> Tuple[int, int, int, int, str]:
        """Generate priority key for planner sorting.
        
        Sorting order (in priority):
        1. Approach-specific vs established vs fallback (0, 1, 2)
        2. Reliability: high=0, medium=1, low=2
        3. Position in approach/established list
        4. Planner name (tiebreaker)
        """
        approach_list = self.capability_catalog.approach_priority.get(planning_approach, [])
        established_list = self.capability_catalog.established_priority
        
        # Reliability score: high < medium < low
        planner = self.planner_db.planners.get(planner_name)
        reliability_order = {'high': 0, 'medium': 1, 'low': 2}
        reliability_score = reliability_order.get(planner.reliability if planner else 'medium', 1)

        if planner_name in approach_list:
            approach_idx = approach_list.index(planner_name)
            established_idx = established_list.index(planner_name) if planner_name in established_list else 10_000
            return (0, reliability_score, approach_idx, established_idx, planner_name)

        if planner_name in established_list:
            return (1, reliability_score, 0, established_list.index(planner_name), planner_name)

        return (2, reliability_score, 0, 0, planner_name)

    def _build_selection_trace(
        self,
        requirements: List[str],
        available_planners: Set[str],
        planning_approach: str,
    ) -> List[Dict[str, Any]]:
        """Explain compatibility and deterministic priority placement per planner."""
        trace = []
        approach_list = self.capability_catalog.approach_priority.get(planning_approach, [])
        established_list = self.capability_catalog.established_priority

        for name, planner in self.planner_db.planners.items():
            compatibility = self.planner_db.evaluate_planner_compatibility(name, requirements)
            priority_group = 'fallback'
            if name in approach_list:
                priority_group = 'approach-priority'
            elif name in established_list:
                priority_group = 'established-priority'

            trace.append({
                'planner': name,
                'planner_name': planner.name,
                'available_in_workspace': name in available_planners,
                'disabled_by_catalog': name in self.capability_catalog.disabled_planners,
                'priority_group': priority_group,
                'priority_key': list(self._priority_key(name, planning_approach)),
                'compatibility': compatibility,
            })

        trace.sort(key=lambda x: tuple(x['priority_key']))
        return trace

    def export_planner_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Export planner capabilities in a JSON-friendly mapping."""
        exported: Dict[str, Dict[str, Any]] = {}
        for name, planner in self.planner_db.planners.items():
            exported[name] = {
                'name': planner.name,
                'description': planner.description,
                'pddl_version': planner.pddl_version,
                'supported_requirements': sorted(planner.supported_requirements),
                'performance_category': planner.performance_category,
                'reliability': planner.reliability,
                'optimization': planner.optimization,
                'temporal': planner.temporal,
                'temporal_only': planner.temporal_only,
                'approach_tags': sorted(planner.approach_tags),
                'notes': planner.notes,
            }
        return exported
    
    def analyze_domain(self, domain_path: str) -> Dict:
        """
        Analyze a PDDL domain file and recommend compatible planners.
        
        Args:
            domain_path: Path to the PDDL domain file
            
        Returns:
            Dictionary with analysis results and planner recommendations
        """
        # Parse the domain file
        domain_info = self.parser.parse_domain_file(domain_path)
        
        # Get compatible planners
        compatible_planners = self.planner_db.get_compatible_planners(domain_info['requirements'])
        planning_approach = self._determine_planning_approach(domain_info['requirements'])
        
        # Filter by available planners in the system
        available_planners = self._get_available_planners()
        selection_trace = self._build_selection_trace(domain_info['requirements'], available_planners, planning_approach)
        available_compatible = [
            (name, planner) for name, planner in compatible_planners
            if name in available_planners and name not in self.capability_catalog.disabled_planners
        ]

        ranked_available_compatible = sorted(
            available_compatible,
            key=lambda x: self._priority_key(x[0], planning_approach)
        )
        
        # Relaxed fallback: planners passing only the extreme-incompatibility check.
        relaxed_planners = self.planner_db.get_relaxed_compatible_planners(domain_info['requirements'])
        strict_names = {name for name, _ in available_compatible}
        available_relaxed = [
            (name, planner) for name, planner in relaxed_planners
            if name in available_planners
            and name not in self.capability_catalog.disabled_planners
            and name not in strict_names
        ]
        ranked_available_relaxed = sorted(
            available_relaxed,
            key=lambda x: self._priority_key(x[0], planning_approach)
        )

        result = {
            'domain_info': domain_info,
            'compatible_planners': compatible_planners,
            'available_compatible_planners': ranked_available_compatible,
            'available_relaxed_planners': ranked_available_relaxed,
            'available_planners': list(available_planners),
            'capability_catalog': {
                'path': str(self.capability_configuration_path),
                'config': self.capability_catalog.to_dict(),
            },
            'selection_trace': selection_trace,
            'planner_capabilities': self.export_planner_capabilities(),
            'analysis_summary': self._generate_analysis_summary(
                domain_info, compatible_planners, ranked_available_compatible, ranked_available_relaxed
            )
        }
        
        return result

    def _get_available_planners(self) -> Set[str]:
        """Get planners that are both marked working and runnable in this workspace."""
        available = set()
        
        if not self.planners_dir.exists():
            return available
        
        for planner_name in self.working_planners:
            if planner_name not in self.planner_db.planners:
                continue
            if self._is_planner_runnable(planner_name):
                available.add(planner_name)
        
        return available

    def _is_planner_runnable(self, planner_name: str) -> bool:
        """Check if a planner has the expected runnable artifact in this repo."""
        planner_dir = self.planners_dir / planner_name
        if not planner_dir.exists() or not planner_dir.is_dir():
            return False

        expected_artifacts = {
            'downward': [planner_dir / 'fast-downward.py'],
            'ff': [planner_dir / 'ff'],
            'conformant-ff': [planner_dir / 'ff'],
            'contingent-ff': [planner_dir / 'ff'],
            'metric-ff': [planner_dir / 'ff'],
            'ff-x': [planner_dir / 'ff'],
            'probabilistic-ff': [planner_dir / 'ff'],
            'lpg': [planner_dir / 'lpg'],
            'enhsp': [planner_dir / 'enhsp.jar'],
            'symk': [planner_dir / 'fast-downward.py'],
            'madagascar': [planner_dir / 'Mp'],
            'optic': [planner_dir / 'build' / 'src' / 'optic' / 'optic-clp'],
            'popf': [planner_dir / 'build' / 'popf'],
            'tfd': [planner_dir / 'downward' / 'tfd'],
            'powerlifted': [planner_dir / 'powerlifted.py']
        }

        artifacts = expected_artifacts.get(planner_name, [])
        return all(path.exists() for path in artifacts)
    
    def _generate_analysis_summary(self, domain_info: Dict,
                                  compatible_planners: List,
                                  available_compatible: List,
                                  available_relaxed: List = None) -> Dict:
        """Generate a summary of the analysis."""
        requirements = domain_info['requirements']
        if available_relaxed is None:
            available_relaxed = []

        # Use relaxed planners for recommendation when strict list is empty.
        planners_for_recommendation = available_compatible if available_compatible else available_relaxed

        summary = {
            'domain_name': domain_info['domain_name'],
            'pddl_version': domain_info['pddl_version'],
            'total_requirements': len(requirements),
            'requirements_list': requirements,
            'total_compatible_planners': len(compatible_planners),
            'available_compatible_planners': len(available_compatible),
            'complexity_level': self._assess_complexity(domain_info),
            'recommended_planner': None,
            'recommended_planner_relaxed': len(available_compatible) == 0 and len(available_relaxed) > 0,
            'planning_approach': self._determine_planning_approach(requirements)
        }

        # Recommend best planner (strict first, relaxed fallback)
        if planners_for_recommendation:
            best_planner = planners_for_recommendation[0]
            summary['recommended_planner'] = {
                'name': best_planner[1].name,
                'system_name': best_planner[0],
                'description': best_planner[1].description,
                'notes': best_planner[1].notes
            }

        return summary
    
    def _assess_complexity(self, domain_info: Dict) -> str:
        """Assess the complexity level of the domain."""
        requirements = set(domain_info['requirements'])
        
        # High complexity indicators
        high_complexity = {'durative-actions', 'continuous-effects', 'derived-predicates', 'preferences'}
        medium_complexity = {'numeric-fluents', 'conditional-effects', 'quantified-preconditions', 'adl'}

        if 'probabilistic-effects' in requirements:
            return 'High'
        
        if requirements & high_complexity:
            return 'High'
        elif requirements & medium_complexity or domain_info['functions'] > 0:
            return 'Medium'
        else:
            return 'Low'
    
    def _determine_planning_approach(self, requirements: List[str]) -> str:
        """Determine the type of planning approach needed."""
        req_set = set(requirements)

        if 'probabilistic-effects' in req_set:
            return 'Probabilistic Planning'
        
        if 'durative-actions' in req_set:
            if 'numeric-fluents' in req_set or 'fluents' in req_set:
                return 'Temporal-Numeric Planning'
            else:
                return 'Temporal Planning'
        elif 'numeric-fluents' in req_set or 'fluents' in req_set:
            return 'Numeric Planning'
        elif 'adl' in req_set or any(r in req_set for r in ['conditional-effects', 'quantified-preconditions']):
            return 'ADL Planning'
        else:
            return 'Classical Planning'
    
    def print_analysis(self, analysis: Dict, verbose: bool = False):
        """Print formatted analysis results."""
        domain_info = analysis['domain_info']
        summary = analysis['analysis_summary']
        
        print("\n" + "="*80)
        print(f"PDDL DOMAIN ANALYSIS: {summary['domain_name']}")
        print("="*80)
        
        print(f"\nDomain File: {domain_info['file_path']}")
        print(f"PDDL Version: {summary['pddl_version']}")
        print(f"Planning Approach: {summary['planning_approach']}")
        print(f"Complexity Level: {summary['complexity_level']}")
        catalog_info = analysis.get('capability_catalog', {})
        if catalog_info:
            print(f"Capability Catalog: {catalog_info.get('path', '')}")
        
        print(f"\nRequirements ({len(summary['requirements_list'])}):")
        for req in summary['requirements_list']:
            print(f"  - :{req}")
        
        if verbose:
            print(f"\nDomain Statistics:")
            print(f"  - Types: {len(domain_info['types'])}")
            print(f"  - Predicates: {domain_info['predicates']}")
            print(f"  - Functions: {domain_info['functions']}")
            print(f"  - Actions: {domain_info['actions']}")
            print(f"  - Durative Actions: {domain_info['durative_actions']}")
            print(f"  - Derived Predicates: {domain_info['derived_predicates']}")
        
        strict_planners = analysis['available_compatible_planners']
        relaxed_planners = analysis.get('available_relaxed_planners', [])
        is_relaxed = summary.get('recommended_planner_relaxed', False)

        if strict_planners:
            print(f"\nCompatible Planners ({summary['total_compatible_planners']} total, {summary['available_compatible_planners']} available):")
            for i, (name, planner) in enumerate(strict_planners):
                status = "AVAILABLE" if name in analysis['available_planners'] else "Not Available"
                print(f"  {i+1}. {planner.name} ({name}) - compatible {status}")
                if verbose:
                    print(f"     {planner.description}")
                    if planner.notes:
                        print(f"     Note: {planner.notes}")
        elif relaxed_planners:
            print(f"\nCompatible Planners (0 strictly compatible — showing partial-match planners):")
            for i, (name, planner) in enumerate(relaxed_planners):
                status = "AVAILABLE" if name in analysis['available_planners'] else "Not Available"
                print(f"  {i+1}. {planner.name} ({name}) - partial match {status}")
                if verbose:
                    print(f"     {planner.description}")
                    if planner.notes:
                        print(f"     Note: {planner.notes}")
        else:
            print(f"\nCompatible Planners (0 total, 0 available):")
            print("  No compatible planners available in the system!")

        if summary['recommended_planner']:
            rec = summary['recommended_planner']
            if is_relaxed:
                print(f"\nRECOMMENDED PLANNER (partial match — may handle domain in practice):")
            else:
                print(f"\nRECOMMENDED PLANNER:")
            print(f"   {rec['name']} ({rec['system_name']})")
            print(f"   {rec['description']}")
            if rec['notes']:
                print(f"   Note: {rec['notes']}")
        else:
            print(f"\nWARNING: No compatible planners available for this domain!")

        if verbose:
            selection_trace = analysis.get('selection_trace', [])
            if selection_trace:
                print("\nSelection Transparency (ordered by catalog priority):")
                for row in selection_trace[:8]:
                    c = row['compatibility']
                    print(
                        f"  - {row['planner_name']} ({row['planner']}): group={row['priority_group']}, "
                        f"available={row['available_in_workspace']}, disabled={row['disabled_by_catalog']}"
                    )
                    if c['normalized_missing']:
                        print(f"      missing: {', '.join(c['normalized_missing'])}")
                    if c['critical_missing']:
                        print(f"      critical missing: {', '.join(c['critical_missing'])}")
                    if c['extreme_reasons']:
                        print(f"      extreme reasons: {', '.join(c['extreme_reasons'])}")
        
        print("\n" + "="*80)


def main():
    """Command-line interface for the PDDL analyzer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze PDDL domains and recommend compatible planners")
    parser.add_argument('domain', help='Path to PDDL domain file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output with detailed statistics')
    parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    parser.add_argument('--repo-root', help='Path to the PDDL solvers repository root')
    
    args = parser.parse_args()
    
    # Initialize analyzer
    repo_root = args.repo_root or os.path.dirname(os.path.abspath(__file__))
    analyzer = PDDLAnalyzer(repo_root)
    
    try:
        # Analyze domain
        analysis = analyzer.analyze_domain(args.domain)
        
        if args.json:
            # JSON output
            json_output = {
                'domain_info': analysis['domain_info'],
                'summary': analysis['analysis_summary'],
                'capability_catalog': analysis.get('capability_catalog', {}),
                'selection_trace': analysis.get('selection_trace', []),
                'planner_capabilities': analysis.get('planner_capabilities', {}),
                'compatible_planners': [
                    {
                        'name': planner.name,
                        'system_name': name,
                        'description': planner.description,
                        'supported_requirements': list(planner.supported_requirements),
                        'pddl_version': planner.pddl_version,
                        'temporal': planner.temporal,
                        'optimization': planner.optimization
                    }
                    for name, planner in analysis['compatible_planners']
                ]
            }
            print(json.dumps(json_output, indent=2))
        else:
            # Human-readable output
            analyzer.print_analysis(analysis, verbose=args.verbose)
            
    except Exception as e:
        print(f"Error analyzing domain: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())