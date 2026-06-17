from __future__ import annotations

import argparse

from ..fallback_site.admin_client import FallbackAdminClient
from ..utils.identity import base_ports_from_env, get_project_id, stable_offset


def infer_fallback_port(project_id: str) -> int:
    base_fb, _ = base_ports_from_env()
    offset = stable_offset(project_id, modulo=50)
    return base_fb + offset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kinfra-status", description="Emit or manage fallback tenant status",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_emit = sub.add_parser("emit", help="Emit a stage or status fields")
    p_emit.add_argument("--tenant", required=False, help="Tenant/project id; defaults to env/auto")
    p_emit.add_argument("--service", required=True, help="Service name")
    p_emit.add_argument("--stage", required=False, help="Stage text (e.g., Building)")
    p_emit.add_argument(
        "--status",
        required=False,
        choices=["pending", "active", "completed", "failed"],
        help="Stage status",
    )
    p_emit.add_argument("--message", required=False, help="Status message override")
    p_emit.add_argument("--state", required=False, help="State string")
    p_emit.add_argument("--host", default="127.0.0.1")
    p_emit.add_argument(
        "--port", type=int, help="Fallback admin port; default inferred from tenant",
    )

    p_del = sub.add_parser("delete", help="Delete a tenant or a specific service row")
    p_del.add_argument("--tenant", required=False)
    p_del.add_argument("--service", required=False)
    p_del.add_argument("--host", default="127.0.0.1")
    p_del.add_argument("--port", type=int)

    p_list = sub.add_parser("list", help="List tenant statuses")
    p_list.add_argument("--tenant", required=False)
    p_list.add_argument("--host", default="127.0.0.1")
    p_list.add_argument("--port", type=int)

    args = parser.parse_args(argv)

    tenant = args.tenant or get_project_id()
    if args.cmd == "emit":
        port = args.port or infer_fallback_port(tenant)
        client = FallbackAdminClient(host=args.host, port=port)
        fields: dict = {}
        if args.message:
            fields["status_message"] = args.message
        if args.state:
            fields["state"] = args.state
        if args.stage:
            fields["steps"] = [{"text": args.stage, "status": args.status or "active"}]
            fields["status_message"] = args.message or args.stage
        client.update_status(tenant=tenant, service_name=args.service, **fields)
        return 0
    if args.cmd == "delete":
        port = args.port or infer_fallback_port(tenant)
        client = FallbackAdminClient(host=args.host, port=port)
        client.delete_status(tenant=args.tenant, service_name=args.service)
        return 0
    if args.cmd == "list":
        port = args.port or infer_fallback_port(tenant)
        client = FallbackAdminClient(host=args.host, port=port)
        res = client.list_status(tenant=args.tenant)
        print(res)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
