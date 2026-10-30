"""Build an offline HTML handbook from a directory of Markdown files."""

from __future__ import annotations

import argparse
from html import escape
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote, unquote, urlsplit


class BuildError(ValueError):
    """Raised when source documentation contains an invalid local reference."""


def route_for(path: Path, docs_root: Path) -> str:
    return path.relative_to(docs_root).with_suffix("").as_posix()


def slugify(value: str) -> str:
    slug = re.sub(r"[^\w-]+", "-", value.strip().lower(), flags=re.UNICODE)
    return slug.strip("-") or "section"


def inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def heading_map(source: Path) -> tuple[str, dict[str, str]]:
    lines = source.read_text(encoding="utf-8").splitlines()
    first_h1 = next(
        (match.group(2).strip() for line in lines if (match := re.match(r"^(#{1})\s+(.+)$", line))),
        source.stem,
    )
    seen: dict[str, int] = {}
    headings: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^#{1,6}\s+(.+)$", line)
        if not match:
            continue
        text = match.group(1).strip()
        base = slugify(text)
        seen[base] = seen.get(base, 0) + 1
        heading_id = base if seen[base] == 1 else f"{base}-{seen[base]}"
        headings[text] = heading_id
        headings[heading_id] = heading_id
    return first_h1, headings


def checked_target(
    target: str,
    source: Path,
    root: Path,
    docs_root: Path,
    output: Path,
    page_routes: dict[Path, str],
    page_headings: dict[Path, dict[str, str]],
    *,
    image: bool = False,
) -> str:
    parsed = urlsplit(target)
    if parsed.scheme:
        if parsed.scheme.lower() in {"http", "https", "mailto"} and not image:
            return target
        raise BuildError(f"unsupported or remote asset reference in {source}: {target}")
    if parsed.netloc:
        raise BuildError(f"network reference is not allowed in {source}: {target}")

    raw_path = unquote(parsed.path.replace("\\", "/"))
    linked = source.resolve() if not raw_path else (source.parent / raw_path).resolve()
    if not inside(linked, root):
        raise BuildError(f"local reference leaves project root in {source}: {target}")
    if not linked.is_file():
        raise BuildError(f"missing local reference in {source}: {target}")

    fragment = unquote(parsed.fragment)
    if linked in page_routes:
        route = page_routes[linked]
        if fragment:
            headings = page_headings[linked]
            heading_id = headings.get(fragment) or headings.get(slugify(fragment))
            if heading_id is None:
                raise BuildError(f"missing heading reference in {source}: {target}")
            route += "/" + heading_id
        return "#" + quote(route, safe="/-_.~")

    relative = Path(os.path.relpath(linked, output.parent)).as_posix()
    href = quote(relative, safe="/-_.~:@")
    if parsed.query:
        href += "?" + parsed.query
    if parsed.fragment:
        href += "#" + parsed.fragment
    return href


def render_inline(
    text: str,
    source: Path,
    root: Path,
    docs_root: Path,
    output: Path,
    page_routes: dict[Path, str],
    page_headings: dict[Path, dict[str, str]],
) -> str:
    held: list[str] = []

    def hold(fragment: str) -> str:
        held.append(fragment)
        return f"\x00{len(held) - 1}\x00"

    text = re.sub(r"`([^`]+)`", lambda match: hold("<code>" + escape(match.group(1)) + "</code>"), text)

    pattern = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)")

    def link(match: re.Match[str]) -> str:
        is_image = bool(match.group(1))
        href = checked_target(
            match.group(3),
            source,
            root,
            docs_root,
            output,
            page_routes,
            page_headings,
            image=is_image,
        )
        if is_image:
            title = f' title="{escape(match.group(4), quote=True)}"' if match.group(4) else ""
            return hold(
                f'<img src="{escape(href, quote=True)}" alt="{escape(match.group(2), quote=True)}"{title}>'
            )
        title = f' title="{escape(match.group(4), quote=True)}"' if match.group(4) else ""
        return hold(f'<a href="{escape(href, quote=True)}"{title}>{escape(match.group(2))}</a>')

    text = pattern.sub(link, text)
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda match: held[int(match.group(1))], text)


