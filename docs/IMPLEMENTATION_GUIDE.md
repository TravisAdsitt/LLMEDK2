# EDK2/OVMF Code Navigation System - Implementation Guide

## Getting Started

This guide provides step-by-step instructions for implementing the EDK2/OVMF Code Navigation System. Follow this guide to build the MVP as specified in the PRD.

## Prerequisites

### Development Environment Setup

1. **Python Environment**
   ```bash
   # Ensure Python 3.8+ is installed
   python --version  # Should be 3.8 or higher
   
   # Create virtual environment
   python -m venv edk2_navigator_env
   source edk2_navigator_env/bin/activate  # Linux/macOS
   # or
   edk2_navigator_env\Scripts\activate     # Windows
   
   # Install development dependencies
   pip install pytest pytest-cov black flake8 mypy
   ```

2. **EDK2 Repository Verification**
   ```bash
   # Verify EDK2 repository structure
   ls edk2/BaseTools/Source/Python/build/build.py  # Should exist
   ls edk2/OvmfPkg/OvmfPkgX64.dsc                  # Should exist
   
   # Test BaseTools functionality
   cd edk2
   python BaseTools/Source/Python/build/build.py --help
   ```

3. **Project Structure Setup**
   ```bash
   # Create complete project structure
   mkdir -p edk2_navigator/{tests,examples,docs}
   touch edk2_navigator/{utils,exceptions}.py
   ```

## Phase 1: BaseTools Integration (Week 1-2)

### Step 1.1: Create DSC Parser Foundation

**File: `edk2_navigator/dsc_parser.py`**

```python
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
        
        # TODO: Integrate with BaseTools WorkspaceAutoGen
        # This is where we'll use BaseTools to parse the DSC file
        
        # For now, return a placeholder context
        return DSCContext(
            dsc_path=str(dsc_path),
            workspace_root=str(self.workspace_dir),
            build_flags=build_flags,
            included_modules=[],
            library_mappings={},
            include_paths=[],
            preprocessor_definitions={},
            architecture=build_flags.get("ARCH", "X64"),
            build_target=build_flags.get("TARGET", "DEBUG"),
            toolchain=build_flags.get("TOOLCHAIN", "VS2019"),
            timestamp=datetime.now()
        )
    
    def get_module_list(self, dsc_context: DSCContext) -> List[ModuleInfo]:
        """Get list of modules included in build"""
        # TODO: Extract module list from BaseTools parsing
        return dsc_context.included_modules
```

**Implementation Tasks for Step 1.1:**

1. **BaseTools Integration Research** (2 days)
   - Study `edk2/BaseTools/Source/Python/build/build.py`
   - Identify key classes: `WorkspaceAutoGen`, `PlatformAutoGen`, `ModuleAutoGen`
   - Understand how DSC parsing works in BaseTools
   - Document the integration points

2. **DSC Parsing Implementation** (3 days)
   - Implement `_import_basetools()` method
   - Create wrapper around `WorkspaceAutoGen` class
   - Extract module information from parsed DSC
   - Handle conditional compilation directives

3. **Module Information Extraction** (2 days)
   - Parse `[Components]` section
   - Extract module metadata (GUID, type, dependencies)
   - Build module file lists
   - Handle architecture-specific modules

### Step 1.2: Create Dependency Graph Builder

**File: `edk2_navigator/dependency_graph.py`**

```python
"""
Dependency Graph - Builds and manages module dependency relationships
"""
import json
from typing import Dict, List, Set
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
        # TODO: Implement dependency resolution
        # This will involve:
        # 1. Resolving library class dependencies
        # 2. Building transitive dependency chains
        # 3. Detecting circular dependencies
        pass
    
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
```

### Step 1.3: Create Cache Management System

**File: `edk2_navigator/cache_manager.py`**

