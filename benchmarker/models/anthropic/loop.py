"""
Agentic sampling loop that calls the Anthropic API and local implementation of anthropic-defined computer use tools.
"""

import platform
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from typing import Any, cast, Optional

import httpx
from anthropic import (
    AsyncAnthropic,
    AsyncAnthropicBedrock,
    AsyncAnthropicVertex,
    APIStatusError,
)
from anthropic.types.beta import (
    BetaCacheControlEphemeralParam,
    BetaContentBlockParam,
    BetaImageBlockParam,
    BetaMessage,
    BetaMessageParam,
    BetaTextBlock,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
    BetaToolUseBlockParam,
)

from .tools import (
    TOOL_GROUPS_BY_VERSION,
    BaseAnthropicTool,
    ToolCollection,
    ToolResult,
    ToolVersion,
)

PROMPT_CACHING_BETA_FLAG = "prompt-caching-2024-07-31"


def _map_model_for_openrouter(model: str) -> str:
    """Map Anthropic model names to OpenRouter model names."""
    model_mapping = {
        "claude-3-7-sonnet-20250219": "anthropic/claude-3.7-sonnet",
        "claude-3-5-sonnet-20241022": "anthropic/claude-3.5-sonnet",
        "claude-3-5-sonnet-20240620": "anthropic/claude-3.5-sonnet",
        "claude-3-haiku-20240307": "anthropic/claude-3-haiku",
        "claude-3-opus-20240229": "anthropic/claude-3-opus",
    }
    return model_mapping.get(model, model)


def _convert_anthropic_to_openai_messages(messages: list[BetaMessageParam], system_prompt: str) -> list[dict]:
    """Convert Anthropic message format to OpenAI format for OpenRouter."""
    openai_messages = []

    # Add system message first
    if system_prompt:
        openai_messages.append({"role": "system", "content": system_prompt})

    for message in messages:
        role = message["role"]
        content = message["content"]

        if isinstance(content, str):
            if content.strip():  # Only add if non-empty
                openai_messages.append({"role": role, "content": content})
        elif isinstance(content, list):
            # Handle complex content blocks
            text_parts = []
            images = []
            tool_results = []

            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text = block.get("text", "").strip()
                        if text:  # Only add non-empty text
                            text_parts.append(text)
                    elif block.get("type") == "image":
                        # OpenAI format for images
                        source = block.get("source", {})
                        if "data" in source and "media_type" in source:
                            images.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{source['media_type']};base64,{source['data']}"
                                }
                            })
                    elif block.get("type") == "tool_result":
                        # Convert tool results to text and images
                        tool_content = block.get("content", "")
                        if isinstance(tool_content, list):
                            for tc in tool_content:
                                if isinstance(tc, dict):
                                    if tc.get("type") == "text":
                                        text = tc.get("text", "").strip()
                                        if text:
                                            tool_results.append(f"Tool result: {text}")
                                    elif tc.get("type") == "image":
                                        # Handle tool result images - add to images list
                                        source = tc.get("source", {})
                                        if "data" in source and "media_type" in source:
                                            images.append({
                                                "type": "image_url",
                                                "image_url": {
                                                    "url": f"data:{source['media_type']};base64,{source['data']}"
                                                }
                                            })
                        elif isinstance(tool_content, str) and tool_content.strip():
                            tool_results.append(f"Tool result: {tool_content.strip()}")

            # Combine all content
            full_content = []
            if text_parts:
                combined_text = " ".join(text_parts).strip()
                if combined_text:
                    full_content.append({"type": "text", "text": combined_text})
            if tool_results:
                combined_results = "\n".join(tool_results).strip()
                if combined_results:
                    full_content.append({"type": "text", "text": combined_results})
            full_content.extend(images)

            # Only add message if it has content
            if full_content:
                if len(full_content) == 1 and full_content[0].get("type") == "text":
                    openai_messages.append({"role": role, "content": full_content[0]["text"]})
                else:
                    openai_messages.append({"role": role, "content": full_content})
            elif role == "assistant":
                # Allow empty assistant messages as they're optional
                openai_messages.append({"role": role, "content": ""})

    return openai_messages