def render_markdown(
    source: Path,
    root: Path,
    docs_root: Path,
    output: Path,
    page_routes: dict[Path, str],
    page_headings: dict[Path, dict[str, str]],
) -> tuple[str, int]:
    lines = source.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    local_references = 0
    heading_ids = page_headings[source]
    used_ids: set[str] = set()

    def inline(value: str) -> str:
        nonlocal local_references
        before = len(re.findall(r"!?\[[^\]]*\]\([^)]+\)", value))
        rendered = render_inline(
            value,
            source,
            root,
            docs_root,
            output,
            page_routes,
            page_headings,
        )
        local_references += before
        return rendered

    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        if line.startswith("```"):
            language = line[3:].strip()
            code: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code.append(lines[index])
                index += 1
            class_attr = f' class="language-{escape(language, quote=True)}"' if language else ""
            out.append(f"<pre><code{class_attr}>{escape(chr(10).join(code))}</code></pre>")
            index += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2).strip()
            heading_id = heading_ids.get(text, slugify(text))
            if heading_id in used_ids:
                suffix = 2
                while f"{heading_id}-{suffix}" in used_ids:
                    suffix += 1
                heading_id = f"{heading_id}-{suffix}"
            used_ids.add(heading_id)
            out.append(f'<h{level} id="{escape(heading_id, quote=True)}">{inline(text)}</h{level}>')
            index += 1
            continue

        if line.strip() in {"---", "***", "___"}:
            out.append("<hr>")
            index += 1
            continue

        if line.startswith("|"):
            rows: list[list[str]] = []
            while index < len(lines) and lines[index].startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", cell.replace(" ", "")) for cell in cells):
                    rows.append(cells)
                index += 1
            if rows:
                header = "".join(f"<th scope=\"col\">{inline(cell)}</th>" for cell in rows[0])
                body = "".join(
                    "<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>"
                    for row in rows[1:]
                )
                out.append(f"<div class=\"table-wrap\"><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>")
            continue

        list_match = re.match(r"^(\s*)([-*+] |\d+[.)] )(.*)$", line)
        if list_match:
            ordered = list_match.group(2)[0].isdigit()
            tag = "ol" if ordered else "ul"
            items: list[str] = []
            while index < len(lines):
                item_match = re.match(r"^\s*(?:[-*+] |\d+[.)] )(.*)$", lines[index])
                if not item_match:
                    break
                items.append(f"<li>{inline(item_match.group(1))}</li>")
                index += 1
            out.append(f"<{tag}>{''.join(items)}</{tag}>")
            continue

        if line.startswith("> "):
            quote_lines: list[str] = []
            while index < len(lines) and lines[index].startswith("> "):
                quote_lines.append(lines[index][2:])
                index += 1
            out.append("<blockquote><p>" + inline(" ".join(quote_lines)) + "</p></blockquote>")
            continue

        paragraph = [line.strip()]
        index += 1
        while (
            index < len(lines)
            and lines[index].strip()
            and not re.match(r"^(#{1,6}\s|```|\||[-*+] |\d+[.)] |>)", lines[index])
        ):
            paragraph.append(lines[index].strip())
            index += 1
        out.append("<p>" + inline(" ".join(paragraph)) + "</p>")

    return "\n".join(out), local_references


def build(root: Path, docs: Path, output: Path, title: str) -> tuple[int, int]:
    root = root.expanduser().resolve()
    docs_root = (root / docs).expanduser().resolve() if not docs.is_absolute() else docs.expanduser().resolve()
    output_path = (root / output).expanduser().resolve() if not output.is_absolute() else output.expanduser().resolve()
    if not inside(docs_root, root) or not docs_root.is_dir():
        raise BuildError(f"Markdown directory must exist inside the project root: {docs_root}")
    if not inside(output_path, root):
        raise BuildError(f"HTML output must stay inside the project root: {output_path}")

    markdown_files = sorted(path.resolve() for path in docs_root.rglob("*.md"))
    if not markdown_files:
        raise BuildError(f"No Markdown files found under {docs_root}")

    page_routes = {path: route_for(path, docs_root) for path in markdown_files}
    page_headings: dict[Path, dict[str, str]] = {}
    page_titles: dict[Path, str] = {}
    for path in markdown_files:
        page_titles[path], page_headings[path] = heading_map(path)

    pages: dict[str, dict[str, str]] = {}
    link_count = 0
    for path in markdown_files:
        body, count = render_markdown(
            path, root, docs_root, output_path, page_routes, page_headings
        )
        route = page_routes[path]
        pages[route] = {"title": page_titles[path], "html": body}
        link_count += count

    payload = json.dumps(pages, ensure_ascii=False).replace("</", "<\\/")
    nav = "".join(
        f'<a href="#{quote(route, safe="/-_.~")}" data-route="{escape(route, quote=True)}">{escape(page["title"])}</a>'
        for route, page in pages.items()
    )
    document = rf"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
