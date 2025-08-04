"""
Extended MCP Server - Includes source editing capabilities for EDK2 files
"""
import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import asdict
from .mcp_server import MCPServer
from .source_editor import SourceEditor, EditResult, FileSearchResult

class ExtendedMCPServer(MCPServer):
    """Extended MCP Server with source editing capabilities"""
    
    def __init__(self, workspace_dir: str, edk2_path: str):
        """Initialize extended MCP server"""
        super().__init__(workspace_dir, edk2_path)
        
        # Initialize source editor
        self.source_editor = SourceEditor(workspace_dir, edk2_path)
        
        # Add editing tools to the existing tools
        self.tools.extend(self._define_editing_tools())
        self.resources.extend(self._define_editing_resources())
    
    def _define_editing_tools(self) -> List[Dict[str, Any]]:
        """Define source editing MCP tools"""
        return [
            {
                "name": "read_source_file",
                "description": "Read the contents of a source file in the EDK2 repository",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the source file relative to workspace"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "write_source_file",
                "description": "Write content to a source file (creates backup automatically)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the source file relative to workspace"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        },
                        "create_backup": {
                            "type": "boolean",
                            "description": "Whether to create a backup before writing",
                            "default": True
                        }
                    },
                    "required": ["file_path", "content"]
                }
            },
            {
                "name": "search_in_source_file",
                "description": "Search for patterns within a source file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the source file relative to workspace"
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Regex pattern to search for"
                        },
                        "context_lines": {
                            "type": "integer",
                            "description": "Number of context lines to include",
                            "default": 3
                        }
                    },
                    "required": ["file_path", "pattern"]
                }
            },
            {
                "name": "replace_in_source_file",
                "description": "Replace text in a source file using regex patterns",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the source file relative to workspace"
                        },
                        "search_pattern": {
                            "type": "string",
                            "description": "Regex pattern to search for"
                        },
                        "replacement": {
                            "type": "string",
                            "description": "Replacement text"
                        },
                        "max_replacements": {
                            "type": "integer",
                            "description": "Maximum number of replacements (-1 for all)",
                            "default": -1
                        }
                    },
                    "required": ["file_path", "search_pattern", "replacement"]
                }
            },
            {
                "name": "insert_at_line",
                "description": "Insert content at a specific line number in a source file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the source file relative to workspace"
                        },
                        "line_number": {
                            "type": "integer",
                            "description": "Line number to insert at (1-based)"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to insert"
                        }
                    },
                    "required": ["file_path", "line_number", "content"]
                }
            },
            {
                "name": "delete_lines",
                "description": "Delete lines from a source file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the source file relative to workspace"
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Starting line number (1-based)"
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "Ending line number (1-based)"
                        }
                    },
                    "required": ["file_path", "start_line", "end_line"]
                }
            },
            {
                "name": "add_function",
                "description": "Add a new function to a source file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the source file relative to workspace"
                        },
                        "function_code": {
                            "type": "string",
                            "description": "Complete function code to add"
                        },
                        "insert_location": {
                            "type": "string",
                            "description": "Where to insert: 'end', 'beginning', or line number",
                            "default": "end"
                        }
                    },
                    "required": ["file_path", "function_code"]
                }
            },
            {
                "name": "modify_function",
                "description": "Modify an existing function in a source file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the source file relative to workspace"
                        },
                        "function_name": {
                            "type": "string",
                            "description": "Name of the function to modify"
                        },
                        "new_function_code": {
                            "type": "string",
                            "description": "New function code to replace the existing function"
                        }
                    },
                    "required": ["file_path", "function_name", "new_function_code"]
                }
            },
            {
                "name": "add_include",
                "description": "Add an include statement to a source file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the source file relative to workspace"
                        },
                        "include_statement": {
                            "type": "string",
                            "description": "Include statement to add (e.g., '#include <Library/UefiLib.h>')"
                        }
                    },
                    "required": ["file_path", "include_statement"]
                }
            },
            {
                "name": "list_backups",
                "description": "List available backup files",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Filter backups for specific file (optional)"
                        }
                    }
                }
            },
            {
                "name": "restore_backup",
                "description": "Restore a file from backup",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "backup_path": {
                            "type": "string",
                            "description": "Path to the backup file"
                        },
                        "target_path": {
                            "type": "string",
                            "description": "Target file path to restore to"
                        }
                    },
                    "required": ["backup_path", "target_path"]
                }
            },
            {
                "name": "find_and_edit_function",
                "description": "Find a function in build-relevant files and prepare it for editing",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "description": "Name of function to find and edit"
                        },
                        "show_content": {
                            "type": "boolean",
                            "description": "Whether to show the current function content",
                            "default": True
                        }
                    },
                    "required": ["function_name"]
                }
            }
        ]
    
    def _define_editing_resources(self) -> List[Dict[str, Any]]:
        """Define editing-related MCP resources"""
        return [
            {
                "uri": "edk2://backup-list",
                "name": "Backup Files List",
                "description": "List of all backup files created during editing",
                "mimeType": "application/json"
            },
            {
                "uri": "edk2://edit-history",
                "name": "Edit History",
                "description": "History of all file edits performed",
                "mimeType": "application/json"
            }
        ]
    
    def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool calls including editing tools"""
        # Handle editing tools
        editing_tools = {
            "read_source_file": self._handle_read_source_file,
            "write_source_file": self._handle_write_source_file,
            "search_in_source_file": self._handle_search_in_source_file,
            "replace_in_source_file": self._handle_replace_in_source_file,
            "insert_at_line": self._handle_insert_at_line,
            "delete_lines": self._handle_delete_lines,
            "add_function": self._handle_add_function,
            "modify_function": self._handle_modify_function,
            "add_include": self._handle_add_include,
            "list_backups": self._handle_list_backups,
            "restore_backup": self._handle_restore_backup,
            "find_and_edit_function": self._handle_find_and_edit_function
        }
        
        if tool_name in editing_tools:
            try:
                return editing_tools[tool_name](arguments)
            except Exception as e:
                return {
                    "error": str(e),
                    "success": False,
                    "error_type": type(e).__name__
                }
        else:
            # Delegate to parent class for navigation tools
            return super().handle_tool_call(tool_name, arguments)
    
    def handle_resource_request(self, uri: str) -> Dict[str, Any]:
        """Handle resource requests including editing resources"""
        if uri == "edk2://backup-list":
            return self._get_backup_list_resource()
        elif uri == "edk2://edit-history":
            return self._get_edit_history_resource()
        else:
            # Delegate to parent class
            return super().handle_resource_request(uri)
    
    # Editing tool handlers
    def _handle_read_source_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle read_source_file tool call"""
        file_path = self._resolve_dsc_path(arguments["file_path"])
        
        try:
            content = self.source_editor.read_file(file_path)
            
            # Get file statistics
            lines = content.split('\n')
            
            return {
                "success": True,
                "file_path": file_path,
                "content": content,
                "line_count": len(lines),
                "character_count": len(content),
                "size_bytes": len(content.encode('utf-8'))
            }
            
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "file_path": file_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    def _handle_write_source_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle write_source_file tool call"""
        file_path = self._resolve_dsc_path(arguments["file_path"])
        content = arguments["content"]
        create_backup = arguments.get("create_backup", True)
        
        result = self.source_editor.write_file(file_path, content, create_backup)
        
        return {
            "success": result.success,
            "file_path": result.file_path,
            "changes_made": result.changes_made,
            "backup_path": result.backup_path,
            "error_message": result.error_message,
            "lines_added": result.lines_added,
            "lines_removed": result.lines_removed,
            "lines_modified": result.lines_modified
        }
    
    def _handle_search_in_source_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search_in_source_file tool call"""
        file_path = self._resolve_dsc_path(arguments["file_path"])
        pattern = arguments["pattern"]
        context_lines = arguments.get("context_lines", 3)
        
        try:
            results = self.source_editor.search_in_file(file_path, pattern, context_lines)
            
            search_results = []
            for result in results:
                search_results.append({
                    "line_number": result.line_number,
                    "line_content": result.line_content,
                    "match_start": result.match_start,
                    "match_end": result.match_end,
                    "context_before": result.context_before,
                    "context_after": result.context_after
                })
            
            return {
                "success": True,
                "file_path": file_path,
                "pattern": pattern,
                "results": search_results,
                "match_count": len(search_results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path,
                "pattern": pattern
            }
    
    def _handle_replace_in_source_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle replace_in_source_file tool call"""
        file_path = self._resolve_dsc_path(arguments["file_path"])
        search_pattern = arguments["search_pattern"]
        replacement = arguments["replacement"]
        max_replacements = arguments.get("max_replacements", -1)
        
        result = self.source_editor.replace_in_file(file_path, search_pattern, replacement, max_replacements)
        
        return {
            "success": result.success,
            "file_path": result.file_path,
            "changes_made": result.changes_made,
            "backup_path": result.backup_path,
            "error_message": result.error_message,
            "lines_modified": result.lines_modified,
            "search_pattern": search_pattern,
            "replacement": replacement
        }
    
    def _handle_insert_at_line(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle insert_at_line tool call"""
        file_path = self._resolve_dsc_path(arguments["file_path"])
        line_number = arguments["line_number"]
        content = arguments["content"]
        
        result = self.source_editor.insert_at_line(file_path, line_number, content)
        
        return {
            "success": result.success,
            "file_path": result.file_path,
            "changes_made": result.changes_made,
            "backup_path": result.backup_path,
            "error_message": result.error_message,
            "lines_added": result.lines_added,
            "line_number": line_number
        }
    
    def _handle_delete_lines(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle delete_lines tool call"""
        file_path = self._resolve_dsc_path(arguments["file_path"])
        start_line = arguments["start_line"]
        end_line = arguments["end_line"]
        
        result = self.source_editor.delete_lines(file_path, start_line, end_line)
        
        return {
            "success": result.success,
            "file_path": result.file_path,
            "changes_made": result.changes_made,
            "backup_path": result.backup_path,
            "error_message": result.error_message,
            "lines_removed": result.lines_removed,
            "start_line": start_line,
            "end_line": end_line
        }
    
    def _handle_add_function(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle add_function tool call"""
        file_path = self._resolve_dsc_path(arguments["file_path"])
        function_code = arguments["function_code"]
        insert_location = arguments.get("insert_location", "end")
        
        result = self.source_editor.add_function(file_path, function_code, insert_location)
        
        return {
            "success": result.success,
            "file_path": result.file_path,
            "changes_made": result.changes_made,
            "backup_path": result.backup_path,
            "error_message": result.error_message,
            "lines_added": result.lines_added,
            "insert_location": insert_location
        }
    
    def _handle_modify_function(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle modify_function tool call"""
        file_path = self._resolve_dsc_path(arguments["file_path"])
        function_name = arguments["function_name"]
        new_function_code = arguments["new_function_code"]
        
        result = self.source_editor.modify_function(file_path, function_name, new_function_code)
        
        return {
            "success": result.success,
            "file_path": result.file_path,
            "function_name": function_name,
            "changes_made": result.changes_made,
            "backup_path": result.backup_path,
            "error_message": result.error_message,
            "lines_modified": result.lines_modified
        }
    
    def _handle_add_include(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle add_include tool call"""
        file_path = self._resolve_dsc_path(arguments["file_path"])
        include_statement = arguments["include_statement"]
        
        result = self.source_editor.add_include(file_path, include_statement)
        
        return {
            "success": result.success,
            "file_path": result.file_path,
            "include_statement": include_statement,
            "changes_made": result.changes_made,
            "backup_path": result.backup_path,
            "error_message": result.error_message,
            "lines_added": result.lines_added
        }
    
    def _handle_list_backups(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list_backups tool call"""
        file_path = self._resolve_dsc_path(arguments.get("file_path"))
        
        try:
            backups = self.source_editor.list_backups(file_path)
            
            return {
                "success": True,
                "backups": backups,
                "count": len(backups),
                "filter_file": file_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "filter_file": file_path
            }
    
    def _handle_restore_backup(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle restore_backup tool call"""
        backup_path = self._resolve_dsc_path(arguments["backup_path"])
        target_path = self._resolve_dsc_path(arguments["target_path"])
        
        result = self.source_editor.restore_backup(backup_path, target_path)
        
        return {
            "success": result.success,
            "target_path": result.file_path,
            "backup_path": backup_path,
            "changes_made": result.changes_made,
            "new_backup_path": result.backup_path,
            "error_message": result.error_message
        }
    
    def _handle_find_and_edit_function(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle find_and_edit_function tool call"""
        if not self.query_engine:
            return {"error": "No DSC context loaded. Call parse_dsc first.", "success": False}
        
        function_name = arguments["function_name"]
        show_content = arguments.get("show_content", True)
        
        try:
            # Find function locations
            locations = self.query_engine.find_function(function_name, self.current_dsc_context)
            
            if not locations:
                return {
                    "success": False,
                    "error": f"Function {function_name} not found in build-relevant code",
                    "function_name": function_name
                }
            
            # Get function content if requested
            function_details = []
            for loc in locations:
                detail = {
                    "file_path": loc.file_path,
                    "line_number": loc.line_number,
                    "module_name": loc.module_name,
                    "signature": loc.function_signature,
                    "is_definition": loc.is_definition,
                    "calling_convention": loc.calling_convention
                }
                
                if show_content and loc.is_definition:
                    try:
                        # Read the file and extract function content
                        file_content = self.source_editor.read_file(loc.file_path)
                        lines = file_content.split('\n')
                        
                        # Get some context around the function
                        start_line = max(0, loc.line_number - 5)
                        end_line = min(len(lines), loc.line_number + 20)
                        
                        detail["content_preview"] = '\n'.join(lines[start_line:end_line])
                        detail["content_start_line"] = start_line + 1
                        
                    except Exception as e:
                        detail["content_error"] = str(e)
                
                function_details.append(detail)
            
            return {
                "success": True,
                "function_name": function_name,
                "locations": function_details,
                "count": len(function_details),
                "definitions": len([loc for loc in locations if loc.is_definition]),
                "declarations": len([loc for loc in locations if not loc.is_definition])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "function_name": function_name
            }
    
    # Resource handlers
    def _get_backup_list_resource(self) -> Dict[str, Any]:
        """Get backup list as a resource"""
        try:
            backups = self.source_editor.list_backups()
            
            return {
                "success": True,
                "content": {
                    "backups": backups,
                    "total_count": len(backups),
                    "backup_directory": str(self.source_editor.backup_dir)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_edit_history_resource(self) -> Dict[str, Any]:
        """Get edit history as a resource"""
        # This would be implemented with proper edit tracking
        # For now, return a placeholder
        return {
            "success": True,
            "content": {
                "message": "Edit history tracking not yet implemented",
                "suggestion": "Use list_backups tool to see file modification history"
            }
        }

# Standalone extended MCP server runner
def run_extended_mcp_server(workspace_dir: str, edk2_path: str, port: int = 8080):
    """Run the extended MCP server as a standalone application"""
    server = ExtendedMCPServer(workspace_dir, edk2_path)
    
    print(f"EDK2 Navigator Extended MCP Server starting...")
    print(f"Workspace: {workspace_dir}")
    print(f"EDK2 Path: {edk2_path}")
    print(f"Available tools: {len(server.tools)}")
    print(f"Available resources: {len(server.resources)}")
    print(f"Editing capabilities: Enabled")
    
    # Simple JSON-RPC server implementation
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
    
    parser = argparse.ArgumentParser(description="EDK2 Navigator Extended MCP Server")
    parser.add_argument("--workspace", required=True, help="Workspace directory")
    parser.add_argument("--edk2-path", required=True, help="EDK2 repository path")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    
    args = parser.parse_args()
    
    run_extended_mcp_server(args.workspace, args.edk2_path, args.port)
