def rbi_external_user(request):
    
    return {
        "rbi_user": getattr(request, "external_user", None)
    }
