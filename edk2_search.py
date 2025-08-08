#!/usr/bin/env python3
"""
EDK2 DSC Search Tool

A code-aware search tool that parses EDK2 DSC files using native BaseTools,
builds an index of all referenced modules, libraries, and packages, and
provides search capabilities with relationship graph generation.
"""

import os
import sys
import argparse
import json
import re
import logging
from pathlib import Path
from collections import defaultdict
import pickle
import hashlib
from datetime import datetime

# Add vendor/edk2 BaseTools to Python path
SCRIPT_DIR = Path(__file__).parent.absolute()
EDK2_DIR = SCRIPT_DIR / "vendor" / "edk2"
BASETOOLS_PYTHON = EDK2_DIR / "BaseTools" / "Source" / "Python"

if BASETOOLS_PYTHON.exists():
    sys.path.insert(0, str(BASETOOLS_PYTHON))
    sys.path.insert(0, str(BASETOOLS_PYTHON / "Common"))
else:
    print(f"Error: EDK2 BaseTools not found at {BASETOOLS_PYTHON}")
    print("Please run: git clone --depth 1 https://github.com/tianocore/edk2.git vendor/edk2")
    sys.exit(1)

# Import BaseTools modules
try:
    from Workspace.WorkspaceDatabase import WorkspaceDatabase
    from Workspace.DscBuildData import DscBuildData
    from Workspace.DecBuildData import DecBuildData
    from Workspace.InfBuildData import InfBuildData
    from Common.Misc import PathClass
    import Common.GlobalData as GlobalData
    from Common.DataType import *
except ImportError as e:
    print(f"Error importing BaseTools modules: {e}")
    print("Make sure EDK2 BaseTools are properly installed")
    sys.exit(1)


