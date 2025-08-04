"""
Basic functionality tests for EDK2 Navigator
"""
import pytest
import tempfile
from pathlib import Path
from edk2_navigator.dsc_parser import DSCParser, DSCContext, ModuleInfo
from edk2_navigator.dependency_graph import DependencyGraphBuilder
from edk2_navigator.cache_manager import CacheManager
from edk2_navigator.utils import validate_edk2_workspace, parse_dsc_section
from edk2_navigator.exceptions import DSCParsingError, WorkspaceValidationError

class TestBasicFunctionality:
    """Test basic functionality of core components"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            
            # Create EDK2 directory structure
            edk2_dir = workspace / "edk2"
            basetools_dir = edk2_dir / "BaseTools" / "Source" / "Python" / "build"
            basetools_dir.mkdir(parents=True)
            
            # Create mock build.py
            build_script = basetools_dir / "build.py"
            build_script.write_text("# Mock build script")
            
            # Create sample DSC file
            dsc_content = """
[Defines]
  PLATFORM_NAME                  = TestPlatform
  PLATFORM_GUID                  = 12345678-1234-1234-1234-123456789abc
  PLATFORM_VERSION               = 0.1
  DSC_SPECIFICATION              = 0x00010005
  OUTPUT_DIRECTORY               = Build/Test
  SUPPORTED_ARCHITECTURES        = X64|IA32
  BUILD_TARGETS                  = DEBUG|RELEASE

[Components]
  TestPkg/TestModule1/TestModule1.inf
  TestPkg/TestModule2/TestModule2.inf
