# EDK2 Navigator LLM Integration

This document explains how to use the EDK2 Navigator tools with Large Language Models (LLMs) for intelligent firmware development.

## Overview

The EDK2 Navigator provides two main integration points for LLMs:

1. **Navigation Tools** - For exploring and understanding EDK2 codebases
2. **Editing Tools** - For safely modifying EDK2 source files with automatic backups

## Quick Start

### 1. Basic LLM Integration Demo

```bash
# Run the basic navigation demo
python llm_edk2_demo.py

# Run interactive session
python llm_edk2_demo.py --interactive
```

### 2. Advanced Editing Integration Demo

```bash
# Run the editing capabilities demo
python llm_edk2_editing_demo.py

# Run interactive editing session
python llm_edk2_editing_demo.py --interactive
```

### 3. Standalone MCP Servers

```bash
# Basic MCP server (navigation only)
python -m edk2_navigator.mcp_server --workspace . --edk2-path edk2

# Extended MCP server (navigation + editing)
python -m edk2_navigator.mcp_server_extended --workspace . --edk2-path edk2
```

## Available Tools

### Navigation Tools (8 tools)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `parse_dsc` | Parse DSC file and initialize build context | `dsc_path`, `build_flags` |
| `get_included_modules` | Get list of modules in build | `filter_by_type`, `include_details` |
| `find_function` | Find function definitions/declarations | `function_name`, `include_declarations` |
| `get_module_dependencies` | Get module dependency information | `module_name`, `include_transitive` |
| `trace_call_path` | Trace function call paths | `function_name`, `max_depth` |
| `analyze_function` | Detailed function analysis | `function_name`, `include_callers` |
| `search_code` | Search for code patterns | `query`, `file_types`, `max_results` |
| `get_build_statistics` | Get build context statistics | None |

### Editing Tools (12 tools)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `read_source_file` | Read source file contents | `file_path` |
| `write_source_file` | Write content to source file | `file_path`, `content`, `create_backup` |
| `search_in_source_file` | Search patterns in file | `file_path`, `pattern`, `context_lines` |
| `replace_in_source_file` | Replace text using regex | `file_path`, `search_pattern`, `replacement` |
| `insert_at_line` | Insert content at line number | `file_path`, `line_number`, `content` |
| `delete_lines` | Delete lines from file | `file_path`, `start_line`, `end_line` |
| `add_function` | Add new function to file | `file_path`, `function_code`, `insert_location` |
| `modify_function` | Modify existing function | `file_path`, `function_name`, `new_function_code` |
| `add_include` | Add include statement | `file_path`, `include_statement` |
| `list_backups` | List available backups | `file_path` (optional) |
| `restore_backup` | Restore file from backup | `backup_path`, `target_path` |
| `find_and_edit_function` | Find function for editing | `function_name`, `show_content` |

## Usage Examples

### Example 1: Understanding OVMF Build Context

```python
from edk2_navigator.mcp_server import MCPServer

# Initialize server
server = MCPServer(".", "edk2")

# Parse OVMF DSC
result = server.handle_tool_call("parse_dsc", {
    "dsc_path": "edk2/OvmfPkg/OvmfPkgX64.dsc",
    "build_flags": {"TARGET": "DEBUG", "ARCH": "X64"}
})

# Get included modules
modules = server.handle_tool_call("get_included_modules", {
    "filter_by_type": "DXE_DRIVER",
    "include_details": True
})

print(f"Found {modules['count']} DXE drivers")
```

### Example 2: Finding and Analyzing Functions

```python
# Find UefiMain function
locations = server.handle_tool_call("find_function", {
    "function_name": "UefiMain",
    "include_declarations": True
})

# Analyze the function
analysis = server.handle_tool_call("analyze_function", {
    "function_name": "UefiMain",
    "include_callers": True,
    "include_callees": True
})

print(f"Found {locations['count']} locations")
print(f"Function has {analysis['callers_count']} callers")
```

### Example 3: Safe Source File Editing

