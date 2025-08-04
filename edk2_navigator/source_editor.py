"""
Source Editor - Tools for editing EDK2 source files with build context awareness
"""
import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from .dsc_parser import DSCContext, ModuleInfo
from .query_engine import QueryEngine, FunctionLocation
from .exceptions import EDK2NavigatorError

@dataclass
class EditResult:
    """Result of a source file edit operation"""
    success: bool
    file_path: str
    changes_made: List[str]
    backup_path: Optional[str] = None
    error_message: Optional[str] = None
    lines_added: int = 0
    lines_removed: int = 0
    lines_modified: int = 0

@dataclass
class FileSearchResult:
    """Result of searching within a file"""
    file_path: str
    line_number: int
    line_content: str
    match_start: int
    match_end: int
    context_before: List[str]
    context_after: List[str]

class SourceEditor:
    """Editor for EDK2 source files with build context awareness"""
    
    def __init__(self, workspace_dir: str, edk2_path: str, create_backups: bool = True):
        """Initialize source editor"""
        self.workspace_dir = Path(workspace_dir).resolve()
        self.edk2_path = Path(edk2_path).resolve()
        self.create_backups = create_backups
        self.backup_dir = self.workspace_dir / ".edk2_navigator_backups"
        
        if create_backups:
            self.backup_dir.mkdir(exist_ok=True)
    
    def read_file(self, file_path: str) -> str:
        """Read contents of a source file"""
        full_path = self.workspace_dir / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            raise EDK2NavigatorError(f"Failed to read file {file_path}: {e}")
    
    def write_file(self, file_path: str, content: str, create_backup: bool = None) -> EditResult:
        """Write content to a source file"""
        full_path = self.workspace_dir / file_path
        
        if create_backup is None:
            create_backup = self.create_backups
        
        backup_path = None
        
        try:
            # Create backup if requested and file exists
            if create_backup and full_path.exists():
                backup_path = self._create_backup(file_path)
            
            # Ensure directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write new content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return EditResult(
                success=True,
                file_path=file_path,
                changes_made=["File written"],
                backup_path=str(backup_path) if backup_path else None
            )
            
        except Exception as e:
            return EditResult(
                success=False,
                file_path=file_path,
                changes_made=[],
                error_message=str(e)
            )
    
    def search_in_file(self, file_path: str, pattern: str, context_lines: int = 3) -> List[FileSearchResult]:
        """Search for a pattern within a file"""
        try:
            content = self.read_file(file_path)
            lines = content.split('\n')
            results = []
            
            # Compile regex pattern
            regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            
            for line_num, line in enumerate(lines):
                for match in regex.finditer(line):
                    # Get context lines
                    start_context = max(0, line_num - context_lines)
                    end_context = min(len(lines), line_num + context_lines + 1)
                    
                    context_before = lines[start_context:line_num]
                    context_after = lines[line_num + 1:end_context]
                    
                    results.append(FileSearchResult(
                        file_path=file_path,
                        line_number=line_num + 1,  # 1-based line numbers
                        line_content=line,
                        match_start=match.start(),
                        match_end=match.end(),
                        context_before=context_before,
                        context_after=context_after
                    ))
            
            return results
            
        except Exception as e:
            raise EDK2NavigatorError(f"Failed to search in file {file_path}: {e}")
    
    def replace_in_file(self, file_path: str, search_pattern: str, replacement: str, 
                       max_replacements: int = -1) -> EditResult:
        """Replace text in a file using regex pattern"""
        try:
            original_content = self.read_file(file_path)
            
            # Perform replacement
            if max_replacements == -1:
                new_content, num_replacements = re.subn(search_pattern, replacement, original_content, flags=re.MULTILINE)
            else:
                new_content, num_replacements = re.subn(search_pattern, replacement, original_content, 
                                                       count=max_replacements, flags=re.MULTILINE)
            
            if num_replacements == 0:
                return EditResult(
                    success=False,
                    file_path=file_path,
                    changes_made=[],
                    error_message="No matches found for replacement"
                )
            
            # Write the modified content
            result = self.write_file(file_path, new_content)
            
            if result.success:
                result.changes_made = [f"Made {num_replacements} replacements"]
                result.lines_modified = num_replacements
            
            return result
            
        except Exception as e:
            return EditResult(
                success=False,
                file_path=file_path,
                changes_made=[],
                error_message=str(e)
            )
    
    def insert_at_line(self, file_path: str, line_number: int, content: str) -> EditResult:
        """Insert content at a specific line number"""
        try:
            original_content = self.read_file(file_path)
            lines = original_content.split('\n')
            
            # Validate line number
            if line_number < 1 or line_number > len(lines) + 1:
                return EditResult(
                    success=False,
                    file_path=file_path,
                    changes_made=[],
                    error_message=f"Invalid line number: {line_number}"
                )
            
            # Insert content (convert to 0-based index)
            insert_lines = content.split('\n')
            lines[line_number - 1:line_number - 1] = insert_lines
            
            new_content = '\n'.join(lines)
            result = self.write_file(file_path, new_content)
            
            if result.success:
                result.changes_made = [f"Inserted {len(insert_lines)} lines at line {line_number}"]
                result.lines_added = len(insert_lines)
            
            return result
            
        except Exception as e:
            return EditResult(
                success=False,
                file_path=file_path,
                changes_made=[],
                error_message=str(e)
            )
    
    def delete_lines(self, file_path: str, start_line: int, end_line: int) -> EditResult:
        """Delete lines from a file"""
        try:
            original_content = self.read_file(file_path)
            lines = original_content.split('\n')
            
            # Validate line numbers
            if start_line < 1 or end_line < start_line or end_line > len(lines):
                return EditResult(
                    success=False,
                    file_path=file_path,
                    changes_made=[],
                    error_message=f"Invalid line range: {start_line}-{end_line}"
                )
            
            # Delete lines (convert to 0-based index)
            lines_to_delete = end_line - start_line + 1
            del lines[start_line - 1:end_line]
            
            new_content = '\n'.join(lines)
            result = self.write_file(file_path, new_content)
            
            if result.success:
                result.changes_made = [f"Deleted {lines_to_delete} lines ({start_line}-{end_line})"]
                result.lines_removed = lines_to_delete
            
            return result
            
        except Exception as e:
            return EditResult(
                success=False,
                file_path=file_path,
                changes_made=[],
                error_message=str(e)
            )
    
    def add_function(self, file_path: str, function_code: str, insert_location: str = "end") -> EditResult:
        """Add a new function to a source file"""
        try:
            original_content = self.read_file(file_path)
            lines = original_content.split('\n')
            
            # Determine where to insert the function
            if insert_location == "end":
                # Insert before the last closing brace or at the end
                insert_line = len(lines)
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].strip() == '}' and not lines[i].startswith(' '):
                        insert_line = i
                        break
            elif insert_location == "beginning":
                # Insert after includes and defines
                insert_line = 0
                for i, line in enumerate(lines):
                    if not (line.startswith('#') or line.strip() == '' or line.startswith('//')):
                        insert_line = i
                        break
            else:
                # Assume it's a line number
                try:
                    insert_line = int(insert_location)
                except ValueError:
                    return EditResult(
                        success=False,
                        file_path=file_path,
                        changes_made=[],
                        error_message=f"Invalid insert location: {insert_location}"
                    )
            
            # Add function with proper spacing
            function_lines = ['', ''] + function_code.split('\n') + ['']
            lines[insert_line:insert_line] = function_lines
            
            new_content = '\n'.join(lines)
            result = self.write_file(file_path, new_content)
            
            if result.success:
                result.changes_made = [f"Added function at line {insert_line}"]
                result.lines_added = len(function_lines)
            
            return result
            
        except Exception as e:
            return EditResult(
                success=False,
                file_path=file_path,
                changes_made=[],
                error_message=str(e)
            )
    
    def modify_function(self, file_path: str, function_name: str, new_function_code: str) -> EditResult:
        """Modify an existing function in a source file"""
        try:
            original_content = self.read_file(file_path)
            
            # Find function definition using regex
            # This is a simplified pattern - a more robust implementation would use proper C parsing
            function_pattern = rf'(\w+\s+(?:EFIAPI\s+)?{re.escape(function_name)}\s*\([^{{]*\{{)'
            
            match = re.search(function_pattern, original_content, re.MULTILINE | re.DOTALL)
            if not match:
                return EditResult(
                    success=False,
                    file_path=file_path,
                    changes_made=[],
                    error_message=f"Function {function_name} not found"
                )
            
            # Find the end of the function by counting braces
            start_pos = match.start()
            brace_count = 0
            end_pos = start_pos
            
            for i, char in enumerate(original_content[start_pos:], start_pos):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break
            
            # Replace the function
            new_content = (original_content[:start_pos] + 
                          new_function_code + 
                          original_content[end_pos:])
            
            result = self.write_file(file_path, new_content)
            
            if result.success:
                result.changes_made = [f"Modified function {function_name}"]
                result.lines_modified = 1
            
            return result
            
        except Exception as e:
            return EditResult(
                success=False,
                file_path=file_path,
                changes_made=[],
                error_message=str(e)
            )
    
    def add_include(self, file_path: str, include_statement: str) -> EditResult:
        """Add an include statement to a source file"""
        try:
            original_content = self.read_file(file_path)
            lines = original_content.split('\n')
            
            # Check if include already exists
            if include_statement in original_content:
                return EditResult(
                    success=False,
                    file_path=file_path,
                    changes_made=[],
                    error_message="Include statement already exists"
                )
            
            # Find where to insert the include (after existing includes)
            insert_line = 0
            for i, line in enumerate(lines):
                if line.startswith('#include'):
                    insert_line = i + 1
                elif line.strip() and not line.startswith('#') and not line.startswith('//'):
                    break
            
            # Insert the include statement
            lines.insert(insert_line, include_statement)
            
            new_content = '\n'.join(lines)
            result = self.write_file(file_path, new_content)
            
            if result.success:
                result.changes_made = [f"Added include: {include_statement}"]
                result.lines_added = 1
            
            return result
            
        except Exception as e:
            return EditResult(
                success=False,
                file_path=file_path,
                changes_made=[],
                error_message=str(e)
            )
    
    def _create_backup(self, file_path: str) -> Path:
        """Create a backup of a file"""
        full_path = self.workspace_dir / file_path
        
        # Create backup filename with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{Path(file_path).name}.{timestamp}.backup"
        backup_path = self.backup_dir / backup_name
        
        # Copy file to backup location
        shutil.copy2(full_path, backup_path)
        
        return backup_path
    
    def list_backups(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available backups"""
        if not self.backup_dir.exists():
            return []
        
        backups = []
        for backup_file in self.backup_dir.glob("*.backup"):
            # Parse backup filename
            parts = backup_file.name.split('.')
            if len(parts) >= 3:
                original_name = '.'.join(parts[:-2])
                timestamp = parts[-2]
                
                if file_path is None or original_name == Path(file_path).name:
                    backups.append({
                        "original_file": original_name,
                        "backup_path": str(backup_file),
                        "timestamp": timestamp,
                        "size": backup_file.stat().st_size
                    })
        
        return sorted(backups, key=lambda x: x["timestamp"], reverse=True)
    
    def restore_backup(self, backup_path: str, target_path: str) -> EditResult:
        """Restore a file from backup"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                return EditResult(
                    success=False,
                    file_path=target_path,
                    changes_made=[],
                    error_message=f"Backup file not found: {backup_path}"
                )
            
            target_file = self.workspace_dir / target_path
            
            # Create backup of current file before restoring
            current_backup = None
            if target_file.exists():
                current_backup = self._create_backup(target_path)
            
            # Copy backup to target location
            shutil.copy2(backup_file, target_file)
            
            return EditResult(
                success=True,
                file_path=target_path,
                changes_made=[f"Restored from backup: {backup_path}"],
                backup_path=str(current_backup) if current_backup else None
            )
            
        except Exception as e:
            return EditResult(
                success=False,
                file_path=target_path,
                changes_made=[],
                error_message=str(e)
            )
