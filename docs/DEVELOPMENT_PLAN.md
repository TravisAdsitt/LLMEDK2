# EDK2/OVMF Code Navigation System - Development Plan

## Project Overview

This document outlines the implementation plan for the EDK2/OVMF Code Navigation System as specified in the PRD. The system will provide DSC-aware code navigation for both human developers and LLM agents working with EDK2 firmware codebases.

## Current Project State

- **Repository Structure**: EDK2 repository is available in `edk2/` directory
- **Target DSC File**: `edk2/OvmfPkg/OvmfPkgX64.dsc` (primary target for MVP)
- **BaseTools Integration**: Build system located in `edk2/BaseTools/Source/Python/build/build.py`
- **Initial Package**: `edk2_navigator/` package created with basic structure

## PRD Requirements Analysis

### Functional Requirements

**FR1: DSC Resolution**
- Parse DSC files to determine included modules/files
- Handle conditional compilation based on build flags
- Support multiple platforms (focus on OvmfPkgX64.dsc for MVP)

**FR2: Code Query Interface**
- `get_included_modules(dsc_path, build_flags)` - Return list of modules in build
- `find_function(function_name, dsc_context)` - Locate function implementations within build scope
- `trace_call_path(function_name, dsc_context)` - Follow function calls through included modules only
- `get_module_dependencies(module_name, dsc_context)` - Show actual build dependencies
- `search_code_semantic(query, dsc_context)` - Semantic search within build-relevant code only

**FR3: Build Context Awareness**
- Maintain mapping of DSC → included files
- Filter out irrelevant code paths not in current build
- Handle include hierarchies correctly

### Non-Functional Requirements

**NFR1: Performance**
- Initial DSC parsing: < 60 seconds for OVMF
- Query response time: < 5 seconds for most operations
- Memory usage: < 2GB for full OVMF graph

**NFR2: Accuracy**
- 100% accuracy on module inclusion (no false positives/negatives)
- Correctly handle all EDK2 conditional compilation patterns

**NFR3: Maintainability**
- Leverage existing BaseTools parsing where possible
- Modular design to enable future enhancements

## Implementation Strategy

### Phase 1: BaseTools Integration (2-3 weeks)

#### Task 1.1: DSC Parser Integration
**Objective**: Extract dependency graph from EDK2 BaseTools without compilation
**Implementation Details**:
- Create `edk2_navigator/dsc_parser.py` that interfaces with BaseTools
- Modify or wrap `edk2/BaseTools/Source/Python/build/build.py` functionality
- Extract module resolution logic from `WorkspaceAutoGen` and `PlatformAutoGen` classes
- Handle conditional compilation directives (`!if`, `!ifdef`, etc.)

**Key Components**:
```python
class DSCParser:
    def __init__(self, workspace_dir, dsc_path):
        # Initialize BaseTools workspace
        
    def parse_dsc(self, build_flags=None):
        # Parse DSC file and return resolved module list
        
    def get_build_context(self):
        # Return build context with all resolved paths
```

**PRD Alignment**: Directly addresses FR1 (DSC Resolution)

#### Task 1.2: Dependency Graph Builder
**Objective**: Create JSON serialization of resolved build graph
**Implementation Details**:
- Create `edk2_navigator/dependency_graph.py`
- Build directed graph of module dependencies
- Serialize to JSON for caching and persistence
- Include file-level dependencies within modules

**Key Components**:
```python
class DependencyGraph:
    def __init__(self):
        self.modules = {}
        self.dependencies = {}
        
    def add_module(self, module_path, module_info):
        # Add module to graph
        
    def build_dependencies(self):
        # Build dependency relationships
        
    def serialize_to_json(self, output_path):
        # Save graph to JSON file
```

**PRD Alignment**: Supports FR3 (Build Context Awareness) and NFR1 (Performance through caching)

#### Task 1.3: Cache Management System
**Objective**: Implement file-based caching with DSC change detection
**Implementation Details**:
- Create `edk2_navigator/cache_manager.py`
- Implement file timestamp-based cache invalidation
- Store parsed DSC results and dependency graphs
- Provide cache hit/miss statistics

