import os
import sys
import argparse
import logging
import shutil
import re
import fnmatch
import subprocess
from datetime import datetime
from typing import List, Dict, Any
from anthropic import Anthropic
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.FileHandler("agent.log")],
)

# Suppress verbose HTTP logs
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


class Tool(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]


class AIAgent:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.messages: List[Dict[str, Any]] = []
        self.tools: List[Tool] = []
        self.backup_dir = ".osaka_backups"
        self.edit_history: List[Dict[str, Any]] = []
        self._setup_backup_directory()
        self._setup_tools()
        print(f"Agent initialized with {len(self.tools)} tools")

    def _setup_backup_directory(self):
        """Create backup directory if it doesn't exist"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def _setup_tools(self):
        self.tools = [
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
            Tool(
                name="undo_last_edit",
                description="Undo the last file edit operation and restore the previous version",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
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

    def _create_backup(self, path: str) -> str:
        """Create a backup of a file before editing"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{os.path.basename(path)}_{timestamp}.backup"
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        if os.path.exists(path):
            shutil.copy2(path, backup_path)
            return backup_path
        return None

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        try:
            if tool_name == "read_file":
                return self._read_file(tool_input["path"])
            elif tool_name == "list_files":
                return self._list_files(tool_input.get("path", "."))
            elif tool_name == "edit_file":
                return self._edit_file(
                    tool_input["path"],
                    tool_input.get("old_text", ""),
                    tool_input["new_text"],
                )
            elif tool_name == "undo_last_edit":
                return self._undo_last_edit()
            elif tool_name == "search_files":
                return self._search_files(
                    tool_input["pattern"],
                    tool_input.get("path", "."),
                    tool_input.get("file_pattern"),
                    tool_input.get("case_sensitive", False),
                    tool_input.get("use_regex", False),
                )
            elif tool_name == "run_command":
                return self._run_command(
                    tool_input["command"],
                    tool_input.get("working_directory", "."),
                    tool_input.get("timeout", 30),
                )
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    def _read_file(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"File contents of {path}:\n{content}"
        except FileNotFoundError:
            return f"File not found: {path}"
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def _list_files(self, path: str) -> str:
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

    def _edit_file(self, path: str, old_text: str, new_text: str) -> str:
        try:
            # Create backup before editing
            backup_path = self._create_backup(path)
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
                    "timestamp": datetime.now()
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
                    "timestamp": datetime.now()
                })

                return f"Successfully created {path}"
        except Exception as e:
            return f"Error editing file: {str(e)}"

    def _undo_last_edit(self) -> str:
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

    def _search_files(
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
                if self.backup_dir in root:
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

    def _run_command(
        self, command: str, working_directory: str = ".", timeout: int = 30
    ) -> str:
        """Execute a shell command and return its output"""
        try:
            if not os.path.exists(working_directory):
                return f"Working directory not found: {working_directory}"

            # Security check - block potentially dangerous commands
            dangerous_patterns = [
                r'\brm\s+-rf\s+/',  # rm -rf /
                r'\bformat\b',       # Windows format
                r'\bmkfs\b',         # make filesystem
                r'\bdd\s+if=',       # disk destroyer
                r'>\s*/dev/sd',      # writing to disk devices
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, command, re.IGNORECASE):
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

    def chat(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        tool_schemas = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self.tools
        ]

        while True:
            try:
                response = self.client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=4096,
                    system="You are a helpful coding assistant operating in a terminal environment. " \
                    "Output only plain text without markdown formatting, as your responses appear directly in the terminal." \
                    "Be concise but thorough, providing clear and practical advice with a friendly tone. " \
                    "Don't use any asterisk characters in your responses.",
                    messages=self.messages,
                    tools=tool_schemas,
                )

                assistant_message = {"role": "assistant", "content": []}

                for content in response.content:
                    if content.type == "text":
                        assistant_message["content"].append(
                            {
                                "type": "text",
                                "text": content.text,
                            }
                        )
                    elif content.type == "tool_use":
                        assistant_message["content"].append(
                            {
                                "type": "tool_use",
                                "id": content.id,
                                "name": content.name,
                                "input": content.input,
                            }
                        )

                self.messages.append(assistant_message)

                tool_results = []
                for content in response.content:
                    if content.type == "tool_use":
                        result = self._execute_tool(content.name, content.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": result,
                            }
                        )

                if tool_results:
                    self.messages.append({"role": "user", "content": tool_results})
                else:
                    return response.content[0].text if response.content else ""

            except Exception as e:
                return f"Error: {str(e)}"


def main():
    parser = argparse.ArgumentParser(
        description="Osaka - A conversational AI agent with file editing capabilities"
    )
    parser.add_argument(
        "--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)"
    )
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "Error: Please provide an API key via --api-key or ANTHROPIC_API_KEY environment variable"
        )
        sys.exit(1)

    agent = AIAgent(api_key)

    print("Osaka")
    print("=================")
    print("A conversational AI agent that can read, list, and edit files.")
    print("Type 'exit' or 'quit' to end the conversation.")
    print("Type 'undo' to revert the last file change.")
    print()

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            if not user_input:
                continue

            print("\nAssistant: ", end="", flush=True)
            response = agent.chat(user_input)
            print(response)
            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            print()


if __name__ == "__main__":
    main()