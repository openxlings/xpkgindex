# 插件

[English](../plugins.md) | **简体中文**

内核知道什么是包索引,但不知道一个包在你的生态里*意味着*什么 —— 命名空间算不算
名字的一部分、读者要写哪一行才能用上这个库、包的哪些属性值得做成分面。这些是插件
的职责,而插件属于索引仓库,不属于框架。

```jsonc
"plugins": [".xpkgindex/plugins/mine.py"]
```

以 `.py` 结尾的仓库相对路径会被直接导入;其他字符串按 `xpkgindex.plugins` 分组的
入口点查找。模块里每一个 `Plugin` 子类都会被实例化。

执行仓库自己的 Python 并没有新增风险:构建本来就在该仓库自己的工作流里执行它自己
的 `.lua` 描述符。

## 形态

```python
from xpkgindex.plugins import Plugin
from xpkgindex.models import Block, Facet, FacetValue, Identity, RowSpec


class MyPlugin(Plugin):
    api_version = 1
    name = "mine"          # 决定 pkg.extensions[name] 的键

    def on_package(self, pkg, raw):
        pkg.facets["kind"] = raw.get("type", "library")
```

所有钩子都是可选的,默认什么都不做。`api_version` 在加载时检查;不匹配只是警告,
插件照样加载。

## 钩子,按构建调用的顺序

| 钩子 | 何时 | 返回 |
|---|---|---|
| `on_index(ctx)` | 一次,在读任何包之前 | — |
| `identity(raw, path)` | 每个描述符,先于关于它的一切 | `Identity` 或 `None` |
| `on_package(pkg, raw)` | 每个包,解析完之后 | — |
| `enrich_remote(packages, http)` | 一次,在所有包都存在之后 | — |
| `facets()` | 一次,在补充之后 | `list[Facet]` |
| `detail_blocks(pkg)` | 每个包 | `list[Block]` |
| `row(pkg)` | 每个包 | `RowSpec` 或 `None` |

顺序在一处尤其关键:`enrich_remote` 跑在分面、区块、行**之前**。一个插件如果解析
出了仅凭描述符拿不到的东西(比如上游清单),它必须还能改变这个包的分类和渲染 ——
而那些一旦算完就改不了了。

### `on_index(ctx)`

仓库级配置:workspace 清单、索引级 TOML、人工维护的覆盖文件。

```python
def on_index(self, ctx):
    text = ctx.read_text("mcpp.toml")        # 不存在时返回 None
    ctx.meta.set("hero_stats", [{"label": "带示例", "value": 64}])
```

`ctx` 提供 `root`、`path(*parts)`、`read_text(relative)`、解析好的 `config`,以及
`meta` —— 一个 `IndexMeta`,它的字段会落到 `index.json` 的 `index` 下,其中
`hero_stats` 会渲染在内核的统计数字旁边。

### `identity(raw, path)`

影响最大的一个钩子。三个字段,彼此不能互相推导:

| 字段 | 是 |
|---|---|
| `display` | 人读的 |
| `slug` | URL 片段,全站唯一 |
| `install_ref` | 客户端 CLI 真正接受的 |

```python
def identity(self, raw, path):
    pkg = raw.get("package", {})
    return Identity.joined(pkg.get("namespace", ""), pkg.get("name", ""))
```

`Identity.plain(ns, name)` 是内核默认:命名空间只是元数据,三个字段都是裸名字。
`Identity.joined(ns, name)` 让命名空间成为标识的一部分 —— `nlohmann.json` ——
展示、URL、安装命令三处都是。

内核永远不会替你拼命名空间。mcpp 要的是 `mcpp add nlohmann.json`;xlings 是拿名字
对着*索引仓库*解析的,`xlings install xim.gcc` 根本不成立。猜错的结果是页面上贴出
一条根本跑不通的安装命令,所以这个选择必须显式。

两个包如果算出同一个 `slug`,构建直接失败。这是插件链路上唯一一个不是警告的失败:
slug 重复意味着一个包的页面把另一个悄悄覆盖掉了,而这正是这个框架要消灭的 bug。

### `on_package(pkg, raw)`

填 `pkg.extensions[self.name]`、`pkg.facets`、`pkg.deps`。`raw` 就是 Lua 沙箱产出
的原始描述符。

```python
def on_package(self, pkg, raw):
    ext = raw.get("package", {}).get("mine", {})
    pkg.extensions["mine"] = {"programs": ext.get("programs", [])}
    pkg.facets["kind"] = "tool" if ext.get("programs") else "library"
```

