"""
Search and multi-file edit tools
"""

import os
import re
import fnmatch
from typing import List
from osaka.tools.base import Tool
from osaka.utils.backup import BackupManager
from osaka.config import BACKUP_DIR


class SearchTools:
    """Collection of search and batch edit tools"""
    
    def __init__(self, backup_manager: BackupManager, edit_history: List):
        self.backup_manager = backup_manager
        self.edit_history = edit_history
    
    @staticmethod
    def get_tool_definitions() -> List[Tool]:
        """Return tool definitions for search operations"""
        return [
            Tool(
                name="search_files",
                description="Search for text patterns across multiple files in a directory. Supports regex patterns and file filtering.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "The text or regex pattern to search for",
                        },
                        "path": {
                            "type": "string",
                            "description": "The directory path to search in (defaults to current directory)",
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "Optional file pattern to filter files (e.g., '*.py', '*.js')",
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Whether the search should be case-sensitive (defaults to false)",
                        },
                        "use_regex": {
                            "type": "boolean",
                            "description": "Whether to treat the pattern as a regex (defaults to false)",
                        },
                    },
                    "required": ["pattern"],
                },
            ),
            Tool(
                name="multi_file_edit",
                description="Edit multiple files at once by applying the same text replacement across all matching files. Useful for refactoring, renaming variables/functions, or updating imports.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "old_text": {
                            "type": "string",
                            "description": "The text to search for and replace in all files",
                        },
                        "new_text": {
                            "type": "string",
                            "description": "The text to replace old_text with",
                        },
                        "path": {
                            "type": "string",
                            "description": "The directory path to search in (defaults to current directory)",
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "Optional file pattern to filter files (e.g., '*.py', '*.js')",
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Whether the search should be case-sensitive (defaults to true)",
                        },
                        "dry_run": {
                            "type": "boolean",
                            "description": "If true, show what would be changed without actually modifying files (defaults to false)",
                        },
                    },
                    "required": ["old_text", "new_text"],
                },
            ),
        ]
    
    def search_files(
        self,
        pattern: str,
        path: str = ".",
        file_pattern: str = None,
        case_sensitive: bool = False,
        use_regex: bool = False,
    ) -> str:
        """Search for text patterns across multiple files"""
        try:
            if not os.path.exists(path):
                return f"Path not found: {path}"

            results = []
            total_matches = 0
            files_searched = 0

            # Compile regex pattern if needed
            if use_regex:
                try:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    regex = re.compile(pattern, flags)
                except re.error as e:
                    return f"Invalid regex pattern: {str(e)}"
            else:
                # For plain text search
                search_pattern = pattern if case_sensitive else pattern.lower()

            # Walk through directory
            for root, dirs, files in os.walk(path):
                # Skip backup directory
                if BACKUP_DIR in root:
                    continue

                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]

                for filename in files:
                    # Skip hidden files
                    if filename.startswith('.'):
                        continue

                    # Apply file pattern filter if specified
                    if file_pattern and not fnmatch.fnmatch(filename, file_pattern):
                        continue

                    filepath = os.path.join(root, filename)

                    try:
                        # Try to read as text file
                        with open(filepath, 'r', encoding='utf-8') as f:
                            lines = f.readlines()

                        files_searched += 1
                        file_matches = []

                        for line_num, line in enumerate(lines, 1):
                            if use_regex:
                                if regex.search(line):
                                    file_matches.append((line_num, line.rstrip()))
                                    total_matches += 1
                            else:
                                search_line = line if case_sensitive else line.lower()
                                if search_pattern in search_line:
                                    file_matches.append((line_num, line.rstrip()))
                                    total_matches += 1

                        if file_matches:
                            results.append({
                                'file': filepath,
                                'matches': file_matches
                            })

                    except (UnicodeDecodeError, PermissionError):
                        # Skip binary files or files we can't read
                        continue

            # Format results
            if not results:
                return f"No matches found for '{pattern}' in {files_searched} files"

            output = [f"Found {total_matches} matches in {len(results)} files (searched {files_searched} files):\n"]

            for result in results:
                output.append(f"\n{result['file']}:")
                for line_num, line in result['matches'][:5]:  # Show first 5 matches per file
                    output.append(f"  Line {line_num}: {line}")
                
                if len(result['matches']) > 5:
                    output.append(f"  ... and {len(result['matches']) - 5} more matches")

            return "\n".join(output)

        except Exception as e:
            return f"Error searching files: {str(e)}"
    
    def multi_file_edit(
        self,
        old_text: str,
        new_text: str,
        path: str = ".",
        file_pattern: str = None,
        case_sensitive: bool = True,
        dry_run: bool = False,
    ) -> str:
        """Edit multiple files at once by replacing old_text with new_text"""
        try:
            if not os.path.exists(path):
                return f"Path not found: {path}"

            files_modified = []
            files_with_matches = []
            total_replacements = 0

            # Walk through directory
            for root, dirs, files in os.walk(path):
                # Skip backup directory
                if BACKUP_DIR in root:
                    continue

                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]

                for filename in files:
                    # Skip hidden files
                    if filename.startswith('.'):
                        continue

                    # Apply file pattern filter if specified
                    if file_pattern and not fnmatch.fnmatch(filename, file_pattern):
                        continue

                    filepath = os.path.join(root, filename)

                    try:
                        # Try to read as text file
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Check if old_text exists in file
                        if case_sensitive:
                            if old_text not in content:
                                continue
                            count = content.count(old_text)
                        else:
                            # Case-insensitive search
                            if old_text.lower() not in content.lower():
                                continue
                            # Count occurrences (case-insensitive)
                            count = content.lower().count(old_text.lower())

                        files_with_matches.append((filepath, count))

                        if not dry_run:
                            # Create backup before editing
                            backup_path = self.backup_manager.create_backup(filepath)

                            # Perform replacement
                            if case_sensitive:
                                new_content = content.replace(old_text, new_text)
                            else:
                                # Case-insensitive replacement
                                pattern = re.compile(re.escape(old_text), re.IGNORECASE)
                                new_content = pattern.sub(new_text, content)

                            # Write modified content
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(new_content)

                            # Record edit in history
                            self.edit_history.append({
                                "path": filepath,
                                "backup_path": backup_path,
                                "action": "edit",
                                "timestamp": self.backup_manager.get_timestamp(),
                                "multi_file": True
                            })

                            files_modified.append(filepath)

                        total_replacements += count

                    except (UnicodeDecodeError, PermissionError):
                        # Skip binary files or files we can't read
                        continue

            # Format results
            if not files_with_matches:
                return f"No files found containing '{old_text}'"

            if dry_run:
                output = [f"DRY RUN - Would modify {len(files_with_matches)} files with {total_replacements} total replacements:\n"]
                for filepath, count in files_with_matches:
                    output.append(f"  {filepath}: {count} replacement(s)")
                output.append(f"\nRun without dry_run=true to apply these changes.")
            else:
                output = [f"Successfully modified {len(files_modified)} files with {total_replacements} total replacements:\n"]
                for filepath in files_modified:
                    output.append(f"  {filepath}")
                output.append(f"\nNote: You can undo these changes using the undo command (reverts one file at a time).")

            return "\n".join(output)

        except Exception as e:
            return f"Error in multi-file edit: {str(e)}"