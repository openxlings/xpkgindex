"""UI strings for the framework chrome.

Only the framework's own text is translated. Everything the index repository
supplies — site title, package descriptions, guide bodies — is rendered as
authored, because the framework has no business machine-translating a
maintainer's words. A consumer that wants translated guides supplies them
through `guides[].translations`; where it does not, the default text shows in
every locale.
"""

from __future__ import annotations

from typing import Dict, List

DEFAULT = "en"

# Display names are written in the language itself: someone looking for
# Chinese should not have to read English to find it.
LANGUAGE_NAMES = {
    "en": "English",
    "zh": "简体中文",
    "zh-Hant": "繁體中文",
}

_EN: Dict[str, str] = {
    "nav.packages": "Packages",
    "nav.stats": "Stats",
    "nav.contributors": "Contributors",
    "nav.about": "About",
    "nav.guides": "Guides",
    "nav.docs_section": "Docs",
    "home.quick_start": "Quick start",
    "nav.search": "Search packages",
    "nav.theme": "Toggle color theme",
    "nav.language": "Language",
    "nav.repository": "Repository",
    "nav.forum": "Community forum",
    "nav.docs": "Documentation",
    "nav.skip": "Skip to content",

    "stat.packages": "packages",
    "stat.namespaces": "namespaces",
    "stat.versions": "versions",

    "home.install": "Install",
    "home.other_install": "Other ways to install",
    "home.growth": "Growth",
    "home.history": "History line",
    "home.contributors": "Contributors",
    "home.see_everyone": "See everyone →",
    "home.all_stats": "All stats →",
    "home.all": "All",
    "home.show": "show",
    "home.no_match": "No package matches.",
    "home.more": "+{n} more",
    "facet.namespace": "namespace",

    "pkg.versions": "Versions",
    "pkg.version": "Version",
    "pkg.platforms": "Platforms",
    "pkg.mirrors": "Mirrors",
    "pkg.source": "source",
    "pkg.latest": "latest",
    "pkg.show_all_versions": "Show all {n} versions",
    "pkg.facts": "Facts",
    "pkg.license": "License",
    "pkg.dependencies": "Dependencies",
    "pkg.required_by": "Required by",
    "pkg.none": "none",
    "pkg.people": "People",
    "pkg.upstream": "Upstream",
    "pkg.descriptor": "Descriptor",
    "pkg.added": "added",
    "pkg.links": "Links",
    "pkg.upstream_repo": "Upstream repository",
    "pkg.homepage": "Homepage",
    "pkg.docs": "Documentation",
    "pkg.descriptor_source": "Descriptor source",
    "pkg.add_like_this": "Add a package like this",
    "pkg.history": "History",
    "pkg.index_default": "index default",
    "pkg.index_default_hint":
        "The descriptor omits a namespace, so it resolves under this index's default one",

    "stats.title": "Stats",
    "stats.over_time": "Packages over time",
    "stats.replayed":
        "Replayed from git history (add / delete / rename), first descriptor {start} → {end}.",
    "stats.composition": "Composition",
    "stats.history": "History line",
    "stats.no_git": "No git history available in this build — the growth curve is skipped.",

    "con.title": "Contributors",
    "con.index": "Index contributors",
    "con.index_caption":
        "The people who write and maintain the descriptors under {dir}/. "
        "Git identities are merged, so one person counts once even across "
        "several names and addresses.",
    "con.commits": "commit",
    "con.commits_plural": "commits",
    "con.packages": "package",
    "con.packages_plural": "packages",
    "con.upstream": "Upstream thanks",
    "con.upstream_caption":
        "These libraries were written by their upstream authors and teams; "
        "this index only wires them into {project}.",
    "con.upstream_count": "{packages} packages ← {upstreams} upstream projects.",
    "con.upstream_note":
        "The count badge is how many packages in this index come from that project.",
    "con.ecosystem": "Ecosystem contributors",
    "con.ecosystem_caption":
        "The union across the ecosystem's own repositories, de-duplicated by GitHub account.",
    "con.ecosystem_hint": "Configure ecosystem.repos to populate this section.",
    "con.offline": "Contributor data is not in the build cache (offline or rate limited).",
    "con.no_git": "No git history available in this build.",

    "guide.language": "Language",
    "guide.guides": "Guides",
    "guide.on_this_page": "On this page",
    "guide.rendered_from":
        "Rendered from {path} in the index repository — one source of truth, "
        "no second copy to drift.",

    "about.title": "About",
    "about.project": "Project",
    "about.index_repo": "Index repository",
    "about.maintainers": "Maintainers",
    "about.license": "License",
    "about.data": "Data",
    "about.data_caption":
        "The site is generated from the descriptors in the index repository. "
        "The same data is published as JSON, in the shape a server API would return.",
    "about.everything": "everything (schema 1)",
    "about.search_payload": "search payload",
    "about.legacy": "legacy schema 0, kept for one release cycle",
    "about.each_package": "Each package also publishes {path}.",
    "about.build": "Build",
    "about.time": "Time",
    "about.commit": "Commit",
    "about.generator": "Generator",
    "about.warnings": "Build warnings",
    "about.warnings_caption":
        "Soft degradations from this build. Data-correctness problems fail the "
        "build instead of appearing here.",

    "alias.moved": "Moved",
    "alias.moved_body": "{short} now lives at",
    "alias.which": "Which {short}?",
    "alias.ambiguous":
        "This short name belongs to more than one package. Earlier versions of "
        "this site collapsed them onto a single page, which silently hid all but "
        "one — so the ambiguity is now shown instead of guessed.",

    "kind.added": "added",
    "kind.updated": "updated",
    "kind.removed": "removed",
}

