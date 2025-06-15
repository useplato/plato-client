import asyncio
import time
from pathlib import Path

from plato.sdk import Plato
from dotenv import load_dotenv

load_dotenv('.env')

async def test_public_url():
    """Test the get_public_url functionality with keepalive and alias."""
    print("Starting public URL test with keepalive and alias...")
    
    try:
        # Initialize the client
        print("Initializing Plato client...")
        client = Plato()
        
        # Create and initialize the environment with keepalive and alias
        print("Creating environment with keepalive=True and alias='public-url-test'...")
        env = await client.make_environment(
            "espocrm", 
            interface_type=None,
            keepalive=True,
            alias="public-url-test"
        )
        print(f"Environment ID: {env.id}")
        
        try:
            # Wait for the environment to be ready
            print("Waiting for environment to be ready...")
            await env.wait_for_ready(timeout=300.0)
            print("Environment ready!")

            # Reset the environment
            print("Resetting environment...")
            await env.reset()
            print("Environment reset complete!")
            
            # Test the new get_public_url method
            print("Fetching public URL...")
            public_url = await env.get_public_url()
            
            print("\n" + "="*60)
            print("PUBLIC URL TEST RESULTS")
            print("="*60)
            print(f"Environment ID: {env.id}")
            print(f"Public URL: {public_url}")
            print(f"Keepalive: True")
            print(f"Alias: public-url-test")
            print("="*60)
            
            # Log the result
            await env.log({
                "message": "Public URL test completed with keepalive and alias",
                "environment_id": env.id,
                "public_url": public_url,
                "keepalive": True,
                "alias": "public-url-test"
            }, "info")
            
            # Wait for user input before closing
            print("\nPress Enter to close the environment and exit...")
            input()
            
        finally:
            # Always ensure we close the environment
            print("Closing environment...")
            await env.close()
            print("Environment closed")
            
            # Close the client to cleanup aiohttp session
            await client.close()
            print("Client closed")
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        raise

    print("Public URL test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_public_url())
