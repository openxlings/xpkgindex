"""xpkg `.lua` descriptor reader.

Executes each descriptor in a sandboxed Lua runtime (lupa) and extracts the
`package` table. The reader fills in only ecosystem-neutral fields; the whole
parsed table is kept on `Package.raw` so plugins can read their own extension
blocks without re-parsing.
"""

from __future__ import annotations

import glob
import os
from typing import Any, Dict, List, Optional, Tuple

from lupa import LuaRuntime

from ..models import Identity, Package, PlatformInfo, Version

# Loader sandbox, kept in lockstep with the xpkg reference implementation:
# `register_loader_sandbox` in libxpkg's `src/xpkg-loader.cppm`. Descriptors
# are data with hooks attached and we only want the data, but the data is
# produced by top-level Lua that may call non-standard globals.
#
# Parity is the point. If this sandbox were more permissive than libxpkg the
# site would advertise packages the toolchain cannot load; if it were
# stricter, valid packages would silently vanish from the index page. So the
# rule is: whatever libxpkg stubs, stub identically — including the deep
# proxy returned by `import()`, which is what lets a descriptor call
# `pkginfo.version()` at file scope without crashing.
#
# (`format` and `is_host` are xmake-era globals the V1 spec explicitly
# forbids — see docs/V1/xpackage-spec.md — but legacy descriptors such as
# busybox, libpng and cairo still call them, and libxpkg stubs them
# defensively for exactly that reason.)
_LUA_SANDBOX = """
do
  local function make_proxy()
    return setmetatable({}, {
      __index    = function(_, k) return make_proxy() end,
      __call     = function() return make_proxy() end,
      __tostring = function() return '' end,
      __concat   = function(a, b) return tostring(a) .. tostring(b) end,
    })
  end
  import = function(name, ...)
    local proxy = make_proxy()
    if type(name) == 'string' then
      local short = name:match('[^.]+$') or name
      rawset(_G, short, proxy)
    end
    return proxy
  end
end

function is_host() return false end
format = string.format

os.host      = os.host      or function() return 'unknown' end
os.isfile    = os.isfile    or function() return false end
os.isdir     = os.isdir     or function() return false end
os.scriptdir = os.scriptdir or function() return '.' end
os.dirs      = os.dirs      or function() return {} end
os.files     = os.files     or function() return {} end
os.exists    = os.exists    or function() return false end
os.tryrm     = os.tryrm     or function() end
os.trymv     = os.trymv     or function() end
os.iorun     = os.iorun     or function() return nil end
os.cd        = os.cd        or function() end
os.mkdir     = os.mkdir     or function() end
os.sleep     = os.sleep     or function() end

path = path or {}
path.join = path.join or function(...)
  local parts = {}
  for i = 1, select('#', ...) do
    local v = select(i, ...)
    if v ~= nil then parts[#parts+1] = tostring(v) end
  end
  return table.concat(parts, '/')
end
path.filename  = path.filename  or function(p) return type(p)=='string' and (p:match('[^/\\\\]+$') or p) or '' end
path.directory = path.directory or function(p) return type(p)=='string' and (p:match('(.*)[/\\\\]') or '.') or '.' end
path.basename  = path.basename  or function(p) return type(p)=='string' and (p:match('[^/\\\\]+$') or p) or '' end

io.readfile  = io.readfile  or function() return '' end
io.writefile = io.writefile or function() end

try = try or function(block) pcall(block[1]) end
cprint = cprint or print

string.replace = string.replace or function(s, old, new) return s:gsub(old, new) end
string.split = string.split or function(s, sep)
  local r = {}
  for m in (s .. sep):gmatch('(.-)' .. sep) do r[#r+1] = m end
  return r
end

raise = raise or function() end

runtime = setmetatable({}, { __index = function() return function() return '' end end })
system  = setmetatable({}, { __index = function() return function() return '' end end })
libxpkg = setmetatable({}, { __index = function() return setmetatable({}, { __index = function() return function() return '' end end }) end })
"""

PLATFORMS = ("linux", "windows", "macosx")


class ReaderError(Exception):
    """A single descriptor failed to parse — reported, never fatal."""


def _make_lua() -> LuaRuntime:
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(_LUA_SANDBOX)
    return lua


def _to_python(obj: Any) -> Any:
    """Recursively convert a Lua table into plain dict/list."""
    if not hasattr(obj, "keys"):
        return obj
    keys = list(obj.keys())
    if not keys:
        return {}
    if all(isinstance(k, (int, float)) for k in keys):
        int_keys = sorted(int(k) for k in keys)
        if int_keys == list(range(1, len(int_keys) + 1)):
            return [_to_python(obj[k]) for k in sorted(keys)]
    result = {}
    for k in keys:
        result[str(k)] = _to_python(obj[k])
    return result


