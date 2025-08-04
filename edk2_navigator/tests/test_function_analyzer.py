"""
Tests for Function Analyzer functionality
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from edk2_navigator.function_analyzer import FunctionAnalyzer, FunctionCall, FunctionDefinition

class TestFunctionAnalyzer:
    """Test cases for Function Analyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create a function analyzer instance"""
        return FunctionAnalyzer()
    
    @pytest.fixture
    def sample_c_code(self):
        """Sample C code with various function patterns"""
        return """
#include <Uefi.h>
#include <Library/BaseLib.h>

/**
 * Test function with documentation
 * @param Value Input value
 * @return Status code
 */
EFI_STATUS
EFIAPI
TestFunction (
  IN UINT32 Value
  )
{
  UINTN LocalVar;
  
  LocalVar = AnotherFunction(Value);
  if (LocalVar == 0) {
    return EFI_INVALID_PARAMETER;
  }
  
  CallThirdFunction();
  return EFI_SUCCESS;
}

STATIC
VOID
EFIAPI
StaticFunction (
  VOID
  )
{
  // Static function implementation
  TestFunction(123);
}

// Function declaration
EFI_STATUS
EFIAPI
DeclaredFunction (
  IN UINTN Parameter
  );

INLINE
BOOLEAN
InlineFunction (
  IN CHAR8 *String
  )
{
  return (String != NULL);
}
"""
    
    def test_analyzer_initialization(self, analyzer):
        """Test function analyzer initialization"""
        assert analyzer.function_definitions == {}
        assert analyzer.function_calls == {}
        assert analyzer.call_graph == {}
        assert len(analyzer.edk2_calling_conventions) > 0
        assert len(analyzer.edk2_types) > 0
        assert len(analyzer.edk2_keywords) > 0
    
    def test_analyze_nonexistent_file(self, analyzer):
        """Test analyzing a file that doesn't exist"""
        result = analyzer.analyze_source_file("/nonexistent/file.c")
        
        assert result == {'definitions': [], 'declarations': [], 'calls': []}
    
    def test_analyze_non_c_file(self, analyzer):
        """Test analyzing a non-C file"""
        with tempfile.NamedTemporaryFile(suffix='.txt', mode='w', delete=False) as f:
            f.write("This is not a C file")
            f.flush()
            
            result = analyzer.analyze_source_file(f.name)
            
            assert result == {'definitions': [], 'declarations': [], 'calls': []}
    
    def test_analyze_source_file_with_functions(self, analyzer, sample_c_code):
        """Test analyzing a source file with various function patterns"""
        with tempfile.NamedTemporaryFile(suffix='.c', mode='w', delete=False) as f:
            f.write(sample_c_code)
            f.flush()
            
            result = analyzer.analyze_source_file(f.name)
            
            # Check that we found definitions
            assert len(result['definitions']) > 0
            assert len(result['declarations']) > 0
            assert len(result['calls']) > 0
            
            # Check specific function definitions
            definition_names = [d.name for d in result['definitions']]
            assert "TestFunction" in definition_names
            assert "StaticFunction" in definition_names
            assert "InlineFunction" in definition_names
            
            # Check function calls
            call_names = [c.called_function for c in result['calls']]
            assert "AnotherFunction" in call_names
            assert "CallThirdFunction" in call_names
            assert "TestFunction" in call_names  # Called by StaticFunction
    
    def test_extract_function_definitions(self, analyzer, sample_c_code):
        """Test extracting function definitions"""
        definitions = analyzer._extract_function_definitions(sample_c_code, "/test/file.c")
        
        assert len(definitions) >= 3  # TestFunction, StaticFunction, InlineFunction
        
        # Find TestFunction
        test_func = next((d for d in definitions if d.name == "TestFunction"), None)
        assert test_func is not None
        assert test_func.return_type == "EFI_STATUS"
        assert test_func.calling_convention == "EFIAPI"
        assert test_func.is_static == False
        assert test_func.is_inline == False
        assert len(test_func.parameters) > 0
        assert test_func.documentation != ""
        
        # Find StaticFunction
        static_func = next((d for d in definitions if d.name == "StaticFunction"), None)
        assert static_func is not None
        assert static_func.is_static == True
        assert static_func.return_type == "VOID"
        
        # Find InlineFunction
        inline_func = next((d for d in definitions if d.name == "InlineFunction"), None)
        assert inline_func is not None
        assert inline_func.is_inline == True
        assert inline_func.return_type == "BOOLEAN"
    
    def test_extract_function_declarations(self, analyzer, sample_c_code):
        """Test extracting function declarations"""
        declarations = analyzer._extract_function_declarations(sample_c_code, "/test/file.c")
        
        assert len(declarations) >= 1
        
        # Find DeclaredFunction
        declared_func = next((d for d in declarations if d.name == "DeclaredFunction"), None)
        assert declared_func is not None
        assert declared_func.return_type == "EFI_STATUS"
        assert declared_func.calling_convention == "EFIAPI"
        assert declared_func.body_start == -1  # No body for declarations
    
    def test_extract_function_calls(self, analyzer, sample_c_code):
        """Test extracting function calls"""
        calls = analyzer._extract_function_calls(sample_c_code, "/test/file.c")
        
        assert len(calls) > 0
        
        call_names = [c.called_function for c in calls]
        assert "AnotherFunction" in call_names
        assert "CallThirdFunction" in call_names
        
        # Check that calls have proper context
        for call in calls:
            assert call.file_path == "/test/file.c"
            assert call.line_number > 0
            assert call.line_content != ""
            assert call.call_context != ""
    
    def test_parse_parameters(self, analyzer):
        """Test parsing function parameters"""
        test_cases = [
            ("VOID", []),
            ("", []),
            ("IN UINT32 Value", [{"keyword": "IN", "type": "UINT32", "name": "Value", "full": "IN UINT32 Value"}]),
            ("OUT CHAR8 *Buffer, IN UINTN Size", [
                {"keyword": "OUT", "type": "CHAR8 *", "name": "Buffer", "full": "OUT CHAR8 *Buffer"},
                {"keyword": "IN", "type": "UINTN", "name": "Size", "full": "IN UINTN Size"}
            ]),
            ("OPTIONAL EFI_HANDLE Handle", [{"keyword": "OPTIONAL", "type": "EFI_HANDLE", "name": "Handle", "full": "OPTIONAL EFI_HANDLE Handle"}])
        ]
        
        for param_str, expected in test_cases:
            result = analyzer._parse_parameters(param_str)
            assert len(result) == len(expected)
            
            for i, param in enumerate(result):
                assert param["keyword"] == expected[i]["keyword"]
                assert param["type"] == expected[i]["type"]
                assert param["name"] == expected[i]["name"]
    
    def test_split_parameters(self, analyzer):
        """Test splitting parameter strings"""
        test_cases = [
            ("UINT32 Value", ["UINT32 Value"]),
            ("UINT32 Value, CHAR8 *String", ["UINT32 Value", "CHAR8 *String"]),
            ("EFI_HANDLE Handle, VOID (*Callback)(VOID), UINTN Size", 
             ["EFI_HANDLE Handle", "VOID (*Callback)(VOID)", "UINTN Size"]),
        ]
        
        for param_str, expected in test_cases:
            result = analyzer._split_parameters(param_str)
            assert result == expected
    
    def test_find_function_end(self, analyzer):
        """Test finding the end of a function definition"""
        code = """
EFI_STATUS TestFunction() {
  if (condition) {
    DoSomething();
  }
  return EFI_SUCCESS;
}
"""
        # Find the opening brace position
        start_pos = code.find('{')
        end_line = analyzer._find_function_end(code, start_pos + 1)
        
        assert end_line > 1  # Should be after the opening line
    
    def test_extract_function_documentation(self, analyzer):
        """Test extracting function documentation"""
        code = """
/**
 * This is a test function
 * @param Value Input parameter
 * @return Status code
 */
EFI_STATUS TestFunction(UINT32 Value) {
"""
        
        # Find function start position
        func_start = code.find("EFI_STATUS TestFunction")
        documentation = analyzer._extract_function_documentation(code, func_start)
        
        assert "This is a test function" in documentation
        assert "@param Value" in documentation
        assert "@return Status code" in documentation
    
    def test_build_call_graph(self, analyzer):
        """Test building call graph from modules"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test module structure
            module_dir = Path(temp_dir) / "TestModule"
            module_dir.mkdir()
            
            # Create source file with function calls
            source_file = module_dir / "test.c"
            source_file.write_text("""
