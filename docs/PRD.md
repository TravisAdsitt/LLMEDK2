# Pillar 1 PRD: EDK2/OVMF Code Navigation System

## Problem Statement

Current EDK2 development tools lack DSC-aware code navigation, making it difficult for both human developers and LLMs to understand which code is actually included in a specific platform build (e.g., OVMF). Traditional static analysis tools fail because they don't understand EDK2's conditional compilation model.

## Goals

**Primary Goal:** Enable intelligent code navigation within DSC-resolved EDK2 codebases for both human developers and LLM agents.

**Success Metrics:**
- LLM can locate relevant code sections for specific functionality (e.g., "find PCI enumeration code")
- Developers can trace function calls through only the modules that are actually built
- System can differentiate between dead code and build-relevant code

## Target Users

1. **LLM Agents** - Need programmatic access to explore and understand OVMF codebase
2. **EDK2 Developers** - Want better navigation tools than current ecosystem provides
3. **Firmware Researchers** - Need to understand code relationships within specific platforms

## Core Requirements

### Functional Requirements

**FR1: DSC Resolution**
- Parse DSC files to determine which modules/files are actually included in build
- Handle conditional compilation based on build flags
- Support multiple platforms (OvmfPkgX64.dsc, OvmfPkgIa32.dsc, etc.)

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

## Implementation Approach

### Phase 1: BaseTools Integration (2-3 weeks)
- Hack BaseTools build.py to extract dependency graph without compilation
- Create JSON serialization of resolved build graph  
- Implement basic file-based caching with DSC change detection

### Phase 2: Query Interface (1-2 weeks)
- Build MCP server exposing core query functions
- Implement function search within build-scoped code
- Add basic call tracing through dependency graph

### Phase 3: Semantic Layer (2-3 weeks)
- Integrate vector database for semantic search
- Populate vectors only with build-relevant code
- Implement context-aware code explanations

## Technical Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Server    │◄──►│  Graph Manager   │◄──►│   BaseTools     │
│                 │    │                  │    │   Integration   │
│ - Query API     │    │ - Dependency     │    │                 │
│ - Tool Registry │    │   Graph          │    │ - DSC Parser    │
│ - Response      │    │ - Build Context  │    │ - Module        │
│   Formatting    │    │ - File Mapping   │    │   Resolution    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Vector DB     │
                       │                 │
                       │ - Semantic      │
                       │   Search        │
                       │ - Build-scoped  │
                       │   Embeddings    │
                       └─────────────────┘
```

## MVP Definition

**Minimum Viable Product:**
- Parse OvmfPkgX64.dsc and generate module inclusion list
- Implement `find_function()` and `get_included_modules()` tools
- Basic MCP server interface for LLM integration
- Simple file change detection for cache invalidation

**Out of Scope for MVP:**
- Multi-platform support
- Advanced semantic search
- Real-time incremental updates
- Performance optimization

## Risks & Mitigations

**Risk 1:** BaseTools integration complexity
- *Mitigation:* Start with simple subprocess calls, refactor later

**Risk 2:** EDK2 build system changes breaking parsing
- *Mitigation:* Focus on stable BaseTools APIs, maintain test suite

**Risk 3:** Performance too slow for interactive use
- *Mitigation:* Implement caching early, profile bottlenecks

## Future Enhancements

- Real-time incremental graph updates
- Multi-platform build context switching  
- Integration with existing IDEs (VS Code extension)
- Community contribution of enhanced BaseTools replacement