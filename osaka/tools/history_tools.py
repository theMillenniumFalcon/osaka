"""
Edit history and undo functionality
"""

import os
import shutil
from typing import List
from osaka.tools.base import Tool


class HistoryTools:
    """Collection of history management tools"""
    
    def __init__(self, edit_history: List):
        self.edit_history = edit_history
    
    @staticmethod
    def get_tool_definitions() -> List[Tool]:
        """Return tool definitions for history operations"""
        return [
            Tool(
                name="undo_last_edit",
                description="Undo the last file edit operation and restore the previous version",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
        ]
    
    def undo_last_edit(self) -> str:
        """Undo the last file edit operation"""
        if not self.edit_history:
            return "No edits to undo"

        try:
            last_edit = self.edit_history.pop()
            path = last_edit["path"]
            backup_path = last_edit["backup_path"]
            action = last_edit["action"]

            if action == "create":
                # If file was created, delete it
                if os.path.exists(path):
                    os.remove(path)
                return f"Undone: Removed newly created file {path}"
            elif action == "edit":
                # If file was edited, restore from backup
                if backup_path and os.path.exists(backup_path):
                    shutil.copy2(backup_path, path)
                    return f"Undone: Restored {path} from backup"
                else:
                    return f"Error: Backup not found for {path}"

        except Exception as e:
            return f"Error undoing edit: {str(e)}"