:root {{ color-scheme: light; font-family: system-ui, sans-serif; color: #18222c; background: #f4f6f8; }}
body {{ margin: 0; }}
header {{ padding: 1rem 1.5rem; background: #17324d; color: white; font-size: 1.15rem; font-weight: 650; }}
.layout {{ display: grid; grid-template-columns: minmax(12rem, 18rem) minmax(0, 1fr); min-height: calc(100vh - 3.5rem); }}
aside {{ padding: 1rem; background: white; border-right: 1px solid #d8e0e8; }}
aside nav {{ display: grid; gap: .35rem; position: sticky; top: 1rem; }}
a {{ color: #1769aa; overflow-wrap: anywhere; }}
aside a {{ display: block; padding: .45rem .55rem; border-radius: .35rem; text-decoration: none; }}
aside a[aria-current="page"] {{ background: #e8f2fc; font-weight: 650; }}
main {{ min-width: 0; max-width: 76rem; padding: clamp(1rem, 4vw, 3rem); }}
article {{ background: white; padding: clamp(1rem, 4vw, 3rem); border: 1px solid #d8e0e8; border-radius: .75rem; }}
h1, h2, h3, h4, h5, h6 {{ line-height: 1.25; }}
pre {{ overflow: auto; padding: 1rem; background: #f1f4f7; border-radius: .45rem; }}
code {{ font-family: ui-monospace, Consolas, monospace; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ padding: .55rem .7rem; border: 1px solid #d8e0e8; text-align: left; }}
th {{ background: #f1f4f7; }}
.table-wrap {{ overflow-x: auto; }}
img {{ max-width: 100%; height: auto; }}
blockquote {{ margin-left: 0; padding-left: 1rem; border-left: .25rem solid #9bb7cf; color: #485c6d; }}
@media (max-width: 700px) {{ .layout {{ grid-template-columns: 1fr; }} aside {{ border-right: 0; border-bottom: 1px solid #d8e0e8; }} aside nav {{ position: static; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr)); }} }}
</style>
</head>
<body>
<header>{escape(title)}</header>
<div class="layout">
<aside><nav aria-label="Documentation pages">{nav}</nav></aside>
<main><article id="content"></article></main>
</div>
<script type="application/json" id="pages">{payload}</script>
<script>
const pages = JSON.parse(document.getElementById('pages').textContent);
const routes = Object.keys(pages);
function render() {{
  const requested = decodeURIComponent(location.hash.slice(1));
  const route = routes.filter((item) => requested === item || requested.startsWith(item + '/'))
    .sort((a, b) => b.length - a.length)[0] || routes[0];
  const page = pages[route];
  document.title = page.title + ' · {escape(title)}';
  document.getElementById('content').innerHTML = page.html;
  document.querySelectorAll('[data-route]').forEach((link) => {{
    if (link.dataset.route === route) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }});
  const suffix = requested.slice(route.length).replace(/^\//, '');
  if (suffix) document.getElementById(suffix)?.scrollIntoView();
  else window.scrollTo(0, 0);
}}
window.addEventListener('hashchange', render);
render();
</script>
<noscript>Enable JavaScript to browse the embedded Markdown pages.</noscript>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return len(pages), link_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project root")
    parser.add_argument("--docs", type=Path, default=Path("docs"), help="Markdown directory")
    parser.add_argument("--output", type=Path, default=Path("index.html"), help="HTML output path")
    parser.add_argument("--title", default="Project handoff", help="HTML page title")
    args = parser.parse_args(argv)
    try:
        pages, links = build(args.root, args.docs, args.output, args.title)
    except (BuildError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Built {args.output} from {pages} Markdown pages; rendered {links} Markdown links and assets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