分面值在前端按空白分隔的 token 匹配,所以
`pkg.facets["surface"] = "module header"` 会让这个包同时出现在该轴的两个值下。

### `enrich_remote(packages, http)`

构建期的网络补充。`http` 是共享缓存:

```python
def enrich_remote(self, packages, http):
    for pkg in packages:
        data = http.get_text(url, project="manifest")   # 离线时为 None
        if data:
            pkg.extensions["mine"]["upstream"] = parse(data)
```

`get(url, project)`(JSON)和 `get_text(url, project)` 在没网、指定了 `--offline`
或请求失败时返回 `None` 而不是抛异常。`project` 用来在已提交的缓存里分组。

**缓存事实,不要缓存结论。** 存「这个包是模块化的」意味着以后改规则就得把每个包
都联网刷一遍;存「它声明的模块名」则意味着规则可以随时改、离线重算。

### `facets()`

声明分面轴。计数由内核填。

```python
def facets(self):
    return [Facet(key="kind", label="怎么用", weight=10, values=[
        FacetValue(key="tool", label="tool", tone="tool"),
        FacetValue(key="library", label="library", tone="module"),
    ])]
```

`weight` 决定轴的顺序;`tone` 引用主题色令牌名。你没声明的值仍会从包里发现并追加
到后面。

### `detail_blocks(pkg)`

包页面的结构化内容。永远不是 HTML —— 区块会原样进入 `index.json`,而且所有消费者
站点共用同一套视觉系统。

| `kind` | `data` |
|---|---|
| `kv` | `{"items": [{"key", "value", "mono"?}]}` |
| `code` | `{"code", "caption"?, "source"?}` |
| `table` | `{"head": [...], "rows": [[...]]}` |
| `list` | `{"items": [...]}` |
| `callout` | `{"text"}` |

```python
Block(kind="kv", title="构建", weight=30, collapsed=False,
      data={"items": [{"key": "modules", "value": "asio", "mono": True}]})
```

`weight` 决定区块顺序;`collapsed` 让它收进折叠。`data["role"] == "interface"` 的
区块会被提出来,渲染成页面最上方那行标志性的用法。

如果一个区块确实无法用这五种表达,`template` 和 `styles` 就是那个明示的逃生口 ——
这是一次明确的承认,而不是把 HTML 字符串塞进 caption 里偷渡。

### `row(pkg)`

列表行,站点上最密集也最常被读的界面。

```python
def row(self, pkg):
    return RowSpec(variant="code", tone="module",
                   lead="import", code="import asio;",
                   install="mcpp add chriskohlhoff.asio@1.34.2",
                   badges=["✓ 有示例"])
```

内置两套布局。`code` 是语义固定的三行 —— 名字作注释、怎么用它、怎么加它 ——
mcpp-index 用的就是它。`card` 以名字和元信息打头、以一条可复制的命令收尾,适合
工具型索引,xim-pkgindex 在用。返回 `None` 则采用 `list.variant` 的站点默认。

`code_muted=True` 表示这行「怎么用」只是形状而非事实 —— 用于描述符从未写明模块名
或头文件的包。不要编造标识符:包页面上一个错的 `#include`,比没有更糟。

## 用读者的语言

插件产出的任何字符串 —— 分面标签、区块标题、徽章、提示 —— 都可以写成按语言的
map:

```python
Facet(key="kind", label={"en": "how you use it", "zh": "怎么用"})
```

标识符不要翻译。见[多语言](i18n.md)。

## 钩子抛异常时

内核记一条警告,丢掉这次调用的产出,继续构建。插件的 bug 只会降级它碰到的那部分
页面,不会把整个站点带下去。警告由 `generate` 打印,并收集在 `site.warnings` 里;
`--strict` 管的是增长对账,不是插件失败。

例外还是那个:slug 重复,直接中止。

## 可以直接读的例子

两个真实索引都带着值得一读的插件:

- [`mcpp-index/.xpkgindex/plugins/mcpp.py`](https://github.com/mcpplibs/mcpp-index/blob/main/.xpkgindex/plugins/mcpp.py)
  —— 拼接式标识、上游 `mcpp.toml` 补全、从 `export module` 声明里读出模块名、
  用法片段取自仓库自己的测试项目。
- [`xim-pkgindex/.xpkgindex/plugins/xim.py`](https://github.com/openxlings/xim-pkgindex/blob/main/.xpkgindex/plugins/xim.py)
  —— 朴素标识、把 xvm / programs / 架构做成分面与区块、card 行布局。
