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
from wo.capabilities import META, REGISTRY       # noqa: E402
from wo.errors import CapabilityError      # noqa: E402

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"


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
    entry = REGISTRY.get(name)
    if entry is None:
        return env.failure(name, f"Unknown capability {name!r}",
                           {"type": "UnknownCapability",
                            "message": f"Available: {', '.join(sorted(REGISTRY))}"})
    cfg, failure = _load_config(args)
    if failure:
        return failure

    if name not in META and name not in cfg.capabilities:
        return env.failure(name, f"Capability {name!r} is not enabled for this site",
                           {"type": "CapabilityDisabled",
                            "message": f"Add \"{name}\" to [audit] capabilities in "
                                       f"site.optimizer.toml to enable it."})

    module = __import__(entry["module"], fromlist=["run"])
    # `compare` consumes stored runs rather than auditing, so it takes run ids
    # instead of doing work. Every other capability ignores unknown keywords.
    kwargs = {"ignore_noindex": getattr(args, "ignore_noindex", False)}
    if name == "compare":
        kwargs.update({
            "baseline": getattr(args, "baseline", None),
            "current": getattr(args, "current", None),
        })
    try:
        result = module.run(cfg, **kwargs)
    except CapabilityError as exc:
        return env.failure(name, "Audit could not run",
                           {"type": exc.kind, "message": str(exc)})

    errors = jsonschema.validate(result, jsonschema.load_schema(SCHEMA_DIR / entry["schema"]))
    if errors:
        return env.failure(name, "Report failed schema validation",
                           {"type": "SchemaViolation", "message": "\n".join(errors)})

    # Compose everything that can fail *before* writing anything. A run folder is
    # an append-only observation; an artifact written by a process that then
    # crashes is a record of the tool's failure, not of the site.
    summary = result["summary"]
    critical = summary["total_critical_issues"]
    warnings = summary["total_warnings"]
    message = f"{len(result['findings'])} findings: {critical} critical, {warnings} warnings"

    written = None
    if not args.dry_run:
        filename = "comparison.json" if name == "compare" else "report.json"
        written = report_module.write_run(cfg, result, run=args.run, filename=filename)

    # Only the two severity counters are capability-neutral. Earlier versions of
    # this message hard-coded `audited_pages`, which only exists in the on-page
    # summary — a silent assumption that broke the moment a second capability
    # reported a different shape. Capability counts live in `data.summary`.
    return env.envelope(
        name, critical == 0,
        "Succeeded" if critical == 0 else "Partial",
        message,
        data={"summary": summary, "findings": result["findings"],
              "run": written["run_dir"].name if written else None,
              "paths": {k: str(v) for k, v in written.items()} if written else None},
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
    schema_name = args.schema
    if not schema_name:
        for entry in REGISTRY.values():
            candidate = SCHEMA_DIR / entry["schema"]
            if jsonschema.validate(json.loads(path.read_text(encoding="utf-8")),
                                   jsonschema.load_schema(candidate)) == []:
                schema_name = entry["schema"]
                break
    if not schema_name:
        return env.failure("validate-report", "No capability schema matches this report",
                           {"type": "SchemaMismatch",
                            "message": f"Pass --schema with one of: "
                                       f"{', '.join(e['schema'] for e in REGISTRY.values())}"})
    errors = jsonschema.validate(
        json.loads(path.read_text(encoding="utf-8")),
        jsonschema.load_schema(SCHEMA_DIR / schema_name),
    )
    if errors:
        return env.failure("validate-report", f"Report is not valid against {schema_name}",
                           {"type": "SchemaViolation", "message": "\n".join(errors)})
    return env.envelope("validate-report", True, "Succeeded",
                        f"{path.name} is valid against {schema_name}", data={"schema": schema_name})


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

    # One subparser per registered capability, generated from the registry.
    # A new capability therefore needs no change here — which is the point of
    # keeping REGISTRY as the single place a capability is declared.
    for capability in sorted(REGISTRY):
        cap = sub.add_parser(capability, help=f"Run the {capability} audit")
        cap.add_argument("--config", help="Path to site.optimizer.toml")
        cap.add_argument("--workspace", help="Workspace root (default: discovered upwards)")
        cap.add_argument("--json", action="store_true", help="Emit the structured envelope")
        cap.add_argument("--strict", action="store_true", help="Exit 1 on any critical finding")
        cap.add_argument("--ignore-noindex", action="store_true",
                         help="Do not report pages marked noindex (on-page)")
        cap.add_argument("--run", help="Explicit run id (default: UTC timestamp)")
        cap.add_argument("--dry-run", action="store_true", help="Audit without writing a run")
        if capability == "compare":
            cap.add_argument("--baseline", help="Baseline run id (default: the previous run)")
            cap.add_argument("--current", help="Run id to compare against the baseline")

    p_runs = sub.add_parser("runs", help="List stored runs for the configured site")
    p_runs.add_argument("--config")
    p_runs.add_argument("--workspace")
    p_runs.add_argument("--json", action="store_true")

    p_val = sub.add_parser("validate-report", help="Validate a report against its schema")
    p_val.add_argument("report")
    p_val.add_argument("--schema", help="Schema file name; autodetected when omitted")
    p_val.add_argument("--json", action="store_true")

    handlers = {
        "init-site": cmd_init_site,
        "runs": cmd_runs,
        "validate-report": cmd_validate_report,
    }
    args = parser.parse_args(argv)
    handler = handlers.get(args.command)
    result = _run_capability(args.command, args) if handler is None else handler(args)
    env.emit(result, getattr(args, "json", False))

    critical = 0
    if args.command in REGISTRY and not getattr(args, "dry_run", False):
        data = result.get("data") or {}
        critical = (data.get("summary") or {}).get("total_critical_issues", 0)
        if data.get("results"):
            for entry in data["results"]:
                critical += ((entry.get("data") or {}).get("summary") or {}).get(
                    "total_critical_issues", 0)

    if getattr(args, "strict", False) and critical > 0:
        return 1
    return 0 if result["success"] else 2


if __name__ == "__main__":
    sys.exit(main())