def _create_computer_tool_schemas() -> list[dict]:
    """Create separate OpenAI schemas for each computer tool action using exact Action_20250124 names."""
    return [
        # Basic actions from Action_20241022
        {
            "type": "function",
            "function": {
                "name": "screenshot",
                "description": "Take a screenshot of the current screen",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "cursor_position",
                "description": "Get current cursor position",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },

        # Click actions from Action_20241022
        {
            "type": "function",
            "function": {
                "name": "left_click",
                "description": "Left click at a specific coordinate",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "coordinate": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "The [x, y] coordinate to click"
                        }
                    },
                    "required": ["coordinate"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "right_click",
                "description": "Right click at a specific coordinate",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "coordinate": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "The [x, y] coordinate to right click"
                        }
                    },
                    "required": ["coordinate"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "double_click",
                "description": "Double click at a specific coordinate",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "coordinate": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "The [x, y] coordinate to double click"
                        }
                    },
                    "required": ["coordinate"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "middle_click",
                "description": "Middle click at a specific coordinate",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "coordinate": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "The [x, y] coordinate to middle click"
                        }
                    },
                    "required": ["coordinate"]
                }
            }
        },

        # Mouse actions from Action_20241022
        {
            "type": "function",
            "function": {
                "name": "mouse_move",
                "description": "Move mouse to a specific coordinate",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "coordinate": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "The [x, y] coordinate to move to"
                        }
                    },
                    "required": ["coordinate"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "left_click_drag",
                "description": "Left click and drag to a specific coordinate",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "coordinate": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "The [x, y] coordinate to drag to"
                        }
                    },
                    "required": ["coordinate"]
                }
            }
        },

        # Keyboard actions from Action_20241022
        {
            "type": "function",
            "function": {
                "name": "type",
                "description": "Type text at the current cursor position",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to type"
                        }
                    },
                    "required": ["text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "key",
                "description": "Press a keyboard key or key combination",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Key to press (e.g., 'Enter', 'Tab', 'Escape', 'ctrl+c')"
                        }
                    },
                    "required": ["text"]
                }
            }
        },

        # New actions from Action_20250124
        {
            "type": "function",
            "function": {
                "name": "left_mouse_down",
                "description": "Press and hold left mouse button down",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "left_mouse_up",
                "description": "Release left mouse button",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "scroll",
                "description": "Scroll in a specific direction",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "coordinate": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "The [x, y] coordinate where to scroll (optional)"
                        },
                        "scroll_direction": {
                            "type": "string",
                            "enum": ["up", "down", "left", "right"],
                            "description": "Direction to scroll"
                        },
                        "scroll_amount": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Amount to scroll"
                        }
                    },
                    "required": ["scroll_direction", "scroll_amount"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "hold_key",
                "description": "Hold a key down for a specified duration",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Key to hold down"
                        },
                        "duration": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "Duration in seconds to hold the key"
                        }
                    },
                    "required": ["text", "duration"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "wait",
                "description": "Wait for a specified duration",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "duration": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "Duration in seconds to wait"
                        }
                    },
                    "required": ["duration"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "triple_click",
                "description": "Triple click at a specific coordinate",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "coordinate": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "The [x, y] coordinate to triple click"
                        }
                    },
                    "required": ["coordinate"]
                }
            }
        }
    ]


