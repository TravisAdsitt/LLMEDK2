"""
Showcase the real DSC parsing capabilities
"""
import sys
from pathlib import Path

# Add edk2_navigator to path
sys.path.insert(0, str(Path(__file__).parent))

from edk2_navigator import DSCParser

def main():
    print("🚀 EDK2 Navigator - Real DSC Parsing Showcase")
    print("=" * 60)
    
    # Setup paths
    workspace_dir = Path.cwd()
    edk2_path = workspace_dir / "edk2"
    dsc_path = edk2_path / "RedfishPkg" / "RedfishPkg.dsc"
    
    print(f"📁 Parsing: {dsc_path.name}")
    print(f"🏗️  Workspace: {workspace_dir}")
    print()
    
    # Parse DSC file
    parser = DSCParser(str(workspace_dir), str(edk2_path))
    context = parser.parse_dsc(str(dsc_path))
    
    print("✅ DSC Parsing Results:")
    print(f"   📦 Platform: {context.preprocessor_definitions.get('PLATFORM_NAME', 'Unknown')}")
    print(f"   🏗️  Architecture: {context.architecture}")
    print(f"   🎯 Build Target: {context.build_target}")
    print(f"   🔧 Toolchain: {context.toolchain}")
    print(f"   📊 Total Modules: {len(context.included_modules)}")
    print(f"   📚 Library Mappings: {len(context.library_mappings)}")
    print(f"   ⚙️  Preprocessor Definitions: {len(context.preprocessor_definitions)}")
    print()
    
    # Show module breakdown by type
    print("📋 Module Breakdown by Type:")
    module_types = {}
    for module in context.included_modules:
        module_type = module.type
        if module_type not in module_types:
            module_types[module_type] = []
        module_types[module_type].append(module)
    
    for module_type, modules in sorted(module_types.items()):
        print(f"   {module_type:20} : {len(modules):3d} modules")
    print()
    
    # Show some interesting modules
    print("🔍 Sample Modules:")
    interesting_modules = [
        ("SEC", "Security Phase"),
        ("PEI_CORE", "PEI Core"),
        ("DXE_CORE", "DXE Core"),
        ("DXE_DRIVER", "DXE Driver"),
        ("DXE_RUNTIME_DRIVER", "Runtime Driver"),
        ("UEFI_DRIVER", "UEFI Driver"),
        ("UEFI_APPLICATION", "UEFI Application")
    ]
    
    for module_type, description in interesting_modules:
        modules_of_type = [m for m in context.included_modules if m.type == module_type]
        if modules_of_type:
            module = modules_of_type[0]  # Show first one
            print(f"   {description:20} : {module.name}")
            print(f"   {'':20}   Path: {module.path}")
            print(f"   {'':20}   GUID: {module.guid}")
            print(f"   {'':20}   Dependencies: {len(module.dependencies)}")
            if module.dependencies:
                deps_sample = module.dependencies[:3]
                deps_str = ", ".join(deps_sample)
                if len(module.dependencies) > 3:
                    deps_str += f" (and {len(module.dependencies) - 3} more)"
                print(f"   {'':20}   Sample deps: {deps_str}")
            print()
    
    # Show library class mappings
    print("📚 Sample Library Class Mappings:")
    sample_libs = list(context.library_mappings.items())[:5]
    for lib_class, implementation in sample_libs:
        print(f"   {lib_class:25} → {implementation}")
    print()
    
    # Show preprocessor definitions
    print("⚙️  Key Preprocessor Definitions:")
    key_defines = ['PLATFORM_NAME', 'PLATFORM_GUID', 'SUPPORTED_ARCHITECTURES', 'BUILD_TARGETS']
    for key in key_defines:
        if key in context.preprocessor_definitions:
            value = context.preprocessor_definitions[key]
            print(f"   {key:25} = {value}")
    print()
    
    print("🎉 Parsing completed successfully!")
    print(f"💾 Results cached for future use")
    print()
    print("🚀 Next Steps:")
    print("   1. ✅ DSC parsing with real module extraction")
    print("   2. 🔄 Dependency graph construction")
    print("   3. 🎯 Function analysis and search")
    print("   4. 🤖 MCP server for LLM integration")
    print("   5. 🧠 Semantic search capabilities")

if __name__ == "__main__":
    main()
