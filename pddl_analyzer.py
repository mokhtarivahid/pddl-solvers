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
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
import json


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
    
    def __init__(self):
        self.planners = self._initialize_planner_database()
    
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
                notes='Good for basic temporal planning'
            ),
            
            # Numeric and Hybrid Planners
            'enhsp': PlannerCapability(
                name='ENHSP',
                supported_requirements=temporal_reqs | numeric_reqs | {'continuous-effects'},
                pddl_version='PDDL 2.1+',
                description='Heuristic search planner for numeric and temporal domains',
                performance_category='high',
                optimization=True,
                temporal=True,
                notes='Specialized in numeric and temporal planning'
            ),
            
            # Lifted Planning
            'powerlifted': PlannerCapability(
                name='PowerLifted',
                supported_requirements=adl_reqs,
                pddl_version='PDDL 1.2+',
                description='Lifted classical planner using first-order representations',
                performance_category='medium',
                optimization=True,
                temporal=False,
                notes='Good for domains with many objects'
            ),
            
            # Symbolic Planners
            'symk': PlannerCapability(
                name='SymK',
                supported_requirements=basic_reqs | {'conditional-effects'},
                pddl_version='PDDL 1.2',
                description='Symbolic planner using binary decision diagrams',
                performance_category='medium',
                optimization=True,
                temporal=False,
                notes='Effective for certain structured domains'
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
                notes='Handles conditional planning with observations'
            ),
            
            # Probabilistic Planning
            'probabilistic-ff': PlannerCapability(
                name='Probabilistic-FF',
                supported_requirements=basic_reqs,
                pddl_version='PDDL 1.2',
                description='Probabilistic planning with FF heuristics',
                performance_category='low',
                optimization=False,
                temporal=False,
                notes='Experimental probabilistic planner'
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
                notes='Experimental learning-based approach'
            ),
            
            'ff-x': PlannerCapability(
                name='FF-X',
                supported_requirements=basic_reqs | {'conditional-effects'},
                pddl_version='PDDL 1.2',
                description='Extended version of FF planner',
                performance_category='medium',
                optimization=False,
                temporal=False,
                notes='FF variant with additional features'
            )
        }
        
        return planners
    
    def get_compatible_planners(self, requirements: List[str]) -> List[Tuple[str, PlannerCapability, float]]:
        """
        Get planners compatible with the given requirements.
        
        Args:
            requirements: List of PDDL requirements
            
        Returns:
            List of tuples: (planner_name, capability, compatibility_score)
        """
        req_set = set(req.lower().replace('_', '-') for req in requirements)
        compatible = []
        
        for name, planner in self.planners.items():
            # Calculate compatibility score
            supported_reqs = planner.supported_requirements
            
            # Essential requirements that must be supported
            essential_missing = req_set - supported_reqs
            
            # Handle special cases and aliases
            essential_missing = self._normalize_requirements(essential_missing, supported_reqs)
            
            if not essential_missing:
                # Full compatibility
                coverage = len(req_set & supported_reqs) / len(req_set) if req_set else 1.0
                compatibility_score = coverage
            else:
                # Partial compatibility - check if missing requirements are critical
                critical_missing = self._get_critical_missing_requirements(essential_missing)
                if not critical_missing:
                    # Missing only non-critical requirements
                    coverage = len(req_set & supported_reqs) / len(req_set) if req_set else 1.0
                    compatibility_score = coverage * 0.8  # Slight penalty for missing features
                else:
                    # Missing critical requirements
                    compatibility_score = 0.0
            
            if compatibility_score > 0:
                compatible.append((name, planner, compatibility_score))
        
        # Sort by compatibility score (descending) and then by performance category
        performance_order = {'high': 3, 'medium': 2, 'low': 1}
        compatible.sort(key=lambda x: (x[2], performance_order.get(x[1].performance_category, 1)), reverse=True)
        
        return compatible
    
    def _normalize_requirements(self, missing_reqs: Set[str], supported_reqs: Set[str]) -> Set[str]:
        """Normalize and handle requirement aliases and implications."""
        normalized_missing = missing_reqs.copy()
        
        # Handle aliases and implications
        aliases = {
            'fluents': 'numeric-fluents',
            'metrics': 'numeric-fluents',
            'object-fluents': 'numeric-fluents'
        }
        
        # ADL implications
        if 'adl' in supported_reqs:
            adl_implied = {
                'strips', 'typing', 'disjunctive-preconditions', 'equality',
                'quantified-preconditions', 'conditional-effects'
            }
            normalized_missing -= adl_implied
        
        # Apply aliases
        for missing in list(normalized_missing):
            if missing in aliases and aliases[missing] in supported_reqs:
                normalized_missing.remove(missing)
        
        return normalized_missing
    
    def _get_critical_missing_requirements(self, missing_reqs: Set[str]) -> Set[str]:
        """Identify which missing requirements are critical (planner cannot handle)."""
        # These requirements are considered critical and cannot be easily worked around
        critical_requirements = {
            'durative-actions', 'numeric-fluents', 'continuous-effects',
            'derived-predicates', 'preferences', 'timed-initial-literals'
        }
        
        return missing_reqs & critical_requirements


