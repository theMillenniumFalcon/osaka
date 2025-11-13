"""
File operation tools: read, list, and edit files
"""

import os
from typing import List
from osaka.tools.base import Tool
from osaka.utils.backup import BackupManager


class FileTools:
    """Collection of file operation tools"""
    
    def __init__(self, backup_manager: BackupManager, edit_history: List):
        self.backup_manager = backup_manager
        self.edit_history = edit_history
    
    @staticmethod
    def get_tool_definitions() -> List[Tool]:
        """Return tool definitions for file operations"""
        return [
            Tool(
                name="read_file",
                description="Read the contents of a file at the specified path",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the file to read",
                        }
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="list_files",
                description="List all files and directories in the specified path",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The directory path to list (defaults to current directory)",
                        }
                    },
                    "required": [],
                },
            ),
            Tool(
                name="edit_file",
                description="Edit a file by replacing old_text with new_text. Creates the file if it doesn't exist.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the file to edit",
                        },
                        "old_text": {
                            "type": "string",
                            "description": "The text to search for and replace (leave empty to create new file)",
                        },
                        "new_text": {
                            "type": "string",
                            "description": "The text to replace old_text with",
                        },
                    },
                    "required": ["path", "new_text"],
                },
            ),
        ]
    
    def read_file(self, path: str) -> str:
        """Read the contents of a file"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"File contents of {path}:\n{content}"
        except FileNotFoundError:
            return f"File not found: {path}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def list_files(self, path: str = ".") -> str:
        """List all files and directories in a path"""
        try:
            if not os.path.exists(path):
                return f"Path not found: {path}"

            items = []
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    items.append(f"[DIR]  {item}/")
                else:
                    items.append(f"[FILE] {item}")

            if not items:
                return f"Empty directory: {path}"

            return f"Contents of {path}:\n" + "\n".join(items)
        except Exception as e:
            return f"Error listing files: {str(e)}"
    
    def edit_file(self, path: str, old_text: str = "", new_text: str = "") -> str:
        """Edit a file by replacing old_text with new_text, or create new file"""
        try:
            # Create backup before editing
            backup_path = self.backup_manager.create_backup(path)
            file_existed = os.path.exists(path)
            
            if file_existed and old_text:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                if old_text not in content:
                    return f"Text not found in file: {old_text}"

                content = content.replace(old_text, new_text)

                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

                # Record edit in history
                self.edit_history.append({
                    "path": path,
                    "backup_path": backup_path,
                    "action": "edit",
                    "timestamp": self.backup_manager.get_timestamp()
                })

                return f"Successfully edited {path}"
            else:
                # Only create directory if path contains subdirectories
                dir_name = os.path.dirname(path)
                if dir_name:
                    os.makedirs(dir_name, exist_ok=True)

                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_text)

                # Record creation in history
                self.edit_history.append({
                    "path": path,
                    "backup_path": backup_path,
                    "action": "create",
                    "timestamp": self.backup_manager.get_timestamp()
                })

                return f"Successfully created {path}"
        except Exception as e:
            return f"Error editing file: {str(e)}"