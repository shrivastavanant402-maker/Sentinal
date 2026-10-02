"""
AegisMesh Model Context Protocol (MCP) Integration Module.
Provides an MCP adapter for external MCP clients (Cursor, Claude Desktop, VS Code)
to enforce runtime policy via AegisMesh Policy Enforcement Point (PEP).
"""
from backend.app.mcp.server import create_mcp_server, run_server

__all__ = ["create_mcp_server", "run_server"]
