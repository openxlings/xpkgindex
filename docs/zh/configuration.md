# 配置

[English](../configuration.md) | **简体中文**

全部内容都在索引仓库根目录的 `.xpkgindex.json` 里。每个键都是可选的。凡是索引自己
提供的字符串,也都可以写成按语言的 map —— 见[多语言](i18n.md)。

```jsonc
{
  "site":  { "title": "…", "description": "…", "logo": "…" },
  "links": { "github": "…", "website": "…", "forum": "…", "docs": "…",
             "custom": [{ "label": "…", "url": "…" }] },
  "about": { "project_name": "…", "project_url": "…", "description": "…",
             "maintainers": ["…"], "license": "Apache-2.0" },

  "theme": {
    "accent": "#5b46d6",
    "style":  "auto",
    "tones":  { "module": "…", "header": "…", "tool": "…", "neutral": "…" },
    "dark":   { "accent": "#9b8bfa", "tones": { } },
    "transition": { "duration": "2s", "easing": "cubic-bezier(.45, .05, .25, 1)" }
  },

  "pkgs_dir": "pkgs",
  "base_url": "https://example.github.io/index",
  "languages": ["en", "zh", "zh-Hant"],
  "install_command_template": "mcpp add {ref}@{version}",
  "list": { "variant": "code" },

  "install": {
    "primary": { "label": "安装 mcpp", "command": "xlings install mcpp -y" },
    "summary": "还没装 xlings?",
    "os": [
      { "id": "unix",    "os": "Linux / macOS",        "command": "…" },
      { "id": "windows", "os": "Windows · PowerShell", "command": "…" }
    ]
  },

  "growth": {
    "total_label": "全部包",
    "series": [{ "label": "import", "facet": "surface", "value": "module", "tone": "module" }]
  },

  "plugins": [".xpkgindex/plugins/mcpp.py"],

  "docs": {
    "nav_label": "文档",
    "landing": "quick-start",
    "entries": [{ "slug": "quick-start", "title": "快速开始",
                  "path": "docs/quick-start.md",
                  "translations": { "zh": "docs/zh/quick-start.md" } }],
    "cta": { "eyebrow": "第一次用?", "title": "快速开始",
             "description": "…", "lines": ["…"], "action": "看指南" }
  },

  "ecosystem": { "owners": ["mcpplibs"], "repos": ["mcpp-community/mcpp"] },

  "identities": ".xpkgindex/identities.json",
  "cache": ".xpkgindex/cache/github.json"
}
```

## `site`

| 键 | 默认 | 说明 |
|---|---|---|
| `title` | `Package Index` | 页面标题、首屏大标题、页脚 |
| `description` | — | 首屏副标题、`<meta name=description>`、订阅副标题 |
| `logo` | `Package Index` | 页头的文字标识 |

## `links`

每一项对应页头的一个图标;不写就不渲染。

| 键 | 图标 | 含义 |
|---|---|---|
| `github` | GitHub 标志 | 本索引的仓库。还会被解析出 `owner/name`,贡献者查询需要它 |
| `website` | 地球 | *项目*自己的官网 —— 不是这个索引 |
| `forum` | 对话框 | 社区论坛 |
| `docs` | 书 | 外部文档 |
| `custom` | — | 额外的文字链接,渲染在页脚 |

## `about`

填充「关于」页:`project_name`、`project_url`、`description`、`maintainers`
(列表)、`license`。

## `theme`

| 键 | 默认 | 说明 |
|---|---|---|
| `accent` | 内置 | 主强调色。旧写法 `primary_color` 仍可用 |
| `style` | `auto` | `auto` 跟随系统;`light` / `dark` 固定 |
| `tones` | `{}` | 语义色令牌:`module`、`header`、`tool`、`neutral` 等。`RowSpec.tone` 或 `FacetValue.tone` 引用的就是这些名字 |
| `dark` | `{}` | `{ "accent": …, "tones": { … } }`,作用于 `[data-theme=dark]` |
| `transition.duration` | `2s` | 昼夜交叉淡入。`0s` 即瞬切 |
| `transition.easing` | `cubic-bezier(.45, .05, .25, 1)` | 任意 CSS 缓动函数 |

