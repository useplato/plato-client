import asyncio
import os
import sys
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt


# Add parent directory to path to import from models
sys.path.append(str(Path(__file__).parent.parent))

from models.openai.computers.remote_playwright import RemotePlaywrightComputer
from models.anthropic.agent import AnthropicAgent
from models.anthropic.tools.computer_browser import ComputerBrowserTool20250124
from playwright.async_api import async_playwright
from models.openai.agent.agent import Agent as OpenAIAgent
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

async def run_anthropic_cua_task(cdp_url, prompt, start_url):
    async with ComputerBrowserTool20250124(cdp_url) as computer:
        agent = AnthropicAgent(
            api_key=os.getenv("ANTHROPIC_API_KEY") or "",
        )
        await computer.goto(start_url)
        await agent.run(prompt, browser_tool=computer)

async def get_action_xpath(action, computer):
  if isinstance(action, dict) and "type" in action and action["type"] == "click":  # type: ignore
      if "x" in action and "y" in action and computer._page is not None:
          x = action["x"]  # type: ignore
          y = action["y"]  # type: ignore
          # get the DOM element at this position
          # Get XPath for the element using a JavaScript function to generate XPath
          element_xpath = await computer._page.evaluate("""(function() {
            var element = document.elementFromPoint(""" + str(x) + """, """ + str(y) + """);
            if (!element) return null;

            function getXPath(node) {
              if (node.id) {
                return '//*[@id="' + node.id + '"]';
              }
              var parts = [];
              while (node && node.nodeType === 1) {  // 1 is Node.ELEMENT_NODE
                var index = 1;
                var sibling = node.previousSibling;
                while (sibling) {
                  if (sibling.nodeType === 1 && sibling.nodeName === node.nodeName) {
                    index++;
                  }
                  sibling = sibling.previousSibling;
                }
                var tagName = node.nodeName.toLowerCase();
                var pathIndex = index > 1 ? '[' + index + ']' : '';
                parts.unshift(tagName + pathIndex);
                node = node.parentNode;
              }
              return '/' + parts.join('/');
            }

            return getXPath(element);
          })()""")
      return element_xpath

async def run_openai_agent(cdp_url, prompt, start_url):
    async with RemotePlaywrightComputer(cdp_url) as computer:
        agent = OpenAIAgent(
            computer=computer,
        )

        await computer.goto(start_url)

        # Create directed graph
        G = nx.DiGraph()
        current_node_id = 0
        _next_node_id = 0

        def _generate_node_id():
            nonlocal _next_node_id
            _next_node_id += 1
            return _next_node_id

        current_url = computer._page.url if computer._page else start_url
        G.add_node(current_node_id, url=current_url, label="Start")




        # Store action history
        action_history = []

        while True:
          items, action_items = await agent.run_single_action(prompt, n_samples=10)

          # Group actions by element_xpath
          actions_by_xpath = {}
          for action in action_items:
              element_xpath = await get_action_xpath(action['action'], computer)
              # Group by xpath
              if element_xpath not in actions_by_xpath:
                  actions_by_xpath[element_xpath] = []
              actions_by_xpath[element_xpath].append(action)

          # Print grouped actions
          for xpath, grouped_actions in actions_by_xpath.items():
              print(f"XPath: {xpath}")
              for action in grouped_actions:
                  print(f"  {action['action']}")


          # select the xpath that has the most items
          max_xpath = max(actions_by_xpath, key=lambda x: len(actions_by_xpath[x]))
          # add edge from current node to the next node
          next_node_id = _generate_node_id()
          G.add_edge(current_node_id, next_node_id, xpath=max_xpath.split("/")[-1] if max_xpath else "", count=len(actions_by_xpath[max_xpath]), actions=str(actions_by_xpath[max_xpath]))
          print("Performing action: ", actions_by_xpath[max_xpath][-1]['action'])

          # for all other xpaths, create new nodes and add edges to them
          for xpath, grouped_actions in actions_by_xpath.items():
            if xpath != max_xpath:
              node_id = _generate_node_id()
              G.add_node(node_id, url=computer._page.url if computer._page else "", label="")
              G.add_edge(current_node_id, node_id, xpath=xpath.split("/")[-1] if xpath else "", count=len(grouped_actions), actions=str(grouped_actions))

          # Execute the selected action
          selected_action = actions_by_xpath[max_xpath][-1]
          items += [selected_action]
          items += await agent.handle_item(selected_action)

          # Record the action taken
          action_history.append({
              'from_node': current_node_id,
              'xpath': max_xpath,
              'action': selected_action['action']
          })

          # Create a new node for the next state after action
          current_node_id = next_node_id
          current_url = computer._page.url if computer._page else ""
          G.add_node(current_node_id, url=current_url, label="Step")

          # Visualize the graph after each step
          plt.figure(figsize=(15, 10))
          pos = nx.kamada_kawai_layout(G)

          # Draw nodes with labels
          nx.draw_networkx_nodes(G, pos, node_size=700)
          nx.draw_networkx_labels(G, pos, labels={n: G.nodes[n]['label'] for n in G.nodes})

          # Draw edges with labels
          nx.draw_networkx_edges(G, pos)
          edge_labels = {(u, v): f"{d['xpath']}\n({d['count']} actions)" for u, v, d in G.edges(data=True)}
          nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)

          # Save the current state of the graph
          plt.savefig(f"action_graph_step_{current_node_id}.png")
          plt.close()

          breakpoint()

        # Final visualization
        plt.figure(figsize=(20, 15))
        pos = nx.kamada_kawai_layout(G)

        # Node colors based on visitation
        node_colors = ['blue' if node in [a['from_node'] for a in action_history] else 'lightblue' for node in G.nodes]

        # Draw the final graph
        nx.draw_networkx_nodes(G, pos, node_size=700, node_color=node_colors)
        nx.draw_networkx_labels(G, pos, labels={n: G.nodes[n]['label'] for n in G.nodes})

        # Draw edges with colors based on whether they were taken
        edges = G.edges(data=True)
        edge_colors = []
        for u, v, d in edges:
            if any(a['from_node'] == u and a['xpath'] == d['xpath'] for a in action_history):
                edge_colors.append('red')  # Edges that were taken
            else:
                edge_colors.append('gray')  # Edges that were available but not taken

        nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=2)

        # Edge labels
        edge_labels = {(u, v): f"{d['xpath']}\n({d['count']} actions)" for u, v, d in edges}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)

        plt.title("Action Graph Explorer")
        plt.savefig("final_action_graph.png")
        print("Final action graph saved to final_action_graph.png")
        plt.show()



async def main():
    # Default values - these could be passed via command line arguments
    prompt = "You are on airbnb.com. Find a place to stay in New York City for the dates June 3rd-6th."
    start_url = "https://www.airbnb.com"

    # Launch browser with Playwright first
    async with async_playwright() as p:
        # Launch browser with Chrome DevTools Protocol (CDP) enabled
        browser = await p.chromium.launch(headless=False, args=['--remote-debugging-port=9222'])

        # Get the CDP URL
        cdp_url = "http://localhost:9222"

        # Run the task 20 times in parallel
        await run_openai_agent(cdp_url, prompt, start_url)


        # Keep browser open for debugging if needed
        print("Press Enter to close the browser...")
        await asyncio.get_event_loop().run_in_executor(None, input)

        # Close the browser
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
