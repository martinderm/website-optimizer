"""Site configuration.

Format note (decision D20): configuration is TOML, not YAML. Python 3.11
shipped `tomllib` in the standard library; YAML did not. The authoring guide
mandates stdlib-only with zero pip dependencies, so a YAML config would either
break that rule or silently depend on a package that happens to be installed on
one machine.

Config layering, deliberately two files:

    site.optimizer.toml            committed, portable values only
    site.optimizer.local.toml      untracked, machine-specific values

A single mixed file cannot be committed without leaking one workstation's
directory layout into every fork of the workspace.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_NAMES = ("site.optimizer.toml", "site.optimizer.local.toml")


@dataclass
class SiteConfig:
    """Portable site identity plus machine-local resolution."""

    site_url: str
    domain: str
    static_dir: Path
    workspace_root: Path
    ignore_path: str = r"admin/.*"
    strict: bool = False
    crawl_mode: str = "static"
    data_classification: str = "internal"
    contacted_private_surface: bool = False
    owner: str = ""
    retention_class: str = "audit-run"
    capabilities: list[str] = field(default_factory=lambda: ["on-page"])
    redirects: dict = field(default_factory=lambda: {
        "file": "static/.htaccess",
        "check_target": True,
        "timeout": 10,
    })

    @property
    def classification(self) -> str:
        """Escalate once if the run met private surface (decision D19)."""
        return "confidential" if self.contacted_private_surface else self.data_classification


class ConfigError(Exception):
    """Raised with a self-correcting message, never a bare KeyError."""


def find_workspace_root(start: Path | None = None) -> Path:
    """Walk up until a marker of an agent workspace appears."""
    current = Path(start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".agents").is_dir() or (candidate / "AGENTS.md").is_file():
            return candidate
    return current


def _as_bool(value, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ConfigError(f"'{field_name}' must be true or false, got {value!r}.")


def _read_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path.name} is not valid TOML: {exc}") from exc


def _merge(base: dict, overlay: dict) -> dict:
    """Deep merge, overlay wins. Section tables merge key by key."""
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load(path: Path | None = None, workspace_root: Path | None = None) -> SiteConfig:
    """Load configuration: the portable file, then local overrides on top.

    The local file is optional and wins where both define a key. That is the
    whole point of the split — the committed file carries what every checkout
    shares, the local file carries what this machine's directory layout needs.
    """
    root = Path(workspace_root) if workspace_root else find_workspace_root()

    if path is not None:
        path = Path(path)
        if not path.is_file():
            raise ConfigError(f"Configuration file not found: {path}")
        data = _read_toml(path)
    else:
        portable = root / CONFIG_NAMES[0]
        if not portable.is_file():
            raise ConfigError(
                f"No site configuration found in {root}.\n"
                f"Create {CONFIG_NAMES[0]} with at least [site] url, or run:\n"
                f"  python scripts/wo.py init-site --site-url https://example.com"
            )
        data = _read_toml(portable)
        local = root / CONFIG_NAMES[1]
        if local.is_file():
            data = _merge(data, _read_toml(local))

    site = data.get("site", {})
    if not site.get("url"):
        raise ConfigError(
            f"Configuration must define [site] url, for example:\n"
            f'  [site]\n  url = "https://example.com"'
        )

    url = str(site["url"]).rstrip("/")
    domain = str(site.get("domain") or url.split("//", 1)[-1].split("/", 1)[0])

    static_dir = Path(str(site.get("static_dir", "public")))
    if not static_dir.is_absolute():
        static_dir = root / static_dir

    audit = data.get("audit", {})
    classification = str(audit.get("data_classification", "internal"))
    allowed = ("public", "internal", "confidential", "restricted")
    if classification not in allowed:
        raise ConfigError(
            f"[audit] data_classification must be one of {allowed}, got {classification!r}."
        )

    return SiteConfig(
        site_url=url,
        domain=domain,
        static_dir=static_dir,
        workspace_root=root,
        ignore_path=str(audit.get("ignore_path", r"admin/.*")),
        strict=_as_bool(audit.get("strict", False), "audit.strict"),
        crawl_mode=str(audit.get("crawl_mode", "static")),
        data_classification=classification,
        contacted_private_surface=bool(audit.get("contacted_private_surface", False)),
        owner=str(audit.get("owner", "")) or root.name,
        retention_class=str(audit.get("retention_class", "audit-run")),
        capabilities=list(audit.get("capabilities", ["on-page"])),
        redirects=_redirect_settings(data),
    )


def _redirect_settings(data: dict) -> dict:
    """`[redirects]` block with defaults and a validated timeout."""
    section = data.get("redirects", {})
    timeout = section.get("timeout", 10)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise ConfigError(
            f"[redirects] timeout must be a positive integer, got {timeout!r}."
        )
    return {
        "file": str(section.get("file", "static/.htaccess")),
        "check_target": _as_bool(section.get("check_target", True), "redirects.check_target"),
        "timeout": timeout,
    }


TEMPLATE = """\
# website-optimizer site configuration
#
# Portable values only. Machine-specific paths belong in
# site.optimizer.local.toml, which is not committed.

[site]
url = "{url}"
domain = "{domain}"
static_dir = "public"

[audit]
capabilities = ["on-page"]
ignore_path = "admin/.*"
strict = false
crawl_mode = "static"

# Set true when the run touches authenticated URLs, a staging host, or an
# internal hostname. Escalates data_classification to "confidential" (D19).
contacted_private_surface = false

# retention_class "audit-run" keeps this run; "crawl-ephemeral" applies to raw
# crawl output under data/, which is regenerable and may be deleted freely.
retention_class = "audit-run"

# Redirect rules are verified live, so this capability needs [redirects].
# Add "redirects" to capabilities above to switch it on.
[redirects]
file = "static/.htaccess"
check_target = true
timeout = 10
"""