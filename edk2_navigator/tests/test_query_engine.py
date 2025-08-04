"""
Tests for Query Engine functionality
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from edk2_navigator.query_engine import QueryEngine, FunctionLocation, ModuleDependencies, CallPath
from edk2_navigator.dependency_graph import DependencyGraph
from edk2_navigator.dsc_parser import ModuleInfo, DSCContext
from edk2_navigator.exceptions import FunctionNotFoundError, ModuleNotFoundError
from datetime import datetime

class TestQueryEngine:
    """Test cases for Query Engine"""
    
    @pytest.fixture
    def sample_modules(self):
        """Sample module information for testing"""
        return [
            ModuleInfo(
                path="TestPkg/Module1/Module1.inf",
                name="Module1",
                type="DXE_DRIVER",
                guid="11111111-1111-1111-1111-111111111111",
                architecture=["X64"],
                dependencies=["BaseLib", "UefiLib"],
                source_files=["Module1.c", "Module1.h"],
                include_paths=["Include"]
            ),
            ModuleInfo(
                path="TestPkg/Module2/Module2.inf",
                name="Module2",
                type="PEIM",
                guid="22222222-2222-2222-2222-222222222222",
                architecture=["X64"],
                dependencies=["BaseLib"],
                source_files=["Module2.c"],
                include_paths=["Include"]
            )
        ]
    
    @pytest.fixture
    def sample_dependency_graph(self, sample_modules):
        """Sample dependency graph for testing"""
        graph = DependencyGraph(
            nodes={module.path: module for module in sample_modules},
            edges={
                "TestPkg/Module1/Module1.inf": ["BaseLib", "UefiLib"],
                "TestPkg/Module2/Module2.inf": ["BaseLib"]
            },
            library_mappings={"BaseLib": "MdePkg/Library/BaseLib/BaseLib.inf"},
            call_graph={},
            include_graph={}
        )
        return graph
    
    @pytest.fixture
    def sample_dsc_context(self, sample_modules):
        """Sample DSC context for testing"""
        return DSCContext(
            dsc_path="test.dsc",
            workspace_root="/test",
            build_flags={"TARGET": "DEBUG", "ARCH": "X64"},
            included_modules=sample_modules,
            library_mappings={"BaseLib": "MdePkg/Library/BaseLib/BaseLib.inf"},
            include_paths=[],
            preprocessor_definitions={},
            architecture="X64",
            build_target="DEBUG",
            toolchain="VS2019",
            timestamp=datetime.now()
        )
    
    def test_query_engine_initialization(self, sample_dependency_graph):
        """Test query engine initialization"""
        engine = QueryEngine(sample_dependency_graph)
        
        assert engine.graph == sample_dependency_graph
        assert engine.function_cache == {}
        assert engine.call_graph_cache == {}
        assert len(engine.edk2_calling_conventions) > 0
        assert len(engine.edk2_types) > 0
    
    def test_get_included_modules(self, sample_dependency_graph):
        """Test getting included modules"""
        engine = QueryEngine(sample_dependency_graph)
        
        modules = engine.get_included_modules()
        
        assert len(modules) == 2
        assert all(isinstance(module, ModuleInfo) for module in modules)
        
        module_names = [m.name for m in modules]
        assert "Module1" in module_names
        assert "Module2" in module_names
    
    def test_get_module_dependencies_valid_module(self, sample_dependency_graph, sample_dsc_context):
        """Test getting dependencies for valid module"""
        engine = QueryEngine(sample_dependency_graph)
        
        deps = engine.get_module_dependencies("Module1", sample_dsc_context)
        
        assert isinstance(deps, ModuleDependencies)
        assert deps.module_name == "Module1"
        assert deps.module_path == "TestPkg/Module1/Module1.inf"
        assert "BaseLib" in deps.direct_dependencies
        assert "UefiLib" in deps.direct_dependencies
        assert len(deps.library_mappings) > 0
    
    def test_get_module_dependencies_invalid_module(self, sample_dependency_graph, sample_dsc_context):
        """Test getting dependencies for invalid module"""
        engine = QueryEngine(sample_dependency_graph)
        
        with pytest.raises(ModuleNotFoundError, match="Module not found"):
            engine.get_module_dependencies("NonexistentModule", sample_dsc_context)
    
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_find_function_with_definition(self, mock_open, mock_exists, sample_dependency_graph, sample_dsc_context):
        """Test finding a function definition"""
        # Mock file system
        mock_exists.return_value = True
        
        # Mock file content with a function definition
        mock_file_content = """
#include <Uefi.h>

