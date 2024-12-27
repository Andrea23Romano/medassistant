from typing import List, Dict, Any
from openai.types.chat import ChatCompletionMessageToolCall
from src.models import Message
from inspect import signature, Parameter
import docstring_parser
import json

class ToolManager:
    def __init__(self):
        self.tools: Dict[str, callable] = {}

    def register_tool(self, name: str, tool_function: callable) -> None:
        """Register a new tool with the manager"""
        self.tools[name] = tool_function

    def apply_tool(self, tool_call: ChatCompletionMessageToolCall) -> Message:
        """Apply the appropriate tool based on the tool call and return a Message"""
        tool_name = tool_call.function.name
        arguments = tool_call.function.arguments

        if tool_name not in self.tools:
            return Message(
                role="tool",
                content=f"Error: Tool '{tool_name}' not found",
                tool_call_id=tool_call.id
            )

        try:
            result = self.tools[tool_name](**eval(arguments))
            return Message(
                role="tool",
                content=str(result),
                tool_call_id=tool_call.id
            )
        except Exception as e:
            return Message(
                role="tool",
                content=f"Error executing tool '{tool_name}': {str(e)}",
                tool_call_id=tool_call.id
            )
    @staticmethod
    def get_tool_definition(tool: callable) -> str:
        """Get the definition of a tool function schema for OpenAI tool definition as a string"""
        try:
            # Get function signature and docstring
            sig = signature(tool)
            doc = docstring_parser.parse(tool.__doc__ or "")
            
            # Build parameters schema
            parameters = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            for name, param in sig.parameters.items():
                if param.default is Parameter.empty:
                    parameters["required"].append(name)
                
                # Map Python types to JSON schema types
                type_map = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object"
                }
                
                param_type = param.annotation if param.annotation != Parameter.empty else str
                param_schema = {"type": type_map.get(param_type, "string")}
                
                # Add description from docstring if available
                for param_doc in doc.params:
                    if param_doc.arg_name == name:
                        param_schema["description"] = param_doc.description
                        break
                        
                parameters["properties"][name] = param_schema

            # Build full schema
            schema = {
                "name": tool.__name__,
                "description": doc.short_description or "",
                "parameters": parameters
            }
            
            return json.dumps(schema)
        except Exception as e:
            return '{}'