#!/usr/bin/env python3
"""
Test script to examine the structure of ComputerBrowserTool20250124.to_params()
"""
import json
import pprint
from models.anthropic.tools.computer_browser import ComputerBrowserTool20250124
from anthropic.types.beta.beta_tool_computer_use_20250124_param import BetaToolComputerUse20250124Param

def main():
    # Create an instance with a dummy CDP URL
    tool = ComputerBrowserTool20250124(cdp_url="ws://localhost:9222")
    
    # Call to_params() to get the schema structure
    params = tool.to_params()
    
    print("=== Raw to_params() output ===")
    print(f"Type: {type(params)}")
    print(f"Content: {params}")
    print()
    
    print("=== Pretty printed structure ===")
    pprint.pprint(params, width=80, depth=10)
    print()
    
    print("=== JSON serialized (if possible) ===")
    try:
        json_str = json.dumps(params, indent=2, default=str)
        print(json_str)
    except Exception as e:
        print(f"JSON serialization failed: {e}")
    print()
    
    print("=== Field analysis ===")
    if isinstance(params, dict):
        for key, value in params.items():
            print(f"  {key}: {type(value).__name__} = {value}")
    else:
        print(f"  Not a dict, type is: {type(params)}")
    print()
    
    print("=== Tool properties ===")
    print(f"tool.name: {tool.name}")
    print(f"tool.api_type: {tool.api_type}")
    print(f"tool.width: {tool.width}")
    print(f"tool.height: {tool.height}")
    print(f"tool.display_num: {tool.display_num}")
    print(f"tool.options: {tool.options}")
    print()
    
    print("=== Anthropic BetaToolComputerUse20250124Param schema ===")
    print(f"Type: {type(BetaToolComputerUse20250124Param)}")
    print(f"Annotations: {getattr(BetaToolComputerUse20250124Param, '__annotations__', 'None')}")
    print(f"Required keys: {getattr(BetaToolComputerUse20250124Param, '__required_keys__', 'None')}")
    print(f"Optional keys: {getattr(BetaToolComputerUse20250124Param, '__optional_keys__', 'None')}")
    print()
    
    print("=== OpenAI format conversion example ===")
    # This shows how you could convert to OpenAI format
    openai_tool_definition = {
        "type": "function",
        "function": {
            "name": params["name"],
            "description": "Control a computer browser using actions like click, type, scroll, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "key", "type", "mouse_move", "left_click", "left_click_drag",
                            "right_click", "middle_click", "double_click", "screenshot",
                            "cursor_position", "left_mouse_down", "left_mouse_up", "scroll",
                            "hold_key", "wait", "triple_click"
                        ],
                        "description": "The action to perform"
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to type or key to press (for 'key', 'type', 'hold_key' actions)"
                    },
                    "coordinate": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 2,
                        "description": "X,Y coordinate for mouse actions [x, y]"
                    },
                    "scroll_direction": {
                        "type": "string",
                        "enum": ["up", "down", "left", "right"],
                        "description": "Direction to scroll (for 'scroll' action)"
                    },
                    "scroll_amount": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Amount to scroll (for 'scroll' action)"
                    },
                    "duration": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Duration in seconds (for 'hold_key', 'wait' actions)"
                    }
                },
                "required": ["action"],
                "additionalProperties": False
            }
        }
    }
    
    print("OpenAI Tool Definition:")
    print(json.dumps(openai_tool_definition, indent=2))

if __name__ == "__main__":
    main()