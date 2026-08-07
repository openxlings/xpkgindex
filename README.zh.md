# xpkgindex

[English](README.md) | **简体中文**

包索引的静态站点框架。内核只知道什么是*包索引* —— 标识、版本、平台、镜像、
历史、贡献者 —— 不知道任何具体的包管理器。凡是与生态语义相关的东西,都放在索引
仓库自己持有的插件里。

```bash
pip install xpkgindex
xpkgindex generate . --output site      # 构建
xpkgindex serve . --port 8000           # 构建后起服务,便于本地 review
```

产物就是一个普通的 HTML + JSON 目录,直接部署到 GitHub Pages 即可;JSON 按 API
响应的形态设计,将来换成服务端时,一条 URL 都不用改。

完整文档在 [`docs/`](docs/zh/README.md):[快速上手](docs/zh/getting-started.md)、
[配置](docs/zh/configuration.md)、[插件](docs/zh/plugins.md)、
[主题](docs/zh/theming.md)、[多语言](docs/zh/i18n.md)、
[数据与 API](docs/zh/data-and-api.md)、[架构](docs/zh/architecture.md)、
[部署](docs/zh/deployment.md)。

---

## 产出什么

| 路径 | 内容 |
|---|---|
| `/` | 首屏 · 增长曲线 · 历史线 · 分面包列表 |
| `/packages/<id>/` | 详情:怎么用、构建语义、版本、镜像、相关的人、历史 |
| `/packages/<id>/index.json` | 同一个包的数据形态 |
| `/stats/` | 随时间的增长、构成、完整历史线 |
| `/contributors/` | 索引贡献者 · 上游致谢 · 生态并集 |
| `/docs/<slug>/` | 仓库自己的 markdown,就地渲染 |
| `/index.json` | 全部内容(schema 1)—— 对外契约 |
| `/search-index.json`、`/sitemap.xml`、`/feed.xml` | 搜索负载、站点地图、Atom 订阅 |

包的 URL 是目录形态而不是 `<name>.html`:这是服务端路由日后可以原样接管的形状,
也给子页面留了位置。

---

## 谁在用

两个真实索引推动了这套设计,而且它们在关键处彼此不一致 —— 这正是内核保持诚实的
原因。

### [`mcpplibs/mcpp-index`](https://github.com/mcpplibs/mcpp-index) —— 81 个包

