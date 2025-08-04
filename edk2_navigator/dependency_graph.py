"""
Dependency Graph - Builds and manages module dependency relationships
"""
import json
import os
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, asdict
from .dsc_parser import ModuleInfo, DSCContext

@dataclass
class DependencyGraph:
    """Represents the complete dependency graph for a build"""
    nodes: Dict[str, ModuleInfo]           # Module nodes keyed by path
    edges: Dict[str, List[str]]            # Dependency edges
    library_mappings: Dict[str, str]       # Library class to implementation mapping
    call_graph: Dict[str, List[str]]       # Function call relationships
    include_graph: Dict[str, List[str]]    # Include file relationships

class DependencyGraphBuilder:
    """Builds dependency graphs from DSC context"""
    
    def __init__(self):
        self.graph = DependencyGraph(
            nodes={},
            edges={},
            library_mappings={},
            call_graph={},
            include_graph={}
        )
    
    def build_from_context(self, dsc_context: DSCContext) -> DependencyGraph:
        """Build dependency graph from DSC context"""
        # Reset graph
        self.graph = DependencyGraph(
            nodes={},
            edges={},
            library_mappings={},
            call_graph={},
            include_graph={}
        )
        
        # Add all modules as nodes
        for module in dsc_context.included_modules:
            self.add_module(module)
        
        # Build dependency relationships
        self._build_dependencies(dsc_context)
        
        return self.graph
    
    def add_module(self, module: ModuleInfo):
        """Add a module to the dependency graph"""
        self.graph.nodes[module.path] = module
        self.graph.edges[module.path] = module.dependencies.copy()
    
    def _build_dependencies(self, dsc_context: DSCContext):
        """Build dependency relationships between modules"""
        # 1. Resolve library class dependencies
        self._resolve_library_dependencies(dsc_context)
        
        # 2. Build include file relationships
        self._build_include_graph(dsc_context)
        
        # 3. Detect and handle circular dependencies
        self._detect_circular_dependencies()
        
        # 4. Build call graph relationships (basic implementation)
        self._build_call_graph()
    
    def _resolve_library_dependencies(self, dsc_context: DSCContext):
        """Resolve library class dependencies to actual implementations"""
        # Store library mappings from DSC context
        self.graph.library_mappings = dsc_context.library_mappings.copy()
        
        # For each module, resolve its library dependencies
        for module_path, module in self.graph.nodes.items():
            resolved_deps = []
            
            for library_class in module.dependencies:
                # Check if this library class has an implementation mapping
                if library_class in dsc_context.library_mappings:
                    implementation_path = dsc_context.library_mappings[library_class]
                    
                    # Find the actual module that implements this library
                    impl_module = self._find_module_by_path_pattern(implementation_path)
                    if impl_module:
                        resolved_deps.append(impl_module.path)
                    else:
                        # Keep the original library class name if no implementation found
                        resolved_deps.append(library_class)
                else:
                    # Keep unresolved library classes
                    resolved_deps.append(library_class)
            
            # Update the module's dependencies with resolved paths
            self.graph.edges[module_path] = resolved_deps
    
    def _find_module_by_path_pattern(self, path_pattern: str) -> Optional[ModuleInfo]:
        """Find a module by matching path patterns (handles relative paths)"""
        # Normalize the path pattern
        normalized_pattern = path_pattern.replace('\\', '/').lower()
        
        # Try exact match first
        for module_path, module in self.graph.nodes.items():
            if module_path.replace('\\', '/').lower() == normalized_pattern:
                return module
        
        # Try partial match (basename)
        pattern_basename = normalized_pattern.split('/')[-1]
        if pattern_basename.endswith('.inf'):
            pattern_basename = pattern_basename[:-4]  # Remove .inf extension
        
        for module_path, module in self.graph.nodes.items():
            module_basename = module_path.replace('\\', '/').split('/')[-1].lower()
            if module_basename.endswith('.inf'):
                module_basename = module_basename[:-4]
            
            if module_basename == pattern_basename:
                return module
        
        return None
    
    def _build_include_graph(self, dsc_context: DSCContext):
        """Build include file relationships between modules"""
        # Initialize include graph
        for module_path in self.graph.nodes:
            self.graph.include_graph[module_path] = []
        
        # For each module, analyze its source files for includes
        for module_path, module in self.graph.nodes.items():
            includes = set()
            
            # Analyze each source file for #include statements
            for source_file in module.source_files:
                file_includes = self._extract_includes_from_file(source_file, dsc_context)
                includes.update(file_includes)
            
            # Convert includes to module dependencies
            for include_file in includes:
                target_module = self._find_module_containing_file(include_file)
                if target_module and target_module.path != module_path:
                    self.graph.include_graph[module_path].append(target_module.path)
    
    def _extract_includes_from_file(self, source_file: str, dsc_context: DSCContext) -> Set[str]:
        """Extract #include statements from a source file"""
        includes = set()
        
        # Try to find the actual file path
        file_path = self._resolve_source_file_path(source_file, dsc_context)
        if not file_path or not os.path.exists(file_path):
            return includes
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#include'):
                        # Extract include file name
                        if '"' in line:
                            # Local include: #include "file.h"
                            start = line.find('"') + 1
                            end = line.find('"', start)
                            if end > start:
                                includes.add(line[start:end])
                        elif '<' in line and '>' in line:
                            # System include: #include <file.h>
                            start = line.find('<') + 1
                            end = line.find('>', start)
                            if end > start:
                                includes.add(line[start:end])
        except Exception:
            # Ignore file read errors
            pass
        
        return includes
    
    def _resolve_source_file_path(self, source_file: str, dsc_context: DSCContext) -> Optional[str]:
        """Resolve relative source file path to absolute path"""
        import os
        from pathlib import Path
        
        # Try relative to workspace root
        workspace_path = Path(dsc_context.workspace_root) / source_file
        if workspace_path.exists():
            return str(workspace_path)
        
        # Try relative to EDK2 root (assuming it's in workspace)
        edk2_path = Path(dsc_context.workspace_root) / "edk2" / source_file
        if edk2_path.exists():
            return str(edk2_path)
        
        return None
    
    def _find_module_containing_file(self, include_file: str) -> Optional[ModuleInfo]:
        """Find which module contains a specific include file"""
        # Simple heuristic: match by directory structure
        include_dir = include_file.split('/')[0] if '/' in include_file else ''
        
        for module in self.graph.nodes.values():
            module_dir = module.path.split('/')[0] if '/' in module.path else ''
            if include_dir and module_dir and include_dir.lower() == module_dir.lower():
                return module
        
        return None
    
    def _detect_circular_dependencies(self):
        """Detect circular dependencies in the dependency graph"""
        def has_cycle_util(node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.graph.edges.get(node, []):
                if neighbor in self.graph.nodes:  # Only check actual modules
                    if neighbor not in visited:
                        if has_cycle_util(neighbor, visited, rec_stack):
                            return True
                    elif neighbor in rec_stack:
                        return True
            
            rec_stack.remove(node)
            return False
        
        visited = set()
        
        # Check each unvisited node for cycles
        for node in self.graph.nodes:
            if node not in visited:
                if has_cycle_util(node, visited, set()):
                    # Circular dependency detected - could log or handle this
                    pass
    
    def _build_call_graph(self):
        """Build basic call graph relationships (placeholder implementation)"""
        # Initialize call graph
        for module_path in self.graph.nodes:
            self.graph.call_graph[module_path] = []
        
        # This is a basic implementation - in a full implementation,
        # we would parse source files to extract function calls
        # For now, we'll use dependency relationships as a proxy
        for module_path, dependencies in self.graph.edges.items():
            for dep in dependencies:
                if dep in self.graph.nodes:
                    # Add call relationship based on dependency
                    if dep not in self.graph.call_graph[module_path]:
                        self.graph.call_graph[module_path].append(dep)
    
    def get_dependencies(self, module_path: str, transitive: bool = False) -> List[str]:
        """Get dependencies for a module"""
        if module_path not in self.graph.edges:
            return []
        
        if not transitive:
            return self.graph.edges[module_path]
        
        # Build transitive dependencies
        visited = set()
        dependencies = []
        self._get_transitive_deps(module_path, visited, dependencies)
        return dependencies
    
    def _get_transitive_deps(self, module_path: str, visited: Set[str], dependencies: List[str]):
        """Recursively build transitive dependencies"""
        if module_path in visited:
            return
        
        visited.add(module_path)
        
        for dep in self.graph.edges.get(module_path, []):
            if dep not in dependencies:
                dependencies.append(dep)
            self._get_transitive_deps(dep, visited, dependencies)
    
    def serialize_to_json(self, output_path: str):
        """Save dependency graph to JSON file"""
        # Convert dataclass to dict for JSON serialization
        graph_dict = {
            'nodes': {path: asdict(module) for path, module in self.graph.nodes.items()},
            'edges': self.graph.edges,
            'library_mappings': self.graph.library_mappings,
            'call_graph': self.graph.call_graph,
            'include_graph': self.graph.include_graph
        }
        
        with open(output_path, 'w') as f:
            json.dump(graph_dict, f, indent=2)
    
    def load_from_json(self, input_path: str) -> DependencyGraph:
        """Load dependency graph from JSON file"""
        with open(input_path, 'r') as f:
            graph_dict = json.load(f)
        
        # Reconstruct ModuleInfo objects
        nodes = {}
        for path, module_data in graph_dict['nodes'].items():
            nodes[path] = ModuleInfo(**module_data)
        
        self.graph = DependencyGraph(
            nodes=nodes,
            edges=graph_dict['edges'],
            library_mappings=graph_dict['library_mappings'],
            call_graph=graph_dict['call_graph'],
            include_graph=graph_dict['include_graph']
        )
        
        return self.graph
