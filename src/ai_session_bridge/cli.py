"""CLI for AI Session Bridge."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .cache import SearchIndex, SessionCache
from .core import get_current_workspace
from .core.config import load_config
from .core.filter import ContentFilter
from .readers import get_registry

console = Console()


@click.group()
@click.version_option()
def main() -> None:
    """AI Session Bridge - Cross-tool AI conversation history reader."""
    pass


@main.command(name="list")
@click.option(
    "--tool",
    "-t",
    multiple=True,
    help="Filter by tools (can specify multiple)",
)
@click.option(
    "--limit",
    "-n",
    type=int,
    default=10,
    help="Maximum number of sessions to show",
)
@click.option(
    "--all",
    "-a",
    is_flag=True,
    help="Show sessions from all workspaces (default: current workspace only)",
)
def list_sessions(tool: tuple[str, ...], limit: int, all: bool) -> None:
    """List AI sessions (default: current workspace only)."""
    config = load_config()
    registry = get_registry()

    # Determine workspace: current workspace unless --all is specified
    if all:
        workspace_path = None
    else:
        workspace_path = get_current_workspace()

    if workspace_path:
        console.print(f"[bold]Sessions for:[/bold] {workspace_path}\n")
    else:
        console.print("[bold]Sessions for:[/bold] All workspaces\n")

    # Determine which tools to query
    tools_to_query = list(tool) if tool else registry.list_tools()

    # Get cache
    cache_dir = config.get_cache_dir()
    session_cache = SessionCache(cache_dir) if config.cache.enabled else None

    # Collect sessions from all tools
    all_sessions = []

    for tool_name in tools_to_query:
        reader = registry.get_reader(tool_name)
        if not reader:
            continue

        try:
            sessions = reader.get_sessions(workspace_path)
            all_sessions.extend(sessions)

            # Cache sessions
            if session_cache:
                for session in sessions:
                    session_cache.cache_summary(session)
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to read {tool_name} sessions: {e}[/yellow]")

    # Sort by update time
    all_sessions.sort(key=lambda s: s.updated_at, reverse=True)

    # Limit results
    all_sessions = all_sessions[:limit]

    if not all_sessions:
        console.print("[yellow]No sessions found.[/yellow]")
        return

    # Display table
    table = Table(show_header=True, header_style="bold magenta", show_lines=True)
    table.add_column("Tool", style="cyan")
    table.add_column("Title", style="yellow", overflow="fold")
    table.add_column("Session ID", style="green", no_wrap=True)
    table.add_column("Workspace", style="white", overflow="fold")
    table.add_column("Messages", justify="right")
    table.add_column("Last Updated")
    table.add_column("Preview", style="white")

    for session in all_sessions:
        # Replace line breaks with spaces for table display
        preview_text = session.preview.replace("\n", " ").replace("\r", " ")
        title_text = (session.title or "").replace("\n", " ").replace("\r", " ") if session.title else "(Untitled)"
        table.add_row(
            session.tool,
            title_text[:40] + "..." if len(title_text) > 40 else title_text,
            session.id,
            session.workspace_path or "",
            str(session.message_count),
            session.updated_at.strftime("%Y-%m-%d %H:%M"),
            preview_text[:50] + "..." if len(preview_text) > 50 else preview_text,
        )

    console.print(table)


@main.command()
@click.argument("session_id")
@click.option("--tool", "-t", help="Tool name (copilot, cursor, rovodev). Auto-detected if not specified.")
@click.option("--no-filter", is_flag=True, help="Disable content filtering")
@click.option("--no-pager", is_flag=True, help="Disable pager (less-like) for long output")
def show(session_id: str, tool: str | None, no_filter: bool, no_pager: bool) -> None:
    """Show details of a specific session."""
    config = load_config()
    registry = get_registry()

    # Search across all workspaces and tools to find the session
    session_file = None
    found_reader = None

    if tool:
        # Tool specified - only search that tool
        tools_to_search = [tool]
    else:
        # Auto-detect - search all tools
        tools_to_search = registry.list_tools()

    for tool_name in tools_to_search:
        reader = registry.get_reader(tool_name)
        if not reader:
            continue

        # Search across all workspaces (workspace_path=None)
        try:
            found_file = reader.find_session_by_id(session_id, None)
            if found_file:
                session_file = found_file
                found_reader = reader
                break
        except Exception:
            continue

    if not session_file or not found_reader:
        console.print(f"[red]Error: Session '{session_id}' not found[/red]")
        sys.exit(1)

    # Read session
    try:
        session = found_reader.read_session(session_file)

        # Apply filtering
        if not no_filter and config.filtering.enabled:
            content_filter = ContentFilter(config.filtering)
            session.messages = [content_filter.filter_message(msg) for msg in session.messages]

        # Build output content
        output_lines = []
        output_lines.append(f"\n[bold]Session:[/bold] {session.id}")
        output_lines.append(f"[bold]Tool:[/bold] {session.tool}")
        output_lines.append(f"[bold]Workspace:[/bold] {session.workspace_path}")
        output_lines.append(f"[bold]Created:[/bold] {session.created_at}")
        output_lines.append(f"[bold]Updated:[/bold] {session.updated_at}")
        output_lines.append(f"[bold]Messages:[/bold] {len(session.messages)}\n")

        # Build messages content
        for i, msg in enumerate(session.messages, 1):
            role_color = {
                "user": "blue",
                "assistant": "green",
                "system": "yellow",
                "tool": "magenta",
            }.get(msg.role.value, "white")

            output_lines.append(f"[{role_color}]--- {msg.role.value.upper()} ({msg.timestamp}) ---[/{role_color}]")
            output_lines.append(msg.content)
            output_lines.append("")

        output_text = "\n".join(output_lines)

        # Use pager for large output unless disabled or not a TTY
        if no_pager or not sys.stdout.isatty():
            console.print(output_text)
        else:
            with console.pager(styles=True):
                console.print(output_text)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("query")
@click.option("--tool", "-t", help="Filter by tool")
@click.option("--limit", "-n", type=int, default=20, help="Maximum results")
@click.option("--all", "-a", is_flag=True, help="Search across all workspaces (default: current workspace only)")
def search(query: str, tool: str | None, limit: int, all: bool) -> None:
    """Search across all sessions for keywords (default: current workspace only)."""
    config = load_config()

    if not config.search.enabled:
        console.print("[yellow]Search is disabled in config[/yellow]")
        sys.exit(1)

    # Determine workspace: current workspace unless --all is specified
    if all:
        workspace_path = None
    else:
        workspace_path = get_current_workspace()

    # Get search index
    cache_dir = config.get_cache_dir()
    search_index = SearchIndex(cache_dir)

    # Auto-index sessions if needed
    console.print("[dim]Indexing sessions...[/dim]")
    registry = get_registry()
    for tool_name, reader in registry.get_all_readers().items():
        try:
            summaries = reader.get_sessions(workspace_path)
            for summary in summaries:
                # Read full session and check if indexing needed
                # Use the original file_path string, not converted to Path
                # This handles special formats like "db_path#session_id" for Cursor
                session_file_path = summary.file_path

                # For simplicity, we'll just index all sessions
                # A production implementation might track mtimes
                try:
                    # Handle special file path formats (like Cursor's "db_path#session_id")
                    if "#" in session_file_path and tool_name == "cursor":
                        # For Cursor sessions, keep the special string format
                        # Cursor reader expects: Path object with the special format as string
                        session_path_arg = Path(session_file_path)
                    else:
                        # For normal file paths
                        session_path_arg = Path(session_file_path)

                    # First try with workspace_path parameter
                    try:
                        session = reader.read_session(session_path_arg, workspace_path)
                    except TypeError:
                        # Reader doesn't support workspace_path parameter (RovodevReader)
                        session = reader.read_session(session_path_arg)

                    # Index the session - use session ID as unique key instead of file path
                    index_key = Path(f"{tool_name}_{session.id}")
                    search_index.index_session(session, index_key)
                except Exception as e:
                    # Skip sessions that fail to parse, but don't fail silently in demo
                    if "/tmp/ai_session_bridge_demo/" in session_file_path:
                        print(f"Debug: Failed to index {session_file_path}: {e}")
                    pass
        except Exception:
            # Continue with other readers
            pass

    console.print(f"[bold]Searching for:[/bold] {query}\n")

    # Search
    try:
        results = search_index.search(query, workspace=workspace_path, tool=tool, limit=limit)

        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return

        # Display results
        table = Table(show_header=True, header_style="bold magenta", show_lines=True)
        table.add_column("Tool", style="cyan")
        table.add_column("Title", style="yellow")
        table.add_column("Session ID", style="green", no_wrap=True)
        table.add_column("Workspace", style="white", overflow="fold")
        table.add_column("Role")
        table.add_column("Timestamp")
        table.add_column("Match", style="white")

        for result in results:
            # Truncate content
            content = result.content[:100] + "..." if len(result.content) > 100 else result.content
            content = content.replace("\n", " ").replace("\r", " ")

            # Format title
            title_text = (
                (result.session_title or "").replace("\n", " ").replace("\r", " ")
                if result.session_title
                else "(Untitled)"
            )
            if len(title_text) > 30:
                title_text = title_text[:30] + "..."

            table.add_row(
                result.tool,
                title_text,
                result.session_id,
                result.workspace_path or "",
                result.role,
                result.timestamp.strftime("%Y-%m-%d %H:%M"),
                content,
            )

        console.print(table)
        console.print(f"\n[dim]Found {len(results)} results[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option("--format", "-f", type=click.Choice(["markdown", "json"]), default="markdown")
@click.option("--output", "-o", type=str, help="Output file (default: stdout)")
@click.option("--all", "-a", is_flag=True, help="Export from all workspaces (default: current workspace only)")
def export(format: str, output: str | None, all: bool) -> None:
    """Export sessions to a file."""
    console.print("[yellow]Export feature not yet implemented[/yellow]")


@main.group()
def cache() -> None:
    """Cache management commands."""
    pass


@cache.command("clear")
def cache_clear() -> None:
    """Clear all cached data."""
    config = load_config()
    cache_dir = config.get_cache_dir()

    session_cache = SessionCache(cache_dir)
    session_cache.clear()

    search_index = SearchIndex(cache_dir)
    search_index.clear()

    console.print("[green]Cache cleared successfully[/green]")


@cache.command("clean")
@click.option("--days", type=int, default=30, help="Remove entries older than N days")
def cache_clean(days: int) -> None:
    """Clean old cache entries."""
    config = load_config()
    cache_dir = config.get_cache_dir()

    session_cache = SessionCache(cache_dir)
    removed = session_cache.clean_old_entries(days)

    console.print(f"[green]Removed {removed} old cache entries[/green]")


@main.group()
def config_cmd() -> None:
    """Configuration management."""
    pass


@config_cmd.command("show")
def config_show() -> None:
    """Show current configuration."""
    config = load_config()

    console.print("[bold]Configuration:[/bold]\n")
    console.print(f"Scope: {config.scope.mode}")
    console.print(f"Cache: {'enabled' if config.cache.enabled else 'disabled'}")
    console.print(f"Cache directory: {config.get_cache_dir()}")
    console.print(f"Search: {'enabled' if config.search.enabled else 'disabled'}")
    console.print(f"Content filtering: {'enabled' if config.filtering.enabled else 'disabled'}")

    console.print("\n[bold]Enabled tools:[/bold]")
    if config.tools.copilot:
        console.print("  - copilot")
    if config.tools.cursor:
        console.print("  - cursor")
    if config.tools.rovodev:
        console.print("  - rovodev")


@main.command()
def serve() -> None:
    """Start the MCP server (STDIO mode)."""
    from .server import run_server

    run_server()


if __name__ == "__main__":
    main()
