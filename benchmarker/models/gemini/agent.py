import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional, Union

from google.genai import types, Client

# Suppress repetitive AFC logging from google_genai
logging.getLogger("google_genai.models").setLevel(logging.WARNING)
from google.genai.types import (
    Candidate,
    Content,
    FinishReason,
    FunctionCall,
    FunctionResponse,
    GenerateContentConfig,
    Part,
)

from .computer import EnvState, GeminiComputerBridge

MAX_RECENT_TURNS_WITH_SCREENSHOTS = 3
PREDEFINED_COMPUTER_USE_FUNCTIONS = {
    "open_web_browser",
    "click_at",
    "hover_at",
    "type_text_at",
    "scroll_document",
    "scroll_at",
    "wait_5_seconds",
    "go_back",
    "go_forward",
    "search",
    "navigate",
    "key_combination",
    "drag_and_drop",
}

FunctionHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


class GeminiBrowserAgent:
    """Slightly modified Google Computer-Use agent with instrumentation hooks."""

    def __init__(
        self,
        *,
        browser_computer: GeminiComputerBridge,
        query: str,
        model_name: str,
        function_declarations: Optional[List[types.FunctionDeclaration]] = None,
        function_handlers: Optional[Dict[str, FunctionHandler]] = None,
        on_assistant_text: Optional[Callable[[str], None]] = None,
        verbose: bool = False,
        temperature: float = 1.0,
        top_p: float = 0.95,
        top_k: int = 40,
        max_output_tokens: int = 8192,
    ):
        self._browser_computer = browser_computer
        self._query = query
        self._model_name = model_name
        self._verbose = verbose
        self._on_assistant_text = on_assistant_text
        self._function_handlers = function_handlers or {}
        self.final_reasoning: Optional[str] = None

        self._client = Client(
            api_key=os.environ.get("GEMINI_API_KEY"),
            # project=os.environ.get("VERTEXAI_PROJECT"),
            # location=os.environ.get("VERTEXAI_LOCATION"),
        )

        self._contents: List[Content] = [
            Content(
                role="user",
                parts=[Part(text=self._query)],
            )
        ]

        self._generate_content_config = GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens,
            tools=[
                types.Tool(
                    computer_use=types.ComputerUse(
                        environment=types.Environment.ENVIRONMENT_BROWSER,
                        excluded_predefined_functions=[],
                    )
                ),
            ],
        )

        if function_declarations:
            self._generate_content_config.tools.append(
                types.Tool(function_declarations=function_declarations)
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _emit_text(self, text: Optional[str]) -> None:
        if not text:
            return
        if self._on_assistant_text:
            self._on_assistant_text(text)

    def _get_model_response(
        self,
        max_retries: int = 5,
        base_delay_s: float = 1,
    ) -> types.GenerateContentResponse:
        for attempt in range(max_retries):
            try:
                return self._client.models.generate_content(
                    model=self._model_name,
                    contents=self._contents,
                    config=self._generate_content_config,
                )
            except Exception as exc:  # pragma: no cover - network errors
                if attempt >= max_retries - 1:
                    raise
                delay = base_delay_s * (2**attempt)
                if self._verbose:
                    print(
                        f"Gemini generate_content failed (attempt {attempt + 1}/{max_retries}): {exc}. "
                        f"Retrying in {delay:.1f}s."
                    )
                time.sleep(delay)
        raise RuntimeError("Exceeded retry attempts for Gemini response.")

    @staticmethod
    def _get_text(candidate: Candidate) -> Optional[str]:
        if not candidate.content or not candidate.content.parts:
            return None
        parts: List[str] = []
        for part in candidate.content.parts:
            if part.text:
                parts.append(part.text)
        return " ".join(parts) or None

    @staticmethod
    def _extract_function_calls(candidate: Candidate) -> List[FunctionCall]:
        if not candidate.content or not candidate.content.parts:
            return []
        calls: List[FunctionCall] = []
        for part in candidate.content.parts:
            if part.function_call:
                calls.append(part.function_call)
        return calls

    def _handle_safety(self, payload: Dict[str, Any]) -> None:
        # Auto-acknowledge safety confirmations to keep automation hands-free.
        if self._verbose:
            explanation = payload.get("explanation", "")
            print(f"Safety confirmation automatically acknowledged. {explanation}")

    def _function_response_from_state(
        self,
        action_name: str,
        state: Union[EnvState, Dict[str, Any]],
        extra_response_fields: Optional[Dict[str, Any]] = None,
    ) -> FunctionResponse:
        extra_response_fields = extra_response_fields or {}
        if isinstance(state, EnvState):
            return FunctionResponse(
                name=action_name,
                response={"url": state.url, **extra_response_fields},
                parts=[
                    types.FunctionResponsePart(
                        inline_data=types.FunctionResponseBlob(
                            mime_type="image/png", data=state.screenshot
                        )
                    )
                ],
            )
        return FunctionResponse(name=action_name, response=state)

    def _apply_screenshot_retention_policy(self) -> None:
        seen_turns = 0
        for content in reversed(self._contents):
            if content.role != "user":
                continue
            if not content.parts:
                continue
            has_screenshot = False
            for part in content.parts:
                fr = part.function_response
                if fr and fr.parts and fr.name in PREDEFINED_COMPUTER_USE_FUNCTIONS:
                    has_screenshot = True
                    break
            if has_screenshot:
                seen_turns += 1
                if seen_turns > MAX_RECENT_TURNS_WITH_SCREENSHOTS:
                    for part in content.parts:
                        fr = part.function_response
                        if (
                            fr
                            and fr.parts
                            and fr.name in PREDEFINED_COMPUTER_USE_FUNCTIONS
                        ):
                            fr.parts = None

    # ------------------------------------------------------------------
    # Primary loop
    # ------------------------------------------------------------------
    def run_one_iteration(self) -> str:
        if self._verbose:
            print("Requesting Gemini Computer Use response...")

        response = self._get_model_response()
        if not response.candidates:
            raise RuntimeError("Gemini returned no candidates.")

        candidate = response.candidates[0]
        if candidate.content:
            self._contents.append(candidate.content)

        reasoning = self._get_text(candidate)
        self._emit_text(reasoning)
        
        # Log reasoning when verbose mode is enabled
        if reasoning and self._verbose:
            print(f"[Gemini] Reasoning: {reasoning}")

        function_calls = self._extract_function_calls(candidate)

        if (
            not reasoning
            and not function_calls
            and candidate.finish_reason == FinishReason.MALFORMED_FUNCTION_CALL
        ):
            return "CONTINUE"

        if not function_calls:
            self.final_reasoning = reasoning
            return "COMPLETE"

        function_responses: List[FunctionResponse] = []
        for function_call in function_calls:
            extra_fields: Dict[str, Any] = {}
            args = dict(function_call.args or {})

            safety_decision = args.pop("safety_decision", None)
            if safety_decision:
                self._handle_safety(safety_decision)
                extra_fields["safety_acknowledgement"] = "true"

            if hasattr(self._browser_computer, function_call.name):
                # Log action being executed
                if self._verbose:
                    print(f"[Gemini] Executing action: {function_call.name} with args: {args}")
                method = getattr(self._browser_computer, function_call.name)
                state = method(**args)
                function_responses.append(
                    self._function_response_from_state(
                        function_call.name, state, extra_fields
                    )
                )
            elif function_call.name in self._function_handlers:
                handler = self._function_handlers[function_call.name]
                result = handler(args)
                function_responses.append(
                    self._function_response_from_state(
                        function_call.name, result, extra_fields
                    )
                )
            else:
                raise ValueError(f"Unsupported function: {function_call.name}")

        self._contents.append(
            Content(
                role="user",
                parts=[Part(function_response=fr) for fr in function_responses],
            )
        )

        self._apply_screenshot_retention_policy()
        return "CONTINUE"

    def agent_loop(self) -> None:
        status = "CONTINUE"
        while status == "CONTINUE":
            status = self.run_one_iteration()
