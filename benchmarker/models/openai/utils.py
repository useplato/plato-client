import os
import aiohttp
import asyncio
import time
from dotenv import load_dotenv
import json
# from PIL import Image
from urllib.parse import urlparse

load_dotenv(override=True)

BLOCKED_DOMAINS = [
    "maliciousbook.com",
    "evilvideos.com",
    "darkwebforum.com",
    "shadytok.com",
    "suspiciouspins.com",
    "ilanbigio.com",
]


async def pp(obj):
    print(json.dumps(obj, indent=4))


# def show_image(base_64_image):
#     image_data = base64.b64decode(base_64_image)
#     image = Image.open(BytesIO(base_64_image))
#     image.show()


# def calculate_image_dimensions(base_64_image):
#     image_data = base64.b64decode(base_64_image)
#     image = Image.open(io.BytesIO(image_data))
#     return image.size


async def sanitize_message(msg: dict) -> dict:
    """Return a copy of the message with image_url omitted for computer_call_output messages."""
    if msg.get("type") == "computer_call_output":
        output = msg.get("output", {})
        if isinstance(output, dict):
            sanitized = msg.copy()
            sanitized["output"] = {**output, "image_url": "[omitted]"}
            return sanitized
    return msg


async def create_response(**kwargs):
    """
    Send a request to the OpenAI API with retry logic.
    Retries for up to 1 minute with exponential backoff on rate limits and server errors.
    """
    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }

    openai_org = os.getenv("OPENAI_ORG")
    if openai_org:
        headers["Openai-Organization"] = openai_org

    max_retry_time = 60  # Maximum retry time in seconds
    start_time = time.time()
    retry_count = 0
    base_delay = 1  # Start with 1 second delay
    max_delay = 10  # Cap the delay at 10 seconds
    last_response = None

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.post(url, headers=headers, json=kwargs) as response:
                    last_response = response
                    response_json = await response.json()

                    if response.status == 200:
                        return response_json

                    error_text = await response.text()
                    print(f"Error: {response.status} {error_text}")

                    # If we get a 429 (rate limit) or 5xx (server error), retry
                    if response.status == 429 or 500 <= response.status < 600:
                        elapsed_time = time.time() - start_time
                        if elapsed_time >= max_retry_time:
                            print(f"Retry time exceeded {max_retry_time} seconds. Giving up after {retry_count} retries.")
                            # Return the last response JSON to maintain compatibility
                            # If it doesn't have the expected structure, create a compatible one
                            if "output" not in response_json or not isinstance(response_json["output"], list):
                                return {
                                    "output": [
                                        {
                                            "type": "message",
                                            "content": f"Request failed after {retry_count} retries: {response.status} {error_text}"
                                        }
                                    ]
                                }
                            return response_json

                        retry_count += 1
                        # Calculate delay with exponential backoff (with jitter)
                        delay = min(base_delay * (2 ** (retry_count - 1)) * (0.9 + 0.2 * asyncio.get_event_loop().time() % 1), max_delay)
                        remaining_time = max_retry_time - elapsed_time
                        delay = min(delay, remaining_time)  # Don't wait longer than our remaining time

                        print(f"Retrying request (attempt {retry_count}) after {delay:.2f}s delay. Elapsed time: {elapsed_time:.2f}s")
                        await asyncio.sleep(delay)
                        continue

                    return response_json

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                elapsed_time = time.time() - start_time
                if elapsed_time >= max_retry_time:
                    print(f"Retry time exceeded {max_retry_time} seconds. Giving up after {retry_count} retries.")
                    # If we have a last response, return its JSON, otherwise create a compatible error response
                    if last_response:
                        try:
                            response_json = await last_response.json()
                            if "output" in response_json and isinstance(response_json["output"], list):
                                return response_json
                        except:
                            pass

                    # Create a response that matches the expected structure
                    return {
                        "output": [
                            {
                                "type": "message",  # Changed from "error"
                                "content": f"Request failed after {retry_count} retries: {str(e)}"
                            }
                        ]
                    }

                retry_count += 1
                delay = min(base_delay * (2 ** (retry_count - 1)) * (0.9 + 0.2 * asyncio.get_event_loop().time() % 1), max_delay)
                remaining_time = max_retry_time - elapsed_time
                delay = min(delay, remaining_time)

                print(f"Connection error: {str(e)}. Retrying (attempt {retry_count}) after {delay:.2f}s delay. Elapsed time: {elapsed_time:.2f}s")
                await asyncio.sleep(delay)


async def check_blocklisted_url(url: str) -> None:
    """Raise ValueError if the given URL (including subdomains) is in the blocklist."""
    hostname = urlparse(url).hostname or ""
    if any(
        hostname == blocked or hostname.endswith(f".{blocked}")
        for blocked in BLOCKED_DOMAINS
    ):
        raise ValueError(f"Blocked URL: {url}")