```python
from edk2_navigator.mcp_server_extended import ExtendedMCPServer

# Initialize extended server
server = ExtendedMCPServer(".", "edk2")

# Read a source file
content = server.handle_tool_call("read_source_file", {
    "file_path": "edk2/OvmfPkg/PlatformPei/Platform.c"
})

# Search for patterns
matches = server.handle_tool_call("search_in_source_file", {
    "file_path": "edk2/OvmfPkg/PlatformPei/Platform.c",
    "pattern": "EFI_STATUS",
    "context_lines": 3
})

# Add a new function (with automatic backup)
result = server.handle_tool_call("add_function", {
    "file_path": "edk2/OvmfPkg/PlatformPei/Platform.c",
    "function_code": """
VOID
EFIAPI
DebugHelper (
  IN CONST CHAR8  *Message
  )
{
  DEBUG ((DEBUG_INFO, "%a\\n", Message));
}""",
    "insert_location": "end"
})

print(f"Backup created: {result['backup_path']}")
```

### Example 4: LLM Integration Pattern

```python
class LLMClient:
    def __init__(self, mcp_server):
        self.server = mcp_server
    
    def process_request(self, user_prompt):
        # 1. Parse user intent
        if "find function" in user_prompt.lower():
            function_name = self.extract_function_name(user_prompt)
            
            # 2. Use appropriate tools
            result = self.server.handle_tool_call("find_function", {
                "function_name": function_name
            })
            
            # 3. Format response for user
            if result["success"]:
                return f"Found {result['count']} locations for {function_name}"
            else:
                return f"Function {function_name} not found"
        
        # Handle other intents...
```

## Safety Features

### Automatic Backups

All editing operations automatically create timestamped backups:

```python
# Every edit creates a backup
result = server.handle_tool_call("write_source_file", {
    "file_path": "test.c",
    "content": "new content",
    "create_backup": True  # Default
})

# Backup path returned
print(f"Backup: {result['backup_path']}")
# Example: .edk2_navigator_backups/test.c.20250102_192030.backup
```

### Backup Management

```python
# List all backups
backups = server.handle_tool_call("list_backups", {})

# List backups for specific file
file_backups = server.handle_tool_call("list_backups", {
    "file_path": "test.c"
})

# Restore from backup
restore = server.handle_tool_call("restore_backup", {
    "backup_path": ".edk2_navigator_backups/test.c.20250102_192030.backup",
    "target_path": "test.c"
})
```

### Build Context Awareness

All operations are aware of the current DSC build context:

```python
# Parse DSC first
server.handle_tool_call("parse_dsc", {
    "dsc_path": "edk2/OvmfPkg/OvmfPkgX64.dsc"
})

# Now function searches are limited to build-relevant code
result = server.handle_tool_call("find_function", {
    "function_name": "SomeFunction"
})
# Only searches modules included in OVMF build
```

## Integration with Real LLMs

### OpenAI Integration Example

```python
import openai
from edk2_navigator.mcp_server_extended import ExtendedMCPServer

class OpenAIEDK2Assistant:
    def __init__(self, api_key, workspace_dir, edk2_path):
        self.client = openai.OpenAI(api_key=api_key)
        self.mcp_server = ExtendedMCPServer(workspace_dir, edk2_path)
        
        # Define available tools for OpenAI
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["inputSchema"]
                }
            }
            for tool in self.mcp_server.tools
        ]
    
    def chat(self, message):
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an EDK2 firmware development assistant with access to code navigation and editing tools."},
                {"role": "user", "content": message}
            ],
            tools=self.tools,
            tool_choice="auto"
        )
        
        # Handle tool calls
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                # Execute tool via MCP server
                result = self.mcp_server.handle_tool_call(function_name, arguments)
                
                # Send result back to OpenAI for final response
                # ... (implementation continues)
```

### Anthropic Claude Integration Example

```python
import anthropic
from edk2_navigator.mcp_server_extended import ExtendedMCPServer

class ClaudeEDK2Assistant:
    def __init__(self, api_key, workspace_dir, edk2_path):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.mcp_server = ExtendedMCPServer(workspace_dir, edk2_path)
    
    def chat(self, message):
        # Format tools for Claude
        tools_description = self._format_tools_for_claude()
        
        response = self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4000,
            messages=[{
                "role": "user", 
                "content": f"{message}\n\nAvailable tools:\n{tools_description}"
            }]
        )
        
        # Parse tool usage from response and execute
        # ... (implementation continues)
```

