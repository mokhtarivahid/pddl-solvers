"""
Planner Capabilities Manager

Loads and manages planner capability rules and planner capability entries
from planner_capabilities.yaml.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class PlannerCapabilitiesCatalog:
    """Catalog for compatibility rules and deterministic planner priority ordering."""
    compatibility_mode: str = "critical-only"  # critical-only | all-missing
    aliases: Dict[str, str] = field(default_factory=dict)
    adl_implied_requirements: Set[str] = field(default_factory=set)
    critical_requirements: Set[str] = field(default_factory=set)
    established_priority: List[str] = field(default_factory=list)
    approach_priority: Dict[str, List[str]] = field(default_factory=dict)
    planner_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    disabled_planners: Set[str] = field(default_factory=set)

    @classmethod
    def default(cls) -> "PlannerCapabilitiesCatalog":
        """Structural defaults when YAML is missing or incomplete."""
        return cls(
            compatibility_mode="critical-only",
            aliases={
                "fluents": "numeric-fluents",
                "metrics": "numeric-fluents",
                "object-fluents": "numeric-fluents",
            },
            adl_implied_requirements={
                "strips", "typing", "disjunctive-preconditions", "equality",
                "quantified-preconditions", "conditional-effects",
            },
            critical_requirements={
                "durative-actions", "numeric-fluents", "continuous-effects",
                "derived-predicates", "preferences", "timed-initial-literals",
                "probabilistic-effects",
            },
            established_priority=[],
            approach_priority={},
        )

    @classmethod
    def from_yaml_mapping(cls, data: Dict[str, Any]) -> "PlannerCapabilitiesCatalog":
        catalog = cls.default()
        compatibility = data.get("compatibility", {})
        priority = data.get("priority", {})

        catalog.compatibility_mode = compatibility.get("mode", catalog.compatibility_mode)
        catalog.aliases.update(compatibility.get("aliases", {}))
        catalog.adl_implied_requirements |= set(compatibility.get("adl_implied_requirements", []))
        catalog.critical_requirements |= set(compatibility.get("critical_requirements", []))

        established = priority.get("established_order", [])
        if established:
            catalog.established_priority = list(established)

        for approach, planners in priority.get("approach_order", {}).items():
            catalog.approach_priority[approach] = list(planners)

        catalog.planner_overrides.update(data.get("planner_overrides", {}))
        catalog.disabled_planners |= set(data.get("disabled_planners", []))
        return catalog

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compatibility_mode": self.compatibility_mode,
            "aliases": dict(sorted(self.aliases.items())),
            "adl_implied_requirements": sorted(self.adl_implied_requirements),
            "critical_requirements": sorted(self.critical_requirements),
            "established_priority": list(self.established_priority),
            "approach_priority": {k: list(v) for k, v in self.approach_priority.items()},
            "disabled_planners": sorted(self.disabled_planners),
        }


class PlannerCapabilities:
    """Loads planner capabilities catalog and planner entries from YAML."""

    def __init__(self, spec_file: Optional[str] = None):
        if spec_file is None:
            repo_root = Path(__file__).parent
            spec_file = repo_root / "planner_capabilities.yaml"

        self.spec_file = Path(spec_file)

    def load(self) -> Tuple[PlannerCapabilitiesCatalog, Dict[str, Any], Optional[str]]:
        """Load catalog and planner entries.

        Returns:
            (catalog, planner_entries, warning_message)
        """
        if yaml is None:
            return (
                PlannerCapabilitiesCatalog.default(),
                {},
                "PyYAML not installed; falling back to built-in analyzer capabilities.",
            )

        if not self.spec_file.exists():
            return (
                PlannerCapabilitiesCatalog.default(),
                {},
                f"{self.spec_file} not found; falling back to built-in analyzer capabilities.",
            )

        try:
            with open(self.spec_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            if not isinstance(data, dict):
                raise ValueError("planner_capabilities.yaml must contain a top-level mapping")

            catalog = PlannerCapabilitiesCatalog.from_yaml_mapping(data)
            planner_entries = data.get("planners", {})
            if not isinstance(planner_entries, dict):
                planner_entries = {}
            return catalog, planner_entries, None
        except Exception as exc:
            return (
                PlannerCapabilitiesCatalog.default(),
                {},
                f"failed to load {self.spec_file}: {exc}. Falling back to built-in defaults.",
            )


# Backward compatibility aliases
PlannerCapabilityConfigurationCatalog = PlannerCapabilitiesCatalog
PlannerCapabilityConfigurations = PlannerCapabilities
PlannerCapabilityCatalog = PlannerCapabilitiesCatalog
PlannerCapabilitiesSpecification = PlannerCapabilities
