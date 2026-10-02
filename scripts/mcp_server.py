#!/usr/bin/env python
"""
AegisMesh Model Context Protocol (MCP) Server.
Executable entry point for IDEs and AI coding agents (Cursor, Claude Desktop, VS Code).
Communicates over stdio JSON-RPC.
"""
import os
import sys

# Ensure project root is in sys.path when executed directly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app.mcp.server import run_server

if __name__ == "__main__":
    run_server(transport="stdio")
