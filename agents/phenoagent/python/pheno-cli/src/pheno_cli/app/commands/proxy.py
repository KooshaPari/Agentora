from __future__ import annotations

import argparse

from ..proxy_gateway.admin_client import ProxyAdminClient
from ..utils.identity import base_ports_from_env, get_project_id, stable_offset


def infer_proxy_port(project_id: str) -> int:
    _, base_px = base_ports_from_env()
    offset = stable_offset(project_id, modulo=50)
    return base_px + offset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kinfra-proxy", description="Manage ProxyServer tenant upstreams",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Add upstream for a tenant")
    p_add.add_argument("--tenant", required=False, help="Tenant/project id; defaults to env/auto")
    p_add.add_argument("--path", required=True, help="Path prefix, e.g., /api")
    p_add.add_argument("--host", default="localhost")
    p_add.add_argument("--port", type=int, required=True, help="Upstream port")
    p_add.add_argument("--service", required=False, help="Service name")
    p_add.add_argument("--proxy-host", default="127.0.0.1")
    p_add.add_argument(
        "--proxy-port", type=int, help="Proxy admin port; default inferred from tenant",
    )

    p_rm = sub.add_parser("remove", help="Remove upstream by path prefix")
    p_rm.add_argument("--path", required=True)
    p_rm.add_argument("--proxy-host", default="127.0.0.1")
    p_rm.add_argument("--proxy-port", type=int)

    p_list = sub.add_parser("list", help="List upstreams (optionally by tenant)")
    p_list.add_argument("--tenant", required=False)
    p_list.add_argument("--proxy-host", default="127.0.0.1")
    p_list.add_argument("--proxy-port", type=int)

    p_dereg = sub.add_parser("deregister", help="Bulk remove by tenant or paths")
    p_dereg.add_argument("--tenant", required=False)
    p_dereg.add_argument("--paths", nargs="*", help="List of path_prefixes")
    p_dereg.add_argument("--proxy-host", default="127.0.0.1")
    p_dereg.add_argument("--proxy-port", type=int)

    args = parser.parse_args(argv)

    if args.cmd == "add":
        tenant = args.tenant or get_project_id()
        px_port = args.proxy_port or infer_proxy_port(tenant)
        client = ProxyAdminClient(host=args.proxy_host, port=px_port)
        client.add_upstream(
            path_prefix=args.path,
            port=args.port,
            host=args.host,
            service_name=args.service,
            tenant=tenant,
        )
        return 0
    if args.cmd == "remove":
        client = ProxyAdminClient(
            host=args.proxy_host, port=args.proxy_port or infer_proxy_port(get_project_id()),
        )
        client.remove_upstream(args.path)
        return 0
    if args.cmd == "list":
        tenant = args.tenant
        client = ProxyAdminClient(
            host=args.proxy_host, port=args.proxy_port or infer_proxy_port(get_project_id()),
        )
        res = client.list_upstreams(tenant=tenant)
        print(res)
        return 0
    if args.cmd == "deregister":
        client = ProxyAdminClient(
            host=args.proxy_host, port=args.proxy_port or infer_proxy_port(get_project_id()),
        )
        res = client.deregister_tenant(tenant=args.tenant, path_prefixes=args.paths)
        print(res)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
