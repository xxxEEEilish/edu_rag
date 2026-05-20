# Repository Workflow

## Response Language

Always answer the user in Chinese.

## Code Style

When writing or modifying code, add detailed Chinese comments for modules, classes,
functions, important fields, and non-obvious logic. Comments should explain intent,
data flow, constraints, and extension points, not merely restate the code.

Use OpenSpec for planned development in this repository.

## Encoding rules

- This project uses UTF-8 for all source files.
- When reading files on Windows PowerShell, do not use plain `Get-Content` for files that may contain Chinese.
- Always use:
  `Get-Content -Encoding UTF8 <path>`
- For Python files with Chinese comments or docstrings, prefer:
  `python -c "from pathlib import Path; print(Path(r'<path>').read_text(encoding='utf-8'))"`
- If terminal output is garbled, set UTF-8 first:
  `$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::new()`
- Do not rewrite files only because terminal output looks garbled. First verify whether it is only a display/encoding issue.

## OpenSpec Commands

The npm package exposes the `openspec` CLI. The `/opsx:*` commands in generated prompt files are chat shortcuts, not PowerShell commands.

When the user asks for one of these flows, follow the matching prompt file:

- `propose <feature>` or `提出/规划 <feature>`: follow `.github/prompts/opsx-propose.prompt.md`
- `apply [change]` or `实现/开工 [change]`: follow `.github/prompts/opsx-apply.prompt.md`
- `archive [change]` or `归档/收工 [change]`: follow `.github/prompts/opsx-archive.prompt.md`

Always use `openspec status`, `openspec instructions`, and the files under `openspec/changes/` as the source of truth for change artifacts and task progress.
