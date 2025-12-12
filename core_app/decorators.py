from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def rbi_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        token = request.session.get("api_token")
        if not token:
            messages.warning(request, "Please sign in first.")
            return redirect("login")  
        return view_func(request, *args, **kwargs)

    return _wrapped_view
