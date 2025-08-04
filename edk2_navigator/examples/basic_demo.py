"""
Basic demonstration of EDK2 Navigator functionality
"""
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import edk2_navigator
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from edk2_navigator.dsc_parser import DSCParser
from edk2_navigator.dependency_graph import DependencyGraphBuilder
from edk2_navigator.cache_manager import CacheManager
from edk2_navigator.utils import validate_edk2_workspace, parse_dsc_section
from edk2_navigator.exceptions import EDK2NavigatorError

def main():
    """Demonstrate basic EDK2 Navigator functionality"""
    print("EDK2 Navigator - Basic Functionality Demo")
    print("=" * 50)
    
    # Setup paths
    current_dir = Path.cwd()
    workspace_dir = current_dir
    edk2_path = current_dir / "edk2"
    
    print(f"Workspace: {workspace_dir}")
    print(f"EDK2 Path: {edk2_path}")
    print()
    
    # Step 1: Validate workspace
    print("1. Validating EDK2 workspace...")
    try:
        is_valid, errors = validate_edk2_workspace(str(workspace_dir), str(edk2_path))
        if is_valid:
            print("   ✓ Workspace validation passed")
        else:
            print("   ✗ Workspace validation failed:")
            for error in errors:
                print(f"     - {error}")
            print("   Note: This is expected in the demo environment")
    except Exception as e:
        print(f"   ✗ Validation error: {e}")
    print()
    
    # Step 2: Initialize components
    print("2. Initializing EDK2 Navigator components...")
    try:
        # Initialize DSC parser
        parser = DSCParser(str(workspace_dir), str(edk2_path))
        print("   ✓ DSC Parser initialized")
        
        # Initialize cache manager
        cache_manager = CacheManager()
        print("   ✓ Cache Manager initialized")
        
        # Initialize dependency graph builder
        graph_builder = DependencyGraphBuilder()
        print("   ✓ Dependency Graph Builder initialized")
        
    except Exception as e:
        print(f"   ✗ Initialization error: {e}")
        return
    print()
    
    # Step 3: Look for DSC files
    print("3. Looking for DSC files...")
    dsc_files = []
    
    # Check for OVMF DSC file (primary target)
    ovmf_dsc = edk2_path / "OvmfPkg" / "OvmfPkgX64.dsc"
    if ovmf_dsc.exists():
        dsc_files.append(str(ovmf_dsc))
        print(f"   ✓ Found OVMF DSC: {ovmf_dsc}")
    
    # Check for other common DSC files
    common_dscs = [
        "EmulatorPkg/EmulatorPkg.dsc",
        "MdeModulePkg/MdeModulePkg.dsc",
        "ShellPkg/ShellPkg.dsc"
    ]
    
    for dsc_rel_path in common_dscs:
        dsc_path = edk2_path / dsc_rel_path
        if dsc_path.exists():
            dsc_files.append(str(dsc_path))
            print(f"   ✓ Found DSC: {dsc_path}")
    
    if not dsc_files:
        print("   ✗ No DSC files found")
        print("   Note: This is expected if EDK2 repository is not present")
        
        # Create a demo DSC file for testing
        demo_dsc_content = """
[Defines]
  PLATFORM_NAME                  = DemoPlatform
  PLATFORM_GUID                  = 12345678-1234-1234-1234-123456789abc
  PLATFORM_VERSION               = 0.1
  DSC_SPECIFICATION              = 0x00010005
  OUTPUT_DIRECTORY               = Build/Demo
  SUPPORTED_ARCHITECTURES        = X64
  BUILD_TARGETS                  = DEBUG|RELEASE

[Components]
  DemoPkg/DemoModule1/DemoModule1.inf
  DemoPkg/DemoModule2/DemoModule2.inf
"""
        demo_dsc_path = workspace_dir / "demo_platform.dsc"
        demo_dsc_path.write_text(demo_dsc_content)
        dsc_files.append(str(demo_dsc_path))
        print(f"   ✓ Created demo DSC: {demo_dsc_path}")
    print()
    
    # Step 4: Parse DSC file
    if dsc_files:
        dsc_path = dsc_files[0]  # Use first available DSC
        print(f"4. Parsing DSC file: {Path(dsc_path).name}")
        
        try:
            # Check cache first
            build_flags = {"TARGET": "DEBUG", "ARCH": "X64", "TOOLCHAIN": "VS2019"}
            
            print("   Checking cache...")
            cached_data = cache_manager.load_cached_data(dsc_path, build_flags)
            if cached_data:
                print("   ✓ Found cached data")
            else:
                print("   ✗ No cached data found")
            
            # Parse DSC file
            print("   Parsing DSC file...")
            dsc_context = parser.parse_dsc(dsc_path, build_flags)
            
            print(f"   ✓ DSC parsed successfully")
            print(f"     Platform: {Path(dsc_context.dsc_path).name}")
            print(f"     Architecture: {dsc_context.architecture}")
            print(f"     Build Target: {dsc_context.build_target}")
            print(f"     Toolchain: {dsc_context.toolchain}")
            print(f"     Modules: {len(dsc_context.included_modules)}")
            
            # Store in cache for future use
            cache_manager.store_parsed_data(dsc_path, build_flags, {
                'dsc_context': {
                    'dsc_path': dsc_context.dsc_path,
                    'architecture': dsc_context.architecture,
                    'build_target': dsc_context.build_target,
                    'module_count': len(dsc_context.included_modules)
                }
            })
            print("   ✓ Data cached for future use")
            
        except Exception as e:
            print(f"   ✗ DSC parsing error: {e}")
            return
        print()
        
        # Step 5: Build dependency graph
        print("5. Building dependency graph...")
        try:
            dependency_graph = graph_builder.build_from_context(dsc_context)
            
            print(f"   ✓ Dependency graph built")
            print(f"     Nodes: {len(dependency_graph.nodes)}")
            print(f"     Edges: {len(dependency_graph.edges)}")
            
            # Serialize graph to JSON for inspection
            graph_output = workspace_dir / "dependency_graph.json"
            dependency_graph_builder = DependencyGraphBuilder()
            dependency_graph_builder.graph = dependency_graph
            dependency_graph_builder.serialize_to_json(str(graph_output))
            print(f"   ✓ Graph saved to: {graph_output}")
            
        except Exception as e:
            print(f"   ✗ Dependency graph error: {e}")
        print()
    
    # Step 6: Cache statistics
    print("6. Cache statistics...")
    try:
        stats = cache_manager.get_cache_stats()
        print(f"   Cache directory: {stats['cache_dir']}")
        print(f"   Cached files: {stats['file_count']}")
        print(f"   Total size: {stats['total_size_mb']:.2f} MB")
        print(f"   Max size: {stats['max_size_mb']:.0f} MB")
    except Exception as e:
        print(f"   ✗ Cache stats error: {e}")
    print()
    
    # Step 7: Demonstrate utility functions
    print("7. Utility function demonstrations...")
    
    if dsc_files:
        try:
            # Read and parse DSC content
            with open(dsc_files[0], 'r') as f:
                dsc_content = f.read()
            
            # Parse sections
            defines = parse_dsc_section(dsc_content, 'Defines')
            components = parse_dsc_section(dsc_content, 'Components')
            
            print(f"   ✓ Parsed DSC sections:")
            print(f"     Defines entries: {len(defines)}")
            print(f"     Component entries: {len(components)}")
            
            if defines:
                print("     Sample defines:")
                for define in defines[:3]:  # Show first 3
                    print(f"       {define}")
            
            if components:
                print("     Sample components:")
                for component in components[:3]:  # Show first 3
                    print(f"       {component}")
                    
        except Exception as e:
            print(f"   ✗ Utility function error: {e}")
    print()
    
    print("Demo completed successfully!")
    print("\nNext steps for full implementation:")
    print("1. Integrate with EDK2 BaseTools for actual DSC parsing")
    print("2. Implement function analysis and search capabilities")
    print("3. Add MCP server for LLM integration")
    print("4. Enhance dependency resolution")
    print("5. Add semantic search capabilities")

if __name__ == "__main__":
    main()