**Key Components**:
```python
class CacheManager:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        
    def is_cache_valid(self, dsc_path):
        # Check if cached data is still valid
        
    def store_parsed_data(self, dsc_path, data):
        # Store parsed DSC data
        
    def load_cached_data(self, dsc_path):
        # Load cached DSC data
```

**PRD Alignment**: Addresses NFR1 (Performance) and supports maintainability

### Phase 2: Query Interface (1-2 weeks)

#### Task 2.1: Core Query Engine
**Objective**: Implement basic query functions for module and function lookup
**Implementation Details**:
- Create `edk2_navigator/query_engine.py`
- Implement all FR2 query functions
- Use dependency graph for efficient lookups
- Support build-scoped filtering

**Key Components**:
```python
class QueryEngine:
    def __init__(self, dependency_graph):
        self.graph = dependency_graph
        
    def get_included_modules(self, dsc_path, build_flags=None):
        # Return list of modules included in build
        
    def find_function(self, function_name, dsc_context):
        # Locate function implementations within build scope
        
    def trace_call_path(self, function_name, dsc_context):
        # Follow function calls through included modules
        
    def get_module_dependencies(self, module_name, dsc_context):
        # Show actual build dependencies
```

**PRD Alignment**: Directly implements FR2 (Code Query Interface)

#### Task 2.2: Function Analysis Engine
**Objective**: Parse C/Assembly files to extract function definitions and calls
**Implementation Details**:
- Create `edk2_navigator/function_analyzer.py`
- Use AST parsing or regex patterns to extract function information
- Build function call graph within build-relevant modules only
- Handle EDK2-specific patterns (EFIAPI, protocols, etc.)

**Key Components**:
```python
class FunctionAnalyzer:
    def __init__(self):
        self.function_definitions = {}
        self.function_calls = {}
        
    def analyze_source_file(self, file_path):
        # Extract functions and calls from source file
        
    def build_call_graph(self, module_list):
        # Build function call graph for included modules
```

**PRD Alignment**: Supports FR2 (find_function, trace_call_path)

#### Task 2.3: MCP Server Implementation
**Objective**: Create MCP server interface for LLM integration
**Implementation Details**:
- Create `edk2_navigator/mcp_server.py`
- Implement MCP protocol for tool registration
- Expose query functions as MCP tools
- Handle JSON-RPC communication

**Key Components**:
```python
class MCPServer:
    def __init__(self, query_engine):
        self.query_engine = query_engine
        
    def register_tools(self):
        # Register available tools with MCP
        
    def handle_tool_call(self, tool_name, arguments):
        # Handle incoming tool calls
```

**PRD Alignment**: Enables LLM integration as specified in target users

### Phase 3: Semantic Layer (2-3 weeks)

#### Task 3.1: Vector Database Integration
**Objective**: Implement semantic search within build-relevant code
**Implementation Details**:
- Create `edk2_navigator/semantic_search.py`
- Integrate with vector database (ChromaDB or similar)
- Generate embeddings only for build-relevant code
- Implement context-aware code explanations

**Key Components**:
```python
class SemanticSearch:
    def __init__(self, vector_db_path):
        self.vector_db = ChromaDB(vector_db_path)
        
    def index_build_relevant_code(self, module_list):
        # Create embeddings for included modules only
        
    def search_code_semantic(self, query, dsc_context):
        # Perform semantic search within build scope
```

**PRD Alignment**: Implements FR2 (search_code_semantic)

#### Task 3.2: Context-Aware Code Explanations
**Objective**: Provide intelligent code explanations based on build context
**Implementation Details**:
- Enhance semantic search with context awareness
- Generate explanations that consider module relationships
- Filter results based on actual build inclusion

**PRD Alignment**: Enhances user experience for both developers and LLMs

## MVP Definition

### Included in MVP
1. **DSC Parser**: Parse OvmfPkgX64.dsc and generate module inclusion list
2. **Core Query Functions**: Implement `find_function()` and `get_included_modules()`
3. **MCP Server**: Basic MCP server interface for LLM integration
4. **Cache System**: Simple file change detection for cache invalidation

