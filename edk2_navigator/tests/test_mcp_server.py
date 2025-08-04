"""
Tests for MCP Server functionality
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from edk2_navigator.mcp_server import MCPServer
from edk2_navigator.dsc_parser import DSCContext, ModuleInfo
from edk2_navigator.dependency_graph import DependencyGraph
from datetime import datetime

class TestMCPServer:
    """Test cases for MCP Server"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            
            # Create EDK2 directory structure
            edk2_dir = workspace / "edk2"
            basetools_dir = edk2_dir / "BaseTools" / "Source" / "Python"
            basetools_dir.mkdir(parents=True)
            
            # Create sample DSC file
            dsc_file = workspace / "test.dsc"
            dsc_content = """
[Defines]
  PLATFORM_NAME = TestPlatform
  PLATFORM_GUID = 12345678-1234-1234-1234-123456789abc
  PLATFORM_VERSION = 0.1
  DSC_SPECIFICATION = 0x00010005
  OUTPUT_DIRECTORY = Build/Test
  SUPPORTED_ARCHITECTURES = X64
  BUILD_TARGETS = DEBUG|RELEASE

[Components]
  TestPkg/Module1/Module1.inf
"""
            dsc_file.write_text(dsc_content)
            
            yield {
                'workspace': str(workspace),
                'edk2_path': str(edk2_dir),
                'dsc_path': str(dsc_file)
            }
    
    @pytest.fixture
    def mcp_server(self, temp_workspace):
        """Create MCP server instance"""
        return MCPServer(temp_workspace['workspace'], temp_workspace['edk2_path'])
    
    @pytest.fixture
    def sample_dsc_context(self):
        """Sample DSC context for testing"""
        modules = [
            ModuleInfo(
                path="TestPkg/Module1/Module1.inf",
                name="Module1",
                type="DXE_DRIVER",
                guid="11111111-1111-1111-1111-111111111111",
                architecture=["X64"],
                dependencies=["BaseLib"],
                source_files=["Module1.c"],
                include_paths=[]
            )
        ]
        
        return DSCContext(
            dsc_path="test.dsc",
            workspace_root="/test",
            build_flags={"TARGET": "DEBUG", "ARCH": "X64"},
            included_modules=modules,
            library_mappings={"BaseLib": "MdePkg/Library/BaseLib/BaseLib.inf"},
            include_paths=[],
            preprocessor_definitions={},
            architecture="X64",
            build_target="DEBUG",
            toolchain="VS2019",
            timestamp=datetime.now()
        )
    
    def test_mcp_server_initialization(self, mcp_server, temp_workspace):
        """Test MCP server initialization"""
        assert mcp_server.workspace_dir == temp_workspace['workspace']
        assert mcp_server.edk2_path == temp_workspace['edk2_path']
        assert mcp_server.current_dsc_context is None
        assert mcp_server.current_dependency_graph is None
        assert mcp_server.query_engine is None
        assert len(mcp_server.tools) > 0
        assert len(mcp_server.resources) > 0
    
    def test_define_tools(self, mcp_server):
        """Test that tools are defined correctly"""
        tools = mcp_server._define_tools()
        
        assert len(tools) > 0
        
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "parse_dsc",
            "get_included_modules",
            "find_function",
            "get_module_dependencies",
            "trace_call_path",
            "analyze_function",
            "search_code",
            "get_build_statistics"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
        
        # Check that each tool has required fields
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert "type" in tool["inputSchema"]
            assert "properties" in tool["inputSchema"]
    
    def test_define_resources(self, mcp_server):
        """Test that resources are defined correctly"""
        resources = mcp_server._define_resources()
        
        assert len(resources) > 0
        
        resource_uris = [resource["uri"] for resource in resources]
        expected_resources = [
            "edk2://current-build-context",
            "edk2://dependency-graph",
            "edk2://function-index"
        ]
        
        for expected_resource in expected_resources:
            assert expected_resource in resource_uris
        
        # Check that each resource has required fields
        for resource in resources:
            assert "uri" in resource
            assert "name" in resource
            assert "description" in resource
            assert "mimeType" in resource
    
    def test_handle_parse_dsc(self, mcp_server, sample_dsc_context):
        """Test handling parse_dsc tool call"""
        # Mock the DSC parser directly on the server instance
        with patch.object(mcp_server.dsc_parser, 'parse_dsc', return_value=sample_dsc_context):
            with patch.object(mcp_server.dependency_graph_builder, 'build_from_context') as mock_build:
                mock_dependency_graph = Mock()
                mock_build.return_value = mock_dependency_graph
                
                # Test parse_dsc call
                arguments = {
                    "dsc_path": "test.dsc",
                    "build_flags": {"TARGET": "DEBUG", "ARCH": "X64"}
                }
                
                result = mcp_server._handle_parse_dsc(arguments)
                
                assert result["success"] == True
                assert "dsc_path" in result
                assert "modules_found" in result
                assert "library_mappings" in result
                assert "architecture" in result
                assert "build_target" in result
                assert "timestamp" in result
                
                # Verify that components were initialized
                assert mcp_server.current_dsc_context is not None
                assert mcp_server.current_dependency_graph is not None
                assert mcp_server.query_engine is not None
    
    def test_handle_get_included_modules_no_context(self, mcp_server):
        """Test get_included_modules without DSC context"""
        result = mcp_server._handle_get_included_modules({})
        
        assert result["success"] == False
        assert "No DSC context loaded" in result["error"]
    
    def test_handle_get_included_modules_with_context(self, mcp_server, sample_dsc_context):
        """Test get_included_modules with DSC context"""
        # Set up mock query engine
        mock_query_engine = Mock()
        mock_modules = [
            ModuleInfo("TestPkg/Module1/Module1.inf", "Module1", "DXE_DRIVER", 
                      "guid", ["X64"], ["BaseLib"], ["Module1.c"], []),
            ModuleInfo("TestPkg/Module2/Module2.inf", "Module2", "PEIM", 
                      "guid2", ["X64"], ["BaseLib"], ["Module2.c"], [])
        ]
        mock_query_engine.get_included_modules.return_value = mock_modules
        mcp_server.query_engine = mock_query_engine
        
        # Test without filter
        result = mcp_server._handle_get_included_modules({})
        
        assert result["success"] == True
        assert result["count"] == 2
        assert len(result["modules"]) == 2
        
        # Test with type filter
        result = mcp_server._handle_get_included_modules({"filter_by_type": "DXE_DRIVER"})
        
        assert result["success"] == True
        assert result["count"] == 1  # Only one DXE_DRIVER
        assert result["filter_applied"] == "DXE_DRIVER"
    
    def test_handle_find_function_no_context(self, mcp_server):
        """Test find_function without DSC context"""
        result = mcp_server._handle_find_function({"function_name": "TestFunction"})
        
        assert result["success"] == False
        assert "No DSC context loaded" in result["error"]
    
    def test_handle_find_function_with_context(self, mcp_server, sample_dsc_context):
        """Test find_function with DSC context"""
        from edk2_navigator.query_engine import FunctionLocation
        
        # Set up mock query engine
        mock_query_engine = Mock()
        mock_locations = [
            FunctionLocation(
                function_name="TestFunction",
                file_path="/test/file.c",
                line_number=10,
                module_name="TestModule",
                function_signature="EFI_STATUS EFIAPI TestFunction(VOID)",
                is_definition=True,
                calling_convention="EFIAPI",
                return_type="EFI_STATUS"
            )
        ]
        mock_query_engine.find_function.return_value = mock_locations
        mcp_server.query_engine = mock_query_engine
        mcp_server.current_dsc_context = sample_dsc_context
        
        result = mcp_server._handle_find_function({"function_name": "TestFunction"})
        
        assert result["success"] == True
        assert result["function_name"] == "TestFunction"
        assert result["count"] == 1
        assert result["definitions"] == 1
        assert result["declarations"] == 0
        assert len(result["locations"]) == 1
        
        location = result["locations"][0]
        assert location["function_name"] == "TestFunction"
        assert location["is_definition"] == True
        assert location["calling_convention"] == "EFIAPI"
    
    def test_handle_get_module_dependencies_no_context(self, mcp_server):
        """Test get_module_dependencies without DSC context"""
        result = mcp_server._handle_get_module_dependencies({"module_name": "TestModule"})
        
        assert result["success"] == False
        assert "No DSC context loaded" in result["error"]
    
    def test_handle_get_module_dependencies_with_context(self, mcp_server, sample_dsc_context):
        """Test get_module_dependencies with DSC context"""
        from edk2_navigator.query_engine import ModuleDependencies
        
        # Set up mock query engine
        mock_query_engine = Mock()
        mock_dependencies = ModuleDependencies(
            module_name="TestModule",
            module_path="TestPkg/TestModule/TestModule.inf",
            direct_dependencies=["BaseLib", "UefiLib"],
            transitive_dependencies=["BaseLib", "UefiLib", "DebugLib"],
            dependents=["OtherModule"],
            library_mappings={"BaseLib": "MdePkg/Library/BaseLib/BaseLib.inf"}
        )
        mock_query_engine.get_module_dependencies.return_value = mock_dependencies
        mcp_server.query_engine = mock_query_engine
        mcp_server.current_dsc_context = sample_dsc_context
        
        result = mcp_server._handle_get_module_dependencies({
            "module_name": "TestModule",
            "include_transitive": True
        })
        
        assert result["success"] == True
        assert result["module_name"] == "TestModule"
        assert result["module_path"] == "TestPkg/TestModule/TestModule.inf"
        assert "BaseLib" in result["direct_dependencies"]
        assert "transitive_dependencies" in result
        assert len(result["dependents"]) == 1
    
    def test_handle_trace_call_path_no_context(self, mcp_server):
        """Test trace_call_path without DSC context"""
        result = mcp_server._handle_trace_call_path({"function_name": "TestFunction"})
        
        assert result["success"] == False
        assert "No DSC context loaded" in result["error"]
    
    def test_handle_trace_call_path_with_context(self, mcp_server, sample_dsc_context):
        """Test trace_call_path with DSC context"""
        from edk2_navigator.query_engine import CallPath
        
        # Set up mock query engine
        mock_query_engine = Mock()
        mock_call_paths = [
            CallPath(
                caller_function="CallerFunc",
                called_function="TestFunction",
                call_chain=["CallerFunc", "TestFunction"],
                file_path="/test/file.c",
                line_number=20
            )
        ]
        mock_query_engine.trace_call_path.return_value = mock_call_paths
        mcp_server.query_engine = mock_query_engine
        mcp_server.current_dsc_context = sample_dsc_context
        
        result = mcp_server._handle_trace_call_path({
            "function_name": "TestFunction",
            "max_depth": 5
        })
        
        assert result["success"] == True
        assert result["function_name"] == "TestFunction"
        assert result["count"] == 1
        assert result["max_depth"] == 5
        assert len(result["call_paths"]) == 1
        
        call_path = result["call_paths"][0]
        assert call_path["caller_function"] == "CallerFunc"
        assert call_path["called_function"] == "TestFunction"
    
    def test_handle_search_code_no_context(self, mcp_server):
        """Test search_code without DSC context"""
        result = mcp_server._handle_search_code({"query": "test query"})
        
        assert result["success"] == False
        assert "No DSC context loaded" in result["error"]
    
    def test_handle_search_code_with_context(self, mcp_server, sample_dsc_context):
        """Test search_code with DSC context"""
        # Set up mock query engine
        mock_query_engine = Mock()
        mock_results = [
            {
                "file_path": "/test/file.c",
                "line_number": 15,
                "line_content": "// This is a test query result",
                "module_name": "TestModule",
                "relevance_score": 0.9
            }
        ]
        mock_query_engine.search_code_semantic.return_value = mock_results
        mcp_server.query_engine = mock_query_engine
        mcp_server.current_dsc_context = sample_dsc_context
        
        result = mcp_server._handle_search_code({
            "query": "test query",
            "file_types": [".c", ".h"],
            "max_results": 10
        })
        
        assert result["success"] == True
        assert result["query"] == "test query"
        assert result["count"] == 1
        assert result["total_found"] == 1
        assert len(result["results"]) == 1
        
        search_result = result["results"][0]
        assert search_result["file_path"] == "/test/file.c"
        assert search_result["line_number"] == 15
    
    def test_handle_get_build_statistics_no_context(self, mcp_server):
        """Test get_build_statistics without DSC context"""
        result = mcp_server._handle_get_build_statistics({})
        
        assert result["success"] == False
        assert "No DSC context loaded" in result["error"]
    
    def test_handle_get_build_statistics_with_context(self, mcp_server, sample_dsc_context):
        """Test get_build_statistics with DSC context"""
        mcp_server.current_dsc_context = sample_dsc_context
        
        result = mcp_server._handle_get_build_statistics({})
        
        assert result["success"] == True
        assert "dsc_path" in result
        assert "architecture" in result
        assert "build_target" in result
        assert "total_modules" in result
        assert "module_types" in result
        assert "library_mappings" in result
        assert "total_source_files" in result
        assert "parse_timestamp" in result
        
        assert result["total_modules"] == len(sample_dsc_context.included_modules)
        assert result["architecture"] == sample_dsc_context.architecture
        assert result["build_target"] == sample_dsc_context.build_target
    
    def test_handle_tool_call_unknown_tool(self, mcp_server):
        """Test handling unknown tool call"""
        result = mcp_server.handle_tool_call("unknown_tool", {})
        
        assert result["success"] == False
        assert "Unknown tool" in result["error"]
    
    def test_handle_tool_call_with_exception(self, mcp_server):
        """Test handling tool call that raises exception"""
        with patch.object(mcp_server, '_handle_parse_dsc', side_effect=Exception("Test error")):
            result = mcp_server.handle_tool_call("parse_dsc", {"dsc_path": "test.dsc"})
            
            assert result["success"] == False
            assert "Test error" in result["error"]
            assert result["error_type"] == "Exception"
    
    def test_handle_resource_request_build_context(self, mcp_server, sample_dsc_context):
        """Test handling build context resource request"""
        mcp_server.current_dsc_context = sample_dsc_context
        
        result = mcp_server.handle_resource_request("edk2://current-build-context")
        
        assert result["success"] == True
        assert "content" in result
        
        content = result["content"]
        assert content["dsc_path"] == sample_dsc_context.dsc_path
        assert content["architecture"] == sample_dsc_context.architecture
        assert content["build_target"] == sample_dsc_context.build_target
    
    def test_handle_resource_request_dependency_graph(self, mcp_server):
        """Test handling dependency graph resource request"""
        # Set up mock dependency graph with proper module mock
        mock_module = ModuleInfo(
            path="TestPkg/Module1/Module1.inf",
            name="Module1",
            type="DXE_DRIVER",
            guid="11111111-1111-1111-1111-111111111111",
            architecture=["X64"],
            dependencies=["BaseLib"],
            source_files=["Module1.c"],
            include_paths=[]
        )
        
        mock_graph = Mock()
        mock_graph.nodes = {"module1": mock_module}
        mock_graph.edges = {"module1": ["dep1"]}
        mock_graph.library_mappings = {"lib1": "impl1"}
        mcp_server.current_dependency_graph = mock_graph
        
        result = mcp_server.handle_resource_request("edk2://dependency-graph")
        
        assert result["success"] == True
        assert "content" in result
        
        content = result["content"]
        assert "nodes_count" in content
        assert "edges_count" in content
        assert "library_mappings" in content
    
    def test_handle_resource_request_function_index(self, mcp_server):
        """Test handling function index resource request"""
        # Set up mock query engine
        mock_query_engine = Mock()
        mock_query_engine.function_cache = {"func1": []}
        mcp_server.query_engine = mock_query_engine
        
        mock_graph = Mock()
        mock_graph.nodes = {"module1": Mock()}
        mcp_server.current_dependency_graph = mock_graph
        
        result = mcp_server.handle_resource_request("edk2://function-index")
        
        assert result["success"] == True
        assert "content" in result
        
        content = result["content"]
        assert "modules_indexed" in content
        assert "cache_size" in content
    
    def test_handle_resource_request_unknown_resource(self, mcp_server):
        """Test handling unknown resource request"""
        result = mcp_server.handle_resource_request("edk2://unknown-resource")
        
        assert result["success"] == False
        assert "Unknown resource" in result["error"]
    
    def test_handle_resource_request_with_exception(self, mcp_server):
        """Test handling resource request that raises exception"""
        with patch.object(mcp_server, '_get_build_context_resource', side_effect=Exception("Test error")):
            result = mcp_server.handle_resource_request("edk2://current-build-context")
            
            assert result["success"] == False
            assert "Test error" in result["error"]
            assert result["error_type"] == "Exception"
    
    def test_get_build_context_resource_no_context(self, mcp_server):
        """Test getting build context resource without context"""
        result = mcp_server._get_build_context_resource()
        
        assert result["success"] == False
        assert "No DSC context loaded" in result["error"]
    
    def test_get_dependency_graph_resource_no_graph(self, mcp_server):
        """Test getting dependency graph resource without graph"""
        result = mcp_server._get_dependency_graph_resource()
        
        assert result["success"] == False
        assert "No dependency graph available" in result["error"]
    
    def test_get_function_index_resource_no_engine(self, mcp_server):
        """Test getting function index resource without query engine"""
        result = mcp_server._get_function_index_resource()
        
        assert result["success"] == False
        assert "No query engine available" in result["error"]
