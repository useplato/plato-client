import asyncio
import inspect
from typing import Any, Awaitable, Callable, Dict, Optional, Sequence

from google.genai import types

from plato.models.env import PlatoEnvironment
from ..anthropic.tools import BaseAnthropicTool

from .agent import GeminiBrowserAgent
from .computer import GeminiComputerBridge
from ..openai.computers.remote_playwright import RemotePlaywrightComputer


def _extract_function_declaration(tool: BaseAnthropicTool) -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name=tool.name,
        description=getattr(tool, "_description", ""),
        parameters=getattr(tool, "_input_schema", {}),
    )


async def run_gemini_cua_task(
    cdp_url: str,
    prompt: str,
    start_url: str,
    env: PlatoEnvironment,
    tools: Sequence[BaseAnthropicTool] | None = None,
    action_callback: Callable[[dict[str, Any]], Awaitable[None] | None] | None = None,
    message_callback: Callable[[dict[str, Any]], Awaitable[None] | None] | None = None,
    model: str = "gemini-2.5-computer-use-preview-10-2025",
    search_engine_url: str = "https://www.google.com",
) -> Optional[dict[str, Any]]:
    loop = asyncio.get_running_loop()

    async def emit_message(message: dict[str, Any]) -> None:
        await env.log(message)
        if message_callback:
            maybe = message_callback(message)
            if inspect.iscoroutine(maybe):
                await maybe

    last_assistant_text: list[str] = []

    def make_sync_emitter() -> Callable[[str], None]:
        def _emit(text: str) -> None:
            last_assistant_text.append(text)
            message = {"role": "assistant", "content": [{"type": "text", "text": text}]}
            future = asyncio.run_coroutine_threadsafe(emit_message(message), loop)
            future.result()

        return _emit

    async def dispatch_action(payload: dict[str, Any]) -> None:
        if action_callback:
            maybe = action_callback(payload)
            if inspect.iscoroutine(maybe):
                await maybe

    async with RemotePlaywrightComputer(cdp_url) as computer:
        page = getattr(computer, "_page", None)
        if page:
            await page.goto(start_url)
            try:
                await env.login(page)
            except Exception as exc:  # pragma: no cover - environment dependent
                print(f"Error logging in with Gemini runner: {exc}")

        # Send baseline event so mutation tracking aligns with other agents.
        await dispatch_action({"type": "baseline"})

        bridge = GeminiComputerBridge(
            loop=loop,
            computer=computer,
            action_callback=dispatch_action,
            search_engine_url=search_engine_url,
        )

        function_declarations: list[types.FunctionDeclaration] = []
        function_handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

        for tool in tools or []:
            if not isinstance(tool, BaseAnthropicTool):
                continue
            function_declarations.append(_extract_function_declaration(tool))

            handler = getattr(tool, "_handler", None)
            if handler is None:
                continue

            def sync_handler(args: Dict[str, Any], *, _handler=handler):
                result = _handler(args)
                if inspect.iscoroutine(result):
                    future = asyncio.run_coroutine_threadsafe(result, loop)
                    result = future.result()
                # Gemini expects plain dict serialisable payloads.
                if isinstance(result, str):
                    return {"message": result}
                return result or {"status": "ok"}

            function_handlers[tool.name] = sync_handler

        async def log_initial_prompt() -> None:
            user_message = {"role": "user", "content": [{"type": "text", "text": prompt}]}
            await emit_message(user_message)

        await log_initial_prompt()

        agent = GeminiBrowserAgent(
            browser_computer=bridge,
            query=prompt,
            model_name=model,
            function_declarations=function_declarations,
            function_handlers=function_handlers,
            on_assistant_text=make_sync_emitter(),
            verbose=True,
        )

        try:
            await asyncio.to_thread(agent.agent_loop)
        finally:
            pass

        final_text = agent.final_reasoning or (last_assistant_text[-1] if last_assistant_text else None)
        if final_text:
            final_message = {
                "role": "assistant",
                "content": [{"type": "text", "text": final_text}],
            }
            return final_message

    return None
