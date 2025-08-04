"""
Utility functions for EDK2 Navigator
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple

def normalize_path(path: str, workspace_root: str) -> str:
    """Normalize a path relative to workspace root"""
    path = Path(path)
    workspace_root = Path(workspace_root)
    
    if path.is_absolute():
        try:
            return str(path.relative_to(workspace_root))
        except ValueError:
            return str(path)
    else:
        return str(path)

def find_inf_files(directory: str, recursive: bool = True) -> List[str]:
    """Find all .inf files in a directory"""
    directory = Path(directory)
    if not directory.exists():
        return []
    
    if recursive:
        return [str(inf_file) for inf_file in directory.rglob("*.inf")]
    else:
        return [str(inf_file) for inf_file in directory.glob("*.inf")]

def parse_inf_file(inf_path: str) -> Dict[str, any]:
    """Parse an INF file and extract basic information"""
    inf_path = Path(inf_path)
    if not inf_path.exists():
        return {}
    
    try:
        with open(inf_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception:
        return {}
    
    info = {
        'path': str(inf_path),
        'name': inf_path.stem,
        'defines': {},
        'sources': [],
        'library_classes': [],
        'protocols': [],
        'guids': []
    }
    
    current_section = None
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('#'):
            continue
        
        # Check for section headers
        if line.startswith('[') and line.endswith(']'):
            current_section = line[1:-1].lower()
            continue
        
        # Parse content based on current section
        if current_section == 'defines':
            if '=' in line:
                key, value = line.split('=', 1)
                info['defines'][key.strip()] = value.strip()
        
        elif current_section == 'sources':
            if line and not line.startswith('['):
                info['sources'].append(line)
        
        elif current_section == 'libraryclasses':
            if line and not line.startswith('['):
                info['library_classes'].append(line)
        
        elif current_section == 'protocols':
            if line and not line.startswith('['):
                info['protocols'].append(line)
        
        elif current_section == 'guids':
            if line and not line.startswith('['):
                info['guids'].append(line)
    
    return info

def parse_dsc_section(content: str, section_name: str) -> List[str]:
    """Parse a specific section from DSC file content"""
    lines = content.split('\n')
    in_section = False
    section_content = []
    
    for line in lines:
        line = line.strip()
        
        # Check for section start
        if line.lower() == f'[{section_name.lower()}]':
            in_section = True
            continue
        
        # Check for section end (new section starts)
        if line.startswith('[') and line.endswith(']') and in_section:
            break
        
        # Collect section content
        if in_section and line and not line.startswith('#'):
            section_content.append(line)
    
    return section_content

def extract_module_path_from_component(component_line: str) -> Optional[str]:
    """Extract module path from a component line in DSC file"""
    # Remove any inline comments
    if '#' in component_line:
        component_line = component_line.split('#')[0]
    
    # Remove any build options (content in braces)
    if '{' in component_line:
        component_line = component_line.split('{')[0]
    
    component_line = component_line.strip()
    
    # Skip lines that are not module paths
    if not component_line or component_line.startswith('<') or component_line.startswith('!') or component_line == '}':
        return None
    
    # Handle library class overrides (NULL|path or LibraryClass|path)
    if '|' in component_line:
        parts = component_line.split('|', 1)
        if len(parts) == 2:
            component_line = parts[1].strip()
    
    # The component line should now just be the path to the INF file
    if component_line.endswith('.inf'):
        return component_line
    
    return None

def resolve_build_flags(dsc_content: str, build_flags: Dict[str, str]) -> Dict[str, str]:
    """Resolve build flags from DSC content and provided flags"""
    resolved_flags = build_flags.copy()
    
    # Parse [Defines] section for default values
    defines_section = parse_dsc_section(dsc_content, 'Defines')
    
    for line in defines_section:
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Map DSC defines to build flags
            if key == 'SUPPORTED_ARCHITECTURES' and 'ARCH' not in resolved_flags:
                # Take first architecture as default
                archs = value.split('|')
                if archs:
                    resolved_flags['ARCH'] = archs[0].strip()
            
            elif key == 'BUILD_TARGETS' and 'TARGET' not in resolved_flags:
                # Take first target as default
                targets = value.split('|')
                if targets:
                    resolved_flags['TARGET'] = targets[0].strip()
    
    # Set defaults if not specified
    if 'ARCH' not in resolved_flags:
        resolved_flags['ARCH'] = 'X64'
    
    if 'TARGET' not in resolved_flags:
        resolved_flags['TARGET'] = 'DEBUG'
    
    if 'TOOLCHAIN' not in resolved_flags:
        resolved_flags['TOOLCHAIN'] = 'VS2019'
    
    return resolved_flags

def is_conditional_line(line: str) -> Tuple[bool, Optional[str]]:
    """Check if a line contains conditional compilation directives"""
    line = line.strip()
    
    # Check for !if, !ifdef, !ifndef directives
    conditional_patterns = [
        r'^\s*!if\s+(.+)',
        r'^\s*!ifdef\s+(\w+)',
        r'^\s*!ifndef\s+(\w+)'
    ]
    
    for pattern in conditional_patterns:
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            return True, match.group(1)
    
    # Check for !endif
    if re.match(r'^\s*!endif', line, re.IGNORECASE):
        return True, None
    
    return False, None

def evaluate_conditional(condition: str, build_flags: Dict[str, str]) -> bool:
    """Evaluate a conditional compilation expression"""
    if not condition:
        return True
    
    # Simple evaluation for common patterns
    # This is a simplified implementation - a full implementation would need
    # a proper expression parser
    
    # Handle simple variable checks
    if condition in build_flags:
        return bool(build_flags[condition])
    
    # Handle equality checks
    if '==' in condition:
        left, right = condition.split('==', 1)
        left = left.strip()
        right = right.strip().strip('"\'')
        
        if left in build_flags:
            return build_flags[left] == right
    
    # Handle inequality checks
    if '!=' in condition:
        left, right = condition.split('!=', 1)
        left = left.strip()
        right = right.strip().strip('"\'')
        
        if left in build_flags:
            return build_flags[left] != right
    
    # Default to True for unknown conditions
    return True

def get_edk2_module_type(inf_content: str) -> str:
    """Extract module type from INF file content"""
    defines_section = parse_dsc_section(inf_content, 'Defines')
    
    for line in defines_section:
        if '=' in line:
            key, value = line.split('=', 1)
            if key.strip().upper() == 'MODULE_TYPE':
                return value.strip()
    
    return 'UNKNOWN'

def get_edk2_module_guid(inf_content: str) -> str:
    """Extract module GUID from INF file content"""
    defines_section = parse_dsc_section(inf_content, 'Defines')
    
    for line in defines_section:
        if '=' in line:
            key, value = line.split('=', 1)
            if key.strip().upper() == 'FILE_GUID':
                return value.strip()
    
    return ''

def validate_edk2_workspace(workspace_path: str, edk2_path: str) -> Tuple[bool, List[str]]:
    """Validate that the workspace contains a proper EDK2 setup"""
    errors = []
    workspace_path = Path(workspace_path)
    edk2_path = Path(edk2_path)
    
    # Check if workspace exists
    if not workspace_path.exists():
        errors.append(f"Workspace directory does not exist: {workspace_path}")
    
    # Check if EDK2 directory exists
    if not edk2_path.exists():
        errors.append(f"EDK2 directory does not exist: {edk2_path}")
    
    # Check for BaseTools
    basetools_path = edk2_path / "BaseTools"
    if not basetools_path.exists():
        errors.append(f"BaseTools directory not found: {basetools_path}")
    
    # Check for BaseTools Python scripts
    build_script = basetools_path / "Source" / "Python" / "build" / "build.py"
    if not build_script.exists():
        errors.append(f"BaseTools build script not found: {build_script}")
    
    return len(errors) == 0, errors
