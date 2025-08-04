# Interactive LLM Session Manager

A comprehensive module for managing interactive LLM sessions with context persistence, recursive tool calling, detailed logging, and file system storage for later analysis.

## Features

### 🤖 LLM Provider Support
- **OpenAI GPT**: Full function calling support with GPT-4 and GPT-3.5
- **Anthropic Claude**: Native tool use with Claude-3 models
- **Extensible**: Easy to add new LLM providers

### 🔄 Recursive Tool Calling
- Automatic tool execution based on LLM responses
- Context-aware tool chaining
- Configurable iteration limits
- Error handling and recovery

### 💾 Context Management
- Persistent session storage to file system
- Automatic context trimming to prevent memory issues
- Message archiving for long conversations
- Session restoration across restarts

### 📊 Comprehensive Logging
- Session-specific log files
- Tool execution timing and success rates
- Detailed error tracking
- Performance metrics

### 🔧 EDK2 Integration
- Full integration with EDK2 Navigator tools
- DSC parsing and build context awareness
- Source code editing with automatic backups
- Module dependency analysis

## Architecture

```
InteractiveLLMSession
├── LLMProvider (OpenAI/Anthropic)
├── ExtendedMCPServer (20+ tools)
├── SessionContext (state management)
├── Message history (with metadata)
└── File system persistence
```

## Quick Start

### Basic Usage

```python
from edk2_navigator.interactive_llm_session import create_interactive_session

# Create a session
session = create_interactive_session(
    workspace_dir=".",
    edk2_path="edk2",
    provider_name="openai",
    model="gpt-4-turbo-preview"
)

# Send a message
response = session.send_message("Parse the OVMF DSC file and show me the modules")

# Get session summary
summary = session.get_session_summary()
print(f"Session {summary['session_id']} has {summary['messages_count']} messages")
```

### Session Manager

```python
from edk2_navigator.interactive_llm_session import SessionManager

# Create manager
manager = SessionManager(".", "edk2")

# Create multiple sessions
session1 = manager.create_session("openai")
session2 = manager.create_session("anthropic")

# List all sessions
sessions = manager.list_sessions()
for session_info in sessions:
    print(f"Session {session_info['session_id']}: {session_info['total_messages']} messages")
```

## Configuration

### Environment Variables

```bash
# For OpenAI
export OPENAI_API_KEY="your-openai-api-key"

# For Anthropic
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

### Session Parameters

```python
session = InteractiveLLMSession(
    workspace_dir=".",
    edk2_path="edk2",
    llm_provider=provider,
    session_id="custom-session-id",  # Optional
    context_dir=".llm_sessions",     # Custom context directory
    max_context_messages=50,         # Context window size
    auto_save_interval=10           # Auto-save every N messages
)
```

## Available Tools

The session has access to all EDK2 Navigator tools:

### Navigation Tools
- `parse_dsc` - Parse DSC files and initialize build context
- `get_included_modules` - List modules in the build
- `find_function` - Find function definitions and declarations
- `get_module_dependencies` - Analyze module dependencies
- `trace_call_path` - Trace function call paths
- `analyze_function` - Detailed function analysis
- `search_code` - Semantic code search
- `get_build_statistics` - Build context statistics

### Editing Tools
- `read_source_file` - Read source file contents
- `write_source_file` - Write to source files with backup
- `search_in_source_file` - Search patterns in files
- `replace_in_source_file` - Replace text with regex
- `insert_at_line` - Insert content at specific lines
- `delete_lines` - Delete line ranges
- `add_function` - Add new functions
- `modify_function` - Modify existing functions
- `add_include` - Add include statements
- `list_backups` - List backup files
- `restore_backup` - Restore from backups
- `find_and_edit_function` - Find and prepare functions for editing

## File System Structure

```
workspace/
├── .llm_sessions/
│   ├── session_abc123.json      # Session state
│   ├── session_abc123.log       # Session logs
│   ├── session_abc123_archive.jsonl  # Archived messages
│   ├── session_abc123_export.json    # Full export
│   └── backups/                 # Source file backups
│       ├── Platform.c.backup.20240103_093000
│       └── ...
```

## Session Data Structure

### Message Format
```json
{
  "role": "user|assistant|tool",
  "content": "message content",
  "timestamp": "2024-01-03T09:30:00Z",
  "message_id": "msg_abc123",
  "tool_calls": [...],
  "tool_call_id": "call_xyz789",
  "metadata": {...}
}
```

### Session Context
```json
{
  "session_id": "session_abc123",
  "created_at": "2024-01-03T09:00:00Z",
  "last_activity": "2024-01-03T09:30:00Z",
  "total_messages": 25,
  "total_tool_calls": 12,
  "current_dsc_context": "OvmfPkg/OvmfPkgX64.dsc",
  "active_files": ["Platform.c", "PlatformPei.inf"],
  "session_metadata": {...}
}
```

## Demo Scripts

### Basic Demo
```bash
python interactive_llm_demo.py --mode demo --provider openai
```

### Session Manager Demo
```bash
python interactive_llm_demo.py --mode manager --provider anthropic
```

### Interactive CLI
```bash
python interactive_llm_demo.py --mode interactive
```

## Advanced Features

### Custom LLM Provider

```python
from edk2_navigator.interactive_llm_session import LLMProvider