_ZH: Dict[str, str] = {
    "nav.packages": "包",
    "nav.stats": "统计",
    "nav.contributors": "贡献者",
    "nav.about": "关于",
    "nav.guides": "指南",
    "nav.docs_section": "文档",
    "home.quick_start": "快速开始",
    "nav.search": "搜索包",
    "nav.theme": "切换深浅主题",
    "nav.language": "语言",
    "nav.repository": "仓库",
    "nav.forum": "社区论坛",
    "nav.docs": "文档",
    "nav.skip": "跳到正文",

    "stat.packages": "个包",
    "stat.namespaces": "个命名空间",
    "stat.versions": "个版本",

    "home.install": "安装",
    "home.other_install": "其它安装方式",
    "home.growth": "增长",
    "home.history": "更新时间线",
    "home.contributors": "贡献者",
    "home.see_everyone": "查看全部 →",
    "home.all_stats": "完整统计 →",
    "home.all": "全部",
    "home.show": "显示",
    "home.no_match": "没有匹配的包。",
    "home.more": "还有 {n} 个",
    "facet.namespace": "命名空间",

    "pkg.versions": "版本",
    "pkg.version": "版本",
    "pkg.platforms": "平台",
    "pkg.mirrors": "镜像",
    "pkg.source": "源站",
    "pkg.latest": "最新",
    "pkg.show_all_versions": "展开全部 {n} 个版本",
    "pkg.facts": "概览",
    "pkg.license": "许可证",
    "pkg.dependencies": "依赖",
    "pkg.required_by": "被依赖",
    "pkg.none": "无",
    "pkg.people": "相关人员",
    "pkg.upstream": "上游",
    "pkg.descriptor": "描述符",
    "pkg.added": "新增者",
    "pkg.links": "链接",
    "pkg.upstream_repo": "上游仓库",
    "pkg.homepage": "主页",
    "pkg.docs": "文档",
    "pkg.descriptor_source": "描述符源码",
    "pkg.add_like_this": "照着加一个包",
    "pkg.history": "历史",
    "pkg.index_default": "索引默认",
    "pkg.index_default_hint": "描述符未写 namespace,归入本索引的默认命名空间",

    "stats.title": "统计",
    "stats.over_time": "包数量随时间变化",
    "stats.replayed": "由 git 历史回放得出(新增 / 删除 / 重命名),首个描述符 {start} → {end}。",
    "stats.composition": "构成",
    "stats.history": "更新时间线",
    "stats.no_git": "本次构建没有 git 历史,增长曲线已跳过。",

    "con.title": "贡献者",
    "con.index": "索引贡献者",
    "con.index_caption": "编写与维护 {dir}/ 下描述符的人。git 身份已归并,同一个人即使用过多个用户名和邮箱也只计一次。",
    "con.commits": "个提交",
    "con.commits_plural": "个提交",
    "con.packages": "个包",
    "con.packages_plural": "个包",
    "con.upstream": "上游致谢",
    "con.upstream_caption": "这些库由上游的作者与团队写就,索引只是把它们接入 {project}。",
    "con.upstream_count": "{packages} 个包 ← {upstreams} 个上游项目。",
    "con.upstream_note": "徽章数字是该上游项目在本索引中被打成了几个包。",
    "con.ecosystem": "生态贡献者",
    "con.ecosystem_caption": "跨生态自有仓库的并集,按 GitHub 账号去重。",
    "con.ecosystem_hint": "配置 ecosystem.repos 以填充本区块。",
    "con.offline": "构建缓存中没有贡献者数据(离线或被限流)。",
    "con.no_git": "本次构建没有 git 历史。",

    "guide.language": "语言",
    "guide.guides": "指南",
    "guide.on_this_page": "本页目录",
    "guide.rendered_from": "由索引仓的 {path} 渲染而来 —— 单一真源,不存在第二份会走样的副本。",

    "about.title": "关于",
    "about.project": "项目",
    "about.index_repo": "索引仓库",
    "about.maintainers": "维护者",
    "about.license": "许可证",
    "about.data": "数据",
    "about.data_caption": "站点由索引仓的描述符生成。同一份数据以 JSON 发布,形态与服务端 API 的响应一致。",
    "about.everything": "全量数据(schema 1)",
    "about.search_payload": "搜索索引",
    "about.legacy": "旧版 schema 0,保留一个发布周期",
    "about.each_package": "每个包另有 {path}。",
    "about.build": "构建",
    "about.time": "时间",
    "about.commit": "提交",
    "about.generator": "生成器",
    "about.warnings": "构建警告",
    "about.warnings_caption": "本次构建的软降级项。数据正确性问题会直接让构建失败,不会出现在这里。",

    "alias.moved": "已迁移",
    "alias.moved_body": "{short} 现在位于",
    "alias.which": "哪一个 {short}?",
    "alias.ambiguous": "这个短名对应多个包。此前的站点把它们塞进同一个页面,悄悄只留下了其中一个——现在改为把歧义摆出来,而不是替你猜。",

    "kind.added": "新增",
    "kind.updated": "更新",
    "kind.removed": "移除",
}

