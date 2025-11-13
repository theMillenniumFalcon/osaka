"""
Backup management utilities
"""

import os
import shutil
from datetime import datetime
from osaka.config import BACKUP_DIR


class BackupManager:
    """Manages file backups before editing"""
    
    def __init__(self, backup_dir: str = None):
        self.backup_dir = backup_dir or BACKUP_DIR
        self._setup_backup_directory()
    
    def _setup_backup_directory(self):
        """Create backup directory if it doesn't exist"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
    
    def create_backup(self, path: str) -> str:
        """
        Create a backup of a file before editing
        
        Args:
            path: Path to the file to backup
            
        Returns:
            str: Path to the backup file, or None if file doesn't exist
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{os.path.basename(path)}_{timestamp}.backup"
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        if os.path.exists(path):
            shutil.copy2(path, backup_path)
            return backup_path
        return None
    
    @staticmethod
    def get_timestamp():
        """Get current timestamp for edit history"""
        return datetime.now()