def _urls(entry: Dict[str, Any]) -> Dict[str, str]:
    """A version's download URLs: either a plain string or a mirror table."""
    url = entry.get("url")
    if isinstance(url, str):
        return {"DEFAULT": url}
    if isinstance(url, dict):
        return {str(k): str(v) for k, v in url.items() if isinstance(v, str)}
    return {}


def _version_key(v: str):
    """Best-effort natural ordering; unparsable segments sort as text."""
    parts = []
    for chunk in v.replace("-", ".").split("."):
        parts.append((0, int(chunk), "") if chunk.isdigit() else (1, 0, chunk))
    return parts


def _platform_info(pdata: Dict[str, Any]) -> Tuple[PlatformInfo, Dict[str, Dict[str, Any]]]:
    info = PlatformInfo(raw=dict(pdata))
    entries: Dict[str, Dict[str, Any]] = {}

    deps = pdata.get("deps")
    if isinstance(deps, list):
        info.deps = [str(d) for d in deps]
    elif isinstance(deps, dict):
        info.deps = [str(v) for v in deps.values()]

    for key, value in pdata.items():
        if key == "deps":
            continue
        if key == "latest":
            if isinstance(value, dict) and "ref" in value:
                info.latest = str(value["ref"])
            continue
        info.versions.append(str(key))
        if isinstance(value, dict):
            entries[str(key)] = value

    info.versions.sort(key=_version_key, reverse=True)
    if not info.latest and info.versions:
        info.latest = info.versions[0]
    return info, entries


def _build(data: Dict[str, Any], filepath: str, rel: str) -> Package:
    pkg = Package(source_file=rel, raw=data)

    for attr in ("description", "homepage", "repo", "docs", "type", "status"):
        val = data.get(attr)
        if isinstance(val, str) and val:
            setattr(pkg, attr, val)

    lic = data.get("licenses")
    if isinstance(lic, list):
        pkg.licenses = [str(v) for v in lic]
    elif isinstance(lic, str):
        pkg.licenses = [lic]

    namespace = str(data.get("namespace") or "")
    name = str(data.get("name") or "")
    if not name:
        # A descriptor missing `name` still needs a stable identity rather than
        # collapsing onto an empty slug (compat.ffmpeg shipped like this once).
        name = os.path.basename(filepath)[: -len(".lua")]
    pkg.identity = Identity.plain(namespace, name)

    xpm = data.get("xpm")
    per_version: Dict[str, Version] = {}
    if isinstance(xpm, dict):
        for platform in PLATFORMS:
            pdata = xpm.get(platform)
            if not isinstance(pdata, dict):
                continue
            info, entries = _platform_info(pdata)
            pkg.platforms[platform] = info
            for vname, entry in entries.items():
                v = per_version.get(vname)
                if v is None:
                    v = Version(version=vname)
                    per_version[vname] = v
                if platform not in v.platforms:
                    v.platforms.append(platform)
                v.urls.update(_urls(entry))
                sha = entry.get("sha256")
                if isinstance(sha, str) and sha and not v.sha256:
                    v.sha256 = sha

    pkg.versions = sorted(per_version.values(),
                          key=lambda v: _version_key(v.version), reverse=True)
    for info in pkg.platforms.values():
        if info.latest:
            pkg.latest = info.latest
            break
    if not pkg.latest and pkg.versions:
        pkg.latest = pkg.versions[0].version

    deps: List[str] = []
    for info in pkg.platforms.values():
        for d in info.deps:
            if d not in deps:
                deps.append(d)
    pkg.deps = deps
    return pkg


def read_file(filepath: str, root: str) -> Optional[Package]:
    """Parse one descriptor. Returns None for ref/alias entries."""
    if not filepath.endswith(".lua"):
        return None
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
        if "package" not in code:
            return None

        lua = _make_lua()
        lua.execute(code)
        table = lua.globals().package
        if table is None:
            return None
        if any(k == "ref" for k in table.keys()):
            return None          # alias entry, not a package of its own

        data = _to_python(table)
        if not isinstance(data, dict):
            return None
        rel = os.path.relpath(filepath, root).replace(os.sep, "/")
        return _build(data, filepath, rel)
    except Exception as exc:                    # noqa: BLE001 - reported, not raised
        raise ReaderError(f"{os.path.basename(filepath)}: {exc}") from exc


def read_dir(pkgs_dir: str, root: str) -> Tuple[List[Package], List[str]]:
    """Parse every `.lua` under `pkgs_dir`. Returns (packages, warnings)."""
    packages: List[Package] = []
    warnings: List[str] = []
    pattern = os.path.join(pkgs_dir, "**", "*.lua")
    for filepath in sorted(glob.glob(pattern, recursive=True)):
        try:
            pkg = read_file(filepath, root)
        except ReaderError as exc:
            warnings.append(f"descriptor parse failed: {exc}")
            continue
        if pkg is not None:
            packages.append(pkg)
    return packages, warnings