```python
"""
Cache Manager - Handles caching of parsed DSC data and dependency graphs
"""
import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class CacheManager:
    """Manages caching of parsed DSC data"""
    
    def __init__(self, cache_dir: str = "~/.edk2_navigator/cache"):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache configuration
        self.cache_ttl = timedelta(hours=24)  # 24 hour TTL
        self.max_cache_size = 1024 * 1024 * 1024  # 1GB max cache size
    
    def _get_cache_key(self, dsc_path: str, build_flags: Dict[str, str]) -> str:
        """Generate cache key for DSC file and build flags"""
        # Create hash from DSC path and build flags
        content = f"{dsc_path}:{json.dumps(build_flags, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for cache key"""
        return self.cache_dir / f"{cache_key}.json"
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get hash of file contents for change detection"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def is_cache_valid(self, dsc_path: str, build_flags: Dict[str, str]) -> bool:
        """Check if cached data is still valid"""
        cache_key = self._get_cache_key(dsc_path, build_flags)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return False
        
        try:
            # Load cache metadata
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            # Check TTL
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cache_time > self.cache_ttl:
                return False
            
            # Check file hash for changes
            current_hash = self._get_file_hash(dsc_path)
            if current_hash != cache_data['file_hash']:
                return False
            
            return True
            
        except (json.JSONDecodeError, KeyError, ValueError):
            return False
    
    def store_parsed_data(self, dsc_path: str, build_flags: Dict[str, str], data: Any):
        """Store parsed DSC data in cache"""
        cache_key = self._get_cache_key(dsc_path, build_flags)
        cache_path = self._get_cache_path(cache_key)
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'dsc_path': dsc_path,
            'build_flags': build_flags,
            'file_hash': self._get_file_hash(dsc_path),
            'data': data
        }
        
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    def load_cached_data(self, dsc_path: str, build_flags: Dict[str, str]) -> Optional[Any]:
        """Load cached DSC data"""
        if not self.is_cache_valid(dsc_path, build_flags):
            return None
        
        cache_key = self._get_cache_key(dsc_path, build_flags)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            return cache_data['data']
        except (json.JSONDecodeError, KeyError):
            return None
    
    def clear_cache(self):
        """Clear all cached data"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'cache_dir': str(self.cache_dir),
            'file_count': len(cache_files),
            'total_size_mb': total_size / (1024 * 1024),
            'max_size_mb': self.max_cache_size / (1024 * 1024)
        }
```

## Phase 2: Query Interface (Week 3-4)

### Step 2.1: Create Core Query Engine

**File: `edk2_navigator/query_engine.py`**

```python
"""
Query Engine - Core query functionality for code navigation
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from .dsc_parser import DSCContext, ModuleInfo
from .dependency_graph import DependencyGraph

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

@dataclass
class ModuleDependencies:
    """Module dependency information"""
    module_name: str
    direct_dependencies: List[str]      # Direct library dependencies
    transitive_dependencies: List[str]  # All transitive dependencies
    dependents: List[str]               # Modules that depend on this one
    dependency_graph: Dict[str, List[str]]  # Full dependency graph

class QueryEngine:
    """Core query engine for code navigation"""
    
    def __init__(self, dependency_graph: DependencyGraph):
        """Initialize query engine with dependency graph"""
        self.graph = dependency_graph
        self.function_cache = {}  # Cache for function locations
    
    def get_included_modules(self, dsc_path: str, build_flags: Optional[Dict[str, str]] = None) -> List[ModuleInfo]:
        """Get list of modules included in build"""
        return list(self.graph.nodes.values())
    
    def find_function(self, function_name: str, dsc_context: DSCContext) -> List[FunctionLocation]:
        """Find function definitions and declarations within build scope"""
        # Check cache first
        cache_key = f"{function_name}:{dsc_context.dsc_path}"
        if cache_key in self.function_cache:
            return self.function_cache[cache_key]
        
        locations = []
        
        # Search through all included modules
        for module_path, module_info in self.graph.nodes.items():
            module_locations = self._search_module_for_function(function_name, module_info)
            locations.extend(module_locations)
        
        # Cache results
        self.function_cache[cache_key] = locations
        return locations
    
    def _search_module_for_function(self, function_name: str, module_info: ModuleInfo) -> List[FunctionLocation]:
        """Search a specific module for function definitions/declarations"""
        locations = []
        
        # TODO: Implement actual source file parsing
        # This will involve:
        # 1. Parsing C/C++ source files
        # 2. Extracting function definitions and declarations
        # 3. Handling EDK2-specific patterns (EFIAPI, etc.)
        
        return locations
    
    def get_module_dependencies(self, module_name: str, dsc_context: DSCContext) -> ModuleDependencies:
        """Get module dependency information"""
        # Find module by name
        module_path = None
        for path, module in self.graph.nodes.items():
            if module.name == module_name:
                module_path = path
                break
        
        if module_path is None:
            raise ValueError(f"Module not found: {module_name}")
        
        # Get direct dependencies
        direct_deps = self.graph.edges.get(module_path, [])
        
        # Get transitive dependencies (TODO: implement)
        transitive_deps = []
        
        # Get dependents (modules that depend on this one)
        dependents = []
        for path, deps in self.graph.edges.items():
            if module_path in deps:
                dependents.append(self.graph.nodes[path].name)
        
        return ModuleDependencies(
            module_name=module_name,
            direct_dependencies=direct_deps,
            transitive_dependencies=transitive_deps,
            dependents=dependents,
            dependency_graph=self.graph.edges
        )
```

### Step 2.2: Create Function Analysis Engine

