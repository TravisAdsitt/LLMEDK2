"""
Custom exceptions for EDK2 Navigator
"""

class EDK2NavigatorError(Exception):
    """Base exception for EDK2 Navigator"""
    pass

class DSCParsingError(EDK2NavigatorError):
    """Exception raised when DSC file parsing fails"""
    def __init__(self, dsc_path: str, message: str):
        self.dsc_path = dsc_path
        self.message = message
        super().__init__(f"DSC parsing failed for {dsc_path}: {message}")

class BaseToolsError(EDK2NavigatorError):
    """Exception raised when BaseTools integration fails"""
    def __init__(self, message: str, basetools_path: str = None):
        self.message = message
        self.basetools_path = basetools_path
        if basetools_path:
            super().__init__(f"BaseTools error at {basetools_path}: {message}")
        else:
            super().__init__(f"BaseTools error: {message}")

class ModuleNotFoundError(EDK2NavigatorError):
    """Exception raised when a module cannot be found"""
    def __init__(self, module_name: str, dsc_path: str = None):
        self.module_name = module_name
        self.dsc_path = dsc_path
        if dsc_path:
            super().__init__(f"Module '{module_name}' not found in DSC: {dsc_path}")
        else:
            super().__init__(f"Module '{module_name}' not found")

class FunctionNotFoundError(EDK2NavigatorError):
    """Exception raised when a function cannot be found"""
    def __init__(self, function_name: str, search_scope: str = None):
        self.function_name = function_name
        self.search_scope = search_scope
        if search_scope:
            super().__init__(f"Function '{function_name}' not found in scope: {search_scope}")
        else:
            super().__init__(f"Function '{function_name}' not found")

class CacheError(EDK2NavigatorError):
    """Exception raised when cache operations fail"""
    def __init__(self, operation: str, message: str):
        self.operation = operation
        self.message = message
        super().__init__(f"Cache {operation} failed: {message}")

class DependencyGraphError(EDK2NavigatorError):
    """Exception raised when dependency graph operations fail"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"Dependency graph error: {message}")

class WorkspaceValidationError(EDK2NavigatorError):
    """Exception raised when workspace validation fails"""
    def __init__(self, workspace_path: str, errors: list):
        self.workspace_path = workspace_path
        self.errors = errors
        error_list = '\n'.join(f"  - {error}" for error in errors)
        super().__init__(f"Workspace validation failed for {workspace_path}:\n{error_list}")

class ConditionalCompilationError(EDK2NavigatorError):
    """Exception raised when conditional compilation evaluation fails"""
    def __init__(self, condition: str, message: str):
        self.condition = condition
        self.message = message
        super().__init__(f"Conditional compilation error for '{condition}': {message}")

class MCPServerError(EDK2NavigatorError):
    """Exception raised when MCP server operations fail"""
    def __init__(self, operation: str, message: str):
        self.operation = operation
        self.message = message
        super().__init__(f"MCP server {operation} failed: {message}")