class EDK2SearchIndex:
    """Manages the searchable index of EDK2 components"""
    
    def __init__(self, workspace_dir=None, packages_path=None, arch="X64"):
        self.workspace_dir = Path(workspace_dir or os.getcwd()).absolute()
        self.packages_path = packages_path or str(self.workspace_dir)
        self.arch = arch
        self.index = {
            'modules': {},      # module_path -> module_info
            'libraries': {},    # library_path -> library_info
            'packages': {},     # package_path -> package_info
            'relationships': defaultdict(list),  # component -> [dependencies]
            'reverse_relationships': defaultdict(list),  # component -> [dependents]
            'files': defaultdict(set),  # component -> set of source files
        }
        self.dsc_info = {}
        self._setup_environment()
        
    def _setup_environment(self):
        """Setup EDK2 environment variables"""
        workspace_str = str(self.workspace_dir)
        packages_path_str = self.packages_path or workspace_str
        
        # Create cache directory if it doesn't exist
        cache_dir = Path(".cache")
        cache_dir.mkdir(exist_ok=True)
        
        # Set environment variables
        os.environ["WORKSPACE"] = workspace_str
        os.environ["PACKAGES_PATH"] = packages_path_str
        os.environ["TARGET"] = "RELEASE"
        os.environ["TARGET_ARCH"] = self.arch
        os.environ["TOOL_CHAIN_TAG"] = "VS2019"
        
        # Initialize GlobalData properly
        GlobalData.gWorkspace = workspace_str
        GlobalData.gGlobalDefines = {
            'WORKSPACE': workspace_str,
            'PACKAGES_PATH': packages_path_str,
            'ARCH': self.arch,
            'TARGET': 'RELEASE',
            'TOOL_CHAIN_TAG': 'VS2019',
            'TARGET_ARCH': self.arch
        }
        GlobalData.gCommandLineDefines = {}
        GlobalData.gPlatformDefines = {}
        
        # Initialize MultipleWorkspace PACKAGES_PATH
        try:
            from Common.MultipleWorkspace import MultipleWorkspace
            # Set up packages path as a list
            packages_list = [workspace_str]
            if packages_path_str != workspace_str:
                packages_list.extend(packages_path_str.split(';' if os.name == 'nt' else ':'))
            
            MultipleWorkspace.PACKAGES_PATH = packages_list
            
            # Also set the class variable directly if it exists
            if hasattr(MultipleWorkspace, '_PACKAGES_PATH'):
                MultipleWorkspace._PACKAGES_PATH = packages_list
                
        except ImportError:
            pass
        
    def parse_dsc(self, dsc_path, macros=None):
        """Parse a DSC file using BaseTools"""
        dsc_path = Path(dsc_path).absolute()
        if not dsc_path.exists():
            raise FileNotFoundError(f"DSC file not found: {dsc_path}")
            
        print(f"Parsing DSC: {dsc_path}")
        
        # Set up macros
        if macros:
            for key, value in macros.items():
                GlobalData.gCommandLineDefines[key] = value
        
        # Create workspace database
        workspace_db = WorkspaceDatabase()
        
        # Parse DSC file
        dsc_file = PathClass(str(dsc_path), str(self.workspace_dir))
        platform = workspace_db.BuildObject[dsc_file, self.arch, "RELEASE", "VS2019"]
        
        if not platform:
            raise ValueError(f"Failed to parse DSC file: {dsc_path}")
            
        self.dsc_info = {
            'path': str(dsc_path),
            'name': platform.PlatformName,
            'guid': platform.Guid,
            'version': platform.Version,
            'arch': self.arch,
        }
        
        # Index modules with progress saving
        print(f"Indexing modules from {platform.PlatformName}...")
        module_count = 0
        total_modules = len(platform.Modules)
        
        for module_path, module_info in platform.Modules.items():
            self._index_module(workspace_db, module_path, module_info)
            module_count += 1
            
            # Save progress every 50 modules
            if module_count % 50 == 0:
                print(f"  Processed {module_count}/{total_modules} modules...")
                self._save_progress_cache()
            
        # Index libraries with progress saving
        print(f"Indexing libraries...")
        try:
            # Handle different types of LibraryClasses containers
            if hasattr(platform.LibraryClasses, 'items'):
                lib_items = platform.LibraryClasses.items()
            elif hasattr(platform.LibraryClasses, 'keys'):
                # For tdict or other container types, use keys() method
                lib_items = []
                for lib_class in platform.LibraryClasses.keys():
                    # Skip None or empty library class names
                    if lib_class is None or lib_class == '':
                        continue
                    print(f"Processing library class: {lib_class}", flush=True)
                    lib_info = platform.LibraryClasses[lib_class]
                    # Skip if library info is also None
                    if lib_info is None:
                        continue
                    lib_items.append((lib_class, lib_info))
            else:
                # If no standard iteration methods work, try to inspect the object
                print(f"LibraryClasses type: {type(platform.LibraryClasses)}")
                print(f"LibraryClasses dir: {[attr for attr in dir(platform.LibraryClasses) if not attr.startswith('_')]}")
                lib_items = []
                # Try to get all attributes that might be library classes
                if hasattr(platform.LibraryClasses, 'GetKeys'):
                    
                    for attr_name, attr_value in platform.LibraryClasses.__dict__.items():
                        if not attr_name.startswith('_') and attr_value is not None:
                            print(f"Processing library class: {attr_name}", flush=True)
                            lib_items.append((attr_name, attr_value))
            
            lib_count = 0
            start_time = datetime.now()
            last_time = start_time
            
            logging.info(f"Found {len(lib_items)} library classes to process")
            
            for i, (lib_class, lib_info) in enumerate(lib_items):
                current_time = datetime.now()
                logging.debug(f"Processing library class {i+1}/{len(lib_items)}: {lib_class}")
                
                if isinstance(lib_info, dict):
                    logging.debug(f"Library class {lib_class} has {len(lib_info)} module types")
                    for module_type, lib_path in lib_info.items():
                        logging.debug(f"Indexing {module_type}: {lib_path}")
                        self._index_library(workspace_db, lib_path, lib_class)
                        lib_count += 1
                else:
                    logging.debug(f"Indexing single library: {lib_info}")
                    self._index_library(workspace_db, lib_info, lib_class)
                    lib_count += 1
                    
                # Show timing for slow library classes
                class_time = datetime.now() - current_time
                if class_time.total_seconds() > 1.0:
                    logging.info(f"Library class {lib_class} took {class_time.total_seconds():.2f} seconds")
                    
                # Save progress every 5 library classes
                if (i + 1) % 5 == 0:
                    elapsed = datetime.now() - start_time
                    recent_elapsed = datetime.now() - last_time
                    print(f"  Processed {i+1}/{len(lib_items)} library classes ({lib_count} total libraries) "
                          f"in {elapsed.total_seconds():.2f} seconds total, "
                          f"last 5 classes took {recent_elapsed.total_seconds():.2f} seconds", flush=True)
                    self._save_progress_cache()
                    last_time = datetime.now()
                    
        except Exception as e:
            print(f"Warning: Could not index libraries: {e}")
                
        # Index packages
        print(f"Indexing packages...")
        for package in platform.Packages:
            self._index_package(workspace_db, package)
            
        print(f"Index complete: {len(self.index['modules'])} modules, "
              f"{len(self.index['libraries'])} libraries, "
              f"{len(self.index['packages'])} packages")
        
        return self.index
        
    def _index_module(self, workspace_db, module_path, module_info):
        """Index a module and its relationships"""
        module_key = str(module_path)
        
        if module_key in self.index['modules']:
            return
            
        # Get module build data
        module_data = workspace_db.BuildObject[module_path, self.arch, "RELEASE", "VS2019"]
        
        if not module_data:
            return
            
        self.index['modules'][module_key] = {
            'path': module_key,
            'name': module_data.BaseName if hasattr(module_data, 'BaseName') else Path(module_key).stem,
            'guid': module_info.Guid if module_info else None,
            'module_type': module_data.ModuleType if hasattr(module_data, 'ModuleType') else None,
            'sources': [],
            'libraries': [],
            'packages': [],
        }
        
        # Index source files
        if hasattr(module_data, 'Sources'):
            for source in module_data.Sources:
                source_path = str(source)
                self.index['modules'][module_key]['sources'].append(source_path)
                self.index['files'][source_path].add(module_key)
                
        # Index library dependencies
        if hasattr(module_data, 'LibraryClasses'):
            for lib_class in module_data.LibraryClasses:
                self.index['modules'][module_key]['libraries'].append(lib_class)
                self.index['relationships'][module_key].append(('library', lib_class))
                self.index['reverse_relationships'][lib_class].append(('module', module_key))
                
        # Index package dependencies
        if hasattr(module_data, 'Packages'):
            for package in module_data.Packages:
                package_key = str(package.MetaFile)
                self.index['modules'][module_key]['packages'].append(package_key)
                self.index['relationships'][module_key].append(('package', package_key))
                self.index['reverse_relationships'][package_key].append(('module', module_key))
                
    def _index_library(self, workspace_db, library_path, library_class):
        """Index a library and its relationships"""
        library_key = str(library_path)
        
        if library_key in self.index['libraries']:
            logging.debug(f"Library {library_key} already indexed, skipping")
            return
            
        logging.debug(f"Starting to index library: {library_key} (class: {library_class})")
        
        try:
            # Get library build data with error handling
            start_time = datetime.now()
            
            # Validate library_path before attempting to access BuildObject
            if not library_path or library_path == '':
                logging.debug(f"Empty library path for class {library_class}, skipping")
                return
                
            # Check if library_path is a tdict object and extract the PathClass object
            if (hasattr(library_path, '__class__') and 
                ('tdict' in str(type(library_path)) or 'tdict' in str(library_path))):
                
                # Extract PathClass object from tdict.data
                try:
                    if hasattr(library_path, 'data') and isinstance(library_path.data, dict):
                        # Get the first available PathClass object (typically 'BASE' module type)
                        for module_type, path_obj in library_path.data.items():
                            if hasattr(path_obj, 'Path') or hasattr(path_obj, 'File'):
                                library_path = path_obj
                                library_key = str(library_path)
                                break
                        else:
                            # No valid PathClass found, skip this library
                            logging.debug(f"No valid PathClass found in tdict for library class {library_class}")
                            return
                    else:
                        # Unexpected tdict structure, skip this library
                        logging.debug(f"Unexpected tdict structure for library class {library_class}")
                        return
                except Exception as e:
                    logging.warning(f"Error extracting PathClass from tdict for library class {library_class}: {e}")
                    return
                    
            library_data = workspace_db.BuildObject[library_path, self.arch, "RELEASE", "VS2019"]
            build_time = datetime.now() - start_time
            
            if build_time.total_seconds() > 0.5:
                logging.info(f"BuildObject for {library_key} took {build_time.total_seconds():.2f} seconds")
            
            if not library_data:
                logging.debug(f"No build data found for library: {library_key}")
                return
                
        except Exception as e:
            logging.warning(f"Failed to get build data for library {library_key} (class: {library_class}): {e}")
            return
            
        try:
            self.index['libraries'][library_key] = {
                'path': library_key,
                'name': library_data.BaseName if hasattr(library_data, 'BaseName') else Path(library_key).stem,
                'class': str(library_class),
                'sources': [],
                'packages': [],
            }
            
            # Index source files with error handling
            if hasattr(library_data, 'Sources'):
                try:
                    for source in library_data.Sources:
                        source_path = str(source)
                        self.index['libraries'][library_key]['sources'].append(source_path)
                        self.index['files'][source_path].add(library_key)
                except Exception as e:
                    logging.debug(f"Error indexing sources for library {library_key}: {e}")
                    
            # Index package dependencies with error handling
            if hasattr(library_data, 'Packages'):
                try:
                    for package in library_data.Packages:
                        package_key = str(package.MetaFile)
                        self.index['libraries'][library_key]['packages'].append(package_key)
                        self.index['relationships'][library_key].append(('package', package_key))
                        self.index['reverse_relationships'][package_key].append(('library', library_key))
                except Exception as e:
                    logging.debug(f"Error indexing packages for library {library_key}: {e}")
                    
        except Exception as e:
            logging.warning(f"Error creating library index entry for {library_key}: {e}")
            return
                
    def _index_package(self, workspace_db, package):
        """Index a package"""
        package_key = str(package.MetaFile)
        
        if package_key in self.index['packages']:
            return
            
        self.index['packages'][package_key] = {
            'path': package_key,
            'name': package.PackageName if hasattr(package, 'PackageName') else Path(package_key).stem,
            'guid': package.Guid if hasattr(package, 'Guid') else None,
            'version': package.Version if hasattr(package, 'Version') else None,
            'includes': [],
            'libraries': [],
            'modules': [],
        }
        
        # Track which libraries and modules use this package
        for lib_key, lib_deps in self.index['relationships'].items():
            if ('package', package_key) in lib_deps:
                if lib_key in self.index['libraries']:
                    self.index['packages'][package_key]['libraries'].append(lib_key)
                elif lib_key in self.index['modules']:
                    self.index['packages'][package_key]['modules'].append(lib_key)
                    
    def search(self, query, search_type='all'):
        """
        Search the index for keywords or filenames
        
        Args:
            query: Search query (keyword or filename)
            search_type: Type of search ('all', 'modules', 'libraries', 'packages', 'files')
        
        Returns:
            List of matching items with their information
        """
        results = []
        query_lower = query.lower()
        
        # Search modules
        if search_type in ['all', 'modules']:
            for module_key, module_info in self.index['modules'].items():
                if (query_lower in module_info['name'].lower() or
                    query_lower in module_key.lower() or
                    any(query_lower in src.lower() for src in module_info['sources'])):
                    results.append({
                        'type': 'module',
                        'path': module_key,
                        'info': module_info
                    })
                    
        # Search libraries
        if search_type in ['all', 'libraries']:
            for lib_key, lib_info in self.index['libraries'].items():
                if (query_lower in lib_info['name'].lower() or
                    query_lower in lib_key.lower() or
                    query_lower in lib_info['class'].lower() or
                    any(query_lower in src.lower() for src in lib_info['sources'])):
                    results.append({
                        'type': 'library',
                        'path': lib_key,
                        'info': lib_info
                    })
                    
        # Search packages
        if search_type in ['all', 'packages']:
            for pkg_key, pkg_info in self.index['packages'].items():
                if (query_lower in pkg_info['name'].lower() or
                    query_lower in pkg_key.lower()):
                    results.append({
                        'type': 'package',
                        'path': pkg_key,
                        'info': pkg_info
                    })
                    
        # Search files
        if search_type in ['all', 'files']:
            for file_path, components in self.index['files'].items():
                if query_lower in file_path.lower():
                    results.append({
                        'type': 'file',
                        'path': file_path,
                        'used_by': list(components)
                    })
                    
        return results
        
    def generate_graph(self, output_path='dependency_graph.dot', component=None):
        """
        Generate a Graphviz DOT file of the dependency relationships
        
        Args:
            output_path: Path to save the DOT file
            component: Optional specific component to graph (None for all)
        """
        dot_lines = ['digraph Dependencies {']
        dot_lines.append('  rankdir=LR;')
        dot_lines.append('  node [shape=box];')
        dot_lines.append('')
        
        # Define node styles
        dot_lines.append('  // Node styles')
        dot_lines.append('  node [shape=box, style=filled];')
        dot_lines.append('')
        
        # Track nodes to add
        nodes_to_add = set()
        edges_to_add = []
        
        if component:
            # Graph specific component and its dependencies
            self._collect_component_graph(component, nodes_to_add, edges_to_add)
        else:
            # Graph all relationships
            for source, targets in self.index['relationships'].items():
                nodes_to_add.add(source)
                for target_type, target in targets:
                    nodes_to_add.add(target)
                    edges_to_add.append((source, target))
                    
        # Add nodes with appropriate styling
        dot_lines.append('  // Nodes')
        for node in nodes_to_add:
            node_id = self._sanitize_dot_id(node)
            node_label = Path(node).name if '/' in node or '\\' in node else node
            
            if node in self.index['modules']:
                color = 'lightblue'
                shape = 'box'
            elif node in self.index['libraries']:
                color = 'lightgreen'
                shape = 'box'
            elif node in self.index['packages']:
                color = 'lightyellow'
                shape = 'box3d'
            else:
                color = 'lightgray'
                shape = 'ellipse'
                
            dot_lines.append(f'  "{node_id}" [label="{node_label}", fillcolor={color}, shape={shape}];')
            
        dot_lines.append('')
        dot_lines.append('  // Edges')
        
        # Add edges
        for source, target in edges_to_add:
            source_id = self._sanitize_dot_id(source)
            target_id = self._sanitize_dot_id(target)
            dot_lines.append(f'  "{source_id}" -> "{target_id}";')
            
        dot_lines.append('}')
        
        # Write DOT file
        output_path = Path(output_path)
        output_path.write_text('\n'.join(dot_lines))
        print(f"Dependency graph saved to: {output_path}")
        
        return output_path
        
    def _collect_component_graph(self, component, nodes, edges, visited=None):
        """Recursively collect nodes and edges for a component"""
        if visited is None:
            visited = set()
            
        if component in visited:
            return
            
        visited.add(component)
        nodes.add(component)
        
        # Add dependencies
        if component in self.index['relationships']:
            for dep_type, dep in self.index['relationships'][component]:
                nodes.add(dep)
                edges.append((component, dep))
                self._collect_component_graph(dep, nodes, edges, visited)
                
        # Add dependents
        if component in self.index['reverse_relationships']:
            for dep_type, dep in self.index['reverse_relationships'][component]:
                nodes.add(dep)
                edges.append((dep, component))
                self._collect_component_graph(dep, nodes, edges, visited)
                
    def _sanitize_dot_id(self, text):
        """Sanitize text for use as a DOT node ID"""
        # Replace problematic characters
        text = text.replace('\\', '/')
        text = text.replace('"', '\\"')
        return text
        
    def _save_progress_cache(self):
        """Save progress cache during parsing"""
        if not self.dsc_info:
            return
            
        # Generate progress cache filename
        dsc_hash = hashlib.md5(self.dsc_info.get('path', '').encode()).hexdigest()[:8]
        progress_cache_path = Path(f".edk2_search_progress_{dsc_hash}.pkl")
        
        try:
            with open(progress_cache_path, 'wb') as f:
                pickle.dump({
                    'dsc_info': self.dsc_info,
                    'index': self.index
                }, f)
        except Exception as e:
            print(f"Warning: Could not save progress cache: {e}")
    
    def save_cache(self, cache_path=None):
        """Save the index to a cache file"""
        if cache_path is None:
            # Generate cache filename based on DSC
            dsc_hash = hashlib.md5(self.dsc_info.get('path', '').encode()).hexdigest()[:8]
            cache_path = Path(f".edk2_search_cache_{dsc_hash}.pkl")
            
        with open(cache_path, 'wb') as f:
            pickle.dump({
                'dsc_info': self.dsc_info,
                'index': self.index
            }, f)
            
        print(f"Cache saved to: {cache_path}")
        
        # Clean up progress cache if it exists
        dsc_hash = hashlib.md5(self.dsc_info.get('path', '').encode()).hexdigest()[:8]
        progress_cache_path = Path(f".edk2_search_progress_{dsc_hash}.pkl")
        if progress_cache_path.exists():
            progress_cache_path.unlink()
            
        return cache_path
        
    def load_cache(self, cache_path):
        """Load the index from a cache file"""
        with open(cache_path, 'rb') as f:
            data = pickle.load(f)
            self.dsc_info = data['dsc_info']
            self.index = data['index']
            
        print(f"Cache loaded from: {cache_path}")
        return True