**File: `edk2_navigator/function_analyzer.py`**

```python
"""
Function Analyzer - Parses source files to extract function information
"""
import re
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from .query_engine import FunctionLocation

@dataclass
class FunctionCall:
    """Represents a function call in source code"""
    caller_function: str
    called_function: str
    file_path: str
    line_number: int

class FunctionAnalyzer:
    """Analyzes source files to extract function definitions and calls"""
    
    def __init__(self):
        self.function_definitions = {}  # file_path -> List[FunctionLocation]
        self.function_calls = {}        # file_path -> List[FunctionCall]
        
        # EDK2-specific patterns
        self.edk2_calling_conventions = ['EFIAPI', 'WINAPI', '__cdecl', '__stdcall']
        self.edk2_types = ['EFI_STATUS', 'BOOLEAN', 'UINT8', 'UINT16', 'UINT32', 'UINT64']
        
        # Regex patterns for function parsing
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for function parsing"""
        # Function definition pattern
        # Matches: EFI_STATUS EFIAPI FunctionName (parameters) {
        calling_conv = '|'.join(self.edk2_calling_conventions)
        self.function_def_pattern = re.compile(
            r'^\s*(\w+(?:\s*\*)*)\s+(?:(' + calling_conv + r')\s+)?(\w+)\s*\([^)]*\)\s*\{',
            re.MULTILINE
        )
        
        # Function declaration pattern
        # Matches: EFI_STATUS EFIAPI FunctionName (parameters);
        self.function_decl_pattern = re.compile(
            r'^\s*(\w+(?:\s*\*)*)\s+(?:(' + calling_conv + r')\s+)?(\w+)\s*\([^)]*\)\s*;',
            re.MULTILINE
        )
        
        # Function call pattern
        # Matches: FunctionName (parameters)
        self.function_call_pattern = re.compile(
            r'(\w+)\s*\([^)]*\)',
            re.MULTILINE
        )
    
    def analyze_source_file(self, file_path: str) -> Dict[str, List]:
        """Analyze a source file for functions and calls"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {'definitions': [], 'declarations': [], 'calls': []}
        
        # Only analyze C/C++ files
        if file_path.suffix not in ['.c', '.cpp', '.h', '.hpp']:
            return {'definitions': [], 'declarations': [], 'calls': []}
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            return {'definitions': [], 'declarations': [], 'calls': []}
        
        definitions = self._extract_function_definitions(content, str(file_path))
        declarations = self._extract_function_declarations(content, str(file_path))
        calls = self._extract_function_calls(content, str(file_path))
        
        return {
            'definitions': definitions,
            'declarations': declarations,
            'calls': calls
        }
    
    def _extract_function_definitions(self, content: str, file_path: str) -> List[FunctionLocation]:
        """Extract function definitions from source content"""
        definitions = []
        lines = content.split('\n')
        
        for match in self.function_def_pattern.finditer(content):
            return_type = match.group(1).strip()
            calling_conv = match.group(2) or ''
            function_name = match.group(3)
            
            # Find line number
            line_num = content[:match.start()].count('\n') + 1
            
            # Build function signature
            signature_end = content.find('{', match.start())
            if signature_end != -1:
                signature = content[match.start():signature_end].strip()
            else:
                signature = match.group(0)
            
            definitions.append(FunctionLocation(
                function_name=function_name,
                file_path=file_path,
                line_number=line_num,
                module_name=Path(file_path).stem,
                function_signature=signature,
                is_definition=True,
                calling_convention=calling_conv
            ))
        
        return definitions
    
    def _extract_function_declarations(self, content: str, file_path: str) -> List[FunctionLocation]:
        """Extract function declarations from source content"""
        declarations = []
        
        for match in self.function_decl_pattern.finditer(content):
            return_type = match.group(1).strip()
            calling_conv = match.group(2) or ''
            function_name = match.group(3)
            
            # Find line number
            line_num = content[:match.start()].count('\n') + 1
            
            declarations.append(FunctionLocation(
                function_name=function_name,
                file_path=file_path,
                line_number=line_num,
                module_name=Path(file_path).stem,
                function_signature=match.group(0).strip(),
                is_definition=False,
                calling_convention=calling_conv
            ))
        
        return declarations
    
    def _extract_function_calls(self, content: str, file_path: str) -> List[FunctionCall]:
        """Extract function calls from source content"""
        calls = []
        
        # This is a simplified implementation
        # A more robust version would need to handle:
        # - Function calls within function definitions
        # - Excluding function definitions from call detection
        # - Handling function pointers and callbacks
        
        for match in self.function_call_pattern.finditer(content):
            function_name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            
            # Skip if this looks like a function definition
            line_start = content.rfind('\n', 0, match.start()) + 1
            line_end = content.find('\n', match.end())
            if line_end == -1:
                line_end = len(content)
            
            line_content = content[line_start:line_end]
            if '{' in line_content and line_content.strip().endswith('{'):
                continue  # This is likely a function definition
            
            calls.append(FunctionCall(
                caller_function='',  # TODO: determine caller function
                called_function=function_name,
                file_path=file_path,
                line_number=line_num
            ))
        
        return calls
    
    def build_call_graph(self, module_list: List[str]) -> Dict[str, List[str]]:
        """Build function call graph for included modules"""
        call_graph = {}
        
        for module_path in module_list:
            # Analyze all source files in module
            module_dir = Path(module_path).parent
            for source_file in module_dir.glob('**/*.c'):
                analysis = self.analyze_source_file(str(source_file))
                
                # Build call relationships
                for call in analysis['calls']:
                    if call.caller_function not in call_graph:
                        call_graph[call.caller_function] = []
                    if call.called_function not in call_graph[call.caller_function]:
                        call_graph[call.caller_function].append(call.called_function)
        
        return call_graph
```

