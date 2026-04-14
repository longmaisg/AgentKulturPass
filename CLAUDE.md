## Principles
- **Save code**: Save all code usage.
- **Small files**: Keep code files under ~100 lines. Split into modules when approaching this limit.
- **Raw data first**: When fetching data, always store into a raw data file first. Scrutinize it to verify correctness and warn on anomalies before processing.
- **Change log**: Log all changes and updates. Write to git as well (use a git update/commit script).
- **uv over pip**: Always use `uv` for dependency management, never `pip`.
- **Token efficiency**: Avoid reading or modifying large files unless strictly necessary.
