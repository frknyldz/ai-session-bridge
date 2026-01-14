# Contributing to AI Session Bridge

Thank you for your interest in contributing to AI Session Bridge! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/frknyldz/ai-session-bridge
   cd ai-session-bridge
   ```

   Or if you forked it:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ai-session-bridge
   cd ai-session-bridge
   ```

2. **Run Setup Script**
   ```bash
   ./setup.sh
   ```

3. **Activate Virtual Environment**
   ```bash
   source venv/bin/activate
   ```

## Development Workflow

### Making Changes

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes

3. Run tests:
   ```bash
   pytest
   ```

4. Run linting:
   ```bash
   ruff check .
   ```

5. Format code:
   ```bash
   ruff format .
   ```

6. Type check (optional):
   ```bash
   mypy src/
   ```

> **Note:** If you ran `./setup.sh`, pre-commit hooks are automatically installed and will run linting and formatting checks before each commit. GitHub Actions will also run all tests automatically when you open a pull request.

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for function arguments and return values
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose
- Maximum line length: 120 characters (configured in pyproject.toml)

### Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for high test coverage (>80%)
- Use pytest fixtures for common test data

**Run tests with coverage:**
```bash
pytest --cov=ai_session_bridge --cov-report=term --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html  # Opens coverage report in browser
```

### Commit Messages

Follow conventional commit format:

```
type(scope): short description

Longer description if needed

Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test changes
- `refactor`: Code refactoring
- `chore`: Maintenance tasks

Examples:
```
feat(readers): add support for Continue.dev sessions
fix(cache): handle missing session files gracefully
docs(readme): update installation instructions
test(filter): add tests for custom filter patterns
```

## Pull Request Process

1. **Update Documentation**
   - Update README.md if adding features
   - Update QUICKSTART.md if changing setup
   - Add docstrings to new code

2. **Add Tests**
   - Write unit tests for new functionality
   - Ensure tests are passing locally

3. **Create Pull Request**
   - Provide clear description of changes
   - Reference any related issues
   - Include screenshots for UI changes
   - Wait for CI/CD checks to pass (tests, linting, type checking)

4. **CI/CD Checks**
   - GitHub Actions will automatically run:
     - Tests on Python 3.10, 3.11, and 3.12
     - Linting with ruff
     - Type checking with mypy
     - Code formatting checks
   - All checks must pass before merge

5. **Code Review**
   - Address reviewer feedback
   - Update PR as needed
   - CI checks will re-run on each update

## Project Structure

```
ai-session-bridge/
├── src/ai_session_bridge/
│   ├── core/          # Core models and utilities
│   ├── readers/       # Session readers for each tool
│   ├── cache/         # Caching and indexing
│   ├── cli.py         # CLI commands
│   └── server.py      # MCP server
├── tests/             # Test files
├── examples/          # Configuration examples
└── docs/              # Documentation
```

## Adding a New Session Reader

To add support for a new AI tool:

1. **Create Reader Class**
   ```python
   # src/ai_session_bridge/readers/newtool.py
   from .base import SessionReader
   from ..core.session import Session, SessionSummary

   class NewToolReader(SessionReader):
       def get_tool_name(self) -> str:
           return "newtool"

       def get_sessions(self, workspace_path: str) -> list[SessionSummary]:
           # Implement session discovery
           pass

       def read_session(self, session_path: Path) -> Session:
           # Implement session parsing
           pass
   ```

2. **Register Reader**
   ```python
   # src/ai_session_bridge/readers/registry.py
   from .newtool import NewToolReader

   def _initialize_readers(self):
       # ... existing readers ...
       self._readers["newtool"] = NewToolReader()
   ```

3. **Add Tests**
   ```python
   # tests/test_readers/test_newtool.py
   def test_newtool_reader():
       # Test your reader
       pass
   ```

4. **Update Documentation**
   - Add to README.md supported tools table
   - Add example in QUICKSTART.md
   - Update configuration examples

## Testing with Real Sessions

To test with actual session files:

1. **Create Test Workspace**
   ```bash
   mkdir -p /tmp/test-workspace
   cd /tmp/test-workspace
   ```

2. **Copy Sample Sessions**
   ```bash
   # Copy your actual session files to test locations
   # This helps verify readers work with real data
   ```

3. **Test CLI**
   ```bash
   ai-session-bridge list --workspace /tmp/test-workspace
   ai-session-bridge show SESSION_ID --tool TOOL_NAME
   ```

4. **Test MCP Server**
   ```bash
   ai-session-bridge serve
   # Test with your AI tool's MCP client
   ```

## Common Tasks

### Adding a New Configuration Option

1. Update `Config` class in `src/ai_session_bridge/core/config.py`
2. Update `_dict_to_config` and `_config_to_dict` functions
3. Update example config in `examples/config.yaml`
4. Document in README.md

### Adding a New CLI Command

1. Add command function in `src/ai_session_bridge/cli.py`
2. Use `@main.command()` decorator
3. Add tests in `tests/test_cli.py` (to be created)
4. Document in README.md

### Adding a New MCP Tool

1. Add tool definition in `list_tools()` in `server.py`
2. Implement handler function
3. Add tests (to be created)
4. Document in README.md

## Documentation

### Docstring Format

Use Google-style docstrings:

```python
def function_name(arg1: str, arg2: int) -> bool:
    """
    Short description.

    Longer description if needed.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ValueError: When something is wrong
    """
    pass
```

## Questions?

- Open an issue for questions
- Join discussions in GitHub Discussions
- Check existing issues and PRs

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
