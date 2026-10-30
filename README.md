# Handoff HTML Skill

**English** | [简体中文](README.zh-CN.md)

A reusable Codex skill and Python standard-library tool that turns a Markdown documentation directory into an offline HTML handbook.

## Features

- Embed Markdown pages and navigation in a single HTML file.
- Check local links, heading anchors, and image references before writing output.
- Keep local references within the project root.
- Work offline without loading remote scripts, stylesheets, or images.

Local files and images remain relative to the project. Keep them beside the generated handbook when sharing it; the HTML file alone does not bundle every linked asset. Remote URLs remain ordinary clickable links.

## Command-line use

Requires **Python 3.10 or newer**; no third-party packages are needed.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe .\scripts\build_handoff_html.py --root "path\to\project" --docs docs --output index.html --title "Project handoff"
```

Put your Markdown files in the project's `docs/` directory, then open the generated `index.html` in a browser. Missing references cause the build to fail with a diagnostic instead of silently producing broken links.

## Use as a Codex skill

Copy this repository's contents into a skill directory named `handoff-html`, keeping [SKILL.md](SKILL.md) at its root. For a user-level installation on Windows:

```powershell
git clone https://github.com/LiTongShuo/handoff-html-skill.git "$env:USERPROFILE\.codex\skills\handoff-html"
```

Then ask Codex to use `handoff-html` to build an offline handbook from your project's Markdown documents. This skill is independent of the camera and annotation projects.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## License

[MIT](LICENSE).
