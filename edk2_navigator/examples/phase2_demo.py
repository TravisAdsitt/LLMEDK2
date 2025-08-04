"""
Phase 2 Demo - Demonstrates the query engine functionality
"""
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import edk2_navigator
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from edk2_navigator import (
    DSCParser, DependencyGraphBuilder, QueryEngine, 
    FunctionAnalyzer, MCPServer, CacheManager
)

def main():
    """Demonstrate Phase 2 query engine functionality"""
    
    print("EDK2 Navigator - Phase 2 Query Engine Demo")
    print("=" * 50)
    
    # Setup paths
    workspace_dir = os.getcwd()
    edk2_path = os.path.join(workspace_dir, "edk2")
    dsc_path = os.path.join(edk2_path, "OvmfPkg", "OvmfPkgX64.dsc")
    
    # Check if EDK2 exists
    if not os.path.exists(edk2_path):
        print(f"❌ EDK2 directory not found at: {edk2_path}")
        print("Please ensure the EDK2 repository is available in the 'edk2' directory.")
        return
    
    if not os.path.exists(dsc_path):
        print(f"❌ OVMF DSC file not found at: {dsc_path}")
        print("Please ensure OVMF package is available in EDK2.")
        return
    
    try:
        # Phase 1: Initialize core components
        print("\n1. Initializing Core Components...")
        parser = DSCParser(workspace_dir, edk2_path)
        cache_manager = CacheManager()
        graph_builder = DependencyGraphBuilder()
        function_analyzer = FunctionAnalyzer()
        
        # Phase 1: Parse DSC file
        print("2. Parsing DSC File...")
        build_flags = {
            "TARGET": "DEBUG",
            "ARCH": "X64",
            "TOOLCHAIN": "VS2019"
        }
        
        dsc_context = parser.parse_dsc(dsc_path, build_flags)
        print(f"   ✅ Parsed: {Path(dsc_context.dsc_path).name}")
        print(f"   📦 Modules found: {len(dsc_context.included_modules)}")
        print(f"   🔗 Library mappings: {len(dsc_context.library_mappings)}")
        
        # Phase 1: Build dependency graph
        print("3. Building Dependency Graph...")
        dependency_graph = graph_builder.build_from_context(dsc_context)
        print(f"   ✅ Graph nodes: {len(dependency_graph.nodes)}")
        print(f"   ➡️  Graph edges: {len(dependency_graph.edges)}")
        
        # Phase 2: Initialize query engine
        print("4. Initializing Query Engine...")
        query_engine = QueryEngine(dependency_graph)
        print("   ✅ Query engine ready")
        
        # Phase 2: Demonstrate module queries
        print("\n5. Demonstrating Module Queries...")
        modules = query_engine.get_included_modules()
        print(f"   📋 Total modules available: {len(modules)}")
        
        # Show sample modules by type
        module_types = {}
        for module in modules:
            if module.type not in module_types:
                module_types[module.type] = []
            module_types[module.type].append(module.name)
        
        print("   📊 Module types breakdown:")
        for mod_type, mod_list in sorted(module_types.items()):
            print(f"      {mod_type}: {len(mod_list)} modules")
            if len(mod_list) <= 3:
                print(f"         Examples: {', '.join(mod_list)}")
            else:
                print(f"         Examples: {', '.join(mod_list[:3])}...")
        
        # Phase 2: Demonstrate function search
        print("\n6. Demonstrating Function Search...")
        
        # Try to find some common EDK2 functions
        test_functions = [
            "UefiMain",
            "InitializeDriver", 
            "DriverEntry",
            "PlatformPei",
            "MemoryDiscoveredPpiNotifyCallback"
        ]
        
        for func_name in test_functions:
            try:
                print(f"   🔍 Searching for function: {func_name}")
                locations = query_engine.find_function(func_name, dsc_context)
                
                if locations:
                    print(f"      ✅ Found {len(locations)} location(s)")
                    for i, loc in enumerate(locations[:3]):  # Show first 3
                        status = "📝 Definition" if loc.is_definition else "📄 Declaration"
                        print(f"         {i+1}. {status} in {Path(loc.file_path).name}:{loc.line_number}")
                        print(f"            Module: {loc.module_name}")
                        print(f"            Signature: {loc.function_signature[:80]}...")
                    
                    if len(locations) > 3:
                        print(f"         ... and {len(locations) - 3} more")
                else:
                    print(f"      ❌ Function not found")
                
                break  # Found at least one function, stop searching
                
            except Exception as e:
                print(f"      ❌ Error searching for {func_name}: {e}")
                continue
        
        # Phase 2: Demonstrate dependency analysis
        print("\n7. Demonstrating Dependency Analysis...")
        
        # Find a module to analyze
        sample_module = None
        for module in modules:
            if module.type == "DXE_DRIVER" and len(module.dependencies) > 0:
                sample_module = module
                break
        
        if sample_module:
            print(f"   🔍 Analyzing module: {sample_module.name}")
            try:
                deps = query_engine.get_module_dependencies(sample_module.name, dsc_context)
                print(f"      📦 Module path: {deps.module_path}")
                print(f"      ⬇️  Direct dependencies: {len(deps.direct_dependencies)}")
                if deps.direct_dependencies:
                    for dep in deps.direct_dependencies[:5]:  # Show first 5
                        print(f"         - {dep}")
                    if len(deps.direct_dependencies) > 5:
                        print(f"         ... and {len(deps.direct_dependencies) - 5} more")
                
                print(f"      ⬆️  Dependents: {len(deps.dependents)}")
                if deps.dependents:
                    for dep in deps.dependents[:3]:  # Show first 3
                        print(f"         - {dep}")
                
            except Exception as e:
                print(f"      ❌ Error analyzing dependencies: {e}")
        else:
            print("   ❌ No suitable module found for dependency analysis")
        
        # Phase 2: Demonstrate MCP Server capabilities
        print("\n8. Demonstrating MCP Server...")
        mcp_server = MCPServer(workspace_dir, edk2_path)
        
        # Parse DSC through MCP server
        parse_result = mcp_server.handle_tool_call("parse_dsc", {
            "dsc_path": dsc_path,
            "build_flags": build_flags
        })
        
        if parse_result.get("success"):
            print("   ✅ MCP Server initialized successfully")
            print(f"      📦 Modules: {parse_result['modules_found']}")
            print(f"      🔗 Libraries: {parse_result['library_mappings']}")
            print(f"      🏗️  Architecture: {parse_result['architecture']}")
            
            # Test MCP tools
            print("   🛠️  Testing MCP tools:")
            
            # Test get_included_modules
            modules_result = mcp_server.handle_tool_call("get_included_modules", {
                "filter_by_type": "DXE_DRIVER",
                "include_details": False
            })
            
            if modules_result.get("success"):
                print(f"      ✅ DXE_DRIVER modules: {modules_result['count']}")
            
            # Test get_build_statistics
            stats_result = mcp_server.handle_tool_call("get_build_statistics", {})
            
            if stats_result.get("success"):
                print(f"      📊 Build statistics:")
                print(f"         Total modules: {stats_result['total_modules']}")
                print(f"         Source files: {stats_result['total_source_files']}")
                print(f"         Module types: {len(stats_result['module_types'])}")
        else:
            print(f"   ❌ MCP Server initialization failed: {parse_result.get('error')}")
        
        # Phase 2: Performance summary
        print("\n9. Performance Summary...")
        cache_stats = cache_manager.get_cache_stats()
        print(f"   💾 Cache directory: {cache_stats['cache_dir']}")
        print(f"   📁 Cache files: {cache_stats['file_count']}")
        print(f"   💿 Cache size: {cache_stats['total_size_mb']:.2f} MB")
        
        print(f"\n✅ Phase 2 Demo completed successfully!")
        print(f"🎯 Key capabilities demonstrated:")
        print(f"   - DSC parsing and module discovery")
        print(f"   - Function search across build-relevant code")
        print(f"   - Module dependency analysis")
        print(f"   - MCP server integration for LLM workflows")
        print(f"   - Caching for performance optimization")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