EFI_STATUS MainFunction() {
    HelperFunction();
    AnotherHelper();
    return EFI_SUCCESS;
}

VOID HelperFunction() {
    UtilityFunction();
}
""")
            
            # Build call graph
            call_graph = analyzer.build_call_graph([str(module_dir / "test.inf")])
            
            assert isinstance(call_graph, dict)
            # The call graph should contain some relationships
            # (exact content depends on the parsing implementation)
    
    def test_get_function_callers(self, analyzer, sample_c_code):
        """Test getting function callers"""
        with tempfile.NamedTemporaryFile(suffix='.c', mode='w', delete=False) as f:
            f.write(sample_c_code)
            f.flush()
            
            # Analyze the file first
            analyzer.analyze_source_file(f.name)
            
            # Get callers of TestFunction
            callers = analyzer.get_function_callers("TestFunction")
            
            # Should find at least one caller (StaticFunction calls TestFunction)
            assert len(callers) > 0
            
            # Check that caller information is correct
            for caller in callers:
                assert isinstance(caller, FunctionCall)
                assert caller.called_function == "TestFunction"
                assert caller.file_path == f.name
    
    def test_get_function_callees(self, analyzer):
        """Test getting function callees"""
        # Set up a simple call graph
        analyzer.call_graph = {
            "MainFunction": ["Helper1", "Helper2"],
            "Helper1": ["Utility"],
            "Helper2": []
        }
        
        callees = analyzer.get_function_callees("MainFunction")
        assert callees == ["Helper1", "Helper2"]
        
        callees = analyzer.get_function_callees("Helper1")
        assert callees == ["Utility"]
        
        callees = analyzer.get_function_callees("NonexistentFunction")
        assert callees == []
    
    def test_analyze_call_depth(self, analyzer):
        """Test analyzing call depth"""
        # Set up a call graph with known depth
        analyzer.call_graph = {
            "Level0": ["Level1A", "Level1B"],
            "Level1A": ["Level2"],
            "Level1B": [],
            "Level2": ["Level3"],
            "Level3": []
        }
        
        depths = analyzer.analyze_call_depth("Level0", max_depth=5)
        
        assert depths["Level0"] == 0
        assert depths["Level1A"] == 1
        assert depths["Level1B"] == 1
        assert depths["Level2"] == 2
        assert depths["Level3"] == 3
    
    def test_find_recursive_calls(self, analyzer):
        """Test finding recursive call chains"""
        # Set up a call graph with recursion
        analyzer.call_graph = {
            "FuncA": ["FuncB"],
            "FuncB": ["FuncC"],
            "FuncC": ["FuncA"],  # Creates a cycle
            "FuncD": ["FuncE"],
            "FuncE": []  # No cycle
        }
        
        recursive_chains = analyzer.find_recursive_calls()
        
        assert len(recursive_chains) > 0
        # Should find the A->B->C->A cycle
        found_cycle = False
        for chain in recursive_chains:
            if "FuncA" in chain and "FuncB" in chain and "FuncC" in chain:
                found_cycle = True
                break
        
        assert found_cycle
    
    def test_get_function_complexity_metrics(self, analyzer):
        """Test getting function complexity metrics"""
        # Set up test data
        analyzer.call_graph = {
            "TestFunction": ["Helper1", "Helper2", "Helper1"],  # Duplicate call
        }
        
        # Mock function calls
        test_calls = [
            FunctionCall("OtherFunc", "TestFunction", "/test.c", 10, "TestFunction();", "context")
        ]
        analyzer.function_calls["/test.c"] = test_calls
        
        metrics = analyzer.get_function_complexity_metrics("TestFunction")
        
        assert "calls_made" in metrics
        assert "called_by" in metrics
        assert "max_call_depth" in metrics
        assert "unique_callees" in metrics
        
        assert metrics["calls_made"] == 3  # Total calls including duplicates
        assert metrics["unique_callees"] == 2  # Unique callees
        assert metrics["called_by"] == 1  # Called by OtherFunc
    
    def test_compile_patterns(self, analyzer):
        """Test that regex patterns compile correctly"""
        # Test function definition pattern
        test_code = "EFI_STATUS EFIAPI TestFunc(VOID) {"
        matches = list(analyzer.function_def_pattern.finditer(test_code))
        assert len(matches) > 0
        
        # Test function declaration pattern
        test_decl = "EFI_STATUS EFIAPI TestFunc(VOID);"
        matches = list(analyzer.function_decl_pattern.finditer(test_decl))
        assert len(matches) > 0
        
        # Test parameter pattern
        test_param = "IN UINT32 Value"
        matches = list(analyzer.parameter_pattern.finditer(test_param))
        assert len(matches) > 0
    
    def test_get_call_context(self, analyzer):
        """Test getting call context"""
        lines = [
            "if (condition) {",
            "  SomeFunction();",
            "  TargetFunction();",
            "  AnotherFunction();",
            "}"
        ]
        
        context = analyzer._get_call_context(lines, 3)  # Line with TargetFunction
        
        assert isinstance(context, str)
        assert len(context) > 0
        # Should contain surrounding lines
        assert "if (condition)" in context or "SomeFunction" in context
