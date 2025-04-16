import re
import numpy as np
import os
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, List

# --- Constants (mirroring owPhysicsConstant.h assumed values) ---
# These should match the values used in your simulation/config files
LIQUID_PARTICLE = 0
ELASTIC_PARTICLE = 1
BOUNDARY_PARTICLE = 2
# Add other constants if needed, e.g., MAX_NEIGHBOR_COUNT, MAX_MEMBRANES_INCLUDING_SAME_PARTICLE
# These might be needed for array sizing if not dynamically determined
# Example value, adjust as needed based on C++ constants or config structure
MAX_NEIGHBOR_COUNT = 10 # Placeholder: Determine the actual max from C++ code or data limits
MAX_MEMBRANES_INCLUDING_SAME_PARTICLE = 5 # Placeholder

# --- Data Structure for Configuration Properties ---
@dataclass
class SimConfig:
    """Holds configuration parameters and counts read from the file."""
    config_path: str
    config_filename: str
    xmin: float = 0.0
    xmax: float = 0.0
    ymin: float = 0.0
    ymax: float = 0.0
    zmin: float = 0.0
    zmax: float = 0.0
    num_liquid_p: int = 0
    num_elastic_p: int = 0
    num_boundary_p: int = 0
    num_total_p: int = 0
    num_membranes: int = 0
    num_connections: int = 0 # Determined during load if needed
    particle_mem_indices_count: int = 0 # Determined during load if needed
    physical_constants: Dict[str, float] = field(default_factory=dict)
    # Internal marker for file position after reading sim box
    _read_position_after_simbox: int = 0

    def get_full_config_path(self) -> str:
        return os.path.join(self.config_path, self.config_filename)

    def get_const(self, name: str, default: Optional[float] = None) -> Optional[float]:
        """Gets a physical constant, returns default if not found."""
        return self.physical_constants.get(name, default)

# --- Helper Function for Parsing Physical Parameters ---
def read_phys_param(line: str) -> Optional[Tuple[str, float]]:
    """Parses a 'name: value // comment' line."""
    # Regex slightly adjusted for Python and potential trailing whitespace
    pattern = re.compile(r"^\s*(\w+)\s*:\s*(\d+(?:\.\d*(?:[eE][+-]?\d+)?)?)\s*(?://.*)?$")
    match = pattern.match(line)
    if match:
        name = match.group(1)
        value = float(match.group(2))
        return name, value
    return None


class ConfigLoader:
    def preload_config(self) -> SimConfig:
        """
        Performs the first pass reading: gets dimensions, counts particles/membranes,
        and reads physical constants.

        Returns:
            A SimConfig object containing the preloaded information.
        """
        config = SimConfig(config_path=self.config_path, config_filename=self.config_filename)
        full_path = config.get_full_config_path()
        current_section = None
        read_position_marker = 0 # Like C++ read_position

        print(f"Preloading configuration from: {full_path}")

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                line_num = 0
                while True:
                    line = f.readline()
                    if not line:
                        break
                    line = line.strip() # Remove leading/trailing whitespace and newline chars
                    if not line or line.startswith("//") or line.startswith("#"): # Skip empty/comment lines
                        continue

                    # Section Detection
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line
                        if current_section == "[simulation box]":
                            try:
                                config.xmin = float(f.readline().strip())
                                config.xmax = float(f.readline().strip())
                                config.ymin = float(f.readline().strip())
                                config.ymax = float(f.readline().strip())
                                config.zmin = float(f.readline().strip())
                                config.zmax = float(f.readline().strip())
                                read_position_marker = f.tell() # Save position after reading sim box
                                config._read_position_after_simbox = read_position_marker
                                current_section = None # Reset section until next marker
                            except (StopIteration, ValueError) as e:
                                raise IOError(f"Error reading simulation box dimensions near line {line_num+1}: {e}")
                        continue # Move to next line after processing section header

                    # --- Section Processing ---
                    if current_section == "[physical parameters]":
                        param = read_phys_param(line)
                        if param:
                            config.physical_constants[param[0]] = param[1]
                        elif line: # Non-empty line that didn't match
                             print(f"Warning: Skipping unrecognized line in [physical parameters]: {line}")


                    elif current_section == "[position]":
                        try:
                            parts = line.split('\t')
                            if len(parts) >= 4:
                                p_type = int(float(parts[3])) # Read type
                                config.num_total_p += 1
                                if p_type == LIQUID_PARTICLE:
                                    config.num_liquid_p += 1
                                elif p_type == ELASTIC_PARTICLE:
                                    config.num_elastic_p += 1
                                elif p_type == BOUNDARY_PARTICLE:
                                    config.num_boundary_p += 1
                                else:
                                     print(f"Warning: Unknown particle type {p_type} in [position] near line {line_num+1}")
                            else:
                                print(f"Warning: Skipping malformed line in [position] near line {line_num+1}: {line}")
                        except (ValueError, IndexError) as e:
                            print(f"Warning: Skipping invalid data line in [position] near line {line_num+1}: {line} ({e})")

                    elif current_section == "[membranes]":
                         # Just count lines with valid structure (e.g., 3 tab-separated integers)
                        try:
                            parts = line.split('\t')
                            if len(parts) >= 3:
                                 # Basic check if they look like integers
                                int(parts[0])
                                int(parts[1])
                                int(parts[2])
                                config.num_membranes += 1
                            else:
                                print(f"Warning: Skipping malformed line in [membranes] near line {line_num+1}: {line}")
                        except ValueError:
                             print(f"Warning: Skipping non-integer line in [membranes] near line {line_num+1}: {line}")

                    elif current_section == "[particleMemIndex]":
                        # Stop pre-loading if we hit this section, as counts should be finalized
                        break
                    elif current_section == "[velocity]" or current_section == "[connection]":
                         # Don't need to process these sections in preload pass
                         pass
                    elif current_section == "[end]":
                        break # Stop preload if we reach the end marker explicitly

        except FileNotFoundError:
            raise FileNotFoundError(f"Could not open configuration file: {full_path}")
        except Exception as e:
            raise RuntimeError(f"An error occurred during preloading: {e}")

        print("Preload complete.")
        print(f"  Simulation Box: X({config.xmin}, {config.xmax}), Y({config.ymin}, {config.ymax}), Z({config.zmin}, {config.zmax})")
        print(f"  Particles - Liquid: {config.num_liquid_p}, Elastic: {config.num_elastic_p}, Boundary: {config.num_boundary_p}, Total: {config.num_total_p}")
        print(f"  Membranes: {config.num_membranes}")
        print(f"  Physical Constants Found: {len(config.physical_constants)}")

        self.config = config # Store for the load_data step
        return config
