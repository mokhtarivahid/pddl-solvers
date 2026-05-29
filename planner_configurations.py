"""
Planner Configurations Manager

Loads and manages planner execution configurations from YAML specification file.
Provides methods to query planner capabilities, configurations, and run commands.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any


class PlannerConfigurations:
    """Manages planner execution configurations from YAML file."""
    
    def __init__(self, spec_file: str = None):
        """
        Initialize specification loader.
        
        Args:
            spec_file: Path to planner_configurations.yaml specification file.
                      If None, looks for planner_configurations.yaml in repo root.
        """
        if spec_file is None:
            # Look for planner_configurations.yaml in repo root
            repo_root = Path(__file__).parent
            spec_file = repo_root / "planner_configurations.yaml"
        
        self.spec_file = Path(spec_file)
        self.spec = {}
        self._load_spec()
    
    def _load_spec(self):
        """Load specification from YAML file."""
        if not self.spec_file.exists():
            raise FileNotFoundError(f"Specification file not found: {self.spec_file}")
        
        try:
            with open(self.spec_file, 'r') as f:
                data = yaml.safe_load(f)
                if data:
                    self.spec = data
                else:
                    raise ValueError("Specification file is empty")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in specification file: {e}")
    
    def get_planner_names(self) -> List[str]:
        """Get list of all available planners."""
        return sorted(list(self.spec.get("planners", {}).keys()))
    
    def has_planner(self, planner_name: str) -> bool:
        """Check if planner exists in specification."""
        return planner_name in self.spec.get("planners", {})
    
    def get_planner_info(self, planner_name: str) -> Dict[str, Any]:
        """Get complete information for a planner."""
        if not self.has_planner(planner_name):
            raise ValueError(f"Planner not found: {planner_name}")
        return self.spec["planners"][planner_name]
    
    def get_planner_description(self, planner_name: str) -> str:
        """Get description of a planner."""
        return self.get_planner_info(planner_name).get("description", "")
    
    def get_planner_executable(self, planner_name: str) -> str:
        """Get executable name for a planner."""
        return self.get_planner_info(planner_name).get("executable", planner_name)
    
    def get_planner_capabilities(self, planner_name: str) -> List[str]:
        """Get capabilities of a planner."""
        return self.get_planner_info(planner_name).get("capabilities", [])
    
    def get_planner_requirements(self, planner_name: str) -> List[str]:
        """Get PDDL requirements for a planner."""
        return self.get_planner_info(planner_name).get("requires", [])
    
    def get_configurations(self, planner_name: str) -> Dict[str, Dict]:
        """Get all configurations for a planner."""
        if not self.has_planner(planner_name):
            raise ValueError(f"Planner not found: {planner_name}")
        return self.spec["planners"][planner_name].get("configurations", {})
    
    def get_default_config(self, planner_name: str) -> str:
        """Get default configuration name for a planner."""
        configs = self.get_configurations(planner_name)
        if "default" in configs:
            return "default"
        # Return first config
        if configs:
            return list(configs.keys())[0]
        return None
    
    def get_config_info(self, planner_name: str, config_name: str) -> Dict[str, Any]:
        """Get information for a specific configuration."""
        configs = self.get_configurations(planner_name)
        if config_name not in configs:
            raise ValueError(
                f"Configuration '{config_name}' not found for planner '{planner_name}'. "
                f"Available: {', '.join(configs.keys())}"
            )
        return configs[config_name]
    
    def get_config_description(self, planner_name: str, config_name: str) -> str:
        """Get description of a configuration."""
        return self.get_config_info(planner_name, config_name).get("description", "")
    
    def get_search_command(self, planner_name: str, config_name: str) -> Optional[str]:
        """Get search command for a configuration (if applicable)."""
        config = self.get_config_info(planner_name, config_name)
        return config.get("search")
    
    def get_config_args(self, planner_name: str, config_name: str) -> List[str]:
        """Get command-line arguments for a configuration."""
        config = self.get_config_info(planner_name, config_name)
        return config.get("args", [])

    def get_config_executable(self, planner_name: str, config_name: str) -> Optional[str]:
        """Get executable override for a configuration, if any."""
        config = self.get_config_info(planner_name, config_name)
        return config.get("executable")
    
    def list_configurations(self, planner_name: str) -> None:
        """Print all available configurations for a planner."""
        if not self.has_planner(planner_name):
            raise ValueError(f"Planner not found: {planner_name}")
        
        configs = self.get_configurations(planner_name)
        print(f"\n{planner_name} - Available Configurations:\n")
        
        for config_name, config_info in configs.items():
            desc = config_info.get("description", "")
            print(f"  {config_name:25} {desc}")
        
        print()
    
    def list_all_planners(self) -> None:
        """Print all available planners with descriptions."""
        print("\nAvailable PDDL Planners:\n")
        
        for planner_name in self.get_planner_names():
            desc = self.get_planner_description(planner_name)
            caps = self.get_planner_capabilities(planner_name)
            caps_str = ", ".join(caps) if caps else "basic"
            print(f"  {planner_name:20} {desc}")
            print(f"  {'':20} Capabilities: {caps_str}")
        
        print()
    
    def is_planner_capable(self, planner_name: str, capability: str) -> bool:
        """Check if planner has a specific capability."""
        return capability in self.get_planner_capabilities(planner_name)
    
    def find_planners_for_requirements(self, requirements: List[str]) -> List[str]:
        """Find planners that support given PDDL requirements."""
        matching = []
        for planner_name in self.get_planner_names():
            planner_reqs = self.get_planner_requirements(planner_name)
            # A planner matches if it requires no additional features,
            # or if it explicitly supports all required features
            if not planner_reqs or all(req in requirements for req in planner_reqs):
                matching.append(planner_name)
        return matching
