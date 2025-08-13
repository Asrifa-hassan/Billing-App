from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

class DisableBackButtonAndRedirectMiddleware(MiddlewareMixin):
    """
    Middleware to:
    1. Disable browser caching for all pages (no back button after logout)
    2. Redirect:
       - Logged-in users away from login/register pages
       - Unauthenticated users away from protected pages
    """

    def process_request(self, request):
        # URLs where logged-in users should NOT go
        auth_pages = [
            reverse('login_page'),
            reverse('register'),
            reverse('forgot_password')
        ]

        # Redirect logged-in users away from auth pages
        if request.user.is_authenticated and request.path in auth_pages:
            return redirect('dashboard')

        # Redirect unauthenticated users from protected pages
        protected_prefixes = [
            '/dashboard',
            '/products',
            '/invoices',
            '/customers',
            '/staff',
            '/create_invoice'
        ]
        if not request.user.is_authenticated and any(request.path.startswith(p) for p in protected_prefixes):
            return redirect('login_page')

    def process_response(self, request, response):
        # Disable caching to prevent back button access
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
