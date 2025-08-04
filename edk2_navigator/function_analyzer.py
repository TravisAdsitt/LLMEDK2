"""
Function Analyzer - Parses source files to extract function information
"""
import re
import os
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from .query_engine import FunctionLocation

@dataclass
class FunctionCall:
    """Represents a function call in source code"""
    caller_function: str
    called_function: str
    file_path: str
    line_number: int
    line_content: str
    call_context: str           # Context around the call (e.g., if statement, loop)

@dataclass
class FunctionDefinition:
    """Detailed function definition information"""
    name: str
    return_type: str
    parameters: List[Dict[str, str]]    # [{'type': 'UINT32', 'name': 'Value'}]
    calling_convention: str
    file_path: str
    line_number: int
    end_line_number: int
    signature: str
    body_start: int
    is_static: bool
    is_inline: bool
    documentation: str          # Comment block above function

class FunctionAnalyzer:
    """Analyzes source files to extract function definitions and calls"""
    
    def __init__(self):
        self.function_definitions = {}  # file_path -> List[FunctionDefinition]
        self.function_calls = {}        # file_path -> List[FunctionCall]
        self.call_graph = {}           # function_name -> List[called_functions]
        
        # EDK2-specific patterns
        self.edk2_calling_conventions = ['EFIAPI', 'WINAPI', '__cdecl', '__stdcall']
        self.edk2_types = ['EFI_STATUS', 'BOOLEAN', 'UINT8', 'UINT16', 'UINT32', 'UINT64',
                          'UINTN', 'INTN', 'VOID', 'CHAR8', 'CHAR16', 'EFI_HANDLE',
                          'EFI_GUID', 'EFI_BOOT_SERVICES', 'EFI_RUNTIME_SERVICES']
        self.edk2_keywords = ['IN', 'OUT', 'OPTIONAL', 'CONST']
        
        # Compile regex patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for function parsing"""
        # Enhanced function definition pattern with parameter parsing
        calling_conv = '|'.join(self.edk2_calling_conventions)
        
        # Function definition with full signature capture
        self.function_def_pattern = re.compile(
            r'^\s*((?:STATIC\s+)?(?:INLINE\s+)?)'  # Optional STATIC/INLINE
            r'(\w+(?:\s*\*)*)\s+'                  # Return type
            r'(?:(' + calling_conv + r')\s+)?'     # Optional calling convention
            r'(\w+)\s*'                            # Function name
            r'\(([^)]*)\)\s*'                      # Parameters
            r'\{',                                 # Opening brace
            re.MULTILINE | re.DOTALL
        )
        
        # Function declaration pattern
        self.function_decl_pattern = re.compile(
            r'^\s*((?:STATIC\s+)?(?:INLINE\s+)?)'  # Optional STATIC/INLINE
            r'(\w+(?:\s*\*)*)\s+'                  # Return type
            r'(?:(' + calling_conv + r')\s+)?'     # Optional calling convention
            r'(\w+)\s*'                            # Function name
            r'\(([^)]*)\)\s*'                      # Parameters
            r';',                                  # Semicolon
            re.MULTILINE | re.DOTALL
        )
        
        # Function call pattern - more precise
        self.function_call_pattern = re.compile(
            r'(\w+)\s*\(',
            re.MULTILINE
        )
        
        # Parameter parsing pattern - handle pointer types properly
        self.parameter_pattern = re.compile(
            r'(?:(' + '|'.join(self.edk2_keywords) + r')\s+)?'  # Optional IN/OUT/OPTIONAL
            r'(\w+)\s+'                                         # Base type
            r'(\*?)(\w+)',                                      # Optional pointer and name
            re.MULTILINE
        )
        
        # Comment block pattern (for documentation)
        self.comment_block_pattern = re.compile(
            r'/\*\*(.*?)\*/',
            re.DOTALL
        )
    
    def analyze_source_file(self, file_path: str) -> Dict[str, List]:
        """Analyze a source file for functions and calls"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {'definitions': [], 'declarations': [], 'calls': []}
        
        # Only analyze C/C++ files
        if file_path.suffix not in ['.c', '.cpp', '.h', '.hpp']:
            return {'definitions': [], 'declarations': [], 'calls': []}
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            return {'definitions': [], 'declarations': [], 'calls': []}
        
        # Extract function information
        definitions = self._extract_function_definitions(content, str(file_path))
        declarations = self._extract_function_declarations(content, str(file_path))
        calls = self._extract_function_calls(content, str(file_path))
        
        # Cache results
        self.function_definitions[str(file_path)] = definitions
        self.function_calls[str(file_path)] = calls
        
        return {
            'definitions': definitions,
            'declarations': declarations,
            'calls': calls
        }
    
    def _extract_function_definitions(self, content: str, file_path: str) -> List[FunctionDefinition]:
        """Extract function definitions from source content"""
        definitions = []
        lines = content.split('\n')
        
        for match in self.function_def_pattern.finditer(content):
            modifiers = match.group(1).strip()  # STATIC, INLINE, etc.
            return_type = match.group(2).strip()
            calling_conv = match.group(3) or ''
            function_name = match.group(4)
            parameters_str = match.group(5)
            
            # Find line numbers
            start_line = content[:match.start()].count('\n') + 1
            end_line = self._find_function_end(content, match.end())
            
            # Parse parameters
            parameters = self._parse_parameters(parameters_str)
            
            # Extract documentation (look for comment block before function)
            documentation = self._extract_function_documentation(content, match.start())
            
            # Build full signature
            signature = f"{return_type} {calling_conv} {function_name}({parameters_str})"
            
            definition = FunctionDefinition(
                name=function_name,
                return_type=return_type,
                parameters=parameters,
                calling_convention=calling_conv,
                file_path=file_path,
                line_number=start_line,
                end_line_number=end_line,
                signature=signature.strip(),
                body_start=match.end(),
                is_static='STATIC' in modifiers.upper(),
                is_inline='INLINE' in modifiers.upper(),
                documentation=documentation
            )
            
            definitions.append(definition)
        
        return definitions
    
    def _extract_function_declarations(self, content: str, file_path: str) -> List[FunctionDefinition]:
        """Extract function declarations from source content"""
        declarations = []
        
        for match in self.function_decl_pattern.finditer(content):
            modifiers = match.group(1).strip()
            return_type = match.group(2).strip()
            calling_conv = match.group(3) or ''
            function_name = match.group(4)
            parameters_str = match.group(5)
            
            # Find line number
            line_num = content[:match.start()].count('\n') + 1
            
            # Parse parameters
            parameters = self._parse_parameters(parameters_str)
            
            # Extract documentation
            documentation = self._extract_function_documentation(content, match.start())
            
            # Build signature
            signature = f"{return_type} {calling_conv} {function_name}({parameters_str})"
            
            declaration = FunctionDefinition(
                name=function_name,
                return_type=return_type,
                parameters=parameters,
                calling_convention=calling_conv,
                file_path=file_path,
                line_number=line_num,
                end_line_number=line_num,
                signature=signature.strip(),
                body_start=-1,  # No body for declarations
                is_static='STATIC' in modifiers.upper(),
                is_inline='INLINE' in modifiers.upper(),
                documentation=documentation
            )
            
            declarations.append(declaration)
        
        return declarations
    
    def _extract_function_calls(self, content: str, file_path: str) -> List[FunctionCall]:
        """Extract function calls from source content"""
        calls = []
        lines = content.split('\n')
        
        # First, get all function definitions in this file to determine context
        definitions = self._extract_function_definitions(content, file_path)
        
        for line_num, line in enumerate(lines, 1):
            # Skip comment lines and preprocessor directives
            stripped_line = line.strip()
            if (stripped_line.startswith('//') or 
                stripped_line.startswith('/*') or 
                stripped_line.startswith('#') or
                stripped_line.startswith('*')):
                continue
            
            # Find function calls in this line
            for match in self.function_call_pattern.finditer(line):
                function_name = match.group(1)
                
                # Skip if this looks like a function definition
                if '{' in line and line.strip().endswith('{'):
                    continue
                
                # Skip common C keywords and macros
                if function_name.upper() in ['IF', 'FOR', 'WHILE', 'SWITCH', 'SIZEOF', 'RETURN']:
                    continue
                
                # Determine the containing function
                containing_function = self._find_containing_function_at_line(definitions, line_num)
                
                # Get call context (surrounding code)
                call_context = self._get_call_context(lines, line_num)
                
                call = FunctionCall(
                    caller_function=containing_function or 'global',
                    called_function=function_name,
                    file_path=file_path,
                    line_number=line_num,
                    line_content=line.strip(),
                    call_context=call_context
                )
                
                calls.append(call)
        
        return calls
    
    def _parse_parameters(self, parameters_str: str) -> List[Dict[str, str]]:
        """Parse function parameters string into structured data"""
        parameters = []
        
        if not parameters_str.strip():
            return parameters
        
        # Split parameters by comma, but be careful of nested parentheses
        param_parts = self._split_parameters(parameters_str)
        
        for param in param_parts:
            param = param.strip()
            if not param or param.upper() == 'VOID':
                continue
            
            # Try to parse with EDK2 keywords
            match = self.parameter_pattern.search(param)
            if match:
                keyword = match.group(1) or ''
                base_type = match.group(2)
                pointer = match.group(3) or ''
                param_name = match.group(4)
                param_type = base_type + (' ' + pointer if pointer else '')
            else:
                # Fallback: simple type name parsing
                parts = param.split()
                if len(parts) >= 2:
                    param_type = ' '.join(parts[:-1])
                    param_name = parts[-1]
                    keyword = ''
                else:
                    param_type = param
                    param_name = ''
                    keyword = ''
            
            parameters.append({
                'keyword': keyword,
                'type': param_type,
                'name': param_name,
                'full': param
            })
        
        return parameters
    
    def _split_parameters(self, parameters_str: str) -> List[str]:
        """Split parameter string by commas, handling nested parentheses"""
        parameters = []
        current_param = ''
        paren_depth = 0
        
        for char in parameters_str:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == ',' and paren_depth == 0:
                parameters.append(current_param.strip())
                current_param = ''
                continue
            
            current_param += char
        
        if current_param.strip():
            parameters.append(current_param.strip())
        
        return parameters
    
    def _find_function_end(self, content: str, start_pos: int) -> int:
        """Find the end line of a function definition"""
        brace_count = 1
        pos = start_pos
        
        while pos < len(content) and brace_count > 0:
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
            pos += 1
        
        return content[:pos].count('\n') + 1
    
    def _extract_function_documentation(self, content: str, function_start: int) -> str:
        """Extract documentation comment block before a function"""
        # Look backwards from function start to find comment block
        lines = content[:function_start].split('\n')
        
        # Find the last non-empty line before the function
        doc_lines = []
        for line in reversed(lines):
            stripped = line.strip()
            if not stripped:
                continue
            
            if stripped.startswith('/**') or stripped.startswith('/*'):
                # Found start of comment block
                doc_lines.append(line)
                break
            elif stripped.startswith('*') or stripped.endswith('*/'):
                # Part of comment block
                doc_lines.append(line)
            else:
                # Not part of comment block
                break
        
        if doc_lines:
            doc_lines.reverse()
            return '\n'.join(doc_lines)
        
        return ''
    
    def _find_containing_function_at_line(self, definitions: List[FunctionDefinition], line_num: int) -> Optional[str]:
        """Find which function contains the given line number"""
        for definition in definitions:
            if definition.line_number <= line_num <= definition.end_line_number:
                return definition.name
        return None
    
    def _get_call_context(self, lines: List[str], line_num: int) -> str:
        """Get context around a function call (e.g., if statement, loop)"""
        # Look at a few lines before to understand context
        start_line = max(0, line_num - 3)
        end_line = min(len(lines), line_num + 2)
        
        context_lines = []
        for i in range(start_line, end_line):
            if i < len(lines):
                line = lines[i].strip()
                if line:
                    context_lines.append(line)
        
        return ' | '.join(context_lines)
    
    def build_call_graph(self, module_list: List[str]) -> Dict[str, List[str]]:
        """Build function call graph for included modules"""
        call_graph = {}
        
        for module_path in module_list:
            # Find all source files in the module
            module_dir = Path(module_path).parent
            
            if not module_dir.exists():
                continue
            
            # Analyze all C/C++ files in the module
            for source_file in module_dir.rglob('*.c'):
                analysis = self.analyze_source_file(str(source_file))
                
                # Build call relationships
                for call in analysis['calls']:
                    caller = call.caller_function
                    called = call.called_function
                    
                    if caller not in call_graph:
                        call_graph[caller] = []
                    
                    if called not in call_graph[caller]:
                        call_graph[caller].append(called)
        
        self.call_graph = call_graph
        return call_graph
    
    def get_function_callers(self, function_name: str) -> List[FunctionCall]:
        """Get all functions that call the specified function"""
        callers = []
        
        for file_path, calls in self.function_calls.items():
            for call in calls:
                if call.called_function == function_name:
                    callers.append(call)
        
        return callers
    
    def get_function_callees(self, function_name: str) -> List[str]:
        """Get all functions called by the specified function"""
        return self.call_graph.get(function_name, [])
    
    def analyze_call_depth(self, function_name: str, max_depth: int = 5) -> Dict[str, int]:
        """Analyze call depth from a given function"""
        call_depths = {}
        visited = set()
        
        def _analyze_depth(func_name: str, current_depth: int):
            if current_depth > max_depth or func_name in visited:
                return
            
            visited.add(func_name)
            call_depths[func_name] = current_depth
            
            # Recurse into called functions
            callees = self.get_function_callees(func_name)
            for callee in callees:
                _analyze_depth(callee, current_depth + 1)
        
        _analyze_depth(function_name, 0)
        return call_depths
    
    def find_recursive_calls(self) -> List[List[str]]:
        """Find recursive call chains in the call graph"""
        recursive_chains = []
        
        def _find_cycles(start_func: str, current_path: List[str], visited: Set[str]):
            if start_func in current_path:
                # Found a cycle
                cycle_start = current_path.index(start_func)
                cycle = current_path[cycle_start:] + [start_func]
                if cycle not in recursive_chains:
                    recursive_chains.append(cycle)
                return
            
            if start_func in visited:
                return
            
            visited.add(start_func)
            current_path.append(start_func)
            
            # Follow all calls from this function
            callees = self.get_function_callees(start_func)
            for callee in callees:
                _find_cycles(callee, current_path.copy(), visited.copy())
        
        # Check each function as a potential start of a recursive chain
        for function_name in self.call_graph.keys():
            _find_cycles(function_name, [], set())
        
        return recursive_chains
    
    def get_function_complexity_metrics(self, function_name: str) -> Dict[str, int]:
        """Get complexity metrics for a function"""
        metrics = {
            'calls_made': 0,
            'called_by': 0,
            'max_call_depth': 0,
            'unique_callees': 0
        }
        
        # Count calls made by this function
        callees = self.get_function_callees(function_name)
        metrics['calls_made'] = len(callees)
        metrics['unique_callees'] = len(set(callees))
        
        # Count how many functions call this one
        callers = self.get_function_callers(function_name)
        metrics['called_by'] = len(callers)
        
        # Calculate max call depth
        call_depths = self.analyze_call_depth(function_name)
        if call_depths:
            metrics['max_call_depth'] = max(call_depths.values())
        
        return metrics