## Best Practices

### 1. Always Parse DSC First

```python
# ✅ Good: Parse DSC to establish context
server.handle_tool_call("parse_dsc", {"dsc_path": "edk2/OvmfPkg/OvmfPkgX64.dsc"})
result = server.handle_tool_call("find_function", {"function_name": "UefiMain"})

# ❌ Bad: Search without context
result = server.handle_tool_call("find_function", {"function_name": "UefiMain"})
# May search irrelevant code not in build
```

### 2. Use Build Context for Relevance

```python
# ✅ Good: Get modules in current build
modules = server.handle_tool_call("get_included_modules", {})

# ✅ Good: Search only in build-relevant code
result = server.handle_tool_call("search_code", {
    "query": "PCI enumeration",
    "file_types": [".c", ".h"]
})
```

### 3. Leverage Automatic Backups

```python
# ✅ Good: Let system create backups automatically
result = server.handle_tool_call("add_function", {
    "file_path": "source.c",
    "function_code": new_function
})

# ✅ Good: Check backup was created
if result["success"] and result["backup_path"]:
    print(f"Safe to proceed, backup at: {result['backup_path']}")
```

### 4. Handle Errors Gracefully

```python
# ✅ Good: Check results and handle errors
result = server.handle_tool_call("find_function", {"function_name": "NonExistent"})

if result["success"]:
    print(f"Found {result['count']} locations")
else:
    print(f"Error: {result['error']}")
    # Provide alternative suggestions to user
```

## Performance Considerations

### Caching

The system automatically caches parsed DSC data:

```python
# First parse: ~2-3 seconds
result1 = server.handle_tool_call("parse_dsc", {"dsc_path": "edk2/OvmfPkg/OvmfPkgX64.dsc"})

# Subsequent parses: <100ms (if file unchanged)
result2 = server.handle_tool_call("parse_dsc", {"dsc_path": "edk2/OvmfPkg/OvmfPkgX64.dsc"})
```

### Memory Usage

- Full OVMF graph: ~50MB memory
- Function search cache: Grows with usage
- Backup files: Stored on disk, not in memory

### Optimization Tips

1. **Reuse server instances** - Don't recreate for each request
2. **Parse DSC once** - Cache the build context
3. **Use specific searches** - Avoid broad patterns
4. **Clean old backups** - Manage disk space

## Troubleshooting

### Common Issues

1. **"No DSC context loaded"**
   ```python
   # Solution: Parse DSC first
   server.handle_tool_call("parse_dsc", {"dsc_path": "path/to/file.dsc"})
   ```

2. **"Function not found"**
   ```python
   # Check if function is in build-relevant code
   modules = server.handle_tool_call("get_included_modules", {})
   # Verify function exists in included modules
   ```

3. **"File not found"**
   ```python
   # Use relative paths from workspace root
   # ✅ Good: "edk2/OvmfPkg/PlatformPei/Platform.c"
   # ❌ Bad: "/absolute/path/to/Platform.c"
   ```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now all tool calls will show detailed information
```

## Contributing

To extend the tools:

1. **Add new navigation tools** - Extend `MCPServer._define_tools()`
2. **Add new editing tools** - Extend `ExtendedMCPServer._define_editing_tools()`
3. **Add new resources** - Extend `_define_resources()` methods
4. **Add tool handlers** - Implement `_handle_new_tool()` methods

Example new tool:

```python
def _define_tools(self):
    tools = super()._define_tools()
    tools.append({
        "name": "my_new_tool",
        "description": "Does something useful",
        "inputSchema": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "First parameter"}
            },
            "required": ["param1"]
        }
    })
    return tools

def _handle_my_new_tool(self, arguments):
    param1 = arguments["param1"]
    # Implementation here
    return {"success": True, "result": "Done"}
```

## License

This project is part of the EDK2 Navigator system. See main project license for details.
