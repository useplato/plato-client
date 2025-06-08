import asyncio
import time
from pathlib import Path

from playwright.async_api import async_playwright
from plato.sdk import Plato

from dotenv import load_dotenv

load_dotenv('.env')

# Create necessary directories at startup
SCREENSHOTS_DIR = Path("screenshots/espocrm_backup")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

async def test_espocrm_backup():
    """Test creating a backup of an EspoCRM environment."""
    
    try:
        # Initialize the client
        client = Plato()
        
        # Create and initialize the EspoCRM environment
        env = await client.make_environment("espocrm")
        print(f"Environment ID: {env.id}")
        
        try:
            # Wait for the environment to be ready
            print("Waiting for environment to be ready...")
            await env.wait_for_ready(timeout=300.0)
            print("Environment ready")
            
            # Reset the environment
            await env.reset()
            print("Environment reset")
            
            # Get the CDP URL for browser connection
            print("Getting CDP URL...")
            cdp_url = await env.get_cdp_url()
            
            # Get live view URL
            live_url = await client.get_live_view_url(env.id)
            print(f"Live view URL: {live_url}")
            
            # Connect to browser and perform some basic actions
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(cdp_url)
                context = browser.contexts[0]
                page = context.pages[0]
                print("Connected to browser")
                
                # Wait for page to load
                await page.wait_for_timeout(3000)
                
                # Take screenshot before backup
                await page.screenshot(path=str(SCREENSHOTS_DIR / "before_backup.png"))
                print("Screenshot taken before backup")
                
                # Navigate to EspoCRM if not already there
                try:
                    # Try to find EspoCRM login elements or navigate to it
                    current_url = page.url
                    print(f"Current URL: {current_url}")
                    
                    # If we're not on EspoCRM, try to navigate to it
                    if "espocrm" not in current_url.lower():
                        await page.goto("http://localhost/")
                        await page.wait_for_timeout(2000)
                    
                    # Take screenshot after navigation
                    await page.screenshot(path=str(SCREENSHOTS_DIR / "after_navigation.png"))
                    print("Screenshot taken after navigation")
                    
                except Exception as nav_error:
                    print(f"Navigation error (continuing): {nav_error}")
                
                # Get initial state
                initial_state = await env.get_state()
                print(f"Initial state retrieved")
                
            # Now test the backup functionality
            print("Creating backup...")
            backup_start_time = time.time()
            
            try:
                backup_result = await env.backup()
                backup_end_time = time.time()
                backup_duration = backup_end_time - backup_start_time
                
                print(f"Backup completed successfully in {backup_duration:.2f} seconds")
                print(f"Backup result: {backup_result}")
                
                # Verify backup result structure
                if isinstance(backup_result, dict):
                    print("✓ Backup returned a dictionary response")
                    
                    # Log any relevant information from the backup result
                    for key, value in backup_result.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"⚠ Unexpected backup result type: {type(backup_result)}")
                
                # Get state after backup to compare
                post_backup_state = await env.get_state()
                print("State retrieved after backup")
                
                # Take a final screenshot
                async with async_playwright() as p:
                    browser = await p.chromium.connect_over_cdp(cdp_url)
                    context = browser.contexts[0]
                    page = context.pages[0]
                    await page.screenshot(path=str(SCREENSHOTS_DIR / "after_backup.png"))
                    print("Final screenshot taken")
                
                print("✓ Backup test completed successfully")
                return True
                
            except Exception as backup_error:
                print(f"✗ Backup failed: {backup_error}")
                return False
            
        finally:
            # Always ensure we close the environment
            await env.close()
            print("Environment closed")
            
            # Close the client to cleanup aiohttp session
            await client.close()
            print("Client closed")
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        return False

async def test_multiple_backups():
    """Test creating multiple backups to ensure consistency."""
    
    print("Testing multiple backups...")
    
    try:
        client = Plato()
        env = await client.make_environment("espocrm")
        
        try:
            await env.wait_for_ready(timeout=300.0)
            await env.reset()
            
            # Create multiple backups
            backup_results = []
            for i in range(3):
                print(f"Creating backup {i+1}/3...")
                backup_result = await env.backup()
                backup_results.append(backup_result)
                print(f"Backup {i+1} completed")
                
                # Small delay between backups
                await asyncio.sleep(1)
            
            print(f"✓ All {len(backup_results)} backups completed successfully")
            
            # Log results
            for i, result in enumerate(backup_results, 1):
                print(f"Backup {i} result: {result}")
                
            return True
            
        finally:
            await env.close()
            await client.close()
            
    except Exception as e:
        print(f"Multiple backup test failed: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("ESPOCRM BACKUP TEST")
    print("="*60)
    
    # Run single backup test
    success1 = asyncio.run(test_espocrm_backup())
    
    print("\n" + "="*60)
    print("MULTIPLE BACKUPS TEST")
    print("="*60)
    
    # Run multiple backup test
    success2 = asyncio.run(test_multiple_backups())
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    print(f"Single backup test: {'✓ PASSED' if success1 else '✗ FAILED'}")
    print(f"Multiple backup test: {'✓ PASSED' if success2 else '✗ FAILED'}")
    print(f"Overall result: {'✓ ALL TESTS PASSED' if success1 and success2 else '✗ SOME TESTS FAILED'}")
    print("="*60) 