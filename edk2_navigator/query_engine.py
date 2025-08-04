"""
Query Engine - Core query functionality for code navigation
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from .dsc_parser import DSCContext, ModuleInfo
from .dependency_graph import DependencyGraph
from .exceptions import FunctionNotFoundError, ModuleNotFoundError

@dataclass
class FunctionLocation:
    """Location of a function in source code"""
    function_name: str           # Function name
    file_path: str              # Source file path
    line_number: int            # Line number in file
    module_name: str            # Containing module
    function_signature: str     # Full function signature
    is_definition: bool         # True if definition, False if declaration
    calling_convention: str     # EFIAPI, WINAPI, etc.
    return_type: str            # Function return type

@dataclass
class ModuleDependencies:
    """Module dependency information"""
    module_name: str
    module_path: str
    direct_dependencies: List[str]      # Direct library dependencies
    transitive_dependencies: List[str]  # All transitive dependencies
    dependents: List[str]               # Modules that depend on this one
    library_mappings: Dict[str, str]    # Library class to implementation mappings

@dataclass
class CallPath:
    """Represents a function call path"""
    caller_function: str
    called_function: str
    call_chain: List[str]       # Full call chain from root to target
    file_path: str
    line_number: int

class QueryEngine:
    """Core query engine for code navigation"""
    
    def __init__(self, dependency_graph: DependencyGraph):
        """Initialize query engine with dependency graph"""
        self.graph = dependency_graph
        self.function_cache = {}  # Cache for function locations
        self.call_graph_cache = {}  # Cache for call graphs
        
        # EDK2-specific patterns
        self.edk2_calling_conventions = ['EFIAPI', 'WINAPI', '__cdecl', '__stdcall']
        self.edk2_types = ['EFI_STATUS', 'BOOLEAN', 'UINT8', 'UINT16', 'UINT32', 'UINT64', 
                          'UINTN', 'INTN', 'VOID', 'CHAR8', 'CHAR16']
        
        # Compile regex patterns for function parsing
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for function parsing"""
        # Function definition pattern - matches function definitions with optional calling convention
        # This pattern handles multi-line function definitions common in EDK2
        calling_conv = '|'.join(self.edk2_calling_conventions)
        self.function_def_pattern = re.compile(
            r'^\s*(\w+(?:\s*\*)*)\s+(?:(' + calling_conv + r')\s+)?(\w+)\s*\([^)]*\)\s*\{',
            re.MULTILINE | re.DOTALL
        )
        
        # Alternative pattern for multi-line function definitions
        self.function_def_multiline_pattern = re.compile(
            r'^\s*(\w+(?:\s*\*)*)\s*\n\s*(?:(' + calling_conv + r')\s*\n\s*)?(\w+)\s*\([^)]*\)\s*\{',
            re.MULTILINE | re.DOTALL
        )
        
        # Function declaration pattern - matches function declarations
        self.function_decl_pattern = re.compile(
            r'^\s*(\w+(?:\s*\*)*)\s+(?:(' + calling_conv + r')\s+)?(\w+)\s*\([^)]*\)\s*;',
            re.MULTILINE | re.DOTALL
        )
        
        # Function call pattern - matches function calls
        self.function_call_pattern = re.compile(
            r'(\w+)\s*\(',
            re.MULTILINE
        )
    
    def get_included_modules(self, dsc_path: str = None, build_flags: Optional[Dict[str, str]] = None) -> List[ModuleInfo]:
        """Get list of modules included in build"""
        return list(self.graph.nodes.values())
    
    def find_function(self, function_name: str, dsc_context: DSCContext = None) -> List[FunctionLocation]:
        """Find function definitions and declarations within build scope"""
        # Check cache first
        cache_key = f"{function_name}"
        if dsc_context:
            cache_key += f":{dsc_context.dsc_path}"
        
        if cache_key in self.function_cache:
            return self.function_cache[cache_key]
        
        locations = []
        
        # Search through all included modules
        for module_path, module_info in self.graph.nodes.items():
            module_locations = self._search_module_for_function(function_name, module_info)
            locations.extend(module_locations)
        
        # Cache results
        self.function_cache[cache_key] = locations
        
        if not locations:
            raise FunctionNotFoundError(function_name, "any included modules")
        
        return locations
    
    def _search_module_for_function(self, function_name: str, module_info: ModuleInfo) -> List[FunctionLocation]:
        """Search a specific module for function definitions/declarations"""
        locations = []
        
        # Search through all source files in the module
        for source_file in module_info.source_files:
            if not source_file.endswith(('.c', '.cpp', '.h', '.hpp')):
                continue
            
            # Try to find the actual file path
            file_locations = self._find_source_file_paths(source_file, module_info.path)
            
            for file_path in file_locations:
                if not os.path.exists(file_path):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Search for function definitions
                    definitions = self._extract_function_definitions(content, file_path, function_name)
                    locations.extend(definitions)
                    
                    # Search for function declarations
                    declarations = self._extract_function_declarations(content, file_path, function_name)
                    locations.extend(declarations)
                    
                except Exception as e:
                    # Skip files that can't be read
                    continue
        
        return locations
    
    def _find_source_file_paths(self, source_file: str, module_path: str) -> List[str]:
        """Find possible paths for a source file"""
        paths = []
        
        # Get module directory
        module_dir = Path(module_path).parent
        
        # Try relative to module directory
        candidate = module_dir / source_file
        if candidate.exists():
            paths.append(str(candidate))
        
        # Try in workspace root
        from .dsc_parser import DSCParser
        # This is a bit of a hack - we should have workspace context
        # For now, try common EDK2 locations
        common_roots = ['edk2', '.']
        for root in common_roots:
            candidate = Path(root) / module_path.replace('/', os.sep)
            candidate = candidate.parent / source_file
            if candidate.exists():
                paths.append(str(candidate))
        
        return paths
    
    def _extract_function_definitions(self, content: str, file_path: str, function_name: str) -> List[FunctionLocation]:
        """Extract function definitions from source content"""
        definitions = []
        
        # Try both single-line and multi-line patterns
        patterns = [self.function_def_pattern, self.function_def_multiline_pattern]
        
        for pattern in patterns:
            for match in pattern.finditer(content):
                return_type = match.group(1).strip()
                calling_conv = match.group(2) or ''
                found_function_name = match.group(3)
                
                # Check if this is the function we're looking for
                if found_function_name != function_name:
                    continue
                
                # Check if we already found this function (avoid duplicates)
                if any(d.function_name == found_function_name and d.line_number == content[:match.start()].count('\n') + 1 for d in definitions):
                    continue
                
                # Find line number
                line_num = content[:match.start()].count('\n') + 1
                
                # Build function signature
                signature_end = content.find('{', match.start())
                if signature_end != -1:
                    signature = content[match.start():signature_end].strip()
                else:
                    signature = match.group(0)
                
                definitions.append(FunctionLocation(
                    function_name=found_function_name,
                    file_path=file_path,
                    line_number=line_num,
                    module_name=Path(file_path).stem,
                    function_signature=signature,
                    is_definition=True,
                    calling_convention=calling_conv,
                    return_type=return_type
                ))
        
        return definitions
    
    def _extract_function_declarations(self, content: str, file_path: str, function_name: str) -> List[FunctionLocation]:
        """Extract function declarations from source content"""
        declarations = []
        
        for match in self.function_decl_pattern.finditer(content):
            return_type = match.group(1).strip()
            calling_conv = match.group(2) or ''
            found_function_name = match.group(3)
            
            # Check if this is the function we're looking for
            if found_function_name != function_name:
                continue
            
            # Find line number
            line_num = content[:match.start()].count('\n') + 1
            
            declarations.append(FunctionLocation(
                function_name=found_function_name,
                file_path=file_path,
                line_number=line_num,
                module_name=Path(file_path).stem,
                function_signature=match.group(0).strip(),
                is_definition=False,
                calling_convention=calling_conv,
                return_type=return_type
            ))
        
        return declarations
    
    def get_module_dependencies(self, module_name: str, dsc_context: DSCContext = None) -> ModuleDependencies:
        """Get module dependency information"""
        # Find module by name
        module_path = None
        target_module = None
        
        for path, module in self.graph.nodes.items():
            if module.name == module_name:
                module_path = path
                target_module = module
                break
        
        if module_path is None:
            raise ModuleNotFoundError(f"Module not found: {module_name}")
        
        # Get direct dependencies
        direct_deps = self.graph.edges.get(module_path, [])
        
        # Get transitive dependencies
        transitive_deps = self._get_transitive_dependencies(module_path)
        
        # Get dependents (modules that depend on this one)
        dependents = []
        for path, deps in self.graph.edges.items():
            if module_path in deps or module_name in deps:
                dependent_module = self.graph.nodes.get(path)
                if dependent_module:
                    dependents.append(dependent_module.name)
        
        return ModuleDependencies(
            module_name=module_name,
            module_path=module_path,
            direct_dependencies=direct_deps,
            transitive_dependencies=transitive_deps,
            dependents=dependents,
            library_mappings=self.graph.library_mappings
        )
    
    def _get_transitive_dependencies(self, module_path: str) -> List[str]:
        """Get all transitive dependencies for a module"""
        visited = set()
        dependencies = []
        self._collect_transitive_deps(module_path, visited, dependencies)
        return dependencies
    
    def _collect_transitive_deps(self, module_path: str, visited: Set[str], dependencies: List[str]):
        """Recursively collect transitive dependencies"""
        if module_path in visited:
            return
        
        visited.add(module_path)
        
        for dep in self.graph.edges.get(module_path, []):
            if dep not in dependencies:
                dependencies.append(dep)
            
            # Try to find the dependency module and recurse
            dep_module_path = None
            for path, module in self.graph.nodes.items():
                if module.name == dep or path == dep:
                    dep_module_path = path
                    break
            
            if dep_module_path:
                self._collect_transitive_deps(dep_module_path, visited, dependencies)
    
    def trace_call_path(self, function_name: str, dsc_context: DSCContext = None, max_depth: int = 10) -> List[CallPath]:
        """Trace function call paths through included modules"""
        call_paths = []
        
        try:
            # First, find all locations where the function is defined
            function_locations = self.find_function(function_name, dsc_context)
            
            if not function_locations:
                return call_paths
            
            # For each definition, find callers
            for location in function_locations:
                if location.is_definition:
                    callers = self._find_function_callers(function_name, location.file_path)
                    
                    for caller in callers:
                        call_path = CallPath(
                            caller_function=caller['caller'],
                            called_function=function_name,
                            call_chain=[caller['caller'], function_name],
                            file_path=caller['file_path'],
                            line_number=caller['line_number']
                        )
                        call_paths.append(call_path)
        
        except FunctionNotFoundError:
            # Return empty list if function is not found
            return []
        
        return call_paths
    
    def _find_function_callers(self, function_name: str, exclude_file: str = None) -> List[Dict]:
        """Find all functions that call the specified function"""
        callers = []
        
        # Search through all modules for calls to this function
        for module_path, module_info in self.graph.nodes.items():
            for source_file in module_info.source_files:
                if not source_file.endswith(('.c', '.cpp')):
                    continue
                
                file_locations = self._find_source_file_paths(source_file, module_info.path)
                
                for file_path in file_locations:
                    if file_path == exclude_file:
                        continue
                    
                    if not os.path.exists(file_path):
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # Find calls to the function
                        calls = self._find_function_calls_in_content(content, function_name, file_path)
                        callers.extend(calls)
                        
                    except Exception:
                        continue
        
        return callers
    
    def _find_function_calls_in_content(self, content: str, function_name: str, file_path: str) -> List[Dict]:
        """Find calls to a specific function in source content"""
        calls = []
        lines = content.split('\n')
        
        # Simple pattern to find function calls
        call_pattern = re.compile(rf'\b{re.escape(function_name)}\s*\(')
        
        for line_num, line in enumerate(lines, 1):
            if call_pattern.search(line):
                # Try to determine the containing function
                containing_function = self._find_containing_function(content, line_num)
                
                calls.append({
                    'caller': containing_function or 'unknown',
                    'file_path': file_path,
                    'line_number': line_num,
                    'line_content': line.strip()
                })
        
        return calls
    
    def _find_containing_function(self, content: str, line_number: int) -> Optional[str]:
        """Find the function that contains the specified line number"""
        lines = content.split('\n')
        
        # Look backwards from the line to find the most recent function definition
        for i in range(line_number - 1, -1, -1):
            line = lines[i]
            
            # Check if this line contains a function definition
            match = self.function_def_pattern.search(line)
            if match:
                return match.group(3)  # Function name
        
        return None
    
    def search_code_semantic(self, query: str, dsc_context: DSCContext = None) -> List[Dict]:
        """Semantic search within build-relevant code only"""
        # This is a placeholder for semantic search functionality
        # In a full implementation, this would use vector embeddings
        # and semantic similarity matching
        
        results = []
        query_lower = query.lower()
        
        # Simple keyword-based search for now
        for module_path, module_info in self.graph.nodes.items():
            for source_file in module_info.source_files:
                if not source_file.endswith(('.c', '.cpp', '.h', '.hpp')):
                    continue
                
                file_locations = self._find_source_file_paths(source_file, module_info.path)
                
                for file_path in file_locations:
                    if not os.path.exists(file_path):
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # Simple keyword matching
                        if query_lower in content.lower():
                            # Find relevant lines
                            lines = content.split('\n')
                            for line_num, line in enumerate(lines, 1):
                                if query_lower in line.lower():
                                    results.append({
                                        'file_path': file_path,
                                        'line_number': line_num,
                                        'line_content': line.strip(),
                                        'module_name': module_info.name,
                                        'relevance_score': 1.0  # Placeholder
                                    })
                    
                    except Exception:
                        continue
        
        return results
