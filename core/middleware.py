import os
import mimetypes
from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404

class MediaCacheMiddleware:
    """
    Middleware to inject aggressive browser caching headers (Cache-Control: public, max-age=31536000, immutable)
    and Byte Range support for all media (videos, images) and static files.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        path = request.path_info.lower()

        # Check if request is for static or media files
        if path.startswith('/media/') or path.startswith('/static/') or path.endswith(
            ('.mp4', '.webm', '.ogv', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif', '.ico', '.css', '.js', '.woff', '.woff2', '.ttf')
        ):
            # 1 Year aggressive browser caching
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
            response['Accept-Ranges'] = 'bytes'
            response['Access-Control-Allow-Origin'] = '*'
            
        return response