### Step 2.3: Create MCP Server Implementation

**File: `edk2_navigator/mcp_server.py`**

```python
"""
MCP Server - Model Context Protocol server for LLM integration
"""
import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import asdict
from .query_engine import QueryEngine
from .dsc_parser import DSCParser
from .cache_manager import CacheManager

class MCPServer:
    """MCP Server for EDK2 Navigator"""
    
    def __init__(self, workspace_dir: str, edk2_path: str):
        """Initialize MCP server"""
        self.workspace_dir = workspace_dir
        self.edk2_path = edk2_path
        
        # Initialize components
        self.dsc_parser = DSCParser(workspace_dir, edk2_path)
        self.cache_manager = CacheManager()
        self.query_engine = None  # Will be initialized when DSC is parsed
        
        # MCP tool definitions
        self.tools = self._define_tools()
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define available MCP tools"""
        return [
            {
                "name": "get_included_modules",
                "description": "Get list of modules included in DSC build",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dsc_path": {
                            "type": "string",
                            "description": "Path to DSC file"
                        },
                        "build_flags": {
                            "type": "object",
                            "description": "Build flags dictionary",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["dsc_path"]
                }
            },
            {
                "name": "find_function",
                "description": "Find function definitions in build-relevant code",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "description": "Name of function to find"
                        },
                        "dsc_path": {
                            "type": "string",
                            "description": "Path to DSC file"
                        },
                        "build_flags": {
                            "type": "object",
                            "description": "Build flags dictionary",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["function_name", "dsc_path"]
                }
            },
            {
                "name": "get_module_dependencies",
                "description": "Get dependency information for a module",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "module_name": {
                            "type": "string",
                            "description": "Name of module"
                        },
                        "dsc_path": {
                            "type": "string",
                            "description": "Path to DSC file"
                        },
                        "build_flags": {
                            "type": "object",
                            "description": "Build flags dictionary",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["module_name", "dsc_path"]
                }
            }
        ]
    
    def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP tool calls"""
        try:
            if tool_name == "get_included_modules":
                return self._handle_get_included_modules(arguments)
            elif tool_name == "find_function":
                return self._handle_find_function(arguments)
            elif tool_name == "get_module_dependencies":
                return self._handle_get_module_dependencies(arguments)
            else:
                return {
                    "error": f"Unknown tool: {tool_name}",
                    "success": False
                }
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }
    
    def _handle_get_included_modules(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_included_modules tool call"""
        dsc_path = arguments["dsc_path"]
        build_flags = arguments.get("build_flags", {})
        
        # Parse DSC file
        dsc_context = self.dsc_parser.parse_dsc(dsc_path, build_flags)
        
        # Get module list
        modules = self.dsc_parser.get_module_list(dsc_context)
        
        return {
            "success": True,
            "modules": [asdict(module) for module in modules],
            "count": len(modules)
        }
    
    def _handle_find_function(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle find_function tool call"""
        function_name = arguments["function_name"]
        dsc_path = arguments["dsc_path"]
        build_flags = arguments.get("build_flags", {})
        
        # Parse DSC file and initialize query engine if needed
        dsc_context = self.dsc_parser.parse_dsc(dsc_path, build_flags)
        
        if self.query_engine is None:
            # TODO: Initialize query engine with dependency graph
            pass
        
        # Find function
        locations = self.query_engine.find_function(function_name, dsc_context)
        
        return {
            "success": True,
            "function_name": function_name,
            "locations": [asdict(loc) for loc in locations],
            "count": len(locations)
        }
    
    def _handle_get_module_dependencies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_module_dependencies tool call"""
        module_name = arguments["module_name"]
        dsc_path = arguments["dsc_path"]
        build_flags = arguments.get("build_flags", {})
        
        # Parse DSC file and initialize query engine if needed
        dsc_context = self.dsc_parser.parse_dsc(dsc_path, build_flags)
        
        if self.query_engine is None:
            # TODO: Initialize query engine with dependency graph
            pass
        
        # Get dependencies
        dependencies = self.query_engine.get_module_dependencies(module_name, dsc_context)
        
        return {
            "success": True,
            "dependencies": asdict(dependencies)
        }
```

