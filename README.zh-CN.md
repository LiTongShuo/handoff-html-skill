# Handoff HTML Skill

[English](README.md) | **简体中文**

将 Markdown 文档目录转换为离线 HTML 手册的可复用 Codex 技能，同时提供仅依赖 Python 标准库的命令行工具。

## 功能

- 将 Markdown 页面与导航嵌入单个 HTML 文件。
- 生成前检查本地链接、标题锚点与图片引用。
- 限制本地引用位于项目根目录内。
- 离线工作，不加载远程脚本、样式表或图片。

本地文件和图片仍使用相对路径。分享时需一并保留对应资源；单个 HTML 不会打包所有链接资产。远程网址保留为普通可点击链接。

## 命令行使用

需要 **Python 3.10 或更新版本**，无需第三方包。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe .\scripts\build_handoff_html.py --root "path\to\project" --docs docs --output index.html --title "项目交接"
```

将 Markdown 文档放在项目的 `docs/` 目录，生成后使用浏览器打开 `index.html`。遇到缺失引用时，构建会给出错误信息并停止。

## 作为 Codex 技能使用

将仓库内容放入名为 `handoff-html` 的技能目录，确保 [SKILL.md](SKILL.md) 位于其根目录。Windows 用户级安装示例：

```powershell
git clone https://github.com/LiTongShuo/handoff-html-skill.git "$env:USERPROFILE\.codex\skills\handoff-html"
```

随后请 Codex 使用 `handoff-html`，从项目的 Markdown 文档生成离线手册。该技能独立于相机及标注项目。

## 测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 许可证

采用 [MIT 许可证](LICENSE)。
