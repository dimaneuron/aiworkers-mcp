"""AIWorkers MCP — manage a neural employee via private HTTP APIs."""

__all__ = ["main"]
__version__ = "0.3.23"


def main() -> None:
    from aiworkers_mcp.server import main as _main

    _main()

