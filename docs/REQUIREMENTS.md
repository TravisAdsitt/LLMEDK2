# EDK2/OVMF Code Navigation System - Technical Requirements

## Overview

This document provides detailed technical requirements for implementing the EDK2/OVMF Code Navigation System based on the PRD specifications. It serves as a technical specification for developers implementing the system.

## System Requirements

### Environment Requirements

- **Python Version**: 3.8+ (compatible with EDK2 BaseTools)
- **Operating System**: Windows 10/11, Linux (Ubuntu 20.04+), macOS 10.15+
- **Memory**: Minimum 4GB RAM, Recommended 8GB+ for large codebases
- **Storage**: 500MB for system, 2GB+ for cache storage
- **EDK2 Repository**: Full EDK2 source tree with BaseTools

### Dependencies

#### Core Dependencies
```
- Python 3.8+
- EDK2 BaseTools (included in EDK2 repository)
- JSON (built-in Python module)
- os, sys, pathlib (built-in Python modules)
- hashlib (for cache validation)
- datetime (for timestamp management)
```

#### Optional Dependencies (Phase 3)
```
- chromadb>=0.4.0 (for semantic search)
- sentence-transformers>=2.2.0 (for embeddings)
- numpy>=1.21.0 (for vector operations)
```

## Functional Requirements Detail

### FR1: DSC Resolution

#### FR1.1: DSC File Parsing
**Requirement**: Parse EDK2 DSC files to extract module inclusion information
**Implementation Details**:
- Support DSC specification version 0x00010005 and later
- Parse `[Components]` sections to identify included modules
- Handle `[LibraryClasses]` sections for library dependencies
- Process `[BuildOptions]` for conditional compilation flags

**Input**: DSC file path, optional build flags dictionary
**Output**: Structured data containing:
```python
{
    "platform_name": str,
    "platform_guid": str,
    "supported_architectures": List[str],
    "build_targets": List[str],
    "modules": List[ModuleInfo],
    "libraries": List[LibraryInfo],
    "build_options": Dict[str, Any]
}
```

#### FR1.2: Conditional Compilation Handling
**Requirement**: Process conditional compilation directives
**Supported Directives**:
- `!if <expression>`
- `!ifdef <macro>`
- `!ifndef <macro>`
- `!else`
- `!endif`
- `!include <file>`

**Build Flag Processing**:
- Support command-line style flags: `-D FLAG=VALUE`
- Handle boolean flags: `-D SECURE_BOOT_ENABLE=TRUE`
- Process architecture-specific flags: `-a X64`
- Support target-specific flags: `-b DEBUG`

#### FR1.3: Multi-Platform Support (Future)
**Requirement**: Support multiple DSC files simultaneously
**Target Platforms**:
- OvmfPkgX64.dsc (MVP focus)
- OvmfPkgIa32.dsc
- OvmfPkgIa32X64.dsc
- Custom platform DSC files

### FR2: Code Query Interface

#### FR2.1: get_included_modules()
**Function Signature**:
```python
def get_included_modules(dsc_path: str, build_flags: Optional[Dict[str, str]] = None) -> List[ModuleInfo]
```

**Parameters**:
- `dsc_path`: Absolute path to DSC file
- `build_flags`: Optional dictionary of build flags

**Return Type**:
```python
class ModuleInfo:
    path: str                    # Relative path from workspace root
    name: str                    # Module name
    type: str                    # Module type (DXE_DRIVER, PEIM, etc.)
    guid: str                    # Module GUID
    architecture: List[str]      # Supported architectures
    dependencies: List[str]      # Library dependencies
    source_files: List[str]      # Source file paths
    include_paths: List[str]     # Include directories
```

**Performance Requirements**:
- First call: < 60 seconds for OVMF
- Cached calls: < 5 seconds
- Memory usage: < 500MB for module list

#### FR2.2: find_function()
**Function Signature**:
```python
def find_function(function_name: str, dsc_context: DSCContext) -> List[FunctionLocation]
```

**Parameters**:
- `function_name`: Name of function to locate
- `dsc_context`: Build context from DSC parsing

**Return Type**:
```python
class FunctionLocation:
    function_name: str           # Function name
    file_path: str              # Source file path
    line_number: int            # Line number in file
    module_name: str            # Containing module
    function_signature: str     # Full function signature
    is_definition: bool         # True if definition, False if declaration
    calling_convention: str     # EFIAPI, WINAPI, etc.
```

**Search Scope**:
- Only search within modules included in build
- Include both .c and .h files
- Handle EDK2-specific patterns (EFIAPI, EFI_STATUS, etc.)
- Support partial name matching with wildcards

#### FR2.3: trace_call_path()
**Function Signature**:
```python
def trace_call_path(function_name: str, dsc_context: DSCContext, max_depth: int = 10) -> CallGraph
```

**Parameters**:
- `function_name`: Starting function name
- `dsc_context`: Build context
- `max_depth`: Maximum recursion depth