_ZH_HANT: Dict[str, str] = {
    "nav.packages": "套件",
    "nav.stats": "統計",
    "nav.contributors": "貢獻者",
    "nav.about": "關於",
    "nav.guides": "指南",
    "nav.docs_section": "文件",
    "home.quick_start": "快速開始",
    "nav.search": "搜尋套件",
    "nav.theme": "切換深淺主題",
    "nav.language": "語言",
    "nav.repository": "儲存庫",
    "nav.forum": "社群論壇",
    "nav.docs": "文件",
    "nav.skip": "跳至內容",

    "stat.packages": "個套件",
    "stat.namespaces": "個命名空間",
    "stat.versions": "個版本",

    "home.install": "安裝",
    "home.other_install": "其他安裝方式",
    "home.growth": "成長",
    "home.history": "更新時間軸",
    "home.contributors": "貢獻者",
    "home.see_everyone": "查看全部 →",
    "home.all_stats": "完整統計 →",
    "home.all": "全部",
    "home.show": "顯示",
    "home.no_match": "沒有符合的套件。",
    "home.more": "還有 {n} 個",
    "facet.namespace": "命名空間",

    "pkg.versions": "版本",
    "pkg.version": "版本",
    "pkg.platforms": "平台",
    "pkg.mirrors": "鏡像",
    "pkg.source": "來源",
    "pkg.latest": "最新",
    "pkg.show_all_versions": "展開全部 {n} 個版本",
    "pkg.facts": "概覽",
    "pkg.license": "授權",
    "pkg.dependencies": "相依",
    "pkg.required_by": "被相依",
    "pkg.none": "無",
    "pkg.people": "相關人員",
    "pkg.upstream": "上游",
    "pkg.descriptor": "描述檔",
    "pkg.added": "新增者",
    "pkg.links": "連結",
    "pkg.upstream_repo": "上游儲存庫",
    "pkg.homepage": "首頁",
    "pkg.docs": "文件",
    "pkg.descriptor_source": "描述檔原始碼",
    "pkg.add_like_this": "照著新增一個套件",
    "pkg.history": "歷史",
    "pkg.index_default": "索引預設",
    "pkg.index_default_hint": "描述檔未填寫 namespace,歸入本索引的預設命名空間",

    "stats.title": "統計",
    "stats.over_time": "套件數量隨時間變化",
    "stats.replayed": "由 git 歷史重播得出(新增 / 刪除 / 更名),首個描述檔 {start} → {end}。",
    "stats.composition": "組成",
    "stats.history": "更新時間軸",
    "stats.no_git": "本次建置沒有 git 歷史,成長曲線已略過。",

    "con.title": "貢獻者",
    "con.index": "索引貢獻者",
    "con.index_caption": "撰寫與維護 {dir}/ 下描述檔的人。git 身分已合併,同一人即使用過多個名稱與信箱也只計一次。",
    "con.commits": "個提交",
    "con.commits_plural": "個提交",
    "con.packages": "個套件",
    "con.packages_plural": "個套件",
    "con.upstream": "上游致謝",
    "con.upstream_caption": "這些函式庫由上游的作者與團隊寫成,索引只是把它們接進 {project}。",
    "con.upstream_count": "{packages} 個套件 ← {upstreams} 個上游專案。",
    "con.upstream_note": "徽章數字是該上游專案在本索引中被打成幾個套件。",
    "con.ecosystem": "生態貢獻者",
    "con.ecosystem_caption": "跨生態自有儲存庫的聯集,依 GitHub 帳號去重。",
    "con.ecosystem_hint": "設定 ecosystem.repos 以填入本區塊。",
    "con.offline": "建置快取中沒有貢獻者資料(離線或遭限流)。",
    "con.no_git": "本次建置沒有 git 歷史。",

    "guide.language": "語言",
    "guide.guides": "指南",
    "guide.on_this_page": "本頁目錄",
    "guide.rendered_from": "由索引儲存庫的 {path} 轉譯而來 —— 單一真實來源,沒有第二份會走樣的副本。",

    "about.title": "關於",
    "about.project": "專案",
    "about.index_repo": "索引儲存庫",
    "about.maintainers": "維護者",
    "about.license": "授權",
    "about.data": "資料",
    "about.data_caption": "站台由索引儲存庫的描述檔產生。同一份資料以 JSON 發布,形態與伺服端 API 的回應一致。",
    "about.everything": "全量資料(schema 1)",
    "about.search_payload": "搜尋索引",
    "about.legacy": "舊版 schema 0,保留一個發布週期",
    "about.each_package": "每個套件另有 {path}。",
    "about.build": "建置",
    "about.time": "時間",
    "about.commit": "提交",
    "about.generator": "產生器",
    "about.warnings": "建置警告",
    "about.warnings_caption": "本次建置的軟降級項。資料正確性問題會直接讓建置失敗,不會出現在這裡。",

    "alias.moved": "已遷移",
    "alias.moved_body": "{short} 現在位於",
    "alias.which": "哪一個 {short}?",
    "alias.ambiguous": "這個短名對應多個套件。先前的站台把它們塞進同一個頁面,悄悄只留下其中一個——現在改為把歧義攤開,而不是替你猜。",

    "kind.added": "新增",
    "kind.updated": "更新",
    "kind.removed": "移除",
}

