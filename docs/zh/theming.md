# 主题

[English](../theming.md) | **简体中文**

三层,按你要承担的程度递增:

1. **令牌** —— `.xpkgindex.json` 里的 `theme`。只有颜色,不写 CSS。
2. **结构** —— 列表布局,以及插件往行里放什么。
3. **模板** —— `Block.template` / `RowSpec.styles`,明示的逃生口,留给前两层确实
   表达不了的情况。

大多数索引永远停在第一层。

## 令牌

`theme` 会被编译成 `static/css/theme.css`,它在 `site.css` 之后加载,所以覆盖而
不用改框架的样式表。只有你配置了的项才会输出 —— 其余全部保留内置值,包括夜间模式
的那套调整。

```jsonc
"theme": {
  "accent": "#5b46d6",
  "style":  "auto",
  "tones":  { "module": "#5b46d6", "header": "#52606d", "tool": "#b8690f" },
  "dark":   { "accent": "#9b8bfa",
              "tones": { "module": "#9b8bfa", "header": "#a7b6c7", "tool": "#e0a260" } },
  "transition": { "duration": "2s", "easing": "cubic-bezier(.45, .05, .25, 1)" }
}
```

### 有哪些令牌

| 分组 | 令牌 |
|---|---|
| 面 | `--bg`、`--bg-sunken`、`--bg-raised`、`--bg-code` |
| 线 | `--line`、`--line-soft` |
| 文字 | `--ink`、`--ink-2`、`--ink-3`、`--ink-4` |
| 语义 | `--tone-accent`、`--tone-module`、`--tone-header`、`--tone-tool`、`--tone-neutral` |
| 图表 | `--series-1`、`--series-2`、`--series-3` |
| 几何 | `--radius`、`--radius-sm`、`--gap`、`--maxw`、`--shadow` |

`theme.accent` 设置 `--tone-accent`;`theme.tones` 下的每个键设置
`--tone-<key>`。插件在 `RowSpec` 或 `FacetValue` 上写的 `tone="module"`,就是靠这
一层变成颜色的 —— 插件自己不需要知道任何颜色。

色调是*给含义起的名字*,不是装饰:同一个色调同时标记一个包的行、它的类型标签,
以及它在增长曲线上的那条线,于是这三处天然一致。

### 白天、夜晚,以及切换

`style` 取 `auto`(跟随系统)、`light` 或 `dark`。访客一旦显式选过,选择会被记住并
从此压过系统设置;这个选择由 `<head>` 里的一小段脚本在首次绘制前应用,所以页面
不会先闪一下错误的主题。

切换本身是交叉淡入:

```jsonc
"transition": { "duration": "2s", "easing": "cubic-bezier(.45, .05, .25, 1)" }
```

`"0s"` 即瞬切,这也是开启了 `prefers-reduced-motion` 的访客始终得到的效果。

实现方式值得一说,因为最直觉的写法撑不住真实的列表页。给 `*` 加 `transition` 会
在每个元素和伪元素上都挂动画 —— 几百个包的页面上就是几万个 —— 切换会卡在 20fps
左右。所以:

- 浏览器支持 **view transition** 时,切换是两张快照在合成器上的交叉淡入。代价与
  页面多大无关;同一个列表页实测稳定 60fps。因为这期间屏幕上是一张静止图,任何
  滚动、点击或按键都会立刻结束淡入。
- 其他情况下,直接对**颜色令牌本身**做插值。它们用 `@property` 注册成 `<color>`
  正是为了能被插值 —— 未注册的自定义属性只会从一个值直接跳到另一个值。这样整页
  只有 `<html>` 上的一条 transition,而不是几万条;而且只在切换期间挂着。

## 列表布局

列表行是各生态分歧最大的地方,所以它是数据,不是标记。内置两套:

**`code`** —— 三行,每行语义固定:

```
// nlohmann.json 3.12.0 — JSON for Modern C++
import nlohmann.json;
mcpp add nlohmann.json@3.12.0          MIT · 3 platforms · ✓ 有示例
```

**`card`** —— 名字与元信息在标题行,一条可复制的命令在着色条带里:

```
gcc 15.1.0   tool   GPL-3.0 · 2 platforms · xvm
The GNU Compiler Collection
xlings install gcc@15.1.0                                    $ gcc
```

用 `list.variant` 设定默认,插件用 `RowSpec.variant` 逐包覆盖。无论选哪套,行在
任何屏幕宽度下都保持三行 —— 放不下的部分以省略号截断而不是换行,因为一行在手机上
变成四行,整个列表赖以成立的扫读节奏就断了。

## 密度与宽度

`--maxw`(默认 `1140px`)决定内容宽度;`--gap` 和两个圆角令牌承担了其余大部分
观感。它们不能通过 `theme.tones` 覆盖 —— 那是几何,不是颜色 —— 所以想换宽度的
索引要么在生成物旁边自带一小段 CSS,要么走模板逃生口。

## 逃生口

`Block.template` 与 `RowSpec.template` / `RowSpec.styles` 允许插件为某个区块或某
一行提供自己的标记。它们存在的意义是:让「这五种区块表达不了」有一个写在插件里、
看得见的答案,而不是把 HTML 字符串塞进 caption 里偷偷混过去。

用了它们,你就放弃了「所有消费者站点看起来像同一套系统」这个保证,所以放到最后
再考虑。