def _create_bash_tool_schema() -> dict:
    """Create OpenAI schema for the bash tool."""
    return {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute bash commands",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    }


def _create_generic_tool_schema(tool_name: str) -> dict:
    """Create OpenAI schema for unknown/generic tools."""
    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": f"Use {tool_name} tool",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }


def _convert_anthropic_tools_to_openai(tool_collection: 'ToolCollection') -> list[dict]:
    """Convert Anthropic tools to OpenAI function calling format."""
    tools = []
    for tool in tool_collection.tools:
        # Get the tool schema from to_params()
        tool_params = tool.to_params()

        # Extract information from the Anthropic tool format
        if isinstance(tool_params, dict):
            tool_name = tool_params.get("name", getattr(tool, 'name', 'unknown'))

            # Create OpenAI-compatible tool definition based on tool type
            if tool_name == "computer":
                tools.extend(_create_computer_tool_schemas())
            elif tool_name == "bash":
                tools.append(_create_bash_tool_schema())
            else:
                tools.append(_create_generic_tool_schema(tool_name))

    return tools


def _map_openrouter_function_to_anthropic(function_name: str, tool_input: dict) -> tuple[str, dict]:
    """Map OpenRouter function names back to Anthropic computer tool format using exact Action_20250124 names."""
    # Map the exact action names back to the unified computer tool
    function_to_action_mapping = {
        # Basic actions from Action_20241022
        "screenshot": ("computer", {"action": "screenshot"}),
        "cursor_position": ("computer", {"action": "cursor_position"}),

        # Click actions from Action_20241022
        "left_click": ("computer", {"action": "left_click", "coordinate": tool_input.get("coordinate")}),
        "right_click": ("computer", {"action": "right_click", "coordinate": tool_input.get("coordinate")}),
        "double_click": ("computer", {"action": "double_click", "coordinate": tool_input.get("coordinate")}),
        "middle_click": ("computer", {"action": "middle_click", "coordinate": tool_input.get("coordinate")}),

        # Mouse actions from Action_20241022
        "mouse_move": ("computer", {"action": "mouse_move", "coordinate": tool_input.get("coordinate")}),
        "left_click_drag": ("computer", {"action": "left_click_drag", "coordinate": tool_input.get("coordinate")}),

        # Keyboard actions from Action_20241022
        "type": ("computer", {"action": "type", "text": tool_input.get("text")}),
        "key": ("computer", {"action": "key", "text": tool_input.get("text")}),

        # New actions from Action_20250124
        "left_mouse_down": ("computer", {"action": "left_mouse_down"}),
        "left_mouse_up": ("computer", {"action": "left_mouse_up"}),
        "scroll": ("computer", {
            "action": "scroll",
            "coordinate": tool_input.get("coordinate"),
            "scroll_direction": tool_input.get("scroll_direction"),
            "scroll_amount": tool_input.get("scroll_amount", 3)
        }),
        "hold_key": ("computer", {
            "action": "hold_key",
            "text": tool_input.get("text"),
            "duration": tool_input.get("duration")
        }),
        "wait": ("computer", {"action": "wait", "duration": tool_input.get("duration")}),
        "triple_click": ("computer", {"action": "triple_click", "coordinate": tool_input.get("coordinate")}),
    }

    if function_name in function_to_action_mapping:
        mapped_name, mapped_input = function_to_action_mapping[function_name]
        # Remove None values
        filtered_input = {k: v for k, v in mapped_input.items() if v is not None}
        print(f"[FUNCTION MAPPING] Mapped '{function_name}' to '{mapped_name}' with action '{filtered_input.get('action')}'")
        return mapped_name, filtered_input

    # For non-computer functions, return as-is
    return function_name, tool_input


def _convert_openai_response_to_anthropic(response) -> BetaMessage:
    """Convert OpenAI response format back to Anthropic format."""
    from anthropic.types.beta import BetaMessage, BetaTextBlock, BetaToolUseBlock, BetaUsage

    content = []
    choice = response.choices[0]
    message = choice.message

    if message.content:
        content.append(BetaTextBlock(type="text", text=message.content))

    if message.tool_calls:
        for tool_call in message.tool_calls:
            import json
            try:
                # Debug: log the raw arguments string
                print(f"[DEBUG] Tool call arguments: '{tool_call.function.arguments}'")

                if not tool_call.function.arguments or tool_call.function.arguments.strip() == "":
                    print(f"[DEBUG] Empty arguments for tool {tool_call.function.name}, using empty dict")
                    tool_input = {}
                else:
                    tool_input = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as e:
                print(f"[DEBUG] JSON decode error for tool {tool_call.function.name}: {e}")
                print(f"[DEBUG] Raw arguments: '{tool_call.function.arguments}'")
                # Use empty dict as fallback
                tool_input = {}

            # Apply function mapping to convert separate functions back to unified computer tool
            mapped_name, mapped_input = _map_openrouter_function_to_anthropic(
                tool_call.function.name, tool_input
            )

            content.append(BetaToolUseBlock(
                type="tool_use",
                id=tool_call.id,
                name=mapped_name,
                input=mapped_input
            ))

    # Map OpenAI finish_reason to Anthropic stop_reason
    finish_reason = choice.finish_reason
    if finish_reason == "stop":
        stop_reason = "end_turn"
    elif finish_reason == "tool_calls":
        stop_reason = "tool_use"
    elif finish_reason == "length":
        stop_reason = "max_tokens"
    else:
        stop_reason = "end_turn"  # Default fallback

    # Convert OpenAI usage to Anthropic usage format
    openai_usage = response.usage
    anthropic_usage = BetaUsage(
        input_tokens=openai_usage.prompt_tokens,
        output_tokens=openai_usage.completion_tokens
    )

    return BetaMessage(
        id=response.id,
        content=content,
        model=response.model,
        role="assistant",
        stop_reason=stop_reason,
        type="message",
        usage=anthropic_usage
    )


class APIProvider(StrEnum):
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    VERTEX = "vertex"
    OPENROUTER = "openrouter"

# This system prompt is optimized for the Docker environment in this repository and
# specific tool combinations enabled.
# We encourage modifying this system prompt to ensure the model has context for the
# environment it is running in, and to provide any additional information that may be
# helpful for the task at hand.
SYSTEM_PROMPT = f"""<SYSTEM_CAPABILITY>
* You are utilising an Ubuntu virtual machine using {platform.machine()} architecture with internet access.
* You can feel free to install Ubuntu applications with your bash tool. Use curl instead of wget.
* To open firefox, please just click on the firefox icon.  Note, firefox-esr is what is installed on your system.
* Using bash tool you can start GUI applications, but you need to set export DISPLAY=:1 and use a subshell. For example "(DISPLAY=:1 xterm &)". GUI apps run with bash tool will appear within your desktop environment, but they may take some time to appear. Take a screenshot to confirm it did.
* When using your bash tool with commands that are expected to output very large quantities of text, redirect into a tmp file and use str_replace_editor or `grep -n -B <lines before> -A <lines after> <query> <filename>` to confirm output.
* When viewing a page it can be helpful to zoom out so that you can see everything on the page.  Either that, or make sure you scroll down to see everything before deciding something isn't available.
* When using your computer function calls, they take a while to run and send back to you.  Where possible/feasible, try to chain multiple of these calls all into one function calls request.
* The current date is {datetime.today().strftime('%A, %B %-d, %Y')}.
</SYSTEM_CAPABILITY>

<IMPORTANT>
* When using Firefox, if a startup wizard appears, IGNORE IT.  Do not even click "skip this step".  Instead, click on the address bar where it says "Search or enter address", and enter the appropriate search term or URL there.
* If the item you are looking at is a pdf, if after taking a single screenshot of the pdf it seems that you want to read the entire document instead of trying to continue to read the pdf from your screenshots + navigation, determine the URL, use curl to download the pdf, install and use pdftotext to convert it to a text file, and then read that text file directly with your StrReplaceEditTool.
</IMPORTANT>"""


async def sampling_loop(
    *,
    model: str,
    provider: APIProvider,
    system_prompt_suffix: str,
    messages: list[BetaMessageParam],
    output_callback: Callable[[BetaContentBlockParam], None],
    tool_output_callback: Callable[[ToolResult, str], None],
    api_response_callback: Callable[
        [httpx.Request, httpx.Response | object | None, Exception | None], None
    ],
    api_key: str,
    only_n_most_recent_images: int | None = None,
    max_tokens: int = 4096,
    tool_version: ToolVersion,
    thinking_budget: int | None = None,
    token_efficient_tools_beta: bool = False,
    pre_initialized_tools: Optional[list[BaseAnthropicTool]] = None,
):
    """
    Agentic sampling loop for the assistant/tool interaction of computer use.
    """
    if pre_initialized_tools:
        tool_collection = ToolCollection(*pre_initialized_tools)
    else:
        tool_group = TOOL_GROUPS_BY_VERSION[tool_version]
        tool_collection = ToolCollection(*(ToolCls() for ToolCls in tool_group.tools))

    system = BetaTextBlockParam(
        type="text",
        text=f"{SYSTEM_PROMPT}{' ' + system_prompt_suffix if system_prompt_suffix else ''}",
    )

    conversation_turn = 0
    max_turns = 50  # Safety limit to prevent infinite loops
    while True:
        conversation_turn += 1
        print(f"[LOOP DEBUG] Starting conversation turn {conversation_turn}")
        print(f"[LOOP DEBUG] Current message count: {len(messages)}")

        if conversation_turn > max_turns:
            print(f"[LOOP DEBUG] Hit max turns limit ({max_turns}), ending conversation")
            return messages

        enable_prompt_caching = False
        betas = []
        if pre_initialized_tools:
            # If using pre-initialized tools, use the latest beta flag
            betas = ["computer-use-2025-01-24"]
        else:
            tool_group = TOOL_GROUPS_BY_VERSION[tool_version]
            betas = [tool_group.beta_flag] if tool_group.beta_flag else []

        if token_efficient_tools_beta:
            betas.append("token-efficient-tools-2025-02-19")
        # Set a reasonable default for image truncation threshold
        image_truncation_threshold = 10  # Remove images in chunks of 10

        print(f"[LOOP DEBUG] Setting up client for provider: {provider}")
        if provider == APIProvider.ANTHROPIC:
            client = AsyncAnthropic(api_key=api_key, max_retries=4)
            enable_prompt_caching = True
        elif provider == APIProvider.VERTEX:
            client = AsyncAnthropicVertex()
        elif provider == APIProvider.BEDROCK:
            client = AsyncAnthropicBedrock()
        elif provider == APIProvider.OPENROUTER:
            # OpenRouter uses OpenAI-compatible API
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com/your-repo/plato-client",
                    "X-Title": "Plato Client",
                    "anthropic-beta": "computer-use-2025-01-24"
                }
            )
            # OpenRouter doesn't support prompt caching
            enable_prompt_caching = False

        if enable_prompt_caching:
            betas.append(PROMPT_CACHING_BETA_FLAG)
            _inject_prompt_caching(messages)
            # Use type ignore to bypass TypedDict check until SDK types are updated
            system["cache_control"] = {"type": "ephemeral"}  # type: ignore

        # Always apply image filtering to prevent exceeding API limits
        # Use only_n_most_recent_images if provided, otherwise use a conservative default
        images_to_keep = only_n_most_recent_images or 90  # Default to 90 to stay under 100 limit
        _maybe_filter_to_n_most_recent_images(
            messages,
            images_to_keep,
            min_removal_threshold=image_truncation_threshold,
        )
        extra_body = {}
        if thinking_budget:
            # Ensure we only send the required fields for thinking
            extra_body = {
                "thinking": {"type": "enabled", "budget_tokens": thinking_budget}
            }

        # Call the API
        # we use raw_response to provide debug information to streamlit. Your
        # implementation may be able call the SDK directly with:
        # `response = client.messages.create(...)` instead.
        import asyncio
        import random

        max_retries = 5
        retry_count = 0
        base_delay = 1.0

        print("[LOOP DEBUG] Starting API call attempt")
        while True:
            print(f"[LOOP DEBUG] API retry attempt {retry_count + 1}/{max_retries}")
            try:
                if provider == APIProvider.OPENROUTER:
                    # Convert messages and tools for OpenRouter/OpenAI format
                    openai_messages = _convert_anthropic_to_openai_messages(messages, system["text"])
                    openai_tools = _convert_anthropic_tools_to_openai(tool_collection)
                    openrouter_model = _map_model_for_openrouter(model)

                    # Use OpenAI format API call
                    response = await client.chat.completions.create(
                        model=openrouter_model,
                        messages=openai_messages,
                        tools=openai_tools if openai_tools else None,
                        max_tokens=max_tokens,
                    )

                    # Convert back to Anthropic format
                    response = _convert_openai_response_to_anthropic(response)

                    # Create a mock raw_response object for compatibility
                    class MockRawResponse:
                        def __init__(self, response):
                            self._response = response
                            # Create mock HTTP response
                            class MockHTTPResponse:
                                def __init__(self):
                                    self.request = None
                            self.http_response = MockHTTPResponse()

                        def parse(self):
                            return self._response

                    raw_response = MockRawResponse(response)
                else:
                    # Use Anthropic format API call
                    raw_response = await client.beta.messages.with_raw_response.create(
                        max_tokens=max_tokens,
                        messages=messages,
                        model=model,
                        system=[system],
                        tools=tool_collection.to_params(),
                        betas=betas,
                        extra_body=extra_body,
                    )
                print("[LOOP DEBUG] API call successful!")
                break  # Success, exit the retry loop
            except (APIStatusError, Exception) as e:
                # Handle both Anthropic and OpenAI errors
                try:
                    if hasattr(e, 'request') and hasattr(e, 'response'):
                        api_response_callback(e.request, e.response, e)
                    else:
                        # Create a mock request for the callback
                        class MockRequest:
                            def __init__(self):
                                self.method = "POST"
                                self.url = "openrouter_api_call"
                        api_response_callback(MockRequest(), None, e)
                except Exception as callback_error:
                    print(f"[DEBUG] Error in api_response_callback: {callback_error}")
                retry_count += 1

                if retry_count >= max_retries:
                    print(f'API ERROR: Maximum retries ({max_retries}) exceeded: {e}')
                    raise e

                # Calculate exponential backoff with jitter
                delay = base_delay * (2 ** (retry_count - 1)) + random.uniform(0, 0.5)
                print(f'API ERROR: {e}. Retrying in {delay:.2f} seconds (attempt {retry_count}/{max_retries})')
                await asyncio.sleep(delay)

        try:
            api_response_callback(
                raw_response.http_response.request, raw_response.http_response, None
            )
        except Exception as callback_error:
            print(f"[DEBUG] Error in api_response_callback: {callback_error}")

        print("[LOOP DEBUG] Parsing API response")
        response = raw_response.parse()

        response_params = _response_to_params(response)
        print(f"[LOOP DEBUG] Response has {len(response_params)} content blocks")

        # Log response content details
        for i, block in enumerate(response_params):
            if block["type"] == "text":
                print(f"[LOOP DEBUG] Block {i}: text ({len(block.get('text', ''))} chars)")
            elif block["type"] == "tool_use":
                print(f"[LOOP DEBUG] Block {i}: tool_use - {block['name']} with input: {str(block.get('input', {}))[:100]}...")

        messages.append(
            {
                "role": "assistant",
                "content": response_params,
            }
        )

        tool_result_content: list[BetaToolResultBlockParam] = []
        tool_use_count = 0
        for content_block in response_params:
            output_callback(content_block)
            if content_block["type"] == "tool_use":
                tool_use_count += 1
                print(f"[LOOP DEBUG] Processing tool use {tool_use_count}: {content_block['name']}")
                tool_input = cast(dict[str, Any], content_block["input"])
                if content_block["name"] == "computer":
                    print(f"[LOOP DEBUG] Computer tool input: {tool_input}")
                    if "action" in tool_input:
                        print(f"[LOOP DEBUG] Action requested: '{tool_input['action']}'")
                result = await tool_collection.run(
                    name=content_block["name"],
                    tool_input=tool_input,
                )
                print(f"[LOOP DEBUG] Tool {content_block['name']} completed")
                print(f"[LOOP DEBUG] Tool result - error: {result.error is not None}, output: {len(result.output or '') if result.output else 0} chars, image: {result.base64_image is not None}")
                if result.output:
                    print(f"[LOOP DEBUG] Tool output preview: {result.output[:200]}...")
                if result.error:
                    print(f"[LOOP DEBUG] Tool error: {result.error[:200]}...")

                tool_result_content.append(
                    _make_api_tool_result(result, content_block["id"])
                )
                tool_output_callback(result, content_block["id"])

        print(f"[LOOP DEBUG] Total tool uses: {tool_use_count}, tool results: {len(tool_result_content)}")

        if not tool_result_content:
            print("[LOOP DEBUG] No tools used, ending conversation loop")
            return messages

        print("[LOOP DEBUG] Adding tool results to messages and continuing conversation")

        # Debug: Log what's in the tool result content
        for i, tool_result in enumerate(tool_result_content):
            content = tool_result.get("content", [])
            if isinstance(content, list):
                text_count = sum(1 for c in content if isinstance(c, dict) and c.get("type") == "text")
                image_count = sum(1 for c in content if isinstance(c, dict) and c.get("type") == "image")
                print(f"[LOOP DEBUG] Tool result {i}: {text_count} text blocks, {image_count} image blocks")
            else:
                print(f"[LOOP DEBUG] Tool result {i}: single content item")

        messages.append({"content": tool_result_content, "role": "user"})


