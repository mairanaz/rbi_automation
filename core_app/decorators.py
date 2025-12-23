from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
import jwt

from analysis_app.models import ExternalUser

def rbi_login_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        token = request.session.get("api_token")
        if not token:
            messages.error(request, "Please log in again.")
            return redirect("login")

        try:
            secret = getattr(settings, "JWT_SECRET", None)
            if not secret or not isinstance(secret, str):
                messages.error(request, "Server JWT secret not configured. Please set JWT_SECRET.")
                return redirect("login")
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            messages.error(request, "Session expired. Please log in again.")
            return redirect("login")
        except jwt.InvalidTokenError:
            messages.error(request, "Invalid session. Please log in again.")
            return redirect("login")

        external_id = str(payload.get("id") or payload.get("sub") or "")
        if not external_id:
            messages.error(request, "Invalid user payload.")
            return redirect("login")

        email = payload.get("email")
        name = payload.get("name")
        staff_id = payload.get("staff_id")
        role = payload.get("role")
        profile_image = payload.get("profile_image")
        google_image = payload.get("google_image") or payload.get("picture")
        avatar = _resolve_avatar_url(profile_image) or _resolve_avatar_url(google_image)


        ext_user, _ = ExternalUser.objects.get_or_create(
            provider="rbi_auth",
            external_id=external_id,
            defaults={
                "email": email,
                "name": name,
                "staff_id": staff_id,
                "role_snapshot": role,
                "last_seen_at": timezone.now(),
            },
        )

        changed = False
        if email and ext_user.email != email:
            ext_user.email = email; changed = True
        if name and ext_user.name != name:
            ext_user.name = name; changed = True
        if staff_id and ext_user.staff_id != staff_id:
            ext_user.staff_id = staff_id; changed = True
        if role and ext_user.role_snapshot != role:
            ext_user.role_snapshot = role; changed = True
        if avatar and ext_user.avatar_url != avatar:
            ext_user.avatar_url = avatar
            changed = True

        ext_user.last_seen_at = timezone.now()
        changed = True

        if changed:
            ext_user.save()

        request.external_user = ext_user
        request.external_payload = payload
        return view_func(request, *args, **kwargs)

    return _wrapped


def _resolve_avatar_url(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = str(raw).strip()

    # google / absolute URL
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw

    # relative upload path from node: /uploads/...
    origin = getattr(settings, "RBI_SERVER_ORIGIN", "").rstrip("/")
    if raw.startswith("/"):
        return f"{origin}{raw}" if origin else raw
    return f"{origin}/{raw}" if origin else raw