**Return Type**:
```python
class CallGraph:
    root_function: str
    call_paths: List[CallPath]
    
class CallPath:
    path: List[FunctionCall]     # Sequence of function calls
    depth: int                   # Call depth
    
class FunctionCall:
    caller: FunctionLocation
    callee: FunctionLocation
    call_site: SourceLocation
```

**Analysis Requirements**:
- Parse C/C++ source files for function calls
- Handle function pointers and callbacks
- Identify protocol function calls
- Support cross-module call tracing
- Filter out calls to functions not in build

#### FR2.4: get_module_dependencies()
**Function Signature**:
```python
def get_module_dependencies(module_name: str, dsc_context: DSCContext) -> ModuleDependencies
```

**Return Type**:
```python
class ModuleDependencies:
    module_name: str
    direct_dependencies: List[str]      # Direct library dependencies
    transitive_dependencies: List[str]  # All transitive dependencies
    dependents: List[str]               # Modules that depend on this one
    dependency_graph: Dict[str, List[str]]  # Full dependency graph
```

#### FR2.5: search_code_semantic() (Phase 3)
**Function Signature**:
```python
def search_code_semantic(query: str, dsc_context: DSCContext, limit: int = 10) -> List[SemanticMatch]
```

**Return Type**:
```python
class SemanticMatch:
    file_path: str
    line_number: int
    code_snippet: str
    similarity_score: float
    context: str
    module_name: str
```

### FR3: Build Context Awareness

#### FR3.1: Build Context Management
**Requirement**: Maintain comprehensive build context information

**Context Structure**:
```python
class DSCContext:
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
```

#### FR3.2: File Filtering
**Requirement**: Filter operations to only include build-relevant files

**Filtering Rules**:
- Only process modules listed in DSC [Components] section
- Include libraries referenced by included modules
- Exclude modules disabled by conditional compilation
- Filter by architecture and build target
- Respect include path hierarchies

## Non-Functional Requirements Detail

### NFR1: Performance Requirements

#### NFR1.1: Parsing Performance
- **Initial DSC Parse**: < 60 seconds for OvmfPkgX64.dsc
- **Cached Parse**: < 5 seconds for subsequent loads
- **Module Resolution**: < 30 seconds for full OVMF module list
- **Function Search**: < 5 seconds for single function lookup
- **Call Tracing**: < 10 seconds for 5-level deep trace

#### NFR1.2: Memory Requirements
- **Base System**: < 100MB memory usage
- **Full OVMF Graph**: < 2GB memory usage
- **Cache Storage**: < 500MB disk space for cached data
- **Concurrent Operations**: Support 10+ simultaneous queries

#### NFR1.3: Scalability
- Support codebases up to 10,000 modules
- Handle source trees up to 1GB in size
- Scale to 100,000+ function definitions
- Support dependency graphs with 50,000+ edges

### NFR2: Accuracy Requirements

#### NFR2.1: Module Inclusion Accuracy
- **Zero False Positives**: Never include modules not in build
- **Zero False Negatives**: Never exclude modules that are in build
- **Conditional Compilation**: 100% accurate handling of !if directives
- **Architecture Filtering**: Correct filtering by target architecture

#### NFR2.2: Function Location Accuracy
- **Definition vs Declaration**: Correctly distinguish function definitions from declarations
- **Scope Awareness**: Only return functions accessible in build context
- **Signature Matching**: Accurate function signature extraction
- **Cross-Reference Validation**: Verify function calls against definitions

### NFR3: Maintainability Requirements

#### NFR3.1: Code Organization
- **Modular Design**: Clear separation of concerns across modules
- **Interface Stability**: Stable APIs for core functionality
- **Error Handling**: Comprehensive error handling and logging
- **Documentation**: Complete API documentation and examples

#### NFR3.2: BaseTools Integration
- **Minimal Modification**: Avoid modifying existing BaseTools code
- **Version Compatibility**: Support multiple BaseTools versions
- **Graceful Degradation**: Handle BaseTools API changes gracefully
- **Isolation**: Isolate BaseTools dependencies in wrapper layer

## Data Models

### Core Data Structures

#### ModuleInfo
```python
@dataclass
class ModuleInfo:
    path: str                    # Relative path from workspace
    name: str                    # Module name
    type: ModuleType            # Enum: DXE_DRIVER, PEIM, etc.
    guid: str                   # Module GUID
    version: str                # Module version
    architecture: List[str]     # Supported architectures
    dependencies: List[str]     # Library dependencies
    source_files: List[str]     # Source file paths
    include_paths: List[str]    # Include directories
    defines: Dict[str, str]     # Preprocessor definitions
    build_options: Dict[str, str]  # Module-specific build options
    protocols: List[str]        # Consumed/produced protocols
    ppis: List[str]            # Consumed/produced PPIs
    guids: List[str]           # Referenced GUIDs
```

