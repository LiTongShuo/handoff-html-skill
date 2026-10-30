---
name: handoff-html
description: Build an offline-browsable HTML handoff from a project's Markdown documentation and validate its local links and assets.
---

# Handoff HTML

Use this skill when a user asks to create or refresh a local HTML handbook from Markdown documentation. Keep Markdown as the source of truth and write the generated HTML only to the requested output path.

## Workflow

1. Identify the project root, Markdown directory, requested output path, and any approved visual reference. Do not edit generated output by hand.
2. Check the source Markdown and referenced local files. Keep user data, credentials, and unrelated project content outside the generated artifact.
3. Run the bundled builder:

   ```powershell
   python <skill-root>\scripts\build_handoff_html.py --root <project-root> --docs <markdown-directory> --output <html-file> --title "<title>"
   ```

   Paths may be absolute or relative to the project root. The builder rejects missing or out-of-root local references and does not fetch remote content.
4. Open the output with a local browser and verify page navigation, headings, code blocks, tables, and referenced local assets. Keep assets at the paths referenced relative to the generated HTML.
5. Report the source directory, output path, and any unsupported Markdown that needs manual handling.

## Boundaries

- This skill does not publish pages, start a documentation server, or push to GitHub.
- Keep remote links as ordinary clickable anchors; remote images and external CSS/JavaScript are not included.
- Use the project's own existing build process when the user asks to update that process. This skill's script is a standalone option and does not replace project-specific builders.
