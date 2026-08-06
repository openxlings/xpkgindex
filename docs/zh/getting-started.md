# 快速上手

[English](../getting-started.md) | **简体中文**

## 环境要求

Python 3.9 及以上。三个依赖随包安装:`jinja2`(模板)、`lupa`(描述符沙箱)、
`markdown-it-py`(渲染你的文档)。

```bash
pip install xpkgindex
# 或者,在 PyPI 上还没有你平台的包之前:
pip install git+https://github.com/openxlings/xpkgindex.git
```

## 框架期望的仓库结构

```
your-index/
├── pkgs/                     # 描述符,任意层级,*.lua
│   └── n/nlohmann.json.lua
├── .xpkgindex.json           # 站点配置(可选,但通常都有)
├── .xpkgindex/
│   ├── plugins/yours.py      # 你的生态语义(可选)
│   ├── identities.json       # 人工的贡献者合并规则(可选)
│   └── cache/github.json     # 提交进仓库的网络缓存(自动生成)
└── docs/*.md                 # 你已有的文档,会被渲染成站点页面
```

只有 `pkgs/` 是必需的 —— 完全不写配置也能构建出一个能用、只是没有署名的站点。
目录叫别的名字就用 `pkgs_dir` 指过去。

## 第一次构建

```bash
xpkgindex generate .              # 输出到 ./site
xpkgindex serve . --port 8000     # 构建后起服务,便于 review
```

`generate` 会打印产出和所有警告:

```
generated 81 packages -> site
  16 namespaces, 119 versions, 2 facet axes, 8 contributors
```

### 参数

| 参数 | 作用 |
|---|---|
| `--output`、`-o` | 输出目录(默认 `site`) |
| `--config`、`-c` | 显式指定 `.xpkgindex.json` 路径 |
| `--offline` | 完全不碰网络,只用已提交的缓存 |
| `--strict` | 把对账警告当作错误 —— CI 里用 |
| `--refresh` | 忽略新鲜度,重新抓取全部缓存条目 |
| `--base-url` | 供 `sitemap.xml` 和 `feed.xml` 使用的绝对基址 |
| `--port` | 仅 `serve`(默认 8000) |

警告不是失败。描述符解析不了、文档文件缺失、插件钩子抛异常 —— 构建会说出来,然后
继续。只有两件事会中止构建:一个包都没解析出来,以及两个包争同一个 URL(见
[架构](architecture.md#标识与-slug))。

## 产物

```
site/
├── index.html                     # 列表、增长曲线、历史
├── packages/<slug>/index.html     # 每个包一页
├── packages/<slug>/index.json     # 同一个包的数据形态
├── packages/<short>.html          # 旧链接的跳转 / 消歧页
├── stats/、contributors/、about/
├── docs/<slug>/                   # 你的 markdown
├── index.json                     # 全部内容(schema 1)
├── search-index.json、sitemap.xml、feed.xml
├── static/                        # css、js、生成的 theme.css
└── zh/、zh-Hant/                  # 若配置了更多语言
```

包的 URL 是目录而不是 `<name>.html`:这样服务端路由日后可以原样接管,加子页面也
不用再迁移一次。

## 该提交什么

提交 `.xpkgindex/cache/github.json`。它只存投影过的字段 —— 头像、登录名、仓库
描述、star 数 —— 提交它意味着 CI 构建可复现、快,并且在未认证限流时也不会垮。
刷新要显式做(`--refresh`),不要每次构建都刷。

不要提交 `site/`。它是构建产物,由 CI 发布。

## 接下来

- [配置](configuration.md) —— 给站点起名、换主题、接上安装命令
- [插件](plugins.md) —— 当内核没有词能表达你生态在意的东西时
- [部署](deployment.md) —— 二十行左右的工作流就能上 GitHub Pages