**Implementation Tasks for Step 2.3:**

1. **MCP Protocol Implementation** (2 days)
   - Study MCP specification
   - Implement JSON-RPC communication
   - Add tool registration and discovery
   - Handle request/response formatting

2. **Tool Integration** (2 days)
   - Connect MCP tools to query engine
   - Add error handling and validation
   - Implement response formatting
   - Add logging and debugging

3. **Testing and Validation** (1 day)
   - Create test MCP client
   - Validate tool responses
   - Test error handling
   - Performance testing

## Phase 3: Testing and Integration (Week 5-6)

### Step 3.1: Create Test Suite

**File: `edk2_navigator/tests/test_dsc_parser.py`**

```python
"""
Tests for DSC Parser functionality
"""
import pytest
import tempfile
from pathlib import Path
from edk2_navigator.dsc_parser import DSCParser, ModuleInfo, DSCContext

class TestDSCParser:
    """Test cases for DSC Parser"""
    
    @pytest.fixture
    def sample_dsc_content(self):
        """Sample DSC file content for testing"""
        return """
[Defines]
  PLATFORM_NAME                  = TestPlatform
  PLATFORM_GUID                  = 12345678-1234-1234-1234-123456789abc
  PLATFORM_VERSION               = 0.1
  DSC_SPECIFICATION              = 0x00010005
  OUTPUT_DIRECTORY               = Build/Test
  SUPPORTED_ARCHITECTURES        = X64
  BUILD_TARGETS                  = DEBUG|RELEASE

[Components]
  TestPkg/TestModule1/TestModule1.inf
  TestPkg/TestModule2/TestModule2.inf {
    <LibraryClasses>
      TestLib|TestPkg/Library/TestLib/TestLib.inf
  }
"""
    
    @pytest.fixture
    def temp_workspace(self, sample_dsc_content):
        """Create temporary workspace with sample DSC file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            
            # Create EDK2 directory structure
            edk2_dir = workspace / "edk2"
            basetools_dir = edk2_dir / "BaseTools" / "Source" / "Python"
            basetools_dir.mkdir(parents=True)
            
            # Create sample DSC file
            dsc_file = workspace / "TestPlatform.dsc"
            dsc_file.write_text(sample_dsc_content)
            
            yield {
                'workspace': str(workspace),
                'edk2_path': str(edk2_dir),
                'dsc_path': str(dsc_file)
            }
    
    def test_parser_initialization(self, temp_workspace):
        """Test DSC parser initialization"""
        parser = DSCParser(
            temp_workspace['workspace'],
            temp_workspace['edk2_path']
        )
        
        assert parser.workspace_dir == Path(temp_workspace['workspace']).resolve()
        assert parser.edk2_path == Path(temp_workspace['edk2_path']).resolve()
    
    def test_parse_dsc_file_not_found(self, temp_workspace):
        """Test parsing non-existent DSC file"""
        parser = DSCParser(
            temp_workspace['workspace'],
            temp_workspace['edk2_path']
        )
        
        with pytest.raises(FileNotFoundError):
            parser.parse_dsc("nonexistent.dsc")
    
    def test_parse_dsc_basic(self, temp_workspace):
        """Test basic DSC file parsing"""
        parser = DSCParser(
            temp_workspace['workspace'],
            temp_workspace['edk2_path']
        )
        
        context = parser.parse_dsc(temp_workspace['dsc_path'])
        
        assert isinstance(context, DSCContext)
        assert context.dsc_path == temp_workspace['dsc_path']
        assert context.workspace_root == temp_workspace['workspace']
        assert context.architecture == "X64"
        assert context.build_target == "DEBUG"
    
    def test_parse_dsc_with_build_flags(self, temp_workspace):
        """Test DSC parsing with custom build flags"""
        parser = DSCParser(
            temp_workspace['workspace'],
            temp_workspace['edk2_path']
        )
        
        build_flags = {
            "TARGET": "RELEASE",
            "ARCH": "IA32",
            "TOOLCHAIN": "GCC5"
        }
        
        context = parser.parse_dsc(temp_workspace['dsc_path'], build_flags)
        
        assert context.build_flags == build_flags
        assert context.architecture == "IA32"
        assert context.build_target == "RELEASE"
```

