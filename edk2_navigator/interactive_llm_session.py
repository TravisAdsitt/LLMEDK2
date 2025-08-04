"""
Interactive LLM Session Manager - Handles context-aware LLM interactions with tool calling
"""
import json
import os
import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from abc import ABC, abstractmethod

from .mcp_server_extended import ExtendedMCPServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Represents a single message in the conversation"""
    role: str  # 'user', 'assistant', 'tool'
    content: str
    timestamp: datetime
    message_id: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'message_id': self.message_id,
            'tool_calls': self.tool_calls,
            'tool_call_id': self.tool_call_id,
            'metadata': self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create from dictionary"""
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            message_id=data['message_id'],
            tool_calls=data.get('tool_calls'),
            tool_call_id=data.get('tool_call_id'),
            metadata=data.get('metadata', {})
        )


@dataclass
class ToolCallResult:
    """Result of a tool call execution"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    call_id: str = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


@dataclass
class SessionContext:
    """Context information for the session"""
    session_id: str
    created_at: datetime
    last_activity: datetime
    total_messages: int
    total_tool_calls: int
    current_dsc_context: Optional[str] = None
    active_files: List[str] = None
    session_metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.active_files is None:
            self.active_files = []
        if self.session_metadata is None:
            self.session_metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'total_messages': self.total_messages,
            'total_tool_calls': self.total_tool_calls,
            'current_dsc_context': self.current_dsc_context,
            'active_files': self.active_files,
            'session_metadata': self.session_metadata
        }


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def call_llm(self, messages: List[Message], available_tools: List[Dict[str, Any]], 
                 **kwargs) -> Dict[str, Any]:
        """Call the LLM with conversation history and available tools"""
        pass

    @abstractmethod
    def supports_tool_calling(self) -> bool:
        """Whether this provider supports native tool calling"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider with function calling support"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-turbo-preview"):
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
            self.model = model if model else "gpt-4-turbo-preview"
        except ImportError:
            raise ImportError("openai package not installed. Install with: pip install openai")

    def supports_tool_calling(self) -> bool:
        return True

    def call_llm(self, messages: List[Message], available_tools: List[Dict[str, Any]], 
                 **kwargs) -> Dict[str, Any]:
        """Call OpenAI API with function calling"""
        
        # Convert messages to OpenAI format
        openai_messages = []
        
        # Add system message
        system_prompt = kwargs.get('system_prompt', self._get_default_system_prompt())
        openai_messages.append({"role": "system", "content": system_prompt})
        
        # Convert conversation messages
        for msg in messages:
            if msg.role == 'tool':
                openai_messages.append({
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id
                })
            else:
                openai_msg = {"role": msg.role, "content": msg.content}
                if msg.tool_calls:
                    openai_msg["tool_calls"] = [
                        {
                            "id": call.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                            "type": "function",
                            "function": {
                                "name": call["name"],
                                "arguments": json.dumps(call["arguments"])
                            }
                        }
                        for call in msg.tool_calls
                    ]
                openai_messages.append(openai_msg)

        # Convert tools to OpenAI format
        openai_tools = []
        for tool in available_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["inputSchema"]
                }
            })

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                tools=openai_tools if openai_tools else None,
                tool_choice="auto" if openai_tools else None,
                temperature=kwargs.get('temperature', 0.1),
                max_tokens=kwargs.get('max_tokens', 4000)
            )

            message = response.choices[0].message
            
            result = {
                "content": message.content or "",
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

            if message.tool_calls:
                result["tool_calls"] = []
                for tool_call in message.tool_calls:
                    result["tool_calls"].append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": json.loads(tool_call.function.arguments)
                    })

            return result

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {"error": str(e)}

    def _get_default_system_prompt(self) -> str:
        return """You are a research assistant for analyzing EDK2 (UEFI Development Kit) codebases. You MUST use the available tools to gather ALL information - you cannot rely on general knowledge about EDK2 or UEFI.

CRITICAL RULES:
1. NEVER provide information without first using tools to verify it
2. ALWAYS use tools to research before answering any question
3. CLEARLY distinguish between tool-verified facts and any assumptions
4. Include specific references to files, functions, and modules found by tools
5. If you don't have tool data, explicitly state "I need to research this using tools"

Available research tools:
- parse_dsc: Parse DSC files to understand build context
- find_function: Locate function definitions and declarations
- search_code: Search for code patterns and keywords
- get_included_modules: List modules in the build
- get_module_dependencies: Analyze module dependencies
- read_source_file: Read actual source code content
- trace_call_path: Follow function call chains

RESPONSE FORMAT:
- Start with tool research to gather facts
- Present findings with specific file/line references
- Clearly label any assumptions as "ASSUMPTION:" 
- End with "SOURCES:" listing all files/modules referenced

IMPORTANT: DSC file paths should be relative to the EDK2 repository root (e.g., "OvmfPkg/OvmfPkgX64.dsc")."""



