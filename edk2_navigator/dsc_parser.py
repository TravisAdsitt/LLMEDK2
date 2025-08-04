"""
DSC Parser - Interfaces with EDK2 BaseTools to parse DSC files
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# Add EDK2 BaseTools to Python path
def setup_basetools_path(edk2_path: str):
    """Add BaseTools to Python path for imports"""
    basetools_path = os.path.join(edk2_path, "BaseTools", "Source", "Python")
    if basetools_path not in sys.path:
        sys.path.insert(0, basetools_path)

@dataclass
class ModuleInfo:
    """Information about a module included in the build"""
    path: str                    # Relative path from workspace root
    name: str                    # Module name
    type: str                    # Module type (DXE_DRIVER, PEIM, etc.)
    guid: str                    # Module GUID
    architecture: List[str]      # Supported architectures
    dependencies: List[str]      # Library dependencies
    source_files: List[str]      # Source file paths
    include_paths: List[str]     # Include directories

@dataclass
class DSCContext:
    """Build context from DSC parsing"""
    dsc_path: str
    workspace_root: str
    build_flags: Dict[str, str]
    included_modules: List[ModuleInfo]
    library_mappings: Dict[str, str]
    include_paths: List[str]
    preprocessor_definitions: Dict[str, str]
    architecture: str
    build_target: str
    toolchain: str
    timestamp: datetime

class DSCParser:
    """Parser for EDK2 DSC files using BaseTools"""
    
    def __init__(self, workspace_dir: str, edk2_path: str):
        """Initialize parser with workspace and EDK2 paths"""
        self.workspace_dir = Path(workspace_dir).resolve()
        self.edk2_path = Path(edk2_path).resolve()
        
        # Setup BaseTools imports
        setup_basetools_path(str(self.edk2_path))
        
        # Import BaseTools modules (will be added after BaseTools integration)
        self._import_basetools()
    
    def _import_basetools(self):
        """Import required BaseTools modules"""
        try:
            # These imports will be added once BaseTools integration is complete
            # from Workspace.WorkspaceDatabase import BuildDB
            # from AutoGen.WorkspaceAutoGen import WorkspaceAutoGen
            # from AutoGen.PlatformAutoGen import PlatformAutoGen
            pass
        except ImportError as e:
            raise ImportError(f"Failed to import BaseTools: {e}")
    
    def parse_dsc(self, dsc_path: str, build_flags: Optional[Dict[str, str]] = None) -> DSCContext:
        """Parse DSC file and return build context"""
        dsc_path = Path(dsc_path).resolve()
        
        if not dsc_path.exists():
            raise FileNotFoundError(f"DSC file not found: {dsc_path}")
        
        # Set default build flags
        if build_flags is None:
            build_flags = {
                "TARGET": "DEBUG",
                "ARCH": "X64",
                "TOOLCHAIN": "VS2019"
            }
        
        # Read and parse DSC file content
        try:
            with open(dsc_path, 'r', encoding='utf-8', errors='ignore') as f:
                dsc_content = f.read()
        except Exception as e:
            raise FileNotFoundError(f"Could not read DSC file {dsc_path}: {e}")
        
        # Parse DSC content
        included_modules = self._parse_components_section(dsc_content, dsc_path)
        library_mappings = self._parse_library_classes_section(dsc_content)
        preprocessor_definitions = self._parse_defines_section(dsc_content)
        
        return DSCContext(
            dsc_path=str(dsc_path),
            workspace_root=str(self.workspace_dir),
            build_flags=build_flags,
            included_modules=included_modules,
            library_mappings=library_mappings,
            include_paths=[],  # TODO: Extract from DSC
            preprocessor_definitions=preprocessor_definitions,
            architecture=build_flags.get("ARCH", "X64"),
            build_target=build_flags.get("TARGET", "DEBUG"),
            toolchain=build_flags.get("TOOLCHAIN", "VS2019"),
            timestamp=datetime.now()
        )
    
    def _parse_components_section(self, dsc_content: str, dsc_path: Path) -> List[ModuleInfo]:
        """Parse [Components] section and extract module information"""
        from .utils import parse_dsc_section, extract_module_path_from_component, parse_inf_file
        
        components = parse_dsc_section(dsc_content, 'Components')
        modules = []
        
        for component_line in components:
            # Extract module path from component line
            module_path = extract_module_path_from_component(component_line)
            if not module_path:
                continue
            
            # Resolve full path to INF file
            # First try relative to workspace root
            inf_path = self.workspace_dir / module_path
            if not inf_path.exists():
                # Try relative to EDK2 directory (most common case)
                inf_path = self.edk2_path / module_path
                if not inf_path.exists():
                    # Try relative to DSC file directory
                    inf_path = dsc_path.parent / module_path
                    if not inf_path.exists():
                        continue
            
            # Parse INF file to get module information
            inf_info = parse_inf_file(str(inf_path))
            if not inf_info:
                continue
            
            # Extract module metadata
            module_name = inf_info['defines'].get('BASE_NAME', inf_path.stem)
            module_type = inf_info['defines'].get('MODULE_TYPE', 'UNKNOWN')
            module_guid = inf_info['defines'].get('FILE_GUID', '')
            
            # Create ModuleInfo
            module = ModuleInfo(
                path=module_path,
                name=module_name,
                type=module_type,
                guid=module_guid,
                architecture=["X64"],  # TODO: Extract from DSC context
                dependencies=inf_info['library_classes'],
                source_files=inf_info['sources'],
                include_paths=[]  # TODO: Extract include paths
            )
            
            modules.append(module)
        
        return modules
    
    def _parse_library_classes_section(self, dsc_content: str) -> Dict[str, str]:
        """Parse [LibraryClasses] section to get library mappings"""
        from .utils import parse_dsc_section
        
        library_classes = parse_dsc_section(dsc_content, 'LibraryClasses')
        mappings = {}
        
        for line in library_classes:
            if '|' in line:
                parts = line.split('|', 1)
                if len(parts) == 2:
                    library_class = parts[0].strip()
                    implementation = parts[1].strip()
                    mappings[library_class] = implementation
        
        return mappings
    
    def _parse_defines_section(self, dsc_content: str) -> Dict[str, str]:
        """Parse [Defines] section to get preprocessor definitions"""
        from .utils import parse_dsc_section
        
        defines = parse_dsc_section(dsc_content, 'Defines')
        definitions = {}
        
        for line in defines:
            if '=' in line:
                parts = line.split('=', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    definitions[key] = value
            elif line.startswith('DEFINE '):
                # Handle DEFINE statements
                define_line = line[7:].strip()  # Remove 'DEFINE '
                if '=' in define_line:
                    parts = define_line.split('=', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        definitions[key] = value
        
        return definitions
    
    def get_module_list(self, dsc_context: DSCContext) -> List[ModuleInfo]:
        """Get list of modules included in build"""
        return dsc_context.included_modules