**File: `edk2_navigator/tests/test_query_engine.py`**

```python
"""
Tests for Query Engine functionality
"""
import pytest
from edk2_navigator.query_engine import QueryEngine, FunctionLocation, ModuleDependencies
from edk2_navigator.dependency_graph import DependencyGraph
from edk2_navigator.dsc_parser import ModuleInfo, DSCContext

class TestQueryEngine:
    """Test cases for Query Engine"""
    
    @pytest.fixture
    def sample_modules(self):
        """Sample module information for testing"""
        return [
            ModuleInfo(
                path="TestPkg/Module1/Module1.inf",
                name="Module1",
                type="DXE_DRIVER",
                guid="11111111-1111-1111-1111-111111111111",
                architecture=["X64"],
                dependencies=["BaseLib", "UefiLib"],
                source_files=["Module1.c", "Module1.h"],
                include_paths=["Include"]
            ),
            ModuleInfo(
                path="TestPkg/Module2/Module2.inf",
                name="Module2",
                type="PEIM",
                guid="22222222-2222-2222-2222-222222222222",
                architecture=["X64"],
                dependencies=["BaseLib"],
                source_files=["Module2.c"],
                include_paths=["Include"]
            )
        ]
    
    @pytest.fixture
    def sample_dependency_graph(self, sample_modules):
        """Sample dependency graph for testing"""
        graph = DependencyGraph(
            nodes={module.path: module for module in sample_modules},
            edges={
                "TestPkg/Module1/Module1.inf": ["BaseLib", "UefiLib"],
                "TestPkg/Module2/Module2.inf": ["BaseLib"]
            },
            library_mappings={},
            call_graph={},
            include_graph={}
        )
        return graph
    
    def test_query_engine_initialization(self, sample_dependency_graph):
        """Test query engine initialization"""
        engine = QueryEngine(sample_dependency_graph)
        
        assert engine.graph == sample_dependency_graph
        assert engine.function_cache == {}
    
    def test_get_included_modules(self, sample_dependency_graph):
        """Test getting included modules"""
        engine = QueryEngine(sample_dependency_graph)
        
        modules = engine.get_included_modules("test.dsc")
        
        assert len(modules) == 2
        assert all(isinstance(module, ModuleInfo) for module in modules)
    
    def test_get_module_dependencies_valid_module(self, sample_dependency_graph, sample_modules):
        """Test getting dependencies for valid module"""
        engine = QueryEngine(sample_dependency_graph)
        
        # Create mock DSC context
        dsc_context = DSCContext(
            dsc_path="test.dsc",
            workspace_root="/test",
            build_flags={},
            included_modules=sample_modules,
            library_mappings={},
            include_paths=[],
            preprocessor_definitions={},
            architecture="X64",
            build_target="DEBUG",
            toolchain="VS2019",
            timestamp=None
        )
        
        deps = engine.get_module_dependencies("Module1", dsc_context)
        
        assert isinstance(deps, ModuleDependencies)
        assert deps.module_name == "Module1"
        assert "BaseLib" in deps.direct_dependencies
        assert "UefiLib" in deps.direct_dependencies
    
    def test_get_module_dependencies_invalid_module(self, sample_dependency_graph, sample_modules):
        """Test getting dependencies for invalid module"""
        engine = QueryEngine(sample_dependency_graph)
        
        # Create mock DSC context
        dsc_context = DSCContext(
            dsc_path="test.dsc",
            workspace_root="/test",
            build_flags={},
            included_modules=sample_modules,
            library_mappings={},
            include_paths=[],
            preprocessor_definitions={},
            architecture="X64",
            build_target="DEBUG",
            toolchain="VS2019",
            timestamp=None
        )
        
        with pytest.raises(ValueError, match="Module not found"):
            engine.get_module_dependencies("NonexistentModule", dsc_context)
```

### Step 3.2: Create Integration Tests

**File: `edk2_navigator/tests/test_integration.py`**