CATALOG: Dict[str, Dict[str, str]] = {
    "en": _EN,
    "zh": _ZH,
    "zh-Hant": _ZH_HANT,
}

# Browser/locale tags that should resolve to one of our catalogs.
ALIASES = {
    "zh-cn": "zh", "zh-hans": "zh", "zh-sg": "zh",
    "zh-tw": "zh-Hant", "zh-hk": "zh-Hant", "zh-mo": "zh-Hant",
}


def normalize(tag: str) -> str:
    if tag in CATALOG:
        return tag
    return ALIASES.get((tag or "").lower(), DEFAULT)


def available(tags: List[str]) -> List[str]:
    """Keep the configured order, drop unknown tags, always leave one."""
    out = [t for t in tags if t in CATALOG]
    return out or [DEFAULT]


class Translator:
    """`t("key")` with `{placeholder}` substitution, falling back to English.

    A missing key returns the key itself rather than an empty string: a broken
    string should be visible in review, not silently blank on the page.
    """

    def __init__(self, lang: str) -> None:
        self.lang = lang if lang in CATALOG else DEFAULT
        self.table = CATALOG[self.lang]

    def __call__(self, key: str, **kwargs) -> str:
        text = self.table.get(key) or _EN.get(key) or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text

    def plural(self, n: int, key: str) -> str:
        """English needs the plural form; the Chinese catalogs map both to the
        same string, so this stays a no-op there."""
        return self(key + ("_plural" if n != 1 else ""))

    @property
    def html_lang(self) -> str:
        return {"zh": "zh-Hans", "zh-Hant": "zh-Hant"}.get(self.lang, self.lang)
