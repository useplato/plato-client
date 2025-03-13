import asyncio
from plato.client import PlatoClient
from plato.models import PlatoEnvironment, PlatoTask

async def test_environment_lifecycle():
    """Test the lifecycle of a Plato environment including creation, reset, and closure."""
    # Initialize the client
    client = PlatoClient()
    
    # Create a sample task
    task = PlatoTask(
        name="example_task",
        metadata={"type": "test"},
        initial_state={"url": "https://example.com"}
    )
    
    # Create and initialize the environment
    env = await client.make_environment("doordash")
    
    try:
        # Wait for the environment to be ready
        await env.wait_for_ready(timeout=30.0)
        
        # Get the CDP URL for browser connection
        cdp_url = await env.get_cdp_url()
        print(f"Environment ready with CDP URL: {cdp_url}")
        
        # Reset the environment with a new task
        await env.reset()
        print("Environment reset with new task")
        breakpoint()

    finally:
        # Always ensure we close the environment
        await env.close()
        print("Environment closed")
        # Close the client to cleanup aiohttp session
        await client.close()
        print("Client closed")

if __name__ == "__main__":
    asyncio.run(test_environment_lifecycle()) 