面向 [mcpp](https://github.com/mcpp-community/mcpp) 构建工具的模块化 C++23 包。
它的插件(`.xpkgindex/plugins/mcpp.py`):

- **命名空间属于标识的一部分。** mcpp 解析的是 `nlohmann.json`,所以插件返回
  `Identity.joined(...)`。没有它时,站点会显示 `mcpp add json@3.12.0` —— 客户端
  直接拒绝,而且三个不同的 `imgui` 包会挤到同一个页面上。
- **按“你怎么用它”给包分类** —— `import`、`#include`、命令行工具,或上游自带的
  `mcpp.toml`。这个轴来自 `mcpp = {}` 扩展块,也是 C++ 用户真正会用来浏览的维度。
- **读取 `mcpp = {}`** 生成构建语义区块:modules、targets、language、
  `import_std`、sources、features、生成的文件。
- **把每个包关联到用它的测试项目。** 这个仓库本身就是一个 mcpp workspace,成员是
  逐库的测试项目,所以包页面上的用法片段是 CI 真的编译并运行过的代码,不是为了
  网站写的。

### [`openxlings/xim-pkgindex`](https://github.com/openxlings/xim-pkgindex) —— 155 个包

[xlings](https://github.com/openxlings/xlings) 包管理器的官方索引。它的插件
(`.xpkgindex/plugins/xim.py`)把 mcpp 的两条假设整个反了过来 —— 这也正是要有
两个消费者的原因:

- **命名空间是标签,不是标识。** xlings 解析的是 `[index:]name[@version]`,对应的
  是*索引仓库*,所以描述符里的 `namespace`(`config`、`xim`)必须留在安装命令之外。
  插件返回 `Identity.plain(...)`。
- **xvm、programs、archs 是 xlings 的概念**,由插件而不是内核渲染。它们曾经住在
  内核模型里,结果泄漏到 mcpp 的页面上,变成毫无意义的 “XVM Managed: No”。
- 分面来自这个索引真正会填的字段:类型、分类、状态。

两个站点看起来也不一样:`theme.accent` 和 `theme.tones` 能从 `.xpkgindex.json`
里给整套设计系统换色 —— 不用 fork,不用改 CSS。

---

## 配置

索引仓库根目录下的 `.xpkgindex.json`:

```jsonc
{
  "site":  { "title": "…", "description": "…", "logo": "…" },
  "links": { "github": "…", "website": "…",   // 项目自己的官网(地球图标)
             "forum": "…", "docs": "…",       // 社区、外部文档
             "custom": [{ "label": "…", "url": "…" }] },
  "about": { "project_name": "…", "project_url": "…", "license": "…" },

  "theme": {
    "accent": "#5b46d6",
    "style":  "auto",                       // auto | light | dark
    "tones":  { "module": "…", "header": "…", "tool": "…" },
    "dark":   { "accent": "#9b8bfa", "tones": {} },
    "transition": { "duration": "2s",       // 昼夜交叉淡入;"0s" 即瞬切
                    "easing": "cubic-bezier(.45, .05, .25, 1)" }
  },

  "pkgs_dir": "pkgs",
  "base_url": "https://example.github.io/index",
  "install_command_template": "mcpp add {ref}@{version}",

  "install": {
    "primary": { "label": "安装 mcpp", "command": "xlings install mcpp -y" },
    "summary": "还没装 xlings?",
    "os": [                                 // 按访客平台自动选中
      { "id": "unix",    "os": "Linux / macOS",        "command": "…" },
      { "id": "windows", "os": "Windows · PowerShell", "command": "…" }
    ]
  },

  "plugins": [".xpkgindex/plugins/mcpp.py"],

  "docs": {
    "nav_label": "文档",
    "landing": "quick-start",
    "entries": [{ "slug": "contributing", "title": "新增一个包",
                  "path": "docs/README.md",
                  "translations": { "zh": "docs/zh/README.md" } }]
  },

  "ecosystem": {
    "owners": ["mcpplibs"],                 // 自己的组织 —— 不计入“上游致谢”
    "repos":  ["mcpp-community/mcpp"]       // 生态贡献者的并集
  }
}
```

`install_command_template` 的占位符:`{ref}`(CLI 真正接受的形式)、`{name}`、
`{namespace}`、`{display}`、`{version}`。

文档渲染的是仓库里已有的 markdown 而不是副本,所以站点不会和文档走散。安装命令
会把每个平台都渲染进 HTML,再由前端选中匹配的那条,因此没有 JS 的访客照样能看到
全部平台。

旧配置继续可用:`primary_color`、`install_commands`、
`install.fallback.commands`,以及模板里的 `{name}`,都仍然被识别。

### 多语言文案

凡是*索引自己*提供的字符串(框架自带的界面文案已经翻译过了),都可以按语言写:

```jsonc
"site":    { "title": { "en": "mcpp Package Index", "zh": "mcpp 包索引" } },
"install": { "primary": { "label": { "en": "Install mcpp", "zh": "安装 mcpp" } } },
"docs":    { "cta": { "title": { "en": "Quick start", "zh": "快速开始" } } }
```

写成纯字符串依然表示“每种语言都一样”,所以单语言索引什么都不用改。解析顺序是:
精确标签(`zh-Hant`)→ 主语言子标签(`zh`)→ 站点默认语言 → 任意已有值 ——
翻译只做了一半的配置,在每种语言下也都能渲染出东西。

插件里同样可用:分面标签、区块标题、徽章、行内提示都支持。**标识符不要翻译**:
`import`、`#include`、`modules`、`targets` 要么是读者真正要敲的,要么就是清单
文件里的字段名。

`index.json` 会把这些 map 展平成默认语言 —— schema 1 承诺的是字符串,解析标签的
消费者不该突然收到一个 map。

只要文档条目为该语言声明了译文,正文就跟随页头的语言切换器。文档顶部那行手写的
`**English** | [简体中文](…)`(为了在 GitHub 上也能读而写的)会按链接识别出来并
从渲染页面中移除 —— 站点已经有一个切换器,而且它管的是整个页面。

---

## 写一个插件

插件就是索引仓库里的一个 Python 文件。构建本来就会在该仓库自己的工作流里执行它
自己的 `.lua` 描述符,所以执行它的 Python 并没有新增信任边界。`pip` 入口点
(分组 `xpkgindex.plugins`)同样支持,便于分发。

```python
from xpkgindex.models import Block, Facet, FacetValue, Identity
from xpkgindex.plugins import Plugin

class MyPlugin(Plugin):
    api_version = 1
    name = "my-ecosystem"

    def on_index(self, ctx):             ...  # 仓库级配置 → ctx.meta
    def identity(self, raw, path):       ...  # 规范标识 / slug / 安装引用
    def on_package(self, pkg, raw):      ...  # extensions、facets、deps
    def facets(self):                    ...  # 声明分面轴
    def detail_blocks(self, pkg):        ...  # 详情页的结构化内容
    def row(self, pkg):                  ...  # 列表行怎么读
    def enrich_remote(self, pkgs, http): ...  # 可选,必须可跳过
```

列表行是一个 `RowSpec`,不是固定模板 —— 站点最密集的那个界面上该放什么,每个生态
的答案不同(mcpp 打头的是你要写的那行代码,xlings 打头的是你会得到的那个二进制):

```python
RowSpec(variant="",                 # "" = 站点默认;否则 code | card
        tone="module",              # 决定标签和条带的颜色
        lead="import",              # 带文字的类型标签
        code="import nlohmann.json;",   # 怎么用它
        code_muted=False,               # code 只是占位形状时为 True
        install="mcpp add nlohmann.json@3.12.0",   # 怎么加它
        badges=["✓ 有示例"])
```

`code` 和 `install` 回答的是两个不同的问题,而且永远落在同一个位置,读者就不必
逐行重新解析:

**`code` 布局** —— 三行,`mcpp-index` 在用:

```
// nlohmann.json 3.12.0 — JSON for Modern C++
import nlohmann.json;                              ← 怎么用它
mcpp add nlohmann.json@3.12.0   MIT · 3 platforms  ← 点命令即可复制
```

当描述符从未写明模块名或头文件时,第 2 行仍然出现,但是灰化的 `import …;` /
`#include <…>` —— 只给形状,不编造标识符,这样节奏不断,也没有哪一行在说假话。

**`card` 布局** —— `xim-pkgindex` 在用,那里的全部问题就是“我要敲什么才能装上”:

```
gcc  15.1.0  [package]                    GPL · 3 platforms · xvm
The GNU Compiler Collection
┌────────────────────────────────────────────────────┐
│ xlings install gcc@15.1.0            $ gcc         │  ← 点击复制
└────────────────────────────────────────────────────┘
```

`"list": {"variant": "card"}` 设定全站默认;插件的 `RowSpec.variant` 可以逐包
覆盖;`row()` 返回 `None` 就完全用默认。类型由*带文字的*标签加上着色条带表达,
而不是单纯一根色条,所以分不清色相的人也读得出来。

**插件返回数据,不返回 HTML。** 一个 `Block`(`kv` / `code` / `table` / `list` /
`callout`)由内核的设计系统渲染,并原样进入 `index.json`,这样消费者站点在视觉上
保持一致,将来的 API 也带着同样的字段。确实需要自己的标记时,显式设置 `template`
和 `styles` —— 这个逃生口是有意留的,它的 CSS 会限定在该插件范围内。

用户为了使用一个包而写的那一行,用 `data["role"] = "interface"` 标出来;它会成为
列表行的标题行,以及详情页最上面那一行。

`on_index` 应该设置 `default_namespace`:省略了 `namespace` 的描述符不是“没有
命名空间”,它属于索引的默认命名空间;把它归到 “—” 是在发明一个并不存在的分组。

---

## 失败模型

数据正确性的问题让构建失败,外部依赖的问题降级处理。

| 情况 | 结果 |
|---|---|
| 两个包解析出同一个 slug | **构建失败**,并指出两个描述符 |
| 增长曲线与工作树对不上 | **构建失败**(工作树脏时降为警告;`--strict` 强制失败) |
| 插件抛异常、加载失败,或 `api_version` 不符 | 警告;丢弃该插件这次的产出 |
| 描述符解析失败 | 警告;跳过该包 |
| 没有 GitHub token / 触发限流 / 离线 | 使用已提交的缓存;缺失的部分省略 |
| 浅克隆 | 跳过增长、历史与贡献者 |
| 文档 markdown 缺失 | 警告;跳过该篇 |

前两条之所以是硬失败,是因为这两个 bug 都真的发生过:三个 `imgui` 包曾经挤成
一个页面;只统计新增,曾把 81 个包的树报成 86 个。

---

## 描述符解析

描述符在沙箱化的 Lua 运行时里执行,并与 xpkg 规范的 C++23 参考实现
[`libxpkg`](https://github.com/mcpplibs/libxpkg) 保持一致 —— 具体来说是它的
`register_loader_sandbox`。对齐本身就是目的:更宽松的沙箱会宣传工具链根本装不上的
包,更严格的则会悄悄丢掉合法的包。

---

## 开发

```bash
pip install -e ".[dev]"
pytest
```

## 许可

Apache-2.0
