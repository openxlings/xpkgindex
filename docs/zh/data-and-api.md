# 数据与 API

[English](../data-and-api.md) | **简体中文**

每次构建都会在页面之外产出机器可读的文档。它们按 API 响应的形态设计是有意的:
将来服务端接管静态构建时,同样的文档在同样的 URL 上供给,所有消费者继续可用。

| URL | 内容 |
|---|---|
| `/index.json` | 全部内容 —— schema 1 |
| `/packages/<slug>/index.json` | 单个包,与 `packages[]` 里的对象一致 |
| `/search-index.json` | 页头搜索用的小负载 |
| `/packages.json` | schema 0,为已有消费者保留一个发布周期 |
| `/sitemap.xml`、`/feed.xml` | 覆盖所有语言;历史线的 Atom 订阅 |

它们只生成一份,使用站点的默认语言。

## `/index.json`

```jsonc
{
  "schema": 1,
  "site":  { "title", "description", "github", "time"?, "commit"?, "commit_url"?, "generator"? },
  "index": { },                    // 插件放进 IndexMeta 的任何东西
  "stats": { "packages", "namespaces", "versions" },
  "facets":  [ { "key", "label", "values": [ { "key", "label", "count", "tone" } ] } ],
  "growth":  [ { "date", "count", "added", "removed" } ],   // 有活动的每一天一个点
  "history": [ { "date", "at", "kind", "slug", "display", "by", "subject" } ],   // 最新 200 条
  "guides":  [ { "slug", "title", "source" } ],
  "packages": [ /* 见下 */ ]
}
```

`site.time`、`site.commit`、`site.commit_url` 是构建溯源信息,CI 提供时才有 ——
见[部署](deployment.md)。

`history[].kind` 取 `added`、`updated` 或 `removed`;`at` 是完整的 ISO 8601 作者
时间戳,`date` 是增长曲线用来分组的那一天。

`growth[].count` 是该日期索引里的包数;`added` 与 `removed` 是当天的增减。只有有
活动的日子才产生点。

### 一个包

```jsonc
{
  "id": "nlohmann.json",
  "namespace": "nlohmann",
  "namespace_effective": "nlohmann",   // 描述符没写时回退到索引默认
  "namespace_implicit": false,         // 描述符没写时为 true
  "name": "json",
  "display": "nlohmann.json",
  "slug": "nlohmann.json",
  "install_ref": "nlohmann.json",
  "description": "...",
  "homepage": "...", "repo": "...", "docs": "...",
  "licenses": ["MIT"],
  "type": "package", "status": "",
  "latest": "3.12.0",
  "platforms": { "linux": { "versions": [...], "latest": "...", "deps": [...] } },
  "versions": [ { "version", "platforms": [...], "urls": { "GLOBAL": "..." }, "sha256" } ],
  "deps": [...], "required_by": [...],
  "facets": { "surface": "module header" },
  "people": {
    "upstream":   { "owner", "url", "avatar", "description", "stars", "host" },
    "descriptor": [ { "login", "name", "avatar", "url", "added" } ]
  },
  "history": [ { "date", "at", "clock", "kind", "by", "subject" } ],   // 最新 12 条
  "extensions": { "mcpp": { } },       // 插件所有,按插件名分组
  "blocks": [ { "kind", "title", "data", "plugin", "collapsed", "weight" } ],
  "source_file": "pkgs/n/nlohmann.json.lua"
}
```

三个标识字段是故意分开的,且不能互相推导 —— `display` 给人看,`slug` 是 URL,
`install_ref` 是客户端 CLI 接受的形式。见[架构](architecture.md#标识与-slug)。

`facets` 的值以空白分隔:`"module header"` 表示这个包同时属于 `surface` 轴的两个
值。

`extensions` 是插件自己数据的落脚点,按插件名分组。它原样传递,这正是让插件的工作
不只对站点可用、而是对任何读这份 JSON 的东西都可用的原因。

### 稳定性

schema 1 承诺:上面这些键、它们的类型,以及目录形态的 URL。有两点值得明说:

- 按语言的文案在这里会展平成默认语言。标签永远是字符串。
- 新键可能出现。请宽容解析,不要假设这个集合是封闭的。

`/packages.json` 是改版前的形态。保留它是为了新站点上线那天,消费旧接口的东西不会
立刻挂掉;它也是唯一一份有明确退休预期的文档。

## `/search-index.json`

刻意做小 —— 页头搜索在第一次按键时才拉取:

```jsonc
[ { "s": "slug", "d": "display", "n": "name", "ns": "namespace",
    "t": "描述,截断到 160 字符", "f": { 分面 }, "v": "最新版本" } ]
```

## `/feed.xml`

历史线的 Atom 形态:最新 40 条事件,每条链到对应的包页面。这是不 watch 仓库也能
跟进一个索引的方式。