def _maybe_filter_to_n_most_recent_images(
    messages: list[BetaMessageParam],
    images_to_keep: int,
    min_removal_threshold: int,
):
    """
    With the assumption that images are screenshots that are of diminishing value as
    the conversation progresses, remove all but the final `images_to_keep` tool_result
    images in place, with a chunk of min_removal_threshold to reduce the amount we
    break the implicit prompt cache.
    """
    if images_to_keep is None:
        return messages

    tool_result_blocks = cast(
        list[BetaToolResultBlockParam],
        [
            item
            for message in messages
            for item in (
                message["content"] if isinstance(message["content"], list) else []
            )
            if isinstance(item, dict) and item.get("type") == "tool_result"
        ],
    )

    total_images = sum(
        1
        for tool_result in tool_result_blocks
        for content in tool_result.get("content", [])
        if isinstance(content, dict) and content.get("type") == "image"
    )

    images_to_remove = total_images - images_to_keep
    # Ensure we don't exceed the API limit of 100 total media items
    # Leave some buffer for potential new images in this turn
    max_images_allowed = 90  # Conservative limit to stay well under 100
    if images_to_keep > max_images_allowed:
        images_to_keep = max_images_allowed
        images_to_remove = total_images - images_to_keep

    # for better cache behavior, we want to remove in chunks
    # but ensure we remove at least the minimum needed to stay under limit
    if images_to_remove > 0:
        # Remove in chunks of min_removal_threshold, but ensure we remove enough
        chunked_removal = (images_to_remove // min_removal_threshold) * min_removal_threshold
        if chunked_removal < images_to_remove:
            chunked_removal += min_removal_threshold
        images_to_remove = chunked_removal
        print(f"[IMAGE FILTER] Removing {images_to_remove} images to stay under API limits")

    for tool_result in tool_result_blocks:
        if isinstance(tool_result.get("content"), list):
            new_content = []
            for content in tool_result.get("content", []):
                if isinstance(content, dict) and content.get("type") == "image":
                    if images_to_remove > 0:
                        images_to_remove -= 1
                        continue
                new_content.append(content)
            tool_result["content"] = new_content

    # Images have been filtered - no need to track the final count


def _response_to_params(
    response: BetaMessage,
) -> list[BetaContentBlockParam]:
    res: list[BetaContentBlockParam] = []
    for block in response.content:
        if isinstance(block, BetaTextBlock):
            if block.text:
                res.append(BetaTextBlockParam(type="text", text=block.text))
            elif getattr(block, "type", None) == "thinking":
                # Handle thinking blocks - include signature field
                thinking_block = {
                    "type": "thinking",
                    "thinking": getattr(block, "thinking", None),
                }
                if hasattr(block, "signature"):
                    thinking_block["signature"] = getattr(block, "signature", None)
                res.append(cast(BetaContentBlockParam, thinking_block))
        else:
            # Handle tool use blocks normally
            res.append(cast(BetaToolUseBlockParam, block.model_dump()))
    return res


def _inject_prompt_caching(
    messages: list[BetaMessageParam],
):
    """
    Set cache breakpoints for the 3 most recent turns
    one cache breakpoint is left for tools/system prompt, to be shared across sessions
    """

    breakpoints_remaining = 3
    for message in reversed(messages):
        if message["role"] == "user" and isinstance(
            content := message["content"], list
        ):
            if breakpoints_remaining:
                breakpoints_remaining -= 1
                # Use type ignore to bypass TypedDict check until SDK types are updated
                content[-1]["cache_control"] = BetaCacheControlEphemeralParam(  # type: ignore
                    {"type": "ephemeral"}
                )
            else:
                if "cache_control" in content[-1]:
                    content[-1].pop("cache_control")
                # we'll only every have one extra turn per loop
                break


def _make_api_tool_result(
    result: ToolResult, tool_use_id: str
) -> BetaToolResultBlockParam:
    """Convert an agent ToolResult to an API ToolResultBlockParam."""
    tool_result_content: list[BetaTextBlockParam | BetaImageBlockParam] | str = []
    is_error = False
    if result.error:
        is_error = True
        tool_result_content = _maybe_prepend_system_tool_result(result, result.error)
    else:
        if result.output:
            tool_result_content.append(
                {
                    "type": "text",
                    "text": _maybe_prepend_system_tool_result(result, result.output),
                }
            )
        if result.base64_image:
            tool_result_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": result.base64_image,
                    },
                }
            )
    return {
        "type": "tool_result",
        "content": tool_result_content,
        "tool_use_id": tool_use_id,
        "is_error": is_error,
    }


def _maybe_prepend_system_tool_result(result: ToolResult, result_text: str):
    if result.system:
        result_text = f"<system>{result.system}</system>\n{result_text}"
    return result_text
