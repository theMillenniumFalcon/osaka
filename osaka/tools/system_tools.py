"""
System command execution tool
"""

import os
import subprocess
from typing import List
from osaka.tools.base import Tool
from osaka.utils.validators import is_command_safe
from osaka.config import DEFAULT_TIMEOUT


class SystemTools:
    """Collection of system operation tools"""
    
    @staticmethod
    def get_tool_definitions() -> List[Tool]:
        """Return tool definitions for system operations"""
        return [
            Tool(
                name="run_command",
                description="Execute a shell command or run a script file. Use this to run programs, execute scripts, or perform system operations.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The command to execute (e.g., 'python script.py', 'ls -la', 'npm test')",
                        },
                        "working_directory": {
                            "type": "string",
                            "description": "The directory to run the command in (defaults to current directory)",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Maximum time in seconds to wait for command completion (defaults to 30)",
                        },
                    },
                    "required": ["command"],
                },
            ),
        ]
    
    def run_command(
        self, command: str, working_directory: str = ".", timeout: int = None
    ) -> str:
        """Execute a shell command and return its output"""
        if timeout is None:
            timeout = DEFAULT_TIMEOUT
            
        try:
            if not os.path.exists(working_directory):
                return f"Working directory not found: {working_directory}"

            # Security check - block potentially dangerous commands
            if not is_command_safe(command):
                return f"Command blocked for safety reasons: {command}"

            # Run the command
            result = subprocess.run(
                command,
                shell=True,
                cwd=working_directory,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            # Format output
            output_parts = []
            
            if result.stdout:
                output_parts.append(f"Output:\n{result.stdout}")
            
            if result.stderr:
                output_parts.append(f"Errors:\n{result.stderr}")
            
            if result.returncode != 0:
                output_parts.append(f"Exit code: {result.returncode}")
            
            if not output_parts:
                output_parts.append("Command completed successfully with no output")

            return "\n\n".join(output_parts)

        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout} seconds: {command}"
        except Exception as e:
            return f"Error running command: {str(e)}"