class CustomProvider(LLMProvider):
    def supports_tool_calling(self) -> bool:
        return True
    
    def call_llm(self, messages, available_tools, **kwargs):
        # Implement your LLM integration
        return {"content": "response", "tool_calls": [...]}
```

### Session Export and Analysis

```python
# Export session for analysis
export_path = session.export_session()

# Load exported data
with open(export_path) as f:
    data = json.load(f)

# Analyze tool usage
stats = data["tool_call_statistics"]
for tool_name, stats in stats["tool_statistics"].items():
    print(f"{tool_name}: {stats['count']} calls, {stats['success_rate']:.2%} success")
```

### Context Trimming and Archiving

The session automatically manages context size:
- Keeps recent messages in active context
- Archives older messages to `.jsonl` files
- Maintains tool call sequences intact
- Configurable context window size

## Error Handling

The session includes comprehensive error handling:
- LLM API failures with retry logic
- Tool execution errors with detailed logging
- Session persistence failures with recovery
- Context corruption detection and repair

## Performance Considerations

### Memory Management
- Automatic context trimming prevents memory bloat
- Message archiving for long conversations
- Configurable context window sizes

### Tool Execution
- Parallel tool execution where possible
- Execution time tracking and optimization
- Caching of expensive operations

### File System
- Efficient JSON serialization
- Incremental saves to prevent data loss
- Cleanup utilities for old sessions

## Logging

### Session Logs
Each session creates detailed logs:
```
2024-01-03 09:30:15 - session_abc123 - INFO - Added message: user - 45 chars
2024-01-03 09:30:16 - session_abc123 - DEBUG - LLM call iteration 1
2024-01-03 09:30:18 - session_abc123 - INFO - Tool parse_dsc executed successfully in 1.23s
2024-01-03 09:30:19 - session_abc123 - INFO - Updated DSC context: OvmfPkg/OvmfPkgX64.dsc
```

### Tool Statistics
Automatic tracking of tool usage:
- Execution times and success rates
- Error patterns and frequency
- Performance trends over time

## Best Practices

### Session Management
1. Use descriptive session IDs for important sessions
2. Export sessions before major changes
3. Clean up old sessions periodically
4. Monitor log files for errors

### Tool Usage
1. Parse DSC files early to establish context
2. Use find_and_edit_function for safe code modifications
3. Always check backup files before major edits
4. Monitor tool execution times

### Context Management
1. Keep context window appropriate for your use case
2. Use session metadata for important state
3. Export sessions for analysis and debugging
4. Archive important conversations

## Troubleshooting

### Common Issues

**Session won't load**
- Check file permissions in `.llm_sessions/`
- Verify JSON file integrity
- Look for corruption in log files

**Tool calls failing**
- Verify EDK2 path is correct
- Check DSC file exists and is parseable
- Review tool arguments in logs

**Memory issues**
- Reduce `max_context_messages`
- Increase `auto_save_interval`
- Clean up old archived messages

**API errors**
- Verify API keys are set correctly
- Check rate limits and quotas
- Review network connectivity

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

session = create_interactive_session(...)
```

## Contributing

To extend the interactive LLM session:

1. **Add new LLM providers**: Inherit from `LLMProvider`
2. **Add new tools**: Extend the MCP server
3. **Improve context management**: Enhance trimming algorithms
4. **Add analysis features**: Extend export functionality

## License

This module is part of the EDK2 Navigator project and follows the same licensing terms.
