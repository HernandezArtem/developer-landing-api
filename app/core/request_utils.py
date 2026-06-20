from starlette.requests import Request


def get_client_ip(request: Request) -> str:
    """
    Real client IP behind nginx/reverse proxy.
    Without X-Forwarded-For all users look like 127.0.0.1 and share one rate limit.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Leftmost = original client (nginx: proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for)
        ip = forwarded.split(",")[0].strip()
        if ip:
            return ip

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    if request.client:
        return request.client.host

    return "unknown"
