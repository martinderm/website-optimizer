#!/usr/bin/env python3
"""website-optimizer — one entry point for every audit run.

    python scripts/wo.py init-site --site-url https://example.com
    python scripts/wo.py on-page [--config FILE] [--json] [--strict]
    python scripts/wo.py run-all [--config FILE] [--json]
    python scripts/wo.py runs  --config FILE
    python scripts/wo.py validate-report FILE

Only `wo.py` is executed. Capability modules are packages, not standalone scripts:
two entry points would drift apart, and the pipeline order belongs in code rather
than in folder names.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wo import config as config_module           # noqa: E402
from wo import envelope as env                   # noqa: E402
from wo import jsonschema                        # noqa: E402
from wo import report as report_module           # noqa: E402
from wo.capabilities import REGISTRY              # noqa: E402

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "audit-report.schema.json"


def _load_config(args):
    """Return (config, None) on success or (None, envelope) on failure."""
    try:
        cfg = config_module.load(
            Path(args.config) if args.config else None,
            Path(args.workspace) if args.workspace else None,
        )
    except config_module.ConfigError as exc:
        return None, env.failure("load-config", "Configuration could not be loaded",
                                 {"type": "ConfigError", "message": str(exc)})
    return cfg, None


def cmd_init_site(args) -> dict:
    if not args.site_url:
        return env.failure("init-site", "A site URL is required",
                           {"type": "MissingArgument",
                            "message": "Pass --site-url, for example https://example.com"})
    url = args.site_url.rstrip("/")
    domain = url.split("//", 1)[-1].split("/", 1)[0]
    root = Path(args.workspace) if args.workspace else config_module.find_workspace_root()
    target = Path(args.out or root / "site.optimizer.toml")
    if target.exists() and not args.force:
        return env.failure("init-site", f"{target.name} already exists",
                           {"type": "FileExists",
                            "message": f"Edit {target} directly, or pass --force to overwrite."})
    report_module.atomic_write(target, config_module.TEMPLATE.format(url=url, domain=domain))
    return env.envelope("init-site", True, "Succeeded",
                        f"Wrote {target.name} for {domain}", data={"path": str(target)})


def _run_capability(name: str, args) -> dict:
    module_name = REGISTRY.get(name)
    if module_name is None:
        return env.failure(name, f"Unknown capability {name!r}",
                           {"type": "UnknownCapability",
                            "message": f"Available: {', '.join(sorted(REGISTRY))}"})
    cfg, failure = _load_config(args)
    if failure:
        return failure

    if name not in cfg.capabilities:
        return env.failure(name, f"Capability {name!r} is not enabled for this site",
                           {"type": "CapabilityDisabled",
                            "message": f"Add \"{name}\" to [audit] capabilities in "
                                       f"site.optimizer.toml to enable it."})

    module = __import__(module_name, fromlist=["run"])
    try:
        result = module.run(cfg, ignore_noindex=args.ignore_noindex)
    except FileNotFoundError as exc:
        return env.failure(name, "Audit could not run", {"type": "MissingInput",
                                                         "message": str(exc)})

    errors = jsonschema.validate(result, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    if errors:
        return env.failure(name, "Report failed schema validation",
                           {"type": "SchemaViolation", "message": "\n".join(errors)})

    written = None
    if not args.dry_run:
        written = report_module.write_run(cfg, result, run=args.run)

    summary = result["summary"]
    return env.envelope(
        name, summary["total_critical_issues"] == 0,
        "Succeeded" if summary["total_critical_issues"] == 0 else "Partial",
        f"{summary['audited_pages']} pages audited, "
        f"{summary['total_critical_issues']} critical, {summary['total_warnings']} warnings",
        data={"summary": summary, "findings": result["findings"],
              "run": written["run_dir"].name if written else None,
              "paths": {k: str(v) for k, v in written.items()} if written else None},
    )


def cmd_on_page(args) -> dict:
    return _run_capability("on-page", args)


def cmd_run_all(args) -> dict:
    """discover -> audit -> compare. Today discover and compare are thin."""
    results = []
    for name in REGISTRY:
        result = _run_capability(name, args)
        if not result["success"] and result["error"].get("type") == "CapabilityDisabled":
            continue
        results.append(result)
    failures = [r for r in results if not r["success"]]
    return env.envelope(
        "run-all", not failures,
        "Succeeded" if not failures else "Partial",
        f"{len(results)} capabilities run, {len(failures)} reported findings or errors",
        data={"results": results},
    )


def cmd_runs(args) -> dict:
    cfg, failure = _load_config(args)
    if failure:
        return failure
    runs = report_module.list_runs(cfg.workspace_root, cfg.domain)
    return env.envelope("runs", True, "Succeeded",
                        f"{len(runs)} stored run(s) for {cfg.domain}", data={"runs": runs})


def cmd_validate_report(args) -> dict:
    path = Path(args.report)
    if not path.is_file():
        return env.failure("validate-report", "Report not found",
                           {"type": "FileNotFound", "message": f"No such file: {path}"})
    errors = jsonschema.validate(
        json.loads(path.read_text(encoding="utf-8")),
        json.loads(SCHEMA_PATH.read_text(encoding="utf-8")),
    )
    if errors:
        return env.failure("validate-report", "Report is not schema valid",
                           {"type": "SchemaViolation", "message": "\n".join(errors)})
    return env.envelope("validate-report", True, "Succeeded", f"{path.name} is valid", data={})


def main(argv=None) -> int:
    env.reconfigure_stdio()
    parser = argparse.ArgumentParser(prog="wo.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--config", help="Path to site.optimizer.toml")
        p.add_argument("--workspace", help="Workspace root (default: discovered upwards)")
        p.add_argument("--json", action="store_true", help="Emit the structured envelope")

    p_init = sub.add_parser("init-site", help="Write a site configuration")
    p_init.add_argument("--site-url", required=False)
    p_init.add_argument("--out")
    p_init.add_argument("--workspace")
    p_init.add_argument("--force", action="store_true")
    p_init.add_argument("--json", action="store_true")

    p_on = sub.add_parser("on-page", help="Audit on-page signals")
    common(p_on)
    p_on.add_argument("--strict", action="store_true", help="Exit 1 on any critical finding")
    p_on.add_argument("--ignore-noindex", action="store_true",
                      help="Do not report pages marked noindex")
    p_on.add_argument("--run", help="Explicit run id (default: UTC timestamp)")
    p_on.add_argument("--dry-run", action="store_true", help="Audit without writing a run")

    p_all = sub.add_parser("run-all", help="Run every enabled capability")
    common(p_all)
    p_all.add_argument("--strict", action="store_true")
    p_all.add_argument("--ignore-noindex", action="store_true")
    p_all.add_argument("--run")
    p_all.add_argument("--dry-run", action="store_true")

    p_runs = sub.add_parser("runs", help="List stored runs for the configured site")
    common(p_runs)

    p_val = sub.add_parser("validate-report", help="Validate a report against the schema")
    p_val.add_argument("report")
    p_val.add_argument("--json", action="store_true")

    handlers = {
        "init-site": cmd_init_site,
        "on-page": cmd_on_page,
        "run-all": cmd_run_all,
        "runs": cmd_runs,
        "validate-report": cmd_validate_report,
    }
    args = parser.parse_args(argv)
    result = handlers[args.command](args)
    env.emit(result, getattr(args, "json", False))

    critical = 0
    if args.command in ("on-page", "run-all") and not getattr(args, "dry_run", False):
        data = result.get("data") or {}
        summary = data.get("summary") or {}
        critical = summary.get("total_critical_issues", 0)
        if data.get("results"):
            for entry in data["results"]:
                critical += ((entry.get("data") or {}).get("summary") or {}).get(
                    "total_critical_issues", 0)

    if getattr(args, "strict", False) and critical > 0:
        return 1
    return 0 if result["success"] else 2


if __name__ == "__main__":
    sys.exit(main())