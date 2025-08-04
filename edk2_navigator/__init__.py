"""
EDK2 Navigator - DSC-aware code navigation for EDK2/OVMF firmware development

This package provides tools for parsing EDK2 DSC files, building dependency graphs,
and enabling intelligent code navigation within EDK2 firmware projects.

Main Components:
- DSCParser: Parse DSC files and extract build context
- DependencyGraphBuilder: Build module dependency relationships
- CacheManager: Cache parsed data for performance
- QueryEngine: Query interface for code navigation (Phase 2)
- MCPServer: MCP server for LLM integration (Phase 2)

Usage:
    from edk2_navigator import DSCParser, DependencyGraphBuilder, CacheManager
    
    # Initialize components
    parser = DSCParser(workspace_dir, edk2_path)
    cache_manager = CacheManager()
    graph_builder = DependencyGraphBuilder()
    
    # Parse DSC file
    context = parser.parse_dsc("path/to/platform.dsc")
    
    # Build dependency graph
    graph = graph_builder.build_from_context(context)
"""

__version__ = "0.1.0"
__author__ = "EDK2 Navigator Development Team"

# Core components (Phase 1 - BaseTools Integration)
from .dsc_parser import DSCParser, DSCContext, ModuleInfo
from .dependency_graph import DependencyGraphBuilder, DependencyGraph
from .cache_manager import CacheManager
from .utils import (
    validate_edk2_workspace,
    parse_dsc_section,
    parse_inf_file,
    normalize_path,
    find_inf_files,
    extract_module_path_from_component,
    resolve_build_flags,
    is_conditional_line,
    evaluate_conditional,
    get_edk2_module_type,
    get_edk2_module_guid
)
from .exceptions import (
    EDK2NavigatorError,
    DSCParsingError,
    BaseToolsError,
    ModuleNotFoundError,
    FunctionNotFoundError,
    CacheError,
    DependencyGraphError,
    WorkspaceValidationError,
    ConditionalCompilationError,
    MCPServerError
)

# Phase 2 components (Query Interface)
from .query_engine import QueryEngine, FunctionLocation, ModuleDependencies, CallPath
from .function_analyzer import FunctionAnalyzer, FunctionCall, FunctionDefinition
from .mcp_server import MCPServer

__all__ = [
    # Core classes
    'DSCParser',
    'DSCContext', 
    'ModuleInfo',
    'DependencyGraphBuilder',
    'DependencyGraph',
    'CacheManager',
    
    # Utility functions
    'validate_edk2_workspace',
    'parse_dsc_section',
    'parse_inf_file',
    'normalize_path',
    'find_inf_files',
    'extract_module_path_from_component',
    'resolve_build_flags',
    'is_conditional_line',
    'evaluate_conditional',
    'get_edk2_module_type',
    'get_edk2_module_guid',
    
    # Exceptions
    'EDK2NavigatorError',
    'DSCParsingError',
    'BaseToolsError',
    'ModuleNotFoundError',
    'FunctionNotFoundError',
    'CacheError',
    'DependencyGraphError',
    'WorkspaceValidationError',
    'ConditionalCompilationError',
    'MCPServerError',
    
    # Phase 2 (Query Interface)
    'QueryEngine',
    'FunctionLocation',
    'ModuleDependencies',
    'CallPath',
    'FunctionAnalyzer',
    'FunctionCall',
    'FunctionDefinition',
    'MCPServer',
]