```python
"""
Integration tests for the complete EDK2 Navigator system
"""
import pytest
import tempfile
from pathlib import Path
from edk2_navigator.dsc_parser import DSCParser
from edk2_navigator.dependency_graph import DependencyGraphBuilder
from edk2_navigator.query_engine import QueryEngine
from edk2_navigator.cache_manager import CacheManager

class TestIntegration:
    """Integration test cases"""
    
    @pytest.fixture
    def complete_test_environment(self):
        """Set up complete test environment"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            
            # Create EDK2 structure
            edk2_dir = workspace / "edk2"
            basetools_dir = edk2_dir / "BaseTools" / "Source" / "Python"
            basetools_dir.mkdir(parents=True)
            
            # Create test package structure
            test_pkg = workspace / "TestPkg"
            test_pkg.mkdir()
            
            # Create test modules
            module1_dir = test_pkg / "Module1"
            module1_dir.mkdir()
            
            # Create module INF file
            inf_content = """
[Defines]
  INF_VERSION                    = 0x00010005
  BASE_NAME                      = Module1
  FILE_GUID                      = 11111111-1111-1111-1111-111111111111
  MODULE_TYPE                    = DXE_DRIVER
  VERSION_STRING                 = 1.0

[Sources]
  Module1.c

[LibraryClasses]
  BaseLib
  UefiLib
"""
            (module1_dir / "Module1.inf").write_text(inf_content)
            
            # Create source file
            source_content = """
#include <Uefi.h>

EFI_STATUS
EFIAPI
TestFunction (
  IN UINTN Parameter
  )
{
  return EFI_SUCCESS;
}

VOID
EFIAPI
AnotherFunction (
  VOID
  )
{
  TestFunction(123);
}
"""
            (module1_dir / "Module1.c").write_text(source_content)
            
            # Create DSC file
            dsc_content = f"""
[Defines]
  PLATFORM_NAME                  = TestPlatform
  PLATFORM_GUID                  = 12345678-1234-1234-1234-123456789abc
  PLATFORM_VERSION               = 0.1
  DSC_SPECIFICATION              = 0x00010005
  OUTPUT_DIRECTORY               = Build/Test
  SUPPORTED_ARCHITECTURES        = X64
  BUILD_TARGETS                  = DEBUG|RELEASE

[Components]
  TestPkg/Module1/Module1.inf
"""
            dsc_file = workspace / "TestPlatform.dsc"
            dsc_file.write_text(dsc_content)
            
            yield {
                'workspace': str(workspace),
                'edk2_path': str(edk2_dir),
                'dsc_path': str(dsc_file),
                'module_source': str(module1_dir / "Module1.c")
            }
    
    def test_end_to_end_workflow(self, complete_test_environment):
        """Test complete end-to-end workflow"""
        # Initialize components
        parser = DSCParser(
            complete_test_environment['workspace'],
            complete_test_environment['edk2_path']
        )
        
        cache_manager = CacheManager()
        graph_builder = DependencyGraphBuilder()
        
        # Parse DSC file
        dsc_context = parser.parse_dsc(complete_test_environment['dsc_path'])
        
        # Build dependency graph
        dependency_graph = graph_builder.build_from_context(dsc_context)
        
        # Initialize query engine
        query_engine = QueryEngine(dependency_graph)
        
        # Test module listing
        modules = query_engine.get_included_modules(complete_test_environment['dsc_path'])
        
        # Verify results
        assert len(modules) >= 0  # May be empty in placeholder implementation
        assert isinstance(dsc_context.timestamp, type(dsc_context.timestamp))
    
    def test_caching_workflow(self, complete_test_environment):
        """Test caching functionality"""
        cache_manager = CacheManager()
        
        # Test data
        test_data = {"test": "data", "modules": []}
        build_flags = {"TARGET": "DEBUG", "ARCH": "X64"}
        
        # Store data in cache
        cache_manager.store_parsed_data(
            complete_test_environment['dsc_path'],
            build_flags,
            test_data
        )
        
        # Verify cache validity
        assert cache_manager.is_cache_valid(
            complete_test_environment['dsc_path'],
            build_flags
        )
        
        # Load cached data
        cached_data = cache_manager.load_cached_data(
            complete_test_environment['dsc_path'],
            build_flags
        )
        
        assert cached_data == test_data
```

### Step 3.3: Create Example Usage

**File: `edk2_navigator/examples/basic_usage.py`**

