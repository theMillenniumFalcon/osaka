"""
Security validation utilities
"""

import re


def is_command_safe(command: str) -> bool:
    """
    Check if a command is safe to execute
    
    Args:
        command: The command string to validate
        
    Returns:
        bool: True if command is safe, False otherwise
    """
    # List of dangerous command patterns
    dangerous_patterns = [
        r'\brm\s+-rf\s+/',  # rm -rf /
        r'\bformat\b',       # Windows format
        r'\bmkfs\b',         # make filesystem
        r'\bdd\s+if=',       # disk destroyer
        r'>\s*/dev/sd',      # writing to disk devices
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return False
    
    return True