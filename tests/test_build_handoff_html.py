from pathlib import Path
import tempfile
import unittest

from scripts.build_handoff_html import BuildError, build


class BuildHandoffHtmlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "docs" / "nested").mkdir(parents=True)
        (self.root / "docs" / "assets").mkdir(parents=True)
        (self.root / "docs" / "index.md").write_text(
            "# Start\n\n[Details](nested/details.md#advanced)\n\n"
            "![diagram](assets/diagram.svg)\n\n"
            "[External](https://example.invalid)\n\n"
            "`<script>alert(1)</script>`\n",
            encoding="utf-8",
        )
        (self.root / "docs" / "nested" / "details.md").write_text(
            "# Details\n\n## Advanced\n\n| Name | Value |\n| --- | --- |\n| item | 1 |\n",
            encoding="utf-8",
        )
        (self.root / "docs" / "assets" / "diagram.svg").write_text(
            "<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_builds_offline_navigation_and_resolves_local_assets(self) -> None:
        pages, links = build(
            self.root, Path("docs"), Path("index.html"), "Example handoff"
        )
        output = (self.root / "index.html").read_text(encoding="utf-8")

        self.assertEqual(pages, 2)
        self.assertEqual(links, 3)
        self.assertIn("#nested/details/advanced", output)
        self.assertIn("docs/assets/diagram.svg", output)
        self.assertIn("https://example.invalid", output)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", output)
        self.assertNotIn('<script src=', output)
        self.assertNotIn('<link href="http', output)
        self.assertNotIn('<img src="http', output)

    def test_missing_local_asset_fails_before_writing_html(self) -> None:
        (self.root / "docs" / "index.md").write_text(
            "# Start\n\n[Missing](not-here.csv)\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(BuildError, "missing local reference"):
            build(self.root, Path("docs"), Path("index.html"), "Example handoff")
        self.assertFalse((self.root / "index.html").exists())

    def test_out_of_root_references_are_rejected(self) -> None:
        outside = self.root.parent / "outside.md"
        outside.write_text("# Outside\n", encoding="utf-8")
        try:
            (self.root / "docs" / "index.md").write_text(
                "# Start\n\n[Outside](../../outside.md)\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(BuildError, "leaves project root"):
                build(self.root, Path("docs"), Path("index.html"), "Example handoff")
        finally:
            outside.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