#### FunctionInfo
```python
@dataclass
class FunctionInfo:
    name: str                   # Function name
    signature: str              # Full function signature
    return_type: str           # Return type
    parameters: List[Parameter] # Function parameters
    file_path: str             # Source file path
    line_number: int           # Line number
    module_name: str           # Containing module
    calling_convention: str    # EFIAPI, etc.
    is_static: bool           # Static function flag
    is_inline: bool           # Inline function flag
    documentation: str         # Function documentation
```

#### DependencyGraph
```python
@dataclass
class DependencyGraph:
    nodes: Dict[str, ModuleInfo]           # Module nodes
    edges: Dict[str, List[str]]            # Dependency edges
    library_mappings: Dict[str, str]       # Library class to implementation mapping
    call_graph: Dict[str, List[str]]       # Function call relationships
    include_graph: Dict[str, List[str]]    # Include file relationships
```

## API Specifications

### Core API

#### DSCParser Class
```python
class DSCParser:
    def __init__(self, workspace_dir: str, edk2_path: str):
        """Initialize parser with workspace and EDK2 paths"""
        
    def parse_dsc(self, dsc_path: str, build_flags: Optional[Dict[str, str]] = None) -> DSCContext:
        """Parse DSC file and return build context"""
        
    def get_module_list(self, dsc_context: DSCContext) -> List[ModuleInfo]:
        """Get list of modules included in build"""
        
    def resolve_dependencies(self, dsc_context: DSCContext) -> DependencyGraph:
        """Build complete dependency graph"""
```

#### QueryEngine Class
```python
class QueryEngine:
    def __init__(self, dependency_graph: DependencyGraph):
        """Initialize query engine with dependency graph"""
        
    def find_function(self, function_name: str, context: DSCContext) -> List[FunctionLocation]:
        """Find function definitions and declarations"""
        
    def trace_calls(self, function_name: str, context: DSCContext, max_depth: int = 10) -> CallGraph:
        """Trace function call paths"""
        
    def get_dependencies(self, module_name: str, context: DSCContext) -> ModuleDependencies:
        """Get module dependency information"""
        
    def search_semantic(self, query: str, context: DSCContext) -> List[SemanticMatch]:
        """Perform semantic code search"""
```

### MCP Server API

#### Tool Definitions
```json
{
  "tools": [
    {
      "name": "get_included_modules",
      "description": "Get list of modules included in DSC build",
      "inputSchema": {
        "type": "object",
        "properties": {
          "dsc_path": {"type": "string"},
          "build_flags": {"type": "object"}
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
          "function_name": {"type": "string"},
          "dsc_path": {"type": "string"},
          "build_flags": {"type": "object"}
        },
        "required": ["function_name", "dsc_path"]
      }
    }
  ]
}
```

## Error Handling

### Error Categories

#### ParseError
- DSC file syntax errors
- Invalid build flags
- Missing include files
- Circular dependencies

#### QueryError
- Function not found
- Invalid module name
- Context mismatch
- Search timeout

#### SystemError
- File system access errors
- Memory allocation failures
- Cache corruption
- BaseTools integration failures

### Error Response Format
```python
@dataclass
class NavigatorError:
    error_type: str             # Error category
    error_code: int            # Numeric error code
    message: str               # Human-readable message
    details: Dict[str, Any]    # Additional error details
    file_path: Optional[str]   # Related file path
    line_number: Optional[int] # Related line number
    suggestions: List[str]     # Suggested fixes
```

## Testing Requirements

### Unit Testing
- **Coverage Target**: > 90% code coverage
- **Test Framework**: pytest
- **Mock Strategy**: Mock BaseTools dependencies
- **Test Data**: Sample DSC files and modules

### Integration Testing
- **End-to-End Tests**: Full DSC parsing to query execution
- **Performance Tests**: Verify performance requirements
- **Compatibility Tests**: Test with multiple EDK2 versions
- **Error Handling Tests**: Verify graceful error handling

### Test Data Requirements
- Sample OVMF DSC file with known module list
- Test modules with various dependency patterns
- Sample C source files with known function definitions
- Invalid DSC files for error testing

## Security Considerations

### Input Validation
- Validate all file paths to prevent directory traversal
- Sanitize build flags to prevent code injection
- Limit resource consumption to prevent DoS attacks
- Validate DSC file syntax to prevent parser exploits

### Access Control
- Respect file system permissions
- Limit access to workspace directory tree
- Prevent access to system files outside workspace
- Log all file access operations

## Deployment Requirements

### Installation
- Python package installable via pip
- Automatic dependency resolution
- Configuration file for workspace settings
- Command-line interface for basic operations

### Configuration
```yaml
# edk2_navigator.yaml
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
  
logging:
  level: "INFO"
  file: "~/.edk2_navigator/logs/navigator.log"
```

This requirements document provides the technical foundation for implementing the EDK2/OVMF Code Navigation System according to the PRD specifications.