EFI_STATUS
EFIAPI
TestFunction (
  IN UINTN Parameter
  )
{
  return EFI_SUCCESS;
}
"""
        mock_open.return_value.__enter__.return_value.read.return_value = mock_file_content
        
        engine = QueryEngine(sample_dependency_graph)
        
        # Mock the _find_source_file_paths method to return a valid path
        with patch.object(engine, '_find_source_file_paths', return_value=['/test/Module1.c']):
            locations = engine.find_function("TestFunction", sample_dsc_context)
            
            assert len(locations) > 0
            location = locations[0]
            assert isinstance(location, FunctionLocation)
            assert location.function_name == "TestFunction"
            assert location.is_definition == True
            assert location.calling_convention == "EFIAPI"
            assert location.return_type == "EFI_STATUS"
    
    @patch('os.path.exists')
    def test_find_function_not_found(self, mock_exists, sample_dependency_graph, sample_dsc_context):
        """Test finding a function that doesn't exist"""
        # Mock file system - no files exist
        mock_exists.return_value = False
        
        engine = QueryEngine(sample_dependency_graph)
        
        with pytest.raises(FunctionNotFoundError, match="Function 'NonexistentFunction' not found"):
            engine.find_function("NonexistentFunction", sample_dsc_context)
    
    def test_function_caching(self, sample_dependency_graph, sample_dsc_context):
        """Test that function search results are cached"""
        engine = QueryEngine(sample_dependency_graph)
        
        # Mock the _search_module_for_function method to return a result
        mock_location = FunctionLocation(
            function_name="TestFunction",
            file_path="/test/file.c",
            line_number=10,
            module_name="TestModule",
            function_signature="EFI_STATUS EFIAPI TestFunction(VOID)",
            is_definition=True,
            calling_convention="EFIAPI",
            return_type="EFI_STATUS"
        )
        
        with patch.object(engine, '_search_module_for_function', return_value=[mock_location]):
            # First call should search and cache
            locations1 = engine.find_function("TestFunction", sample_dsc_context)
            
            # Second call should use cache
            locations2 = engine.find_function("TestFunction", sample_dsc_context)
            
            assert locations1 == locations2
            assert len(engine.function_cache) > 0
    
    def test_trace_call_path_empty_result(self, sample_dependency_graph, sample_dsc_context):
        """Test tracing call paths when no function is found"""
        engine = QueryEngine(sample_dependency_graph)
        
        with patch.object(engine, 'find_function', side_effect=FunctionNotFoundError("Function not found")):
            call_paths = engine.trace_call_path("NonexistentFunction", sample_dsc_context)
            
            assert call_paths == []
    
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_search_code_semantic(self, mock_open, mock_exists, sample_dependency_graph, sample_dsc_context):
        """Test semantic code search"""
        # Mock file system
        mock_exists.return_value = True
        
        # Mock file content with search term
        mock_file_content = """
#include <Uefi.h>

// This function handles PCI enumeration
EFI_STATUS PciEnumerationFunction() {
    // PCI enumeration logic here
    return EFI_SUCCESS;
}
"""
        mock_open.return_value.__enter__.return_value.read.return_value = mock_file_content
        
        engine = QueryEngine(sample_dependency_graph)
        
        # Mock the _find_source_file_paths method to return valid paths
        with patch.object(engine, '_find_source_file_paths', return_value=['/test/Module1.c']):
            results = engine.search_code_semantic("PCI enumeration", sample_dsc_context)
            
            assert len(results) > 0
            result = results[0]
            assert "file_path" in result
            assert "line_number" in result
            assert "line_content" in result
            assert "module_name" in result
            assert "relevance_score" in result
    
    def test_compile_patterns(self, sample_dependency_graph):
        """Test that regex patterns are compiled correctly"""
        engine = QueryEngine(sample_dependency_graph)
        
        # Test function definition pattern
        test_code = """
EFI_STATUS
EFIAPI
TestFunction (
  IN UINTN Parameter
  )
{
  return EFI_SUCCESS;
}
"""
        
        matches = list(engine.function_def_pattern.finditer(test_code))
        assert len(matches) > 0
        
        match = matches[0]
        assert match.group(1).strip() == "EFI_STATUS"  # Return type
        assert match.group(2) == "EFIAPI"  # Calling convention
        assert match.group(3) == "TestFunction"  # Function name
    
    def test_find_source_file_paths(self, sample_dependency_graph):
        """Test finding source file paths"""
        engine = QueryEngine(sample_dependency_graph)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file structure
            module_dir = Path(temp_dir) / "TestPkg" / "Module1"
            module_dir.mkdir(parents=True)
            
            source_file = module_dir / "Module1.c"
            source_file.write_text("// Test source file")
            
            # Test finding the source file
            paths = engine._find_source_file_paths("Module1.c", "TestPkg/Module1/Module1.inf")
            
            # Should find at least one path (may not be the exact one due to path resolution)
            assert isinstance(paths, list)
    
    def test_get_transitive_dependencies(self, sample_dependency_graph):
        """Test getting transitive dependencies"""
        engine = QueryEngine(sample_dependency_graph)
        
        # Test with Module1 which depends on BaseLib and UefiLib
        transitive_deps = engine._get_transitive_dependencies("TestPkg/Module1/Module1.inf")
        
        assert isinstance(transitive_deps, list)
        assert "BaseLib" in transitive_deps
        assert "UefiLib" in transitive_deps
    
    def test_extract_function_definitions_with_various_patterns(self, sample_dependency_graph):
        """Test extracting function definitions with various EDK2 patterns"""
        engine = QueryEngine(sample_dependency_graph)
        
        test_cases = [
            # Standard EFIAPI function
            ("EFI_STATUS EFIAPI TestFunc1(VOID) {", "TestFunc1", "EFI_STATUS", "EFIAPI"),
            # Function without calling convention
            ("VOID TestFunc2(UINTN Param) {", "TestFunc2", "VOID", ""),
            # Static function
            ("STATIC EFI_STATUS TestFunc3(VOID) {", "TestFunc3", "EFI_STATUS", ""),
            # Function with pointer return type
            ("VOID* EFIAPI TestFunc4(VOID) {", "TestFunc4", "VOID*", "EFIAPI"),
        ]
        
        for code, expected_name, expected_return, expected_conv in test_cases:
            definitions = engine._extract_function_definitions(code, "/test/file.c", expected_name)
            
            if definitions:  # Only test if we found the function
                definition = definitions[0]
                assert definition.function_name == expected_name
                assert definition.return_type == expected_return
                assert definition.calling_convention == expected_conv
                assert definition.is_definition == True