完整令牌清单与切换实现见[主题](theming.md)。

## 构建

| 键 | 默认 | 说明 |
|---|---|---|
| `pkgs_dir` | `pkgs` | 描述符所在目录,相对仓库根 |
| `urls.style` | `directory` | `directory` 产出 `/packages/x/`;`file` 产出 `/packages/x/index.html`,用于「只提供文件、不把目录解析成 index」的宿主。`--url-style` 可在单次构建里覆盖 |
| `base_url` | — | 绝对 URL,供 `sitemap.xml` / `feed.xml` 使用;`--base-url` 会覆盖 |
| `languages` | `["en"]` | 界面语言。第一个是默认语言,放在站点根 |
| `install_command_template` | `{ref}@{version}` | 占位符:`{ref}`、`{name}`、`{namespace}`、`{display}`、`{version}` |
| `list.variant` | `code` | `code` 或 `card`;插件可以逐包覆盖 |
| `plugins` | `[]` | 仓库相对的 `.py` 路径,或 `xpkgindex.plugins` 分组下的入口点名 |
| `identities` | `.xpkgindex/identities.json` | 人工的贡献者合并规则 |
| `cache` | `.xpkgindex/cache/github.json` | 提交进仓库的网络缓存 |

`{ref}` 就是 `Identity.install_ref` —— 客户端 CLI 真正接受的形式。它和展示名是
故意分开的两个字段,原因见[架构](architecture.md#标识与-slug)。

## `install`

首页的安装区。每个平台的命令都会渲染进 HTML,再由前端揭示匹配的那条,所以没有
JavaScript 的访客也能看到全部。

| 键 | 说明 |
|---|---|
| `primary.label`、`primary.command` | 主命令 |
| `summary` | 折叠区的标题,里面是各平台命令 |
| `os[]` | `{ id, os, command }`。`id` 与识别出的平台匹配:`unix`、`linux`、`macos`、`windows` |

不写 `primary.command` 时,各平台列表直接展开显示,而不是收在折叠里。旧写法
`install_commands` 与 `install.fallback.commands` 仍然可用。

## `growth`

首页和统计页的曲线。总数线始终会画,`series` 是在它之上再加线。

| 键 | 说明 |
|---|---|
| `total_label` | 总数线的图例文字 |
| `series[].label` | 图例文字 |
| `series[].facet`、`series[].value` | 哪些包计入这条线 |
| `series[].tone` | 线色取自主题色令牌;若与强调色完全相同则自动回退到调色板,避免两条线同色 |

每条线都由与总数相同的每日快照算出,所以它能回答“去年三月这类包有多少”,而不只是
今天有多少。

## `docs`

渲染仓库里已有的 markdown —— 没有第二份副本,也就不会走散。

| 键 | 说明 |
|---|---|
| `nav_label` | 导航里这一节的名字。字符串、按语言的 map,或者不写以使用框架自带的翻译 |
| `landing` | 导航项和首页卡片指向的那篇文档的 slug |
| `entries[]` | `{ slug, title, path, translations }` |
| `entries[].translations` | `{ 语言: 路径 }` —— 正文跟随页头的语言切换器 |
| `cta` | 首页卡片:`eyebrow`、`title`、`description`、`lines[]`、`action` |

文档自己的 `# H1` 会成为页面标题,并从正文中移除,所以不会出现两次。`title` 是它
在导航里的名字;两者在多语言下如何配合,见[多语言](i18n.md#文档)。旧键 `guides`
仍被当作 `docs` 的同义词。

## `ecosystem`

| 键 | 说明 |
|---|---|
| `owners` | 你自己的组织和账号。会从「上游致谢」中排除 —— 你对自己不是第三方 |
| `repos` | 额外的仓库,其贡献者计入生态贡献者 |
