# xpkgindex 文档

[English](../README.md) | **简体中文**

xpkgindex 把一个装满 xpkg 描述符的目录变成静态网站。内核知道什么是*包索引* ——
标识、版本、平台、镜像、历史、贡献者;它不知道任何具体的包管理器,那部分属于索引
仓库自己持有的插件。

这些文档讲的是框架本身。如果你在维护一个索引、想要一个站点,从
[快速上手](getting-started.md)和[配置](configuration.md)开始。如果你的生态里有些
概念内核根本没有对应的词,读[插件](plugins.md)。

## 文档清单

| 文档 | 讲什么 |
|---|---|
| [快速上手](getting-started.md) | 安装、仓库应有的结构、第一次构建、本地预览、该提交什么 |
| [配置](configuration.md) | `.xpkgindex.json` 的每个键、默认值,以及它改变了什么 |
| [插件](plugins.md) | 插件 API v1 —— 钩子、调用顺序、数据模型、失败行为 |
| [主题](theming.md) | 设计令牌、夜间模式、列表布局、模板逃生口 |
| [多语言](i18n.md) | 界面语言、按语言的文案、文档译文、语言自动识别 |
| [数据与 API](data-and-api.md) | `index.json` schema 1 及其他机器可读产物 |
| [架构](architecture.md) | 一次构建到底怎么跑,分阶段说明,以及为什么是这个顺序 |
| [部署](deployment.md) | GitHub Pages、构建溯源、网络缓存、CI 参数 |

## 代码在哪

| 路径 | 职责 |
|---|---|
| `xpkgindex/cli.py` | `generate` 与 `serve` |
| `xpkgindex/build.py` | 流水线:描述符 → `SiteData` |
| `xpkgindex/config.py` | `.xpkgindex.json` → `SiteConfig` |
| `xpkgindex/models.py` | `Identity`、`Package`、`Block`、`RowSpec`、`Facet`、`Person` 等 |
| `xpkgindex/readers/xpkg_lua.py` | 描述符沙箱,与 `libxpkg` 保持一致 |
| `xpkgindex/plugins/__init__.py` | 插件基类、加载、逐钩子隔离 |
| `xpkgindex/data/` | git 历史回放、GitHub 缓存、身份合并 |
| `xpkgindex/guides.py` | 把仓库自己的 markdown 渲染成站点页面 |
| `xpkgindex/charts.py` | 增长曲线,内联 SVG |
| `xpkgindex/render.py` | 单个语言的全部页面 |
| `xpkgindex/serialize.py` | `index.json` 契约 |
| `xpkgindex/i18n.py` | 框架界面文案与语言解析 |
| `xpkgindex/templates/`、`xpkgindex/static/` | Jinja 模板、CSS、JS |

## 两个真实例子

设计能保持诚实,是因为有两个彼此不一致的索引在用:

- [`mcpplibs/mcpp-index`](https://github.com/mcpplibs/mcpp-index) —— mcpp 把
  命名空间当作标识的一部分(`nlohmann.json`),列表行打头的是你要写的那行代码
  (`import nlohmann.json;`),并且会从上游 `mcpp.toml` 清单里补充信息。
- [`openxlings/xim-pkgindex`](https://github.com/openxlings/xim-pkgindex) ——
  xlings 把命名空间当作*标签*,名字是对着索引仓库解析的,所以命名空间绝不能进入
  安装命令。列表行打头的是你会得到的那个二进制(`$ gcc`)。

凡是某个设计决定看起来很随意的地方,通常就是这两个生态往相反方向拉扯的那个点。