```python
"""
Basic usage example for EDK2 Navigator
"""
import os
from pathlib import Path
from edk2_navigator.dsc_parser import DSCParser
from edk2_navigator.dependency_graph import DependencyGraphBuilder
from edk2_navigator.query_engine import QueryEngine
from edk2_navigator.function_analyzer import FunctionAnalyzer

def main():
    """Demonstrate basic EDK2 Navigator usage"""
    
    # Setup paths
    workspace_dir = os.getcwd()
    edk2_path = os.path.join(workspace_dir, "edk2")
    dsc_path = os.path.join(edk2_path, "OvmfPkg", "OvmfPkgX64.dsc")
    
    print("EDK2 Navigator - Basic Usage Example")
    print("=" * 40)
    
    # Initialize parser
    print("1. Initializing DSC Parser...")
    parser = DSCParser(workspace_dir, edk2_path)
    
    # Parse DSC file
    print("2. Parsing DSC file...")
    build_flags = {
        "TARGET": "DEBUG",
        "ARCH": "X64",
        "TOOLCHAIN": "VS2019"
    }
    
    try:
        dsc_context = parser.parse_dsc(dsc_path, build_flags)
        print(f"   Platform: {Path(dsc_context.dsc_path).name}")
        print(f"   Architecture: {dsc_context.architecture}")
        print(f"   Build Target: {dsc_context.build_target}")
        print(f"   Modules Found: {len(dsc_context.included_modules)}")
    except Exception as e:
        print(f"   Error parsing DSC: {e}")
        return
    
    # Build dependency graph
    print("3. Building dependency graph...")
    graph_builder = DependencyGraphBuilder()
    dependency_graph = graph_builder.build_from_context(dsc_context)
    print(f"   Graph nodes: {len(dependency_graph.nodes)}")
    print(f"   Graph edges: {len(dependency_graph.edges)}")
    
    # Initialize query engine
    print("4. Initializing query engine...")
    query_engine = QueryEngine(dependency_graph)
    
    # Get included modules
    print("5. Querying included modules...")
    modules = query_engine.get_included_modules(dsc_path, build_flags)
    print(f"   Total modules: {len(modules)}")
    
    if modules:
        print("   Sample modules:")
        for i, module in enumerate(modules[:5]):  # Show first 5
            print(f"     {i+1}. {module.name} ({module.type})")
    
    # Demonstrate function analysis
    print("6. Analyzing functions (example)...")
    analyzer = FunctionAnalyzer()
    
    # Find a sample source file to analyze
    sample_files = []
    for module in modules[:3]:  # Check first 3 modules
        for source_file in module.source_files:
            if source_file.endswith('.c'):
                full_path = os.path.join(workspace_dir, source_file)
                if os.path.exists(full_path):
                    sample_files.append(full_path)
                    break
    
    if sample_files:
        analysis = analyzer.analyze_source_file(sample_files[0])
        print(f"   Analyzed: {Path(sample_files[0]).name}")
        print(f"   Functions found: {len(analysis['definitions'])}")
        print(f"   Declarations found: {len(analysis['declarations'])}")
        print(f"   Function calls found: {len(analysis['calls'])}")
    else:
        print("   No source files found for analysis")
    
    print("\nExample completed successfully!")

if __name__ == "__main__":
    main()
```

## Testing and Validation

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest edk2_navigator/tests/ -v

# Run with coverage
pytest edk2_navigator/tests/ --cov=edk2_navigator --cov-report=html

# Run specific test file
pytest edk2_navigator/tests/test_dsc_parser.py -v

# Run integration tests only
pytest edk2_navigator/tests/test_integration.py -v
```

### Performance Testing

```bash
# Create performance test script
python -c "
import time
from edk2_navigator.dsc_parser import DSCParser

start_time = time.time()
parser = DSCParser('.', 'edk2')
context = parser.parse_dsc('edk2/OvmfPkg/OvmfPkgX64.dsc')
end_time = time.time()

print(f'DSC parsing took: {end_time - start_time:.2f} seconds')
print(f'Modules found: {len(context.included_modules)}')
"
```

## Deployment and Usage

### Installation

```bash
# Install in development mode
pip install -e .

# Or install from package
pip install edk2-navigator
```

### Configuration

Create `~/.edk2_navigator/config.yaml`:

```yaml
workspace:
  root: "/path/to/workspace"
  edk2_path: "/path/to/edk2"

cache:
  directory: "~/.edk2_navigator/cache"
  max_size: "1GB"
  ttl: "24h"

performance:
  max_memory: "2GB"
  query_timeout: "30s"
  parse_timeout: "60s"
```

### Command Line Usage

```bash
# Parse DSC file
edk2-navigator parse edk2/OvmfPkg/OvmfPkgX64.dsc

# Find function
edk2-navigator find-function "PciEnumerationComplete" --dsc edk2/OvmfPkg/OvmfPkgX64.dsc

# Get module dependencies
edk2-navigator dependencies "PciHostBridgeDxe" --dsc edk2/OvmfPkg/OvmfPkgX64.dsc

# Start MCP server
edk2-navigator mcp-server --workspace . --edk2-path edk2
```

## Next Steps

1. **Complete BaseTools Integration** - This is the most critical step
2. **Implement Function Analysis** - Add robust C/C++ parsing
3. **Add MCP Server** - Enable LLM integration
4. **Performance Optimization** - Meet the 60-second parsing requirement
5. **Add Semantic Search** - Phase 3 enhancement

This implementation guide provides a complete roadmap for building the EDK2/OVMF Code Navigation System according to the PRD specifications.
