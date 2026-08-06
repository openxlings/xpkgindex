# 部署

[English](../deployment.md) | **简体中文**

产物是一个普通目录。任何能提供静态文件的东西都能托管它。

## GitHub Pages

```yaml
name: deploy-site

on:
  push:
    branches: [main]
    paths: ['pkgs/**', '.xpkgindex.json', '.xpkgindex/**', 'docs/**']
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # 增长曲线要回放整个日志
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install git+https://github.com/openxlings/xpkgindex.git
      - name: Generate
        env:
          GITHUB_TOKEN:               ${{ secrets.GITHUB_TOKEN }}
          XPKGINDEX_BUILD_TIME:       ${{ github.event.head_commit.timestamp }}
          XPKGINDEX_BUILD_COMMIT:     ${{ github.sha }}
          XPKGINDEX_BUILD_COMMIT_URL: ${{ github.server_url }}/${{ github.repository }}/commit/${{ github.sha }}
        run: xpkgindex generate . --output site
      - uses: actions/upload-pages-artifact@v3
        with:
          path: ./site

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

**`fetch-depth: 0` 不是可选的。** 增长曲线、历史线和贡献者名单都从 git 日志回放
得来;浅克隆产出的曲线会从浅克隆边界开始,而构建自带的对账检查会当场告诉你这件事。

### 构建溯源

三个环境变量,都可选,都会出现在「关于」页和 `index.json` 的 `site` 下:

| 变量 | 变成 |
|---|---|
| `XPKGINDEX_BUILD_TIME` | 这个站点是什么时候构建的 |
| `XPKGINDEX_BUILD_COMMIT` | 它构建自哪个提交 |
| `XPKGINDEX_BUILD_COMMIT_URL` | 指向那个提交的链接 |

`workflow_dispatch` 触发时 `head_commit.timestamp` 是空的,补一下:

```bash
if [ -z "$XPKGINDEX_BUILD_TIME" ]; then
  XPKGINDEX_BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ); export XPKGINDEX_BUILD_TIME
fi
```

## 网络缓存

`GITHUB_TOKEN` 提高 API 限额,并启用把贡献者身份合并起来的 作者→登录名 映射。
没有它构建照样成功,只是头像少一些、合并弱一些。

`.xpkgindex/cache/github.json` 是要提交的。它只存投影过的字段 —— 登录名、头像、
描述、star 数 —— 因此构建可复现,并且在未认证限流时也活得下来。

显式刷新,而不是每次构建都刷:

```yaml
name: refresh-site-cache
on: { workflow_dispatch: }

jobs:
  refresh:
    runs-on: ubuntu-latest
    permissions: { contents: write }
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install git+https://github.com/openxlings/xpkgindex.git
      - env: { GITHUB_TOKEN: '${{ secrets.GITHUB_TOKEN }}' }
        run: xpkgindex generate . --output /tmp/site --refresh
      - run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add .xpkgindex/cache
          git diff --staged --quiet || git commit -m "chore(site): refresh upstream cache"
          git push
```

两个真实索引带的就是这个工作流,并且都是在上游清单或仓库描述变动之后手动跑一次。

## 在 CI 里做校验

在 PR 上构建但不发布:

```bash
xpkgindex generate . --output /tmp/site --offline --strict
```

`--offline` 让 PR 不消耗 API 限额,并让结果只取决于仓库里的内容。`--strict` 把
增长对账的警告变成错误 —— 如果回放出的历史和工作树不一致,站点上的曲线就是错的,
这值得让构建失败。

不算错误的警告由 `generate` 打印;一个在其输出里 grep `warning:` 的 PR 检查是合理
的额外防线。

## 其他任何地方

```bash
xpkgindex generate . --output site --base-url https://packages.example.org
```

`--base-url` 只被 `sitemap.xml` 和 `feed.xml` 使用 —— 站点内部的链接全是相对的,
所以同一份产物在域名根目录、子目录,甚至从磁盘打开都能用。用任何静态文件服务器
托管 `site/` 即可;目录形态的 URL 需要 `index.html` 解析,而这是它们默认都做的。

### 不解析目录的宿主

有些静态宿主只提供文件:`/stats/` 在那里是 404,只有 `/stats/index.html` 存在。
本框架写出的内链全是目录形态,所以在这类宿主上,首页能渲染,点第一下就 404。

```bash
xpkgindex generate . --output site --url-style file
```

之后所有内链都以 `index.html` 结尾 —— 包括你自己文档正文里的那些(它们在构建期
被改写)。两种形态写到磁盘的文件完全相同,所以这只是重新渲染一次,而不是另一个
站点;同一个仓库可以同时发两种形态:

```bash
xpkgindex generate . --output site                     # GitHub Pages
xpkgindex generate . --output site-flat --url-style file   # 另一个宿主
```

配置里的 `urls.style` 设定每次构建的默认值,命令行参数覆盖单次构建。

发布前想本地看一眼:

```bash
xpkgindex serve . --port 8000
```

它会构建并起服务,并发送 `Cache-Control: no-store` —— 一个还在显示上一次构建的
预览,比没有预览更糟。
