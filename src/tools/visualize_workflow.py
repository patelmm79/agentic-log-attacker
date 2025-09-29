import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.main import app
from langchain_core.runnables.graph_mermaid import MermaidDrawMethod

# Get the graph
graph = app.get_graph()

# Draw the graph
png_data = graph.draw_mermaid_png(draw_method=MermaidDrawMethod.PYPPETEER)

# Save the image
with open("workflow.png", "wb") as f:
    f.write(png_data)

print("Workflow visualization saved to workflow.png")