class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider with robust function calling support"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
            self.model = model if model else "claude-3-5-sonnet-20241022"
            print(f"Using Anthropic model: {self.model}")
        except ImportError:
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")

    def supports_tool_calling(self) -> bool:
        return True

    def _convert_tools_to_anthropic_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tools to Anthropic's expected format"""
        anthropic_tools = []
        
        for tool in tools:
            # Handle both function-style and direct tool definitions
            if "function" in tool:
                func_def = tool["function"]
                input_schema = func_def.get("parameters", {})
            else:
                # Direct tool definition
                input_schema = tool.get("inputSchema", {})

            
            # # Ensure input_schema has required 'type' field
            # if not input_schema.get("type"):
            #     input_schema["type"] = "object"
            
            # # Ensure properties exist if type is object
            # if input_schema.get("type") == "object" and "properties" not in input_schema:
            #     # If the tool definition has properties, copy them in
            #     if "properties" in tool:
            #         input_schema["properties"] = tool["properties"]
            #     else:
                    # input_schema["properties"] = {}
            
            anthropic_tool = {
                "name": tool.get("function", {}).get("name") if "function" in tool else tool["name"],
                "description": tool.get("function", {}).get("description", "") if "function" in tool else tool.get("description", ""),
                "input_schema": input_schema
            }
            anthropic_tools.append(anthropic_tool)
        
        return anthropic_tools

    def _convert_messages_to_anthropic_format(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert messages to Anthropic format with proper tool handling"""
        anthropic_messages = []
        
        for msg in messages:
            if msg.role == 'system':
                # System messages are handled separately in Anthropic
                continue
            elif msg.role == 'tool':
                # Tool results
                anthropic_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": str(msg.content)  # Ensure content is string
                        }
                    ]
                })
            elif msg.role == 'assistant' and hasattr(msg, 'tool_calls') and msg.tool_calls:
                # Assistant message with tool calls
                content = []
                
                # Add text content if present
                if msg.content and msg.content.strip():
                    content.append({"type": "text", "text": msg.content})
                
                # Add tool calls
                for tool_call in msg.tool_calls:
                    # Ensure arguments are properly formatted
                    arguments = tool_call.get("arguments", {})
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse tool arguments as JSON: {arguments}")
                            arguments = {"raw_input": arguments}
                    
                    content.append({
                        "type": "tool_use",
                        "id": tool_call.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                        "name": tool_call["name"],
                        "input": arguments
                    })
                
                anthropic_messages.append({
                    "role": "assistant",
                    "content": content
                })
            else:
                # Regular user/assistant messages
                anthropic_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        return anthropic_messages

    def _extract_system_prompt(self, messages: List[Message], default_system: str) -> str:
        """Extract system prompt from messages or use default"""
        for msg in messages:
            if msg.role == 'system':
                return msg.content
        return default_system

    def call_llm(self, messages: List[Message], available_tools: List[Dict[str, Any]] = None, 
                 **kwargs) -> Dict[str, Any]:
        """Call Anthropic API with robust function calling support"""
        
        try:
            # Extract system prompt
            system_prompt = self._extract_system_prompt(
                messages, 
                kwargs.get('system_prompt', self._get_default_system_prompt())
            )
            
            # Convert messages to Anthropic format
            anthropic_messages = self._convert_messages_to_anthropic_format(messages)
            
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "max_tokens": kwargs.get('max_tokens', 4096),
                "temperature": kwargs.get('temperature', 0.1),
                "system": system_prompt,
                "messages": anthropic_messages
            }

            
            # Add tools if available
            if available_tools:
                anthropic_tools = self._convert_tools_to_anthropic_format(available_tools)
                api_params["tools"] = anthropic_tools
                
                # Set tool choice if specified
                tool_choice = kwargs.get('tool_choice')
                if tool_choice:
                    if tool_choice == "auto":
                        api_params["tool_choice"] = {"type": "auto"}
                    elif tool_choice == "required":
                        api_params["tool_choice"] = {"type": "any"}
                    elif isinstance(tool_choice, dict) and "name" in tool_choice:
                        api_params["tool_choice"] = {
                            "type": "tool",
                            "name": tool_choice["name"]
                        }
            # Make API call
            response = self.client.messages.create(**api_params)

            # Process response
            result = {
                "content": "",
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                "finish_reason": getattr(response, 'stop_reason', 'stop')
            }

            # Extract content and tool calls
            tool_calls = []
            text_content = []
            
            for content_block in response.content:
                if content_block.type == "text":
                    text_content.append(content_block.text)
                elif content_block.type == "tool_use":
                    # Use original format for compatibility
                    tool_calls.append({
                        "id": content_block.id,
                        "name": content_block.name,
                        "arguments": content_block.input
                    })

            result["content"] = "\n".join(text_content)
            
            if tool_calls:
                result["tool_calls"] = tool_calls

            return result

        except Exception as e:
            logger.error(f"Anthropic API error: {type(e).__name__}: {e}")
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "content": "",
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            }

    def _get_default_system_prompt(self) -> str:
        return """You are a research assistant for analyzing EDK2 (UEFI Development Kit) codebases. You MUST use the available tools to gather ALL information - you cannot rely on general knowledge about EDK2 or UEFI.

CRITICAL RULES:
1. NEVER provide information without first using tools to verify it
2. ALWAYS use tools to research before answering any question
3. CLEARLY distinguish between tool-verified facts and any assumptions
4. Include specific references to files, functions, and modules found by tools
5. If you don't have tool data, explicitly state "I need to research this using tools"

Available research tools:
- parse_dsc: Parse DSC files to understand build context
- find_function: Locate function definitions and declarations
- search_code: Search for code patterns and keywords
- get_included_modules: List modules in the build
- get_module_dependencies: Analyze module dependencies
- read_source_file: Read actual source code content
- trace_call_path: Follow function call chains

RESPONSE FORMAT:
- Start with tool research to gather facts
- Present findings with specific file/line references
- Clearly label any assumptions as "ASSUMPTION:" 
- End with "SOURCES:" listing all files/modules referenced

IMPORTANT: DSC file paths should be relative to the EDK2 repository root (e.g., "OvmfPkg/OvmfPkgX64.dsc")."""

    def stream_llm(self, messages: List[Message], available_tools: List[Dict[str, Any]] = None, 
                   **kwargs):
        """Stream responses from Anthropic API (tool calls will complete before streaming text)"""
        
        try:
            # Extract system prompt
            system_prompt = self._extract_system_prompt(
                messages, 
                kwargs.get('system_prompt', self._get_default_system_prompt())
            )
            
            # Convert messages to Anthropic format
            anthropic_messages = self._convert_messages_to_anthropic_format(messages)
            
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "max_tokens": kwargs.get('max_tokens', 4096),
                "temperature": kwargs.get('temperature', 0.1),
                "system": system_prompt,
                "messages": anthropic_messages,
                "stream": True
            }
            
            # Add tools if available
            if available_tools:
                anthropic_tools = self._convert_tools_to_anthropic_format(available_tools)
                api_params["tools"] = anthropic_tools

            # Make streaming API call
            stream = self.client.messages.create(**api_params)
            
            current_tool_calls = []
            current_tool_call = None
            
            for chunk in stream:
                if chunk.type == "message_start":
                    yield {
                        "type": "message_start",
                        "usage": {
                            "input_tokens": chunk.message.usage.input_tokens,
                            "output_tokens": 0,
                            "total_tokens": chunk.message.usage.input_tokens
                        }
                    }
                elif chunk.type == "content_block_start":
                    if chunk.content_block.type == "tool_use":
                        # Use original format for compatibility
                        current_tool_call = {
                            "id": chunk.content_block.id,
                            "name": chunk.content_block.name,
                            "arguments": ""
                        }
                elif chunk.type == "content_block_delta":
                    if chunk.delta.type == "text_delta":
                        yield {
                            "type": "content_delta",
                            "content": chunk.delta.text
                        }
                    elif chunk.delta.type == "input_json_delta" and current_tool_call:
                        current_tool_call["arguments"] += chunk.delta.partial_json
                elif chunk.type == "content_block_stop":
                    if current_tool_call:
                        current_tool_calls.append(current_tool_call)
                        current_tool_call = None
                elif chunk.type == "message_delta":
                    yield {
                        "type": "message_delta",
                        "finish_reason": chunk.delta.stop_reason,
                        "usage": {
                            "output_tokens": chunk.usage.output_tokens,
                            "total_tokens": chunk.usage.output_tokens
                        }
                    }
                elif chunk.type == "message_stop":
                    if current_tool_calls:
                        yield {
                            "type": "tool_calls",
                            "tool_calls": current_tool_calls
                        }
                    yield {"type": "message_stop"}
                    
        except Exception as e:
            logger.error(f"Anthropic streaming error: {type(e).__name__}: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }


class InteractiveLLMSession:
    """Manages an interactive LLM session with context and tool calling"""
    
    def __init__(self, 
                 workspace_dir: str,
                 edk2_path: str,
                 llm_provider: LLMProvider,
                 session_id: Optional[str] = None,
                 context_dir: Optional[str] = None,
                 max_context_messages: int = 50,
                 auto_save_interval: int = 10):
        """
        Initialize interactive LLM session
        
        Args:
            workspace_dir: Workspace directory path
            edk2_path: EDK2 repository path
            llm_provider: LLM provider instance
            session_id: Optional session ID (generates new if None)
            context_dir: Directory to save context files (defaults to workspace/.llm_sessions)
            max_context_messages: Maximum messages to keep in context
            auto_save_interval: Auto-save interval in messages
        """
        self.workspace_dir = Path(workspace_dir)
        self.edk2_path = Path(edk2_path)
        self.llm_provider = llm_provider
        self.max_context_messages = max_context_messages
        self.auto_save_interval = auto_save_interval
        
        # Initialize session
        self.session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
        self.context_dir = Path(context_dir) if context_dir else self.workspace_dir / ".llm_sessions"
        self.context_dir.mkdir(exist_ok=True)
        
        # Initialize MCP server
        self.mcp_server = ExtendedMCPServer(str(self.workspace_dir), str(self.edk2_path))
        
        # Session state
        self.messages: List[Message] = []
        self.context = SessionContext(
            session_id=self.session_id,
            created_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            total_messages=0,
            total_tool_calls=0
        )
        
        # Logging setup
        self.session_log_file = self.context_dir / f"{self.session_id}.log"
        self.setup_session_logging()
        
        # Load existing session if it exists
        self.load_session()
        
        logger.info(f"Initialized LLM session {self.session_id}")

    def setup_session_logging(self):
        """Setup session-specific logging"""
        session_logger = logging.getLogger(f"session_{self.session_id}")
        session_logger.setLevel(logging.DEBUG)
        
        # File handler for session logs
        file_handler = logging.FileHandler(self.session_log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Detailed formatter for session logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        session_logger.addHandler(file_handler)
        self.session_logger = session_logger

    def add_message(self, role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None,
                   tool_call_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Add a message to the conversation"""
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc),
            message_id=f"msg_{uuid.uuid4().hex[:8]}",
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            metadata=metadata or {}
        )
        
        self.messages.append(message)
        self.context.total_messages += 1
        self.context.last_activity = datetime.now(timezone.utc)
        
        # Log the message
        self.session_logger.info(f"Added message: {role} - {len(content)} chars")
        if tool_calls:
            self.session_logger.info(f"Tool calls: {[call['name'] for call in tool_calls]}")
        
        # Auto-save periodically
        if self.context.total_messages % self.auto_save_interval == 0:
            self.save_session()
        
        # Trim context if needed
        self._trim_context()
        
        return message

    def send_message(self, user_message: str, **llm_kwargs) -> Dict[str, Any]:
        """
        Send a user message and get LLM response with recursive tool calling
        
        Args:
            user_message: User's message
            **llm_kwargs: Additional arguments for LLM call
            
        Returns:
            Dictionary with response details
        """
        start_time = time.time()
        
        # Add user message
        self.add_message("user", user_message)
        self.session_logger.info(f"User message: {user_message[:100]}...")
        
        # Get LLM response with recursive tool calling
        response_data = self._get_llm_response_with_tools(**llm_kwargs)
        
        total_time = time.time() - start_time
        
        # Log session statistics
        self.session_logger.info(f"Session completed in {total_time:.2f}s")
        self.session_logger.info(f"Total messages: {self.context.total_messages}")
        self.session_logger.info(f"Total tool calls: {self.context.total_tool_calls}")
        
        return {
            "session_id": self.session_id,
            "response": response_data,
            "total_time": total_time,
            "context": self.context.to_dict()
        }

    def _get_llm_response_with_tools(self, max_iterations: int = 30, **llm_kwargs) -> Dict[str, Any]:
        """Get LLM response with recursive tool calling"""
        
        iterations = 0
        total_tool_calls = 0
        
        while iterations < max_iterations:
            iterations += 1
            
            # Get recent messages for context
            context_messages = self._get_context_messages()
            
            # Call LLM
            self.session_logger.debug(f"LLM call iteration {iterations}")
            llm_response = self.llm_provider.call_llm(
                context_messages, 
                self.mcp_server.tools,
                **llm_kwargs
            )
            
            if "error" in llm_response:
                self.session_logger.error(f"LLM error: {llm_response['error']}")
                self.add_message("assistant", f"I encountered an error: {llm_response['error']}")
                return llm_response
            
            # Add assistant message
            assistant_content = llm_response.get("content", "")
            tool_calls = llm_response.get("tool_calls", [])
            
            self.add_message("assistant", assistant_content, tool_calls=tool_calls)
            
            # If no tool calls, we're done
            if not tool_calls:
                self.session_logger.info(f"LLM response completed in {iterations} iterations")
                return llm_response
            
            # Execute tool calls
            self.session_logger.info(f"Executing {len(tool_calls)} tool calls")
            tool_results = self._execute_tool_calls(tool_calls)
            total_tool_calls += len(tool_calls)
            
            # Add tool results as messages
            for result in tool_results:
                tool_content = json.dumps(result.result, indent=2)
                self.add_message(
                    "tool", 
                    tool_content,
                    tool_call_id=result.call_id,
                    metadata={
                        "tool_name": result.tool_name,
                        "execution_time": result.execution_time,
                        "success": result.success
                    }
                )
        
        # Max iterations reached
        self.session_logger.warning(f"Max iterations ({max_iterations}) reached")
        self.add_message("assistant", "I've reached the maximum number of tool calling iterations. Let me summarize what I've found so far.")
        
        return {
            "content": "Maximum tool calling iterations reached",
            "iterations": iterations,
            "total_tool_calls": total_tool_calls
        }

    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[ToolCallResult]:
        """Execute a list of tool calls"""
        results = []
        
        for tool_call in tool_calls:
            start_time = time.time()
            tool_name = tool_call["name"]
            arguments = tool_call["arguments"]
            call_id = tool_call.get("id", f"call_{uuid.uuid4().hex[:8]}")
            
            self.session_logger.debug(f"Executing tool: {tool_name} with args: {arguments}")
            
            try:
                # Execute tool via MCP server
                result = self.mcp_server.handle_tool_call(tool_name, arguments)
                execution_time = time.time() - start_time
                
                success = result.get("success", True)
                error_message = result.get("error") if not success else None
                
                tool_result = ToolCallResult(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=result,
                    execution_time=execution_time,
                    success=success,
                    error_message=error_message,
                    call_id=call_id
                )
                
                results.append(tool_result)
                self.context.total_tool_calls += 1
                
                # Log tool execution
                if success:
                    self.session_logger.info(f"Tool {tool_name} executed successfully in {execution_time:.2f}s")
                else:
                    self.session_logger.error(f"Tool {tool_name} failed: {error_message}")
                
                # Update context based on tool results
                self._update_context_from_tool_result(tool_name, result)
                
            except Exception as e:
                execution_time = time.time() - start_time
                error_message = str(e)
                
                tool_result = ToolCallResult(
                    tool_name=tool_name,
                    arguments=arguments,
                    result={"error": error_message, "success": False},
                    execution_time=execution_time,
                    success=False,
                    error_message=error_message,
                    call_id=call_id
                )
                
                results.append(tool_result)
                self.session_logger.error(f"Tool {tool_name} exception: {error_message}")
        
        return results

    def _update_context_from_tool_result(self, tool_name: str, result: Dict[str, Any]):
        """Update session context based on tool results"""
        if tool_name == "parse_dsc" and result.get("success"):
            self.context.current_dsc_context = result.get("dsc_path")
            self.session_logger.info(f"Updated DSC context: {self.context.current_dsc_context}")
        
        elif tool_name in ["read_source_file", "write_source_file", "modify_function"] and result.get("success"):
            file_path = result.get("file_path")
            if file_path and file_path not in self.context.active_files:
                self.context.active_files.append(file_path)
                self.session_logger.info(f"Added active file: {file_path}")

    def _get_context_messages(self) -> List[Message]:
        """Get recent messages for LLM context"""
        if len(self.messages) <= self.max_context_messages:
            return self.messages
        
        # Keep recent messages and ensure we don't break tool call sequences
        recent_messages = self.messages[-self.max_context_messages:]
        
        # If the first message is a tool result, include its corresponding assistant message
        if recent_messages[0].role == "tool":
            for i in range(len(self.messages) - self.max_context_messages - 1, -1, -1):
                if self.messages[i].role == "assistant" and self.messages[i].tool_calls:
                    recent_messages.insert(0, self.messages[i])
                    break
        
        return recent_messages

    def _trim_context(self):
        """Trim context to prevent memory issues"""
        max_total_messages = self.max_context_messages * 3  # Keep more in storage
        
        if len(self.messages) > max_total_messages:
            # Keep recent messages and save older ones to file
            old_messages = self.messages[:-max_total_messages]
            self.messages = self.messages[-max_total_messages:]
            
            # Save trimmed messages
            self._save_trimmed_messages(old_messages)
            self.session_logger.info(f"Trimmed {len(old_messages)} old messages")

    def _save_trimmed_messages(self, messages: List[Message]):
        """Save trimmed messages to archive file"""
        archive_file = self.context_dir / f"{self.session_id}_archive.jsonl"
        
        with open(archive_file, "a", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg.to_dict()) + "\n")

    def save_session(self):
        """Save session state to file system"""
        session_file = self.context_dir / f"{self.session_id}.json"
        
        session_data = {
            "context": self.context.to_dict(),
            "messages": [msg.to_dict() for msg in self.messages],
            "mcp_server_state": {
                "current_dsc_context": self.mcp_server.current_dsc_context.dsc_path if self.mcp_server.current_dsc_context else None,
                "tools_count": len(self.mcp_server.tools)
            }
        }
        
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        self.session_logger.info(f"Session saved to {session_file}")

    def load_session(self):
        """Load session state from file system"""
        session_file = self.context_dir / f"{self.session_id}.json"
        
        if not session_file.exists():
            self.session_logger.info("No existing session file found")
            return
        
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            
            # Load context
            context_data = session_data["context"]
            self.context = SessionContext(
                session_id=context_data["session_id"],
                created_at=datetime.fromisoformat(context_data["created_at"]),
                last_activity=datetime.fromisoformat(context_data["last_activity"]),
                total_messages=context_data["total_messages"],
                total_tool_calls=context_data["total_tool_calls"],
                current_dsc_context=context_data.get("current_dsc_context"),
                active_files=context_data.get("active_files", []),
                session_metadata=context_data.get("session_metadata", {})
            )
            
            # Load messages
            self.messages = [Message.from_dict(msg_data) for msg_data in session_data["messages"]]
            
            # Restore MCP server state if needed
            mcp_state = session_data.get("mcp_server_state", {})
            if mcp_state.get("current_dsc_context"):
                try:
                    # Re-parse DSC to restore context
                    self.mcp_server.handle_tool_call("parse_dsc", {
                        "dsc_path": mcp_state["current_dsc_context"]
                    })
                except Exception as e:
                    self.session_logger.warning(f"Failed to restore DSC context: {e}")
            
            self.session_logger.info(f"Session loaded: {len(self.messages)} messages, {self.context.total_tool_calls} tool calls")
            
        except Exception as e:
            self.session_logger.error(f"Failed to load session: {e}")

    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session"""
        return {
            "session_id": self.session_id,
            "context": self.context.to_dict(),
            "messages_count": len(self.messages),
            "recent_activity": [
                {
                    "role": msg.role,
                    "timestamp": msg.timestamp.isoformat(),
                    "content_length": len(msg.content),
                    "has_tool_calls": bool(msg.tool_calls)
                }
                for msg in self.messages[-5:]  # Last 5 messages
            ],
            "available_tools": len(self.mcp_server.tools),
            "session_files": {
                "log_file": str(self.session_log_file),
                "context_file": str(self.context_dir / f"{self.session_id}.json"),
                "archive_file": str(self.context_dir / f"{self.session_id}_archive.jsonl")
            }
        }

    def export_session(self, export_path: Optional[str] = None) -> str:
        """Export complete session data for analysis"""
        if export_path is None:
            export_path = self.context_dir / f"{self.session_id}_export.json"
        
        export_data = {
            "session_summary": self.get_session_summary(),
            "full_conversation": [msg.to_dict() for msg in self.messages],
            "tool_call_statistics": self._get_tool_call_statistics(),
            "export_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        self.session_logger.info(f"Session exported to {export_path}")
        return str(export_path)

    def _get_tool_call_statistics(self) -> Dict[str, Any]:
        """Get statistics about tool calls in this session"""
        tool_stats = {}
        total_execution_time = 0
        
        for msg in self.messages:
            if msg.role == "tool" and msg.metadata:
                tool_name = msg.metadata.get("tool_name")
                execution_time = msg.metadata.get("execution_time", 0)
                success = msg.metadata.get("success", True)
                
                if tool_name:
                    if tool_name not in tool_stats:
                        tool_stats[tool_name] = {
                            "count": 0,
                            "total_time": 0,
                            "success_count": 0,
                            "error_count": 0
                        }
                    
                    tool_stats[tool_name]["count"] += 1
                    tool_stats[tool_name]["total_time"] += execution_time
                    total_execution_time += execution_time
                    
                    if success:
                        tool_stats[tool_name]["success_count"] += 1
                    else:
                        tool_stats[tool_name]["error_count"] += 1
        
        # Calculate averages
        for tool_name, stats in tool_stats.items():
            if stats["count"] > 0:
                stats["average_time"] = stats["total_time"] / stats["count"]
                stats["success_rate"] = stats["success_count"] / stats["count"]
        
        return {
            "tool_statistics": tool_stats,
            "total_tool_calls": self.context.total_tool_calls,
            "total_execution_time": total_execution_time,
            "average_execution_time": total_execution_time / max(1, self.context.total_tool_calls)
        }


# Factory functions and utilities
def create_llm_provider(provider_name: str, **kwargs) -> LLMProvider:
    """Factory function to create LLM providers"""
    provider_name = provider_name.lower()
    
    if provider_name == "openai":
        return OpenAIProvider(**kwargs)
    elif provider_name == "anthropic":
        return AnthropicProvider(**kwargs)
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")


def create_interactive_session(workspace_dir: str, 
                             edk2_path: str,
                             provider_name: str = "openai",
                             session_id: Optional[str] = None,
                             **provider_kwargs) -> InteractiveLLMSession:
    """
    Factory function to create an interactive LLM session
    
    Args:
        workspace_dir: Workspace directory path
        edk2_path: EDK2 repository path
        provider_name: LLM provider name ("openai", "anthropic")
        session_id: Optional session ID
        **provider_kwargs: Additional arguments for LLM provider
    
    Returns:
        InteractiveLLMSession instance
    """
    provider = create_llm_provider(provider_name, **provider_kwargs)
    return InteractiveLLMSession(
        workspace_dir=workspace_dir,
        edk2_path=edk2_path,
        llm_provider=provider,
        session_id=session_id
    )


# class SessionManager:
#     """Manages multiple LLM sessions"""
    
#     def __init__(self, workspace_dir: str, edk2_path: str):
#         self.workspace_dir = Path(workspace_dir)
#         self.edk2_path = Path(edk2_path)
#         self.sessions_dir = self.workspace_dir / ".llm_sessions"
#         self.sessions_dir.mkdir(exist_ok=True)
#         self.active_sessions: Dict[str, InteractiveLLMSession] = {}
    
#     def create_session(self, provider_name: str = "openai", **provider_kwargs) -> InteractiveLLMSession:
#         """Create a new session"""
#         print(provider_kwargs)
#         session = create_interactive_session(
#             str(self.workspace_dir),
#             str(self.edk2_path),
#             provider_name,
#             **provider_kwargs
#         )
        
#         self.active_sessions[session.session_id] = session
#         return session
    
#     def get_session(self, session_id: str) -> Optional[InteractiveLLMSession]:
#         """Get an existing session"""
#         if session_id in self.active_sessions:
#             return self.active_sessions[session_id]
        
#         # Try to load from file
#         session_file = self.sessions_dir / f"{session_id}.json"
#         if session_file.exists():
#             # Create a new session instance and load the data
#             # This would need the provider info stored in the session file
#             # For now, return None if not in active sessions
#             pass
        
#         return None
    
#     def list_sessions(self) -> List[Dict[str, Any]]:
#         """List all available sessions"""
#         sessions = []
        
#         # Add active sessions
#         for session_id, session in self.active_sessions.items():
#             sessions.append({
#                 "session_id": session_id,
#                 "status": "active",
#                 "created_at": session.context.created_at.isoformat(),
#                 "last_activity": session.context.last_activity.isoformat(),
#                 "total_messages": session.context.total_messages,
#                 "total_tool_calls": session.context.total_tool_calls
#             })
        
#         # Add stored sessions
#         for session_file in self.sessions_dir.glob("*.json"):
#             if not session_file.name.endswith("_export.json"):
#                 session_id = session_file.stem
#                 if session_id not in self.active_sessions:
#                     try:
#                         with open(session_file, "r") as f:
#                             session_data = json.load(f)
                        
#                         context = session_data["context"]
#                         sessions.append({
#                             "session_id": session_id,
#                             "status": "stored",
#                             "created_at": context["created_at"],
#                             "last_activity": context["last_activity"],
#                             "total_messages": context["total_messages"],
#                             "total_tool_calls": context["total_tool_calls"]
#                         })
#                     except Exception as e:
#                         logger.warning(f"Failed to read session {session_id}: {e}")
        
#         return sorted(sessions, key=lambda x: x["last_activity"], reverse=True)
    
#     def cleanup_old_sessions(self, days_old: int = 30):
#         """Clean up old session files"""
#         cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
#         cleaned_count = 0
        
#         for session_file in self.sessions_dir.glob("*.json"):
#             try:
#                 if session_file.stat().st_mtime < cutoff_date.timestamp():
#                     session_file.unlink()
#                     cleaned_count += 1
                    
#                     # Also remove associated log and archive files
#                     session_id = session_file.stem
#                     log_file = self.sessions_dir / f"{session_id}.log"
#                     archive_file = self.sessions_dir / f"{session_id}_archive.jsonl"
                    
#                     if log_file.exists():
#                         log_file.unlink()
#                     if archive_file.exists():
#                         archive_file.unlink()
                        
#             except Exception as e:
#                 logger.warning(f"Failed to clean up {session_file}: {e}")
        
#         logger.info(f"Cleaned up {cleaned_count} old session files")
#         return cleaned_count