def discover_macros(dsc_path, workspace_dir=None):
    """
    Scan DSC and referenced INF files to discover candidate -D macros
    
    This helps identify build options that might be needed
    """
    macros = set()
    dsc_path = Path(dsc_path)
    
    # Common EDK2 macros
    common_macros = [
        'TOOL_CHAIN_TAG',
        'TARGET',
        'ARCH',
        'DEBUG_ENABLE',
        'SECURE_BOOT_ENABLE',
        'TPM2_ENABLE',
        'NETWORK_ENABLE',
        'HTTP_BOOT_ENABLE',
    ]
    
    # Parse DSC for conditional statements
    if dsc_path.exists():
        content = dsc_path.read_text()
        
        # Find !if statements
        if_pattern = re.compile(r'!if\s+.*?\$\(([A-Z_][A-Z0-9_]*)\)', re.IGNORECASE)
        macros.update(if_pattern.findall(content))
        
        # Find !ifdef statements
        ifdef_pattern = re.compile(r'!ifdef\s+([A-Z_][A-Z0-9_]*)', re.IGNORECASE)
        macros.update(ifdef_pattern.findall(content))
        
    # Add common macros
    macros.update(common_macros)
    
    return sorted(macros)


def main():
    parser = argparse.ArgumentParser(
        description='EDK2 DSC Search Tool - Parse and search EDK2 codebases',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clone EDK2 if needed
  %(prog)s --clone-edk2
  
  # Discover macros in a DSC file
  %(prog)s discover-macros OvmfPkg/OvmfPkgX64.dsc
  
  # Build search index from DSC
  %(prog)s build-set OvmfPkg/OvmfPkgX64.dsc
  
  # Search for components
  %(prog)s search --dsc OvmfPkg/OvmfPkgX64.dsc "PciHostBridge"
  
  # Generate dependency graph
  %(prog)s build-set OvmfPkg/OvmfPkgX64.dsc --graph dependencies.dot
        """
    )
    
    parser.add_argument('--edk2-dir', 
                       default='vendor/edk2',
                       help='Path to EDK2 tree (default: vendor/edk2)')
    
    parser.add_argument('--clone-edk2',
                       action='store_true',
                       help='Shallow clone EDK2 if not present')
    
    parser.add_argument('--packages-path',
                       help='PACKAGES_PATH (semicolon-separated on Windows)')
    
    parser.add_argument('--arch',
                       nargs='+',
                       default=['X64'],
                       help='Architecture(s) (default: X64)')
    
    parser.add_argument('-D',
                       action='append',
                       dest='macros',
                       help='Define a macro (e.g., -D DEBUG_ENABLE=TRUE)')
    
    parser.add_argument('--use-cache',
                       action='store_true',
                       help='Use cached index if available')
    
    parser.add_argument('--write-cache',
                       action='store_true',
                       help='Write index to cache after building')
    
    parser.add_argument('--json',
                       action='store_true',
                       help='Output in JSON format')
    
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Enable verbose logging for debugging')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # discover-macros command
    discover_parser = subparsers.add_parser('discover-macros',
                                           help='Scan DSC to list candidate -D macros')
    discover_parser.add_argument('dsc', help='DSC file path')
    
    # build-set command
    build_parser = subparsers.add_parser('build-set',
                                        help='Build file set from DSC')
    build_parser.add_argument('dsc', help='DSC file path')
    build_parser.add_argument('--graph',
                             help='Generate dependency graph DOT file')
    build_parser.add_argument('--write-cache',
                             action='store_true',
                             help='Write index to cache after building')
    build_parser.add_argument('--verbose', '-v',
                             action='store_true',
                             help='Enable verbose logging for debugging')
    
    # search command
    search_parser = subparsers.add_parser('search',
                                         help='Search within resolved file set')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--dsc', required=True, help='DSC file path')
    search_parser.add_argument('--type',
                              choices=['all', 'modules', 'libraries', 'packages', 'files'],
                              default='all',
                              help='Type of components to search')
    
    args = parser.parse_args()
    
    # Configure logging
    if hasattr(args, 'verbose') and args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    
    # Handle --clone-edk2
    if args.clone_edk2:
        edk2_dir = Path(args.edk2_dir)
        if not edk2_dir.exists():
            print(f"Cloning EDK2 to {edk2_dir}...")
            os.system(f'git clone --depth 1 https://github.com/tianocore/edk2.git {edk2_dir}')
        else:
            print(f"EDK2 already exists at {edk2_dir}")
        return
    
    # Check if EDK2 exists
    if not Path(args.edk2_dir).exists():
        print(f"Error: EDK2 not found at {args.edk2_dir}")
        print(f"Run with --clone-edk2 to download it")
        return 1
    
    # Process commands
    if args.command == 'discover-macros':
        macros = discover_macros(args.dsc)
        if args.json:
            print(json.dumps(macros, indent=2))
        else:
            print("Discovered macros:")
            for macro in macros:
                print(f"  -D {macro}=<value>")
                
    elif args.command == 'build-set':
        # Parse macros
        macros = {}
        if args.macros:
            for macro_def in args.macros:
                if '=' in macro_def:
                    key, value = macro_def.split('=', 1)
                    macros[key] = value
                else:
                    macros[macro_def] = "TRUE"
        
        # Build index
        workspace = Path(args.dsc).parent.parent if '/' in args.dsc else Path.cwd()
        indexer = EDK2SearchIndex(
            workspace_dir=workspace,
            packages_path=args.packages_path,
            arch=args.arch[0]
        )
        
        # Check cache
        cache_path = None
        if args.use_cache:
            dsc_hash = hashlib.md5(args.dsc.encode()).hexdigest()[:8]
            cache_path = Path(f".edk2_search_cache_{dsc_hash}.pkl")
            if cache_path.exists():
                indexer.load_cache(cache_path)
            else:
                indexer.parse_dsc(args.dsc, macros)
                if args.write_cache:
                    indexer.save_cache(cache_path)
        else:
            indexer.parse_dsc(args.dsc, macros)
            if args.write_cache:
                indexer.save_cache()
        
        # Generate graph if requested
        if args.graph:
            indexer.generate_graph(args.graph)
        
        # Output summary
        if args.json:
            summary = {
                'dsc': indexer.dsc_info,
                'modules': len(indexer.index['modules']),
                'libraries': len(indexer.index['libraries']),
                'packages': len(indexer.index['packages']),
                'files': len(indexer.index['files']),
            }
            print(json.dumps(summary, indent=2))
        else:
            print(f"\nBuild set complete:")
            print(f"  DSC: {indexer.dsc_info['name']}")
            print(f"  Modules: {len(indexer.index['modules'])}")
            print(f"  Libraries: {len(indexer.index['libraries'])}")
            print(f"  Packages: {len(indexer.index['packages'])}")
            print(f"  Files: {len(indexer.index['files'])}")
            
    elif args.command == 'search':
        # Parse macros
        macros = {}
        if args.macros:
            for macro_def in args.macros:
                if '=' in macro_def:
                    key, value = macro_def.split('=', 1)
                    macros[key] = value
                else:
                    macros[macro_def] = "TRUE"
        
        # Build or load index
        workspace = Path(args.dsc).parent.parent if '/' in args.dsc else Path.cwd()
        indexer = EDK2SearchIndex(
            workspace_dir=workspace,
            packages_path=args.packages_path,
            arch=args.arch[0]
        )
        
        # Try to load from cache first
        dsc_hash = hashlib.md5(args.dsc.encode()).hexdigest()[:8]
        cache_path = Path(f".edk2_search_cache_{dsc_hash}.pkl")
        if cache_path.exists():
            indexer.load_cache(cache_path)
        else:
            print("Building index (use --write-cache to save for next time)...")
            indexer.parse_dsc(args.dsc, macros)
        
        # Perform search
        results = indexer.search(args.query, args.type)
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\nSearch results for '{args.query}':")
            print(f"Found {len(results)} matches\n")
            
            for result in results:
                print(f"Type: {result['type']}")
                print(f"Path: {result['path']}")
                if result['type'] == 'file':
                    print(f"Used by: {', '.join(result['used_by'])}")
                else:
                    info = result['info']
                    print(f"Name: {info.get('name', 'N/A')}")
                    if 'guid' in info and info['guid']:
                        print(f"GUID: {info['guid']}")
                print()
                
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
