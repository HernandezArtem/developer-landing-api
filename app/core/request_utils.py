from starlette.requests import Request


def normalize_ip(ip: str) -> str:
    ip = (ip or "").strip()
    if ip.startswith("::ffff:"):
        ip = ip[7:]
    return ip


def get_client_ip(request: Request) -> str:
    """
    Real client IP behind nginx/reverse proxy.
    Without X-Forwarded-For all users look like 127.0.0.1 and share one rate limit.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = normalize_ip(forwarded.split(",")[0])
        if ip:
            return ip

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return normalize_ip(real_ip)

    if request.client and request.client.host:
        return normalize_ip(request.client.host)

    return "unknown"
