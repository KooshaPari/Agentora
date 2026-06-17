from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


def _temp_flag(item: Mapping[str, object]) -> str:
    tc = item.get("temperature_constraint") if isinstance(item, dict) else None
    if not isinstance(tc, dict):
        return ""
    t = str(tc.get("type", "")).lower()
    if t == "fixed":
        v = tc.get("value")
        return f"[temp:{v}]" if v is not None else "[temp:fixed]"
    if t == "range":
        mn = tc.get("min")
        mx = tc.get("max")
        if mn is not None and mx is not None:
            return f"[temp:{mn}-{mx}]"
        return "[temp:range]"
    if t == "discrete":
        vals = tc.get("values")
        try:
            n = len(vals)  # type: ignore[arg-type]
            return f"[temp:{n}]" if n else "[temp:discrete]"
        except Exception:
            return "[temp:discrete]"
    return ""


def format_catalog_items(
    items: Iterable[Mapping[str, object]],
    show_details: bool = False,
    show_temperature_details: bool = False,
) -> list[str]:
    """Format catalog model entries with capability flags and optional details.

    Flags rendered: [json] [json:schema] [json:strict] [func] [func+] [stream] [img] or [img:Nmb] [think] + [temp:...]
    If show_temperature_details=True and show_details=True, an extra "Temperature:" line is included when constraints exist.
    """
    out: list[str] = []
    for m in items:
        mid = str(m.get("id", ""))
        ctx = int(m.get("context_window", 0) or 0)
        ctx_str = f"{ctx:,}" if ctx else "?"
        flags: list[str] = []
        # JSON flags: [json], [json:schema], [json:strict]
        json_supported = bool(m.get("supports_json_mode"))
        has_json_schema = bool(m.get("json_schema") or m.get("json_schemas"))
        strict_json = bool(m.get("strict_json"))
        if json_supported:
            emitted = False
            if strict_json:
                flags.append("json:strict")
                emitted = True
            if has_json_schema:
                flags.append("json:schema")
                emitted = True
            if not emitted:
                flags.append("json")
        # Function-calling flags: [func] baseline, [func+] if schemas present
        func_supported = bool(m.get("supports_function_calling"))
        has_func_schema = bool(
            m.get("function_schemas")
            or m.get("functions")
            or m.get("tool_schemas")
            or m.get("tools_schema"),
        )
        if func_supported and has_func_schema:
            flags.append("func+")
        elif func_supported:
            flags.append("func")
        if m.get("supports_streaming"):
            flags.append("stream")
        if m.get("supports_images"):
            try:
                ms = m.get("max_image_size_mb")
                if ms:
                    sval = str(int(ms)) if isinstance(ms, (int, float)) else str(ms)
                    flags.append(f"img:{sval}mb")
                else:
                    flags.append("img")
            except Exception:
                flags.append("img")
        if m.get("supports_extended_thinking"):
            flags.append("think")
        tf = _temp_flag(m)
        if tf:
            flags.append(tf)
        flags_str = (
            (" ".join(f"[{f}]" if not f.startswith("[temp:") else f for f in flags))
            if flags
            else ""
        )
        if show_details:
            line = f"- **{mid}** (ctx {ctx_str}) {flags_str}".rstrip()
            out.append(line)
            desc = m.get("description")
            if desc:
                out.append(f"  {desc}")
            if show_temperature_details and isinstance(m, dict):
                tc = m.get("temperature_constraint")
                if isinstance(tc, dict) and tc.get("type"):
                    t = str(tc.get("type")).lower()
                    if t == "fixed":
                        out.append(f"  Temperature: fixed {tc.get('value')}")
                    elif t == "range":
                        out.append(f"  Temperature: {tc.get('min')} – {tc.get('max')}")
                    elif t == "discrete":
                        vals = tc.get("values")
                        try:
                            n = len(vals)  # type: ignore[arg-type]
                            out.append(f"  Temperature: {n} discrete values")
                        except Exception:
                            out.append("  Temperature: discrete values")
        else:
            line = f"- `{mid}` (ctx {ctx_str}) {flags_str}".rstrip()
            out.append(line)
    return out
