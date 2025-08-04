"""
MCP Server - Model Context Protocol server for LLM integration
"""
import json
import asyncio
import sys
from typing import Dict, Any, List, Optional
from dataclasses import asdict
from .query_engine import QueryEngine, FunctionLocation, ModuleDependencies, CallPath
from .function_analyzer import FunctionAnalyzer, FunctionCall, FunctionDefinition
from .dsc_parser import DSCParser, DSCContext, ModuleInfo
from .dependency_graph import DependencyGraphBuilder, DependencyGraph
from .cache_manager import CacheManager
from .exceptions import EDK2NavigatorError, FunctionNotFoundError, ModuleNotFoundError
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
os.environ["ANTHROPIC_API_KEY"] = os.getenv("CLAUDE_API_KEY", "")

class MCPServer:
    """MCP Server for EDK2 Navigator"""
    
    def __init__(self, workspace_dir: str, edk2_path: str):
        """Initialize MCP server"""
        self.workspace_dir = workspace_dir
        self.edk2_path = edk2_path
        
        # Initialize components
        self.dsc_parser = DSCParser(workspace_dir, edk2_path)
        self.cache_manager = CacheManager()
        self.dependency_graph_builder = DependencyGraphBuilder()
        self.function_analyzer = FunctionAnalyzer()
        
        # These will be initialized when DSC is parsed
        self.current_dsc_context = None
        self.current_dependency_graph = None
        self.query_engine = None
        
        # MCP tool definitions
        self.tools = self._define_tools()
        self.resources = self._define_resources()
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define available MCP tools"""
        return [
            {
                "name": "parse_dsc",
                "description": "Parse DSC file and initialize build context",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dsc_path": {
                            "type": "string",
                            "description": "Path to DSC file relative to workspace"
                        },
                        "build_flags": {
                            "type": "object",
                            "description": "Build flags dictionary (TARGET, ARCH, TOOLCHAIN)",
                            "properties": {
                                "TARGET": {"type": "string", "default": "DEBUG"},
                                "ARCH": {"type": "string", "default": "X64"},
                                "TOOLCHAIN": {"type": "string", "default": "VS2019"}
                            },
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["dsc_path"]
                }
            },
            {
                "name": "get_included_modules",
                "description": "Get list of modules included in DSC build",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filter_by_type": {
                            "type": "string",
                            "description": "Filter modules by type (DXE_DRIVER, PEIM, etc.)"
                        },
                        "include_details": {
                            "type": "boolean",
                            "description": "Include detailed module information",
                            "default": False
                        }
                    }
                }
            },
            {
                "name": "find_function",
                "description": "Find function definitions and declarations in build-relevant code",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "description": "Name of function to find"
                        },
                        "include_declarations": {
                            "type": "boolean",
                            "description": "Include function declarations in results",
                            "default": True
                        },
                        "module_filter": {
                            "type": "string",
                            "description": "Filter results to specific module name"
                        }
                    },
                    "required": ["function_name"]
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
                        "include_transitive": {
                            "type": "boolean",
                            "description": "Include transitive dependencies",
                            "default": True
                        }
                    },
                    "required": ["module_name"]
                }
            },
            {
                "name": "trace_call_path",
                "description": "Trace function call paths through included modules",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "description": "Name of function to trace"
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum call depth to trace",
                            "default": 10
                        }
                    },
                    "required": ["function_name"]
                }
            },
            {
                "name": "analyze_function",
                "description": "Get detailed analysis of a function including calls and complexity",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "description": "Name of function to analyze"
                        },
                        "include_callers": {
                            "type": "boolean",
                            "description": "Include functions that call this function",
                            "default": True
                        },
                        "include_callees": {
                            "type": "boolean",
                            "description": "Include functions called by this function",
                            "default": True
                        }
                    },
                    "required": ["function_name"]
                }
            },
            {
                "name": "search_code",
                "description": "Search for code patterns within build-relevant modules",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (keywords or patterns)"
                        },
                        "file_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "File types to search (.c, .h, etc.)",
                            "default": [".c", ".cpp", ".h", ".hpp"]
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 50
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_build_statistics",
                "description": "Get statistics about the current build context",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    
    def _define_resources(self) -> List[Dict[str, Any]]:
        """Define available MCP resources"""
        return [
            {
                "uri": "edk2://current-build-context",
                "name": "Current Build Context",
                "description": "Information about the currently parsed DSC build context",
                "mimeType": "application/json"
            },
            {
                "uri": "edk2://dependency-graph",
                "name": "Dependency Graph",
                "description": "Complete module dependency graph for current build",
                "mimeType": "application/json"
            },
            {
                "uri": "edk2://function-index",
                "name": "Function Index",
                "description": "Index of all functions found in build-relevant modules",
                "mimeType": "application/json"
            }
        ]
    
    def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP tool calls"""
        try:
            if tool_name == "parse_dsc":
                return self._handle_parse_dsc(arguments)
            elif tool_name == "get_included_modules":
                return self._handle_get_included_modules(arguments)
            elif tool_name == "find_function":
                return self._handle_find_function(arguments)
            elif tool_name == "get_module_dependencies":
                return self._handle_get_module_dependencies(arguments)
            elif tool_name == "trace_call_path":
                return self._handle_trace_call_path(arguments)
            elif tool_name == "analyze_function":
                return self._handle_analyze_function(arguments)
            elif tool_name == "search_code":
                return self._handle_search_code(arguments)
            elif tool_name == "get_build_statistics":
                return self._handle_get_build_statistics(arguments)
            else:
                return {
                    "error": f"Unknown tool: {tool_name}",
                    "success": False
                }
        except Exception as e:
            return {
                "error": str(e),
                "success": False,
                "error_type": type(e).__name__
            }
    
    def handle_resource_request(self, uri: str) -> Dict[str, Any]:
        """Handle MCP resource requests"""
        try:
            if uri == "edk2://current-build-context":
                return self._get_build_context_resource()
            elif uri == "edk2://dependency-graph":
                return self._get_dependency_graph_resource()
            elif uri == "edk2://function-index":
                return self._get_function_index_resource()
            else:
                return {
                    "error": f"Unknown resource: {uri}",
                    "success": False
                }
        except Exception as e:
            return {
                "error": str(e),
                "success": False,
                "error_type": type(e).__name__
            }
    
    def _handle_parse_dsc(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle parse_dsc tool call"""
        dsc_path = arguments["dsc_path"]
        build_flags = arguments.get("build_flags", {})
        
        # Set default build flags
        default_flags = {"TARGET": "DEBUG", "ARCH": "X64", "TOOLCHAIN": "VS2019"}
        default_flags.update(build_flags)
        build_flags = default_flags
        
        # Resolve DSC path - try multiple locations
        resolved_dsc_path = self._resolve_dsc_path(dsc_path)
        
        # Parse DSC file
        self.current_dsc_context = self.dsc_parser.parse_dsc(resolved_dsc_path, build_flags)
        
        # Build dependency graph
        self.current_dependency_graph = self.dependency_graph_builder.build_from_context(
            self.current_dsc_context
        )
        
        # Initialize query engine
        self.query_engine = QueryEngine(self.current_dependency_graph)
        
        return {
            "success": True,
            "dsc_path": self.current_dsc_context.dsc_path,
            "modules_found": len(self.current_dsc_context.included_modules),
            "library_mappings": len(self.current_dsc_context.library_mappings),
            "architecture": self.current_dsc_context.architecture,
            "build_target": self.current_dsc_context.build_target,
            "timestamp": self.current_dsc_context.timestamp.isoformat()
        }
    
    def _resolve_dsc_path(self, dsc_path: str) -> str:
        """Resolve DSC path by trying multiple locations"""
        import os
        from pathlib import Path
        
        # If it's already an absolute path and exists, use it
        if os.path.isabs(dsc_path) and os.path.exists(dsc_path):
            return dsc_path
        
        # Try relative to workspace directory
        workspace_path = os.path.join(self.workspace_dir, dsc_path)
        if os.path.exists(workspace_path):
            return workspace_path
        
        # Try relative to EDK2 directory (most common case)
        edk2_path = os.path.join(self.edk2_path, dsc_path)
        if os.path.exists(edk2_path):
            return edk2_path
        
        # If none found, return the original path and let the parser handle the error
        return dsc_path
    
    def _handle_get_included_modules(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_included_modules tool call"""
        if not self.query_engine:
            return {"error": "No DSC context loaded. Call parse_dsc first.", "success": False}
        
        filter_by_type = arguments.get("filter_by_type")
        include_details = arguments.get("include_details", False)
        
        modules = self.query_engine.get_included_modules()
        
        # Apply type filter if specified
        if filter_by_type:
            modules = [m for m in modules if m.type == filter_by_type]
        
        # Format response
        if include_details:
            module_data = [asdict(module) for module in modules]
        else:
            module_data = [
                {
                    "name": module.name,
                    "type": module.type,
                    "path": module.path,
                    "guid": module.guid
                }
                for module in modules
            ]
        
        return {
            "success": True,
            "modules": module_data,
            "count": len(modules),
            "filter_applied": filter_by_type
        }
    
    def _handle_find_function(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle find_function tool call"""
        if not self.query_engine:
            return {"error": "No DSC context loaded. Call parse_dsc first.", "success": False}
        
        function_name = arguments["function_name"]
        include_declarations = arguments.get("include_declarations", True)
        module_filter = arguments.get("module_filter")
        
        try:
            locations = self.query_engine.find_function(function_name, self.current_dsc_context)
            
            # Apply module filter if specified
            if module_filter:
                locations = [loc for loc in locations if module_filter.lower() in loc.module_name.lower()]
            
            # Filter by definition/declaration preference
            if not include_declarations:
                locations = [loc for loc in locations if loc.is_definition]
            
            location_data = []
            for loc in locations:
                location_data.append({
                    "function_name": loc.function_name,
                    "file_path": loc.file_path,
                    "line_number": loc.line_number,
                    "module_name": loc.module_name,
                    "signature": loc.function_signature,
                    "is_definition": loc.is_definition,
                    "calling_convention": loc.calling_convention,
                    "return_type": loc.return_type
                })
            
            return {
                "success": True,
                "function_name": function_name,
                "locations": location_data,
                "count": len(location_data),
                "definitions": len([loc for loc in locations if loc.is_definition]),
                "declarations": len([loc for loc in locations if not loc.is_definition])
            }
            
        except FunctionNotFoundError as e:
            return {
                "success": False,
                "error": str(e),
                "function_name": function_name,
                "locations": [],
                "count": 0
            }
    
    def _handle_get_module_dependencies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_module_dependencies tool call"""
        if not self.query_engine:
            return {"error": "No DSC context loaded. Call parse_dsc first.", "success": False}
        
        module_name = arguments["module_name"]
        include_transitive = arguments.get("include_transitive", True)
        
        try:
            dependencies = self.query_engine.get_module_dependencies(
                module_name, self.current_dsc_context
            )
            
            result = {
                "success": True,
                "module_name": dependencies.module_name,
                "module_path": dependencies.module_path,
                "direct_dependencies": dependencies.direct_dependencies,
                "dependents": dependencies.dependents,
                "library_mappings": dependencies.library_mappings
            }
            
            if include_transitive:
                result["transitive_dependencies"] = dependencies.transitive_dependencies
            
            return result
            
        except ModuleNotFoundError as e:
            return {
                "success": False,
                "error": str(e),
                "module_name": module_name
            }
    
    def _handle_trace_call_path(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle trace_call_path tool call"""
        if not self.query_engine:
            return {"error": "No DSC context loaded. Call parse_dsc first.", "success": False}
        
        function_name = arguments["function_name"]
        max_depth = arguments.get("max_depth", 10)
        
        try:
            call_paths = self.query_engine.trace_call_path(
                function_name, self.current_dsc_context, max_depth
            )
            
            path_data = []
            for path in call_paths:
                path_data.append({
                    "caller_function": path.caller_function,
                    "called_function": path.called_function,
                    "call_chain": path.call_chain,
                    "file_path": path.file_path,
                    "line_number": path.line_number
                })
            
            return {
                "success": True,
                "function_name": function_name,
                "call_paths": path_data,
                "count": len(path_data),
                "max_depth": max_depth
            }
            
        except FunctionNotFoundError as e:
            return {
                "success": False,
                "error": str(e),
                "function_name": function_name,
                "call_paths": [],
                "count": 0
            }
    
    def _handle_analyze_function(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analyze_function tool call"""
        if not self.query_engine:
            return {"error": "No DSC context loaded. Call parse_dsc first.", "success": False}
        
        function_name = arguments["function_name"]
        include_callers = arguments.get("include_callers", True)
        include_callees = arguments.get("include_callees", True)
        
        try:
            # Find function locations first
            locations = self.query_engine.find_function(function_name, self.current_dsc_context)
            
            result = {
                "success": True,
                "function_name": function_name,
                "locations": [asdict(loc) for loc in locations],
                "definitions_count": len([loc for loc in locations if loc.is_definition]),
                "declarations_count": len([loc for loc in locations if not loc.is_definition])
            }
            
            # Get complexity metrics
            complexity = self.function_analyzer.get_function_complexity_metrics(function_name)
            result["complexity_metrics"] = complexity
            
            # Get callers if requested
            if include_callers:
                callers = self.function_analyzer.get_function_callers(function_name)
                result["callers"] = [
                    {
                        "caller_function": call.caller_function,
                        "file_path": call.file_path,
                        "line_number": call.line_number,
                        "line_content": call.line_content
                    }
                    for call in callers
                ]
                result["callers_count"] = len(callers)
            
            # Get callees if requested
            if include_callees:
                callees = self.function_analyzer.get_function_callees(function_name)
                result["callees"] = callees
                result["callees_count"] = len(callees)
            
            return result
            
        except FunctionNotFoundError as e:
            return {
                "success": False,
                "error": str(e),
                "function_name": function_name
            }
    
    def _handle_search_code(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search_code tool call"""
        if not self.query_engine:
            return {"error": "No DSC context loaded. Call parse_dsc first.", "success": False}
        
        query = arguments["query"]
        file_types = arguments.get("file_types", [".c", ".cpp", ".h", ".hpp"])
        max_results = arguments.get("max_results", 50)
        
        # Use semantic search from query engine
        results = self.query_engine.search_code_semantic(query, self.current_dsc_context)
        
        # Filter by file types
        filtered_results = []
        for result in results:
            file_path = result["file_path"]
            if any(file_path.endswith(ext) for ext in file_types):
                filtered_results.append(result)
        
        # Limit results
        if len(filtered_results) > max_results:
            filtered_results = filtered_results[:max_results]
        
        return {
            "success": True,
            "query": query,
            "results": filtered_results,
            "count": len(filtered_results),
            "total_found": len(results),
            "file_types_filter": file_types
        }
    
    def _handle_get_build_statistics(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_build_statistics tool call"""
        if not self.current_dsc_context:
            return {"error": "No DSC context loaded. Call parse_dsc first.", "success": False}
        
        # Collect statistics
        modules = self.current_dsc_context.included_modules
        module_types = {}
        total_source_files = 0
        
        for module in modules:
            module_type = module.type
            if module_type not in module_types:
                module_types[module_type] = 0
            module_types[module_type] += 1
            total_source_files += len(module.source_files)
        
        return {
            "success": True,
            "dsc_path": self.current_dsc_context.dsc_path,
            "architecture": self.current_dsc_context.architecture,
            "build_target": self.current_dsc_context.build_target,
            "total_modules": len(modules),
            "module_types": module_types,
            "library_mappings": len(self.current_dsc_context.library_mappings),
            "preprocessor_definitions": len(self.current_dsc_context.preprocessor_definitions),
            "total_source_files": total_source_files,
            "parse_timestamp": self.current_dsc_context.timestamp.isoformat()
        }
    
    def _get_build_context_resource(self) -> Dict[str, Any]:
        """Get current build context as a resource"""
        if not self.current_dsc_context:
            return {"error": "No DSC context loaded", "success": False}
        
        return {
            "success": True,
            "content": {
                "dsc_path": self.current_dsc_context.dsc_path,
                "workspace_root": self.current_dsc_context.workspace_root,
                "build_flags": self.current_dsc_context.build_flags,
                "architecture": self.current_dsc_context.architecture,
                "build_target": self.current_dsc_context.build_target,
                "toolchain": self.current_dsc_context.toolchain,
                "modules_count": len(self.current_dsc_context.included_modules),
                "library_mappings_count": len(self.current_dsc_context.library_mappings),
                "timestamp": self.current_dsc_context.timestamp.isoformat()
            }
        }
    
    def _get_dependency_graph_resource(self) -> Dict[str, Any]:
        """Get dependency graph as a resource"""
        if not self.current_dependency_graph:
            return {"error": "No dependency graph available", "success": False}
        
        return {
            "success": True,
            "content": {
                "nodes_count": len(self.current_dependency_graph.nodes),
                "edges_count": len(self.current_dependency_graph.edges),
                "library_mappings": self.current_dependency_graph.library_mappings,
                "nodes": {path: asdict(module) for path, module in self.current_dependency_graph.nodes.items()},
                "edges": self.current_dependency_graph.edges
            }
        }
    
    def _get_function_index_resource(self) -> Dict[str, Any]:
        """Get function index as a resource"""
        if not self.query_engine:
            return {"error": "No query engine available", "success": False}
        
        # This would be expensive to compute for all functions
        # For now, return a summary
        return {
            "success": True,
            "content": {
                "message": "Function index available via find_function tool",
                "modules_indexed": len(self.current_dependency_graph.nodes) if self.current_dependency_graph else 0,
                "cache_size": len(self.query_engine.function_cache)
            }
        }

# Standalone MCP server runner
def run_mcp_server(workspace_dir: str, edk2_path: str, port: int = 8080):
    """Run the MCP server as a standalone application"""
    server = MCPServer(workspace_dir, edk2_path)
    
    print(f"EDK2 Navigator MCP Server starting...")
    print(f"Workspace: {workspace_dir}")
    print(f"EDK2 Path: {edk2_path}")
    print(f"Available tools: {len(server.tools)}")
    print(f"Available resources: {len(server.resources)}")
    
    # Simple JSON-RPC server implementation
    # In a full implementation, this would use proper MCP protocol
    while True:
        try:
            # Read JSON-RPC request from stdin
            line = input()
            if not line:
                continue
            
            request = json.loads(line)
            
            if request.get("method") == "tools/call":
                tool_name = request["params"]["name"]
                arguments = request["params"].get("arguments", {})
                
                response = server.handle_tool_call(tool_name, arguments)
                
                result = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": response
                }
                
                print(json.dumps(result))
            
            elif request.get("method") == "resources/read":
                uri = request["params"]["uri"]
                
                response = server.handle_resource_request(uri)
                
                result = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": response
                }
                
                print(json.dumps(result))
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if 'request' in locals() else None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            print(json.dumps(error_response))

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="EDK2 Navigator MCP Server")
    parser.add_argument("--workspace", required=True, help="Workspace directory")
    parser.add_argument("--edk2-path", required=True, help="EDK2 repository path")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    
    args = parser.parse_args()
    
    run_mcp_server(args.workspace, args.edk2_path, args.port)
