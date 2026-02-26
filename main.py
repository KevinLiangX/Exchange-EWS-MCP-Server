import sys
import os
from pathlib import Path

# Ensure env vars are loaded early
from dotenv import load_dotenv

base_dir = Path(__file__).resolve().parent
env_path = base_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


from src.ews_exchange_mcp.server import mcp

def main():
    mode = os.environ.get("MCP_MODE", "stdio")
    port = int(os.environ.get("MCP_PORT", 3101)) # Different port to test alongside Node
    if mode == "http":
        print(f"Starting EWS MCP Python Server on HTTP port {port} on 0.0.0.0...", file=sys.stderr)
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = port
        mcp.run(transport="streamable-http") 
    elif mode == "sse":
        print(f"Starting EWS MCP Python Server on SSE port {port} on 0.0.0.0...", file=sys.stderr)
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = port
        
        from starlette.middleware.cors import CORSMiddleware
        import uvicorn
        
        app = mcp.sse_app()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        print("Starting EWS MCP Server on Standard I/O...", file=sys.stderr)
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
