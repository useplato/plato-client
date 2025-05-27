import asyncio
import os
import random
import json
from collections import deque
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import logging

from plato import Plato, PlatoTask

load_dotenv(dotenv_path=".env")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# NOTE: When running this script, you MUST clear all existing S3 objects for the respective environment.
# Otherwise, playwright will hit the stored network request and get a cached response, breaking the exploration.

# PLATO_API_URL = os.environ.get("PLATO_API_URL", "http://localhost:8080/api")
PLATO_API_URL = "http://localhost:8080/api"
PLATO_API_KEY = os.environ.get("PLATO_API_KEY")
assert PLATO_API_KEY, "PLATO_API_KEY environment variable is not set. Please set it in your .env file."

# ROOT_URL = "https://www.craigslist.com/"
ROOT_URL = "https://sfbay.craigslist.org/"


MAIN_CATEGORIES = [
    "community", 
    "events",
    "for sale",
    "gigs",
    "housing",
    "jobs",
    "resumes",
    "services"
]

SEARCH_TERMS = [
    "apartment",
    "furniture",
    "electronics",
    "car",
    "bicycle",
    "job",
    "free"
]

REGIONS = ["sfbay"]

async def scroll_page(page):
    """Scroll through the entire page to ensure all lazy-loaded content is visible."""
    await asyncio.sleep(1)
    
    page_height = await page.evaluate('document.body.scrollHeight')
    retry_count = 0
    while page_height <= 0 and retry_count < 3:
        logger.info(f"Page height is {page_height}, waiting for content to load...")
        await asyncio.sleep(1)
        page_height = await page.evaluate('document.body.scrollHeight')
        retry_count += 1
    
    logger.info(f"Page height: {page_height}")
    screen_height = await page.evaluate('window.innerHeight')
    scrolled_distance = 0
    
    if page_height <= 0:
        logger.warning("Page height is still 0, using default height")
        page_height = 5000  
    
    while scrolled_distance < page_height:
        await page.mouse.wheel(0, screen_height)
        await asyncio.sleep(0.5)
        
        try:
            await page.wait_for_load_state('networkidle', timeout=2000)
        except Exception:
            pass
            
        new_page_height = await page.evaluate('document.body.scrollHeight')
        if new_page_height > page_height:
            page_height = new_page_height
            logger.info(f"Page grew to {page_height}px")
            
        scrolled_distance += screen_height
        
    await page.evaluate('window.scrollTo(0, 0);')
    logger.info("Completed scrolling through page")

async def extract_links(page, visited_urls):
    """Extract all valid Craigslist listing links from the page."""
    links = await page.locator("a[href^='https://']").all()
    new_links = []
    
    for link in links:
        try:
            href = await link.get_attribute("href")
            if href and "craigslist" in href and "search" not in href and href not in visited_urls:
                new_links.append(href)

        except Exception:
            continue
            
    return new_links

async def scrape(client: Plato, task: PlatoTask):
    env = await client.make_environment(task.env_id, open_page_on_start=False, record_network_requests=True, passthrough=True)
    logger.info(f"Environment made for task {task.name}")

    await env.wait_for_ready()
    logger.info(f"Environment ready for task {task.name}")

    await env.reset(task)
    logger.info(f"Environment reset for task {task.name}")

    cdp_url = await env.get_cdp_url()
    
    live_url = await env.get_live_view_url()
    logger.info(f"Live URL: {live_url}")

    browser = None
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            page = await browser.new_page()
            
            url_queue = deque()
            visited_urls = set()

            # Inititial URL for craigslist, remove after we know what categories we want to scrape
            root_url = "https://www.craigslist.com/"
            await page.goto(root_url, wait_until="domcontentloaded")
            await scroll_page(page)
            visited_urls.add(root_url)

            root_url = ROOT_URL
            await page.goto(root_url, wait_until="domcontentloaded")
            await scroll_page(page)
            visited_urls.add(root_url)

            initial_url = "https://sfbay.craigslist.org/search/hhh"
            await page.goto(initial_url, wait_until="domcontentloaded")
            await scroll_page(page)
            visited_urls.add(initial_url)

            links = await extract_links(page, visited_urls)
            logger.info(f"Initial links: {links}")
            for link in links:
                url_queue.append(link)
                
            logger.info(f"Initial page loaded, found {links} links to explore")
            
            iteration_count = 0
            max_iterations = 100_000
            
            while url_queue and iteration_count < max_iterations:
                iteration_count += 1
                logger.info(f"Iteration {iteration_count}, queue size: {len(url_queue)}, visited: {len(visited_urls)}")
                
                # if random.random() < 0.7 and url_queue:
                current_url = url_queue.popleft()
                
                if current_url in visited_urls:
                    continue
                    
                logger.info(f"Visiting URL from queue: {current_url}")
                
                try:
                    await page.goto(current_url, timeout=10000)
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    await scroll_page(page)
                    
                    visited_urls.add(current_url)
                    
                    # new_links = await extract_links(page, visited_urls)
                    # for link in new_links:
                    #     if link not in url_queue and link not in visited_urls:
                    #         url_queue.append(link)
                            
                    # logger.info(f"Found {len(new_links)} new links at {current_url}")
                except Exception as e:
                    logger.error(f"Error visiting {current_url}: {e}")

                await asyncio.sleep(1)
            
            logger.info(f"Exploration complete. Visited {len(visited_urls)} URLs.")
            
        except Exception as e:
            logger.error(f"Error in browser automation: {e}")
            raise
        finally:
            if browser:
                try:
                    await browser.close()
                    logger.info(f"Browser closed for task {task.name}")
                except Exception as e:
                    logger.error(f"Error closing browser: {e}")

            await env.close()
            logger.info(f"Environment closed for task {task.name}")

async def main():
    client = Plato(base_url=PLATO_API_URL, api_key=PLATO_API_KEY)
    task = PlatoTask(
        name="explore_craigslist",
        prompt="Explore Craigslist and find interesting links.",
        env_id="craigslist",
        start_url="https://www.craigslist.org/",
        eval_config=None,
    )
    try:
        await scrape(client, task)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
