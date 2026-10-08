class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        from .portal_configuration import for_request
        portal=for_request(request)
        if portal and portal.frame_origins and (request.path in ('/','/kalender.ics') or request.path.startswith('/informationen/')):
            response['Content-Security-Policy']=response['Content-Security-Policy'].replace("frame-ancestors 'none'","frame-ancestors "+' '.join(portal.frame_origins))
            response.headers.pop('X-Frame-Options',None)
        response["Referrer-Policy"] = "same-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if not request.path.startswith("/static/"):
            response["Cache-Control"] = "no-store"
        return response
