from typing import Optional
from anthropic.types.beta import BetaMessageParam

from .loop import sampling_loop, APIProvider
from .tools import ToolResult, ComputerBrowserTool20250124

def default_tool_output_callback(result: ToolResult, tool_id: str):
  # print(f"\nTool Output (ID: {tool_id}):")
  if result.output:
    # print(f"Output: {result.output}")
    pass
  if result.error:
    print(f"Error: {result.error}")
    pass
  if result.system:
    print(f"System: {result.system}")
  # print("-" * 50)


class AnthropicAgent:
  def __init__(
    self,
    api_key: str,
    model: str = "claude-3-7-sonnet-20250219",
    max_tokens: int = 4096,
    thinking_budget: Optional[int] = None,
  ):
    self.api_key = api_key
    self.model = model
    self.max_tokens = max_tokens
    self.thinking_budget = thinking_budget
    self.output_callback = lambda x: None  # We don't print model outputs
    self.tool_output_callback = default_tool_output_callback
    self.api_response_callback = lambda x, y, z: None

  async def run(self, prompt: str, browser_tool: Optional[ComputerBrowserTool20250124] = None, cdp_url: Optional[str] = None):
    """Run the agent with a prompt and either a pre-initialized browser tool or CDP URL.

    Args:
        prompt: The user's instruction/prompt
        browser_tool: Optional pre-initialized ComputerBrowserTool instance
        cdp_url: Optional Chrome DevTools Protocol URL for browser control (used only if browser_tool is None)
    """
    if not browser_tool and not cdp_url:
      raise ValueError("Either browser_tool or cdp_url must be provided")

    if not browser_tool:
      assert cdp_url is not None  # for type checking
      browser_tool = ComputerBrowserTool20250124(cdp_url=cdp_url)

    # Initialize messages with the user's prompt
    messages: list[BetaMessageParam] = [
      {
        "role": "user",
        "content": prompt,
      }
    ]

    # Create a custom system prompt that includes browser-specific instructions
    system_prompt_suffix = """
    <BROWSER_CAPABILITY>
    * You have access to a browser through Chrome DevTools Protocol (CDP).
    * You can control the browser to navigate pages, click elements, type text, etc.
    * All browser interactions are handled through Playwright.
    * Screenshots will be taken automatically after most actions to show the results.
    </BROWSER_CAPABILITY>
    """

    # Override tool version to use the latest computer browser tool
    tool_version = "computer_use_20250124"

    # Run the sampling loop with the browser tool
    async with browser_tool:
      messages = await sampling_loop(
        model=self.model,
        provider=APIProvider.OPENROUTER,
        system_prompt_suffix=system_prompt_suffix,
        messages=messages,
        output_callback=self.output_callback,
        tool_output_callback=self.tool_output_callback,
        api_response_callback=self.api_response_callback,
        api_key=self.api_key,
        max_tokens=self.max_tokens,
        thinking_budget=self.thinking_budget,
        tool_version=tool_version,
        token_efficient_tools_beta=True,
        pre_initialized_tools=[browser_tool],
      )

      if len(messages) > 0:
        print(f'DONE running {len(messages)} messages')

    return messages
