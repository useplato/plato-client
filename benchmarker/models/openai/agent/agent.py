import asyncio
from models.openai.computers import Computer
from models.openai.utils import (
    create_response,
    # show_image,
    pp,
    sanitize_message,
    check_blocklisted_url,
)
import json
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class Agent:
    """
    A sample agent class that can be used to interact with a computer.

    (See simple_cua_loop.py for a simple example without an agent.)
    """

    def __init__(
        self,
        model="computer-use-preview",
        computer: Optional[Computer] = None,
        tools: list[dict] = [],
        acknowledge_safety_check_callback: Callable[[str], bool] = lambda msg: False,
    ):
        self.model = model
        self.computer = computer
        self.tools = tools
        self.print_steps = True
        self.debug = False
        self.show_images = False
        self.acknowledge_safety_check_callback = acknowledge_safety_check_callback

        if computer:
            self.tools += [
                {
                    "type": "computer-preview",
                    "display_width": computer.dimensions[0],
                    "display_height": computer.dimensions[1],
                    "environment": computer.environment,
                },
            ]

    def debug_print(self, *args):
        if self.debug:
            asyncio.run(pp(*args))

    async def handle_item(self, item):
        """Handle each item; may cause a computer action + screenshot."""
        if item["type"] == "message":
            if self.print_steps:
                print(item["content"][0]["text"])

        if item["type"] == "reasoning":
            if self.print_steps:
                reasoning_content = item.get("reasoning", "")
                print(f"[Reasoning] {reasoning_content}")

        if item["type"] == "function_call":
            name, args = item["name"], json.loads(item["arguments"])
            if self.print_steps:
                print(f"{name}({args})")

            if self.computer and hasattr(self.computer, name):
                method = getattr(self.computer, name)
                if asyncio.iscoroutinefunction(method):
                    await method(**args)
                else:
                    method(**args)
            return [
                {
                    "type": "function_call_output",
                    "call_id": item["call_id"],
                    "output": "success",  # hard-coded output for demo
                }
            ]

        if item["type"] == "computer_call":
            if not self.computer:
                raise ValueError("Computer object not provided to Agent")

            action = item["action"]
            action_type = action["type"]
            action_args = {k: v for k, v in action.items() if k != "type"}
            if self.print_steps:
                print(f"{action_type}({action_args})")

            method = getattr(self.computer, action_type)
            if asyncio.iscoroutinefunction(method):
                await method(**action_args)
            else:
                method(**action_args)

            screenshot_base64 = await self.computer.screenshot()
            # if self.show_images:
            #     show_image(screenshot_base64)

            # if user doesn't ack all safety checks exit with error
            pending_checks = item.get("pending_safety_checks", [])
            # for check in pending_checks:
            #     message = check["message"]
            #     if not self.acknowledge_safety_check_callback(message):
            #         raise ValueError(
            #             f"Safety check failed: {message}. Cannot continue with unacknowledged safety checks."
            #         )

            call_output = {
                "type": "computer_call_output",
                "call_id": item["call_id"],
                "acknowledged_safety_checks": pending_checks,
                "output": {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{screenshot_base64}",
                },
            }

            # additional URL safety checks for browser environments
            if self.computer.environment == "browser":
                # Do not await here - get_current_url is sync
                current_url = self.computer.get_current_url()
                await check_blocklisted_url(current_url)
                call_output["output"]["current_url"] = current_url

            return [call_output]
        return []

    async def run_full_turn(
        self, input_items, print_steps=True, debug=False, show_images=False
    ):
        self.print_steps = print_steps
        self.debug = debug
        self.show_images = show_images
        new_items = []

        # keep looping until we get a final response
        while new_items[-1].get("role") != "assistant" if new_items else True:
            self.debug_print([await sanitize_message(msg) for msg in input_items + new_items])

            response = await create_response(
                model=self.model,
                input=input_items + new_items,
                tools=self.tools,
                truncation="auto",
            )
            self.debug_print(response)

            if "output" not in response and self.debug:
                print(response)
                raise ValueError("No output from model")
            else:
                new_items += response["output"]
                for item in response["output"]:
                    new_items += await self.handle_item(item)

        return new_items

    async def run_in_loop(self, prompt, max_steps=30):
        """Run the agent in a loop, processing user input and generating responses.

        Args:
            prompt: Initial user prompt
            max_steps: Maximum number of interaction steps before stopping
        """
        if not self.computer:
            raise ValueError("Computer object not provided to Agent for run_in_loop")

        items = [{"role": "user", "content": prompt}]

        tools = [
            {
                "type": "computer-preview",
                "display_width": self.computer.dimensions[0],
                "display_height": self.computer.dimensions[1],
                "environment": self.computer.environment,
            }
        ]

        current_step = 0

        while current_step < max_steps:  # keep looping until we get a final response
            response = await create_response(
                model="computer-use-preview",
                input=items,
                tools=tools,
                truncation="auto",
            )

            if "output" not in response:
                print(response)
                current_step += 1
                continue

            items += response["output"]

            for item in response["output"]:
                items += await self.handle_item(item)

            if items[-1].get("role") == "assistant":
                logger.info(f"assistant: {items[-1]}")
                contents = items[-1].get("content", [])
                content = contents[-1]["text"] if contents else ""
                if "?" in content or "unable" in content.lower():
                    items.append({"role": "user", "content": "continue"})
                else:
                    break

            current_step += 1

        return items

    async def run_in_loop_generator(self, prompt, max_steps=30):
        """Run the agent in a loop, processing user input and generating responses.
        This is an async generator version that yields each item as it's processed.

        Args:
            prompt: Initial user prompt
            max_steps: Maximum number of interaction steps before stopping

        Yields:
            Each item (message, function call, etc.) as it's processed
        """
        if not self.computer:
            raise ValueError("Computer object not provided to Agent for run_in_loop_generator")

        items = [{"role": "user", "content": prompt}]
        # Yield the initial user prompt
        yield items[-1]

        tools = [
            {
                "type": "computer-preview",
                "display_width": self.computer.dimensions[0],
                "display_height": self.computer.dimensions[1],
                "environment": self.computer.environment,
            }
        ]

        current_step = 0

        while current_step < max_steps:  # keep looping until we get a final response
            response = await create_response(
                model="computer-use-preview",
                input=items,
                tools=tools,
                truncation="auto",
            )

            if "output" not in response:
                print(response)
                current_step += 1
                continue

            # Process and yield each output item
            for item in response["output"]:
                items.append(item)
                
                # Don't yield reasoning items immediately - wait to see if there are following items
                if item["type"] != "reasoning":
                    yield item

                # Process any items generated by handle_item
                handle_results = await self.handle_item(item)
                for result in handle_results:
                    items.append(result)
                    # yield result

                # If this was a reasoning item and we have results, yield the reasoning item first, then the results
                if item["type"] == "reasoning" and handle_results:
                    yield item
                    for result in handle_results:
                        yield result
                elif item["type"] == "reasoning" and not handle_results:
                    # If reasoning item has no following items, skip it entirely to avoid API errors
                    pass

            if items[-1].get("role") == "assistant":
                logger.info(f"assistant: {items[-1]}")
                # yield items[-1]
                contents = items[-1].get("content", [])
                content = contents[-1]["text"] if contents else ""
                if "?" in content or "unable" in content.lower():
                    user_continue = {"role": "user", "content": "continue"}
                    items.append(user_continue)
                    yield user_continue
                else:
                    break

            current_step += 1

