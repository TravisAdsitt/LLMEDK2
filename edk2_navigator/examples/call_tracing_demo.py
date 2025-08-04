"""
Call Tracing Demo - Demonstrates function call tracing capabilities
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
    """Demonstrate function call tracing capabilities"""
    
    print("EDK2 Navigator - Function Call Tracing Demo")
    print("=" * 60)
    
    # Setup paths
    workspace_dir = os.getcwd()
    edk2_path = os.path.join(workspace_dir, "edk2")
    dsc_path = os.path.join(edk2_path, "OvmfPkg", "OvmfPkgX64.dsc")
    
    # Check if EDK2 exists
    if not os.path.exists(edk2_path):
        print(f"❌ EDK2 directory not found at: {edk2_path}")
        return 1
    
    if not os.path.exists(dsc_path):
        print(f"❌ OVMF DSC file not found at: {dsc_path}")
        return 1
    
    try:
        # Initialize components
        print("\n1. Initializing Components...")
        parser = DSCParser(workspace_dir, edk2_path)
        cache_manager = CacheManager()
        graph_builder = DependencyGraphBuilder()
        function_analyzer = FunctionAnalyzer()
        
        # Parse DSC file
        print("2. Parsing DSC File...")
        build_flags = {
            "TARGET": "DEBUG",
            "ARCH": "X64",
            "TOOLCHAIN": "VS2019"
        }
        
        dsc_context = parser.parse_dsc(dsc_path, build_flags)
        print(f"   ✅ Parsed: {Path(dsc_context.dsc_path).name}")
        print(f"   📦 Modules found: {len(dsc_context.included_modules)}")
        
        # Build dependency graph
        print("3. Building Dependency Graph...")
        dependency_graph = graph_builder.build_from_context(dsc_context)
        
        # Initialize query engine
        print("4. Initializing Query Engine...")
        query_engine = QueryEngine(dependency_graph)
        
        # Demonstrate function call tracing
        print("\n" + "=" * 60)
        print("FUNCTION CALL TRACING DEMONSTRATION")
        print("=" * 60)
        
        # Find some interesting functions to trace
        print("\n5. Finding Functions to Trace...")
        
        # Look for common EDK2 entry points and key functions
        interesting_functions = [
            "DriverEntry",
            "UefiMain", 
            "InitializeDriver",
            "PlatformPei",
            "MemoryDiscoveredPpiNotifyCallback",
            "ProcessFirmwareVolume",
            "InstallProtocolInterface",
            "LocateProtocol"
        ]
        
        found_functions = []
        for func_name in interesting_functions:
            try:
                locations = query_engine.find_function(func_name, dsc_context)
                if locations:
                    found_functions.append((func_name, locations))
                    print(f"   ✅ Found: {func_name} ({len(locations)} location(s))")
                    break  # Just demonstrate with first found function
            except Exception:
                continue
        
        if not found_functions:
            print("   ❌ No interesting functions found for tracing")
            return 1
        
        # Demonstrate call tracing for the first found function
        target_function, locations = found_functions[0]
        print(f"\n6. Tracing Calls for Function: {target_function}")
        print("-" * 40)
        
        # Show function definitions
        print(f"   📍 Function Definitions:")
        for i, loc in enumerate(locations[:3], 1):  # Show first 3
            status = "🔧 Definition" if loc.is_definition else "📋 Declaration"
            print(f"      {i}. {status}")
            print(f"         File: {Path(loc.file_path).name}")
            print(f"         Line: {loc.line_number}")
            print(f"         Module: {loc.module_name}")
            print(f"         Signature: {loc.function_signature[:100]}...")
            if loc.calling_convention:
                print(f"         Convention: {loc.calling_convention}")
        
        # Trace call paths
        print(f"\n   🔍 Tracing Call Paths...")
        try:
            call_paths = query_engine.trace_call_path(target_function, dsc_context, max_depth=3)
            
            if call_paths:
                print(f"      ✅ Found {len(call_paths)} call path(s)")
                
                for i, path in enumerate(call_paths[:5], 1):  # Show first 5
                    print(f"      {i}. Call Path:")
                    print(f"         Caller: {path.caller_function}")
                    print(f"         Called: {path.called_function}")
                    print(f"         File: {Path(path.file_path).name}:{path.line_number}")
                    print(f"         Chain: {' → '.join(path.call_chain)}")
                
                if len(call_paths) > 5:
                    print(f"         ... and {len(call_paths) - 5} more call paths")
            else:
                print(f"      ℹ️  No call paths found (function may be entry point)")
        
        except Exception as e:
            print(f"      ❌ Error tracing calls: {e}")
        
        # Demonstrate detailed function analysis
        print(f"\n7. Detailed Function Analysis...")
        print("-" * 40)
        
        # Analyze a specific source file for detailed call information
        sample_location = locations[0] if locations else None
        if sample_location and sample_location.is_definition:
            print(f"   🔬 Analyzing file: {Path(sample_location.file_path).name}")
            
            try:
                analysis = function_analyzer.analyze_source_file(sample_location.file_path)
                
                print(f"      📊 Analysis Results:")
                print(f"         Definitions: {len(analysis['definitions'])}")
                print(f"         Declarations: {len(analysis['declarations'])}")
                print(f"         Function Calls: {len(analysis['calls'])}")
                
                # Show function definitions in this file
                if analysis['definitions']:
                    print(f"      🔧 Function Definitions:")
                    for i, defn in enumerate(analysis['definitions'][:3], 1):
                        print(f"         {i}. {defn.name}")
                        print(f"            Return Type: {defn.return_type}")
                        print(f"            Parameters: {len(defn.parameters)}")
                        print(f"            Lines: {defn.line_number}-{defn.end_line_number}")
                        if defn.calling_convention:
                            print(f"            Convention: {defn.calling_convention}")
                        if defn.is_static:
                            print(f"            Scope: STATIC")
                
                # Show function calls made from this file
                if analysis['calls']:
                    print(f"      📞 Function Calls Made:")
                    call_summary = {}
                    for call in analysis['calls']:
                        caller = call.caller_function
                        if caller not in call_summary:
                            call_summary[caller] = []
                        call_summary[caller].append(call.called_function)
                    
                    for caller, callees in list(call_summary.items())[:3]:
                        unique_callees = list(set(callees))
                        print(f"         {caller} calls:")
                        for callee in unique_callees[:5]:
                            count = callees.count(callee)
                            print(f"           - {callee} ({count}x)")
                        if len(unique_callees) > 5:
                            print(f"           ... and {len(unique_callees) - 5} more")
            
            except Exception as e:
                print(f"      ❌ Error analyzing file: {e}")
        
        # Demonstrate MCP server call tracing tools
        print(f"\n8. MCP Server Call Tracing Tools...")
        print("-" * 40)
        
        mcp_server = MCPServer(workspace_dir, edk2_path)
        
        # Parse DSC through MCP server
        parse_result = mcp_server.handle_tool_call("parse_dsc", {
            "dsc_path": dsc_path,
            "build_flags": build_flags
        })
        
        if parse_result.get("success"):
            print("   ✅ MCP Server initialized")
            
            # Test trace_call_path tool
            print("   🔍 Testing trace_call_path tool:")
            trace_result = mcp_server.handle_tool_call("trace_call_path", {
                "function_name": target_function,
                "max_depth": 3
            })
            
            if trace_result.get("success"):
                paths = trace_result.get("call_paths", [])
                print(f"      ✅ Found {len(paths)} call paths via MCP")
                
                for i, path in enumerate(paths[:3], 1):
                    print(f"         {i}. {path.get('caller_function')} → {path.get('called_function')}")
                    print(f"            File: {Path(path.get('file_path', '')).name}")
            else:
                print(f"      ❌ MCP trace failed: {trace_result.get('error')}")
            
            # Test find_function tool
            print("   🔍 Testing find_function tool:")
            find_result = mcp_server.handle_tool_call("find_function", {
                "function_name": target_function,
                "include_declarations": True
            })
            
            if find_result.get("success"):
                locations = find_result.get("locations", [])
                print(f"      ✅ Found {len(locations)} locations via MCP")
                
                for i, loc in enumerate(locations[:2], 1):
                    loc_type = "Definition" if loc.get("is_definition") else "Declaration"
                    print(f"         {i}. {loc_type} in {Path(loc.get('file_path', '')).name}:{loc.get('line_number')}")
            else:
                print(f"      ❌ MCP find failed: {find_result.get('error')}")
        
        else:
            print(f"   ❌ MCP Server initialization failed: {parse_result.get('error')}")
        
        # Summary
        print(f"\n" + "=" * 60)
        print("CALL TRACING CAPABILITIES SUMMARY")
        print("=" * 60)
        
        print(f"✅ Function Discovery:")
        print(f"   - Find function definitions and declarations")
        print(f"   - Parse function signatures and parameters")
        print(f"   - Identify calling conventions (EFIAPI, etc.)")
        
        print(f"\n✅ Call Path Tracing:")
        print(f"   - Trace who calls a specific function")
        print(f"   - Build call chains and dependency paths")
        print(f"   - Identify call contexts and locations")
        
        print(f"\n✅ Advanced Analysis:")
        print(f"   - Detailed source file analysis")
        print(f"   - Function complexity metrics")
        print(f"   - Call graph construction")
        print(f"   - Recursive call detection")
        
        print(f"\n✅ MCP Integration:")
        print(f"   - trace_call_path tool for LLM workflows")
        print(f"   - find_function tool with rich metadata")
        print(f"   - Integration with build context")
        
        print(f"\n🎯 Use Cases:")
        print(f"   - Understanding firmware boot flow")
        print(f"   - Tracing protocol implementations")
        print(f"   - Finding function dependencies")
        print(f"   - Code navigation and exploration")
        print(f"   - Impact analysis for changes")
        
        print(f"\n✅ Call Tracing Demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