### Excluded from MVP
- Multi-platform support (focus on OvmfPkgX64.dsc only)
- Advanced semantic search
- Real-time incremental updates
- Performance optimization beyond basic caching

## File Structure

```
edk2_navigator/
├── __init__.py                 # Package initialization
├── dsc_parser.py              # DSC parsing and BaseTools integration
├── dependency_graph.py        # Dependency graph management
├── cache_manager.py           # Caching system
├── query_engine.py            # Core query implementation
├── function_analyzer.py       # Function analysis and call tracing
├── mcp_server.py             # MCP server implementation
├── semantic_search.py        # Semantic search (Phase 3)
├── utils.py                  # Utility functions
└── tests/                    # Test suite
    ├── test_dsc_parser.py
    ├── test_query_engine.py
    └── test_mcp_server.py
```

## Technical Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Server    │◄──►│  Query Engine    │◄──►│   DSC Parser    │
│                 │    │                  │    │                 │
│ - Tool Registry │    │ - Module Lookup  │    │ - BaseTools     │
│ - JSON-RPC      │    │ - Function Search│    │   Integration   │
│ - Response      │    │ - Call Tracing   │    │ - Conditional   │
│   Formatting    │    │ - Dependencies   │    │   Compilation   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Dependency      │    │ Cache Manager   │
                       │ Graph           │    │                 │
                       │                 │    │ - File Change   │
                       │ - Module Graph  │    │   Detection     │
                       │ - Function      │    │ - JSON Storage  │
                       │   Call Graph    │    │ - Performance   │
                       └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Vector DB     │
                       │   (Phase 3)     │
                       │                 │
                       │ - Semantic      │
                       │   Search        │
                       │ - Build-scoped  │
                       │   Embeddings    │
                       └─────────────────┘
```

## Development Timeline

### Week 1-2: Phase 1 Foundation
- Set up BaseTools integration
- Implement DSC parser
- Create dependency graph builder
- Basic cache management

### Week 3-4: Phase 1 Completion
- Complete cache system
- Optimize DSC parsing performance
- Add comprehensive error handling
- Unit tests for Phase 1 components

### Week 5: Phase 2 Core Queries
- Implement query engine
- Add function analysis
- Create MCP server foundation

### Week 6: Phase 2 Completion
- Complete MCP server implementation
- Add call tracing functionality
- Integration testing
- Performance optimization

### Week 7-8: Phase 3 (Optional)
- Vector database integration
- Semantic search implementation
- Context-aware explanations

### Week 9: Integration & Testing
- End-to-end testing
- Performance benchmarking
- Documentation completion
- MVP delivery

## Risk Mitigation

### Risk 1: BaseTools Integration Complexity
**Mitigation**: Start with subprocess calls to existing BaseTools, refactor for direct integration later

### Risk 2: Performance Requirements
**Mitigation**: Implement aggressive caching early, profile bottlenecks, optimize critical paths

### Risk 3: EDK2 Build System Changes
**Mitigation**: Focus on stable BaseTools APIs, maintain comprehensive test suite

## Success Metrics

### MVP Success Criteria
1. Successfully parse OvmfPkgX64.dsc in < 60 seconds
2. `get_included_modules()` returns accurate module list
3. `find_function()` locates functions within build scope
4. MCP server responds to LLM queries in < 5 seconds
5. Cache system reduces subsequent parsing time by > 80%

### Quality Metrics
- 100% accuracy on module inclusion detection
- Zero false positives in function location
- Memory usage stays under 2GB for full OVMF graph
- All unit tests pass with > 90% code coverage

## Next Steps for Implementation

1. **Immediate**: Set up development environment and BaseTools integration
2. **Week 1**: Begin DSC parser implementation using existing BaseTools code
3. **Week 2**: Create dependency graph and basic caching
4. **Week 3**: Implement core query functions
5. **Week 4**: Add MCP server and LLM integration
6. **Week 5+**: Optimize performance and add advanced features

This plan provides a clear roadmap for implementing the EDK2/OVMF Code Navigation System while meeting all PRD requirements and maintaining focus on the MVP deliverables.