class PDDLAnalyzer:
    """Main analyzer that combines parsing and planner matching."""
    
    def __init__(self, repo_root: str = None):
        self.parser = PDDLRequirementsParser()
        self.planner_db = PlannerCapabilityDatabase()
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.planners_dir = self.repo_root / "planners"
    
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
        
        # Filter by available planners in the system
        available_planners = self._get_available_planners()
        available_compatible = [
            (name, planner, score) for name, planner, score in compatible_planners
            if name in available_planners
        ]
        
        result = {
            'domain_info': domain_info,
            'compatible_planners': compatible_planners,
            'available_compatible_planners': available_compatible,
            'available_planners': list(available_planners),
            'analysis_summary': self._generate_analysis_summary(domain_info, compatible_planners, available_compatible)
        }
        
        return result
    
    def _get_available_planners(self) -> Set[str]:
        """Get list of planners actually available in the system."""
        available = set()
        
        if not self.planners_dir.exists():
            return available
        
        for planner_dir in self.planners_dir.iterdir():
            if planner_dir.is_dir():
                planner_name = planner_dir.name
                if planner_name in self.planner_db.planners:
                    available.add(planner_name)
        
        return available
    
    def _generate_analysis_summary(self, domain_info: Dict, 
                                  compatible_planners: List, 
                                  available_compatible: List) -> Dict:
        """Generate a summary of the analysis."""
        requirements = domain_info['requirements']
        
        summary = {
            'domain_name': domain_info['domain_name'],
            'pddl_version': domain_info['pddl_version'],
            'total_requirements': len(requirements),
            'requirements_list': requirements,
            'total_compatible_planners': len(compatible_planners),
            'available_compatible_planners': len(available_compatible),
            'complexity_level': self._assess_complexity(domain_info),
            'recommended_planner': None,
            'planning_approach': self._determine_planning_approach(requirements)
        }
        
        # Recommend best planner
        if available_compatible:
            best_planner = available_compatible[0]
            summary['recommended_planner'] = {
                'name': best_planner[1].name,
                'system_name': best_planner[0],
                'compatibility_score': best_planner[2],
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
        
        if requirements & high_complexity:
            return 'High'
        elif requirements & medium_complexity or domain_info['functions'] > 0:
            return 'Medium'
        else:
            return 'Low'
    
    def _determine_planning_approach(self, requirements: List[str]) -> str:
        """Determine the type of planning approach needed."""
        req_set = set(requirements)
        
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
        
        print(f"\nCompatible Planners ({summary['total_compatible_planners']} total, {summary['available_compatible_planners']} available):")
        
        available_planners = analysis['available_compatible_planners']
        if available_planners:
            for i, (name, planner, score) in enumerate(available_planners[:5]):  # Show top 5
                status = "AVAILABLE" if name in analysis['available_planners'] else "Not Available"
                print(f"  {i+1}. {planner.name} ({name}) - {score:.1%} compatible {status}")
                if verbose:
                    print(f"     {planner.description}")
                    if planner.notes:
                        print(f"     Note: {planner.notes}")
        else:
            print("  No compatible planners available in the system!")
        
        if summary['recommended_planner']:
            rec = summary['recommended_planner']
            print(f"\nRECOMMENDED PLANNER:")
            print(f"   {rec['name']} ({rec['system_name']}) - {rec['compatibility_score']:.1%} compatible")
            print(f"   {rec['description']}")
            if rec['notes']:
                print(f"   Note: {rec['notes']}")
        else:
            print(f"\nWARNING: No compatible planners available for this domain!")
        
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
                'compatible_planners': [
                    {
                        'name': planner.name,
                        'system_name': name,
                        'compatibility_score': score,
                        'description': planner.description,
                        'supported_requirements': list(planner.supported_requirements),
                        'pddl_version': planner.pddl_version,
                        'temporal': planner.temporal,
                        'optimization': planner.optimization
                    }
                    for name, planner, score in analysis['compatible_planners']
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