"""
            dsc_file = workspace / "TestPlatform.dsc"
            dsc_file.write_text(dsc_content)
            
            yield {
                'workspace': str(workspace),
                'edk2_path': str(edk2_dir),
                'dsc_path': str(dsc_file),
                'dsc_content': dsc_content
            }
    
    def test_workspace_validation(self, temp_workspace):
        """Test workspace validation functionality"""
        # Test valid workspace
        is_valid, errors = validate_edk2_workspace(
            temp_workspace['workspace'],
            temp_workspace['edk2_path']
        )
        assert is_valid
        assert len(errors) == 0
        
        # Test invalid workspace
        is_valid, errors = validate_edk2_workspace(
            "/nonexistent/path",
            "/nonexistent/edk2"
        )
        assert not is_valid
        assert len(errors) > 0
    
    def test_dsc_parser_initialization(self, temp_workspace):
        """Test DSC parser initialization"""
        parser = DSCParser(
            temp_workspace['workspace'],
            temp_workspace['edk2_path']
        )
        
        assert parser.workspace_dir == Path(temp_workspace['workspace']).resolve()
        assert parser.edk2_path == Path(temp_workspace['edk2_path']).resolve()
    
    def test_dsc_parser_basic_parsing(self, temp_workspace):
        """Test basic DSC file parsing"""
        parser = DSCParser(
            temp_workspace['workspace'],
            temp_workspace['edk2_path']
        )
        
        # Test successful parsing
        context = parser.parse_dsc(temp_workspace['dsc_path'])
        
        assert isinstance(context, DSCContext)
        assert context.dsc_path == temp_workspace['dsc_path']
        assert context.workspace_root == temp_workspace['workspace']
        assert context.architecture == "X64"
        assert context.build_target == "DEBUG"
        
        # Test with custom build flags
        build_flags = {"TARGET": "RELEASE", "ARCH": "IA32"}
        context = parser.parse_dsc(temp_workspace['dsc_path'], build_flags)
        
        assert context.build_flags == build_flags
        assert context.architecture == "IA32"
        assert context.build_target == "RELEASE"
    
    def test_dsc_parser_file_not_found(self, temp_workspace):
        """Test DSC parser with non-existent file"""
        parser = DSCParser(
            temp_workspace['workspace'],
            temp_workspace['edk2_path']
        )
        
        with pytest.raises(FileNotFoundError):
            parser.parse_dsc("nonexistent.dsc")
    
    def test_dependency_graph_builder(self, temp_workspace):
        """Test dependency graph builder"""
        parser = DSCParser(
            temp_workspace['workspace'],
            temp_workspace['edk2_path']
        )
        
        context = parser.parse_dsc(temp_workspace['dsc_path'])
        
        # Build dependency graph
        builder = DependencyGraphBuilder()
        graph = builder.build_from_context(context)
        
        assert graph is not None
        assert isinstance(graph.nodes, dict)
        assert isinstance(graph.edges, dict)
    
    def test_cache_manager_basic_operations(self, temp_workspace):
        """Test cache manager basic operations"""
        cache_manager = CacheManager()
        
        # Test data
        test_data = {"test": "data", "modules": []}
        build_flags = {"TARGET": "DEBUG", "ARCH": "X64"}
        
        # Initially cache should not be valid
        assert not cache_manager.is_cache_valid(
            temp_workspace['dsc_path'],
            build_flags
        )
        
        # Store data in cache
        cache_manager.store_parsed_data(
            temp_workspace['dsc_path'],
            build_flags,
            test_data
        )
        
        # Now cache should be valid
        assert cache_manager.is_cache_valid(
            temp_workspace['dsc_path'],
            build_flags
        )
        
        # Load cached data
        cached_data = cache_manager.load_cached_data(
            temp_workspace['dsc_path'],
            build_flags
        )
        
        assert cached_data == test_data
        
        # Test cache stats
        stats = cache_manager.get_cache_stats()
        assert 'cache_dir' in stats
        assert 'file_count' in stats
        assert stats['file_count'] >= 1
    
    def test_parse_dsc_section_utility(self, temp_workspace):
        """Test DSC section parsing utility"""
        content = temp_workspace['dsc_content']
        
        # Test parsing Defines section
        defines = parse_dsc_section(content, 'Defines')
        assert len(defines) > 0
        
        # Check for expected defines
        platform_name_found = False
        for line in defines:
            if 'PLATFORM_NAME' in line and 'TestPlatform' in line:
                platform_name_found = True
                break
        assert platform_name_found
        
        # Test parsing Components section
        components = parse_dsc_section(content, 'Components')
        assert len(components) == 2
        assert 'TestPkg/TestModule1/TestModule1.inf' in components
        assert 'TestPkg/TestModule2/TestModule2.inf' in components
    
    def test_cache_clear_functionality(self, temp_workspace):
        """Test cache clearing functionality"""
        cache_manager = CacheManager()
        
        # Store some test data
        test_data = {"test": "data"}
        build_flags = {"TARGET": "DEBUG", "ARCH": "X64"}
        
        cache_manager.store_parsed_data(
            temp_workspace['dsc_path'],
            build_flags,
            test_data
        )
        
        # Verify cache exists
        assert cache_manager.is_cache_valid(
            temp_workspace['dsc_path'],
            build_flags
        )
        
        # Clear cache
        cache_manager.clear_cache()
        
        # Verify cache is cleared
        assert not cache_manager.is_cache_valid(
            temp_workspace['dsc_path'],
            build_flags
        )
    
    def test_module_info_dataclass(self):
        """Test ModuleInfo dataclass functionality"""
        module = ModuleInfo(
            path="TestPkg/TestModule/TestModule.inf",
            name="TestModule",
            type="DXE_DRIVER",
            guid="12345678-1234-1234-1234-123456789abc",
            architecture=["X64"],
            dependencies=["BaseLib", "UefiLib"],
            source_files=["TestModule.c", "TestModule.h"],
            include_paths=["Include"]
        )
        
        assert module.path == "TestPkg/TestModule/TestModule.inf"
        assert module.name == "TestModule"
        assert module.type == "DXE_DRIVER"
        assert "BaseLib" in module.dependencies
        assert "TestModule.c" in module.source_files
