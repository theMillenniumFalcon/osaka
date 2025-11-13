"""
Main AI Agent class - orchestrates tools and API communication
"""

from typing import List, Dict, Any
from anthropic import Anthropic

from osaka.config import MAX_TOKENS, MODEL_NAME, SYSTEM_PROMPT
from osaka.tools.file_tools import FileTools
from osaka.tools.search_tools import SearchTools
from osaka.tools.system_tools import SystemTools
from osaka.tools.history_tools import HistoryTools
from osaka.utils.backup import BackupManager


class AIAgent:
    """Main agent that handles conversation and tool execution"""
    
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.messages: List[Dict[str, Any]] = []
        self.edit_history: List[Dict[str, Any]] = []
        
        # Initialize backup manager
        self.backup_manager = BackupManager()
        
        # Initialize tool handlers
        self.file_tools = FileTools(self.backup_manager, self.edit_history)
        self.search_tools = SearchTools(self.backup_manager, self.edit_history)
        self.system_tools = SystemTools()
        self.history_tools = HistoryTools(self.edit_history)
        
        # Collect all tool definitions
        self.tools = []
        self.tools.extend(self.file_tools.get_tool_definitions())
        self.tools.extend(self.search_tools.get_tool_definitions())
        self.tools.extend(self.system_tools.get_tool_definitions())
        self.tools.extend(self.history_tools.get_tool_definitions())
        
        print(f"Agent initialized with {len(self.tools)} tools")
    
    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Execute a tool by name with given input
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool
            
        Returns:
            str: Result of the tool execution
        """
        try:
            # File tools
            if tool_name == "read_file":
                return self.file_tools.read_file(tool_input["path"])
            elif tool_name == "list_files":
                return self.file_tools.list_files(tool_input.get("path", "."))
            elif tool_name == "edit_file":
                return self.file_tools.edit_file(
                    tool_input["path"],
                    tool_input.get("old_text", ""),
                    tool_input["new_text"],
                )
            
            # Search tools
            elif tool_name == "search_files":
                return self.search_tools.search_files(
                    tool_input["pattern"],
                    tool_input.get("path", "."),
                    tool_input.get("file_pattern"),
                    tool_input.get("case_sensitive", False),
                    tool_input.get("use_regex", False),
                )
            elif tool_name == "multi_file_edit":
                return self.search_tools.multi_file_edit(
                    tool_input["old_text"],
                    tool_input["new_text"],
                    tool_input.get("path", "."),
                    tool_input.get("file_pattern"),
                    tool_input.get("case_sensitive", True),
                    tool_input.get("dry_run", False),
                )
            
            # System tools
            elif tool_name == "run_command":
                return self.system_tools.run_command(
                    tool_input["command"],
                    tool_input.get("working_directory", "."),
                    tool_input.get("timeout", 30),
                )
            
            # History tools
            elif tool_name == "undo_last_edit":
                return self.history_tools.undo_last_edit()
            
            else:
                return f"Unknown tool: {tool_name}"
                
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"
    
    def chat(self, user_input: str) -> str:
        """
        Process a user message and return the agent's response
        
        Args:
            user_input: The user's message
            
        Returns:
            str: The agent's response
        """
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
                    model=MODEL_NAME,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
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