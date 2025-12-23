
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
import requests
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponse
from datetime import datetime
from django.conf import settings
from django.urls import reverse


class LoginAPIView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(username=email, password=password)
        
        if user is not None:
            return Response({
                "message": "Login successful",
                "email": user.email
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "message": "Invalid email or password"
            }, status=status.HTTP_400_BAD_REQUEST)



def google_callback(request):
    token = request.GET.get("token")

    if not token:
        messages.error(request, "Google login failed.")
        return redirect("login")

   
    request.session["api_token"] = token  

    try:
        
        api_url = f"{settings.RBI_API_BASE_URL}/auth/profile"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(api_url, headers=headers, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            user_data = data.get("user", {})  

            email = user_data.get("email")
            role = user_data.get("role")
            user_id = user_data.get("id")
            name = user_data.get("name") or user_data.get("fullName")

            profile_image = (
                user_data.get("profile_image")
                or user_data.get("google_image")
                or user_data.get("picture")
            )
            request.session["email"] = email

           
            request.session["rbi_user"] = {
                "id": user_id,
                "email": email,
                "name": name,  
                "role": role,
                "profile_image": profile_image,

            }

        else:
            print("Profile error:", resp.text)
            messages.error(request, "Failed to fetch user profile from API.")
            return redirect("login")

    except Exception as e:
        print("Error fetching user profile:", e)
        messages.error(request, "Error connecting to profile API.")
        return redirect("login")

    messages.success(request, "Logged in with Google successfully.")
    return redirect("analysis_app:upload")

def resolve_avatar(raw):
    if not raw:
        return None
    raw = str(raw).strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    origin = getattr(settings, "RBI_SERVER_ORIGIN", "").rstrip("/")
    if raw.startswith("/"):
        return f"{origin}{raw}" if origin else raw
    return f"{origin}/{raw}" if origin else raw

    avatar_url = resolve_avatar(profile_image)

    ExternalUser.objects.update_or_create(
        provider="rbi_auth",
        external_id=str(user_id),
        defaults={
            "email": email,
            "name": name,
            "role_snapshot": role,
            "avatar_url": avatar_url,
            "last_seen_at": timezone.now(),
        },
    )

def google_login(request):
  
    callback_url = request.build_absolute_uri(reverse("google_callback"))

 
    base_api_url = f"{settings.RBI_API_BASE_URL}/auth/google"

    params = {
        "redirect_uri": callback_url,
    }

    # http://localhost:6501/api/v1/auth/google?redirect_uri=http://localhost:8000/auth/google/callback/
    return redirect(f"{base_api_url}?{urlencode(params)}")

   
def user_registration(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        name = f"{first_name} {last_name}".strip()
        email = request.POST.get("email")
        phone = request.POST.get("phone")

        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        profile_image = request.FILES.get("profile_image")

        
        if password != confirm_password:
            messages.error(request, "Password and confirm password not match.")
            return redirect("registration")

        if not all([name, email, phone, password]):
            messages.error(request, "Please fill in all fields.")
            return redirect("registration")

        api_url = f"{settings.RBI_API_BASE_URL}/auth/register"

      
        payload = {
            "name": name,
            "email": email,
            "password": password,
            "phone": phone,
        
        }

        files = None
        if profile_image:
            files = {
                "profile_image": (
                    profile_image.name,
                    profile_image,
                    profile_image.content_type,
                )
            }

        try:
            response = requests.post(
                api_url,
                data=payload,
                files=files,
                timeout=15,
            )

            print("DEBUG RBI URL:", api_url)
            print("DEBUG status:", response.status_code)
            print("DEBUG body:", response.text)

            if response.status_code in (200, 201):
                messages.success(request, "Account created successfully. Please login.")
                return redirect("login")
            else:
                try:
                    data = response.json()
                    msg = data.get("message", "Registration failed.")
                except Exception:
                    msg = f"Registration failed. Status code: {response.status_code}"
                messages.error(request, msg)
                return redirect("registration")

        except Exception as e:
            print("Register error:", e)
            messages.error(request, "Error connecting to registration API.")
            return redirect("registration")

    return render(request, "registration.html")

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        api_url = f"{settings.RBI_API_BASE_URL}/auth/login"

        try:
            response = requests.post(api_url, json={
                "email": email,
                "password": password
            }, timeout=10)
        except Exception as e:
            messages.error(request, f"Cannot connect to RBI server: {e}")
            return redirect("login")

        if response.status_code == 200:
            result = response.json()

            # ✅ ikut response sebenar RBI_SERVER awak
            # contoh kalau response = { "token": "...", "user": { ... } }
            token = result.get("token")
            user_data = result.get("user", {}) or {}

            # 🔐 simpan token untuk semua request lain (dashboard, dll.)
            request.session["api_token"] = token

            # 📩 simpan email untuk convenience
            request.session["email"] = user_data.get("email") or email

            # 👤 simpan full info user RBI dalam session
            request.session["rbi_user"] = {
                "id": user_data.get("id"),
                "email": user_data.get("email") or email,
                "name": user_data.get("fullName") or user_data.get("name"),
                "role": user_data.get("role"),
            }

            messages.success(request, "Login successful!")
            return redirect("analysis_app:upload")

        else:
            try:
                result = response.json()
                msg = result.get("message", "Login failed.")
            except:
                msg = "Something went wrong."

            messages.error(request, msg)
            return redirect("login")

    return render(request, "login.html")
def dashboard(request):
    token = request.session.get("api_token")
    if not token:
        messages.warning(request, "Please log in first.")
        return redirect("login")

    api_url = f"{settings.RBI_API_BASE_URL}/analysis/list?page=1&limit=10&status=completed"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            result = response.json()
            analyses = result.get("data", {}).get("analyses", [])

           
            upload_history = []
            for item in analyses:
                created_at_raw = item.get("createdAt")

                try:
                    created_at = datetime.strptime(created_at_raw, "%Y-%m-%dT%H:%M:%S.%fZ")
                except ValueError:
                    created_at = datetime.strptime(created_at_raw, "%Y-%m-%dT%H:%M:%SZ")

               
                formatted_date = created_at.strftime("%d %b %Y, %I:%M %p")
                upload_history.append({
                    "file_name": item["original_filename"],
                    "created_at": formatted_date,
                    "file_type": "Excel + PowerPoint",
                    "status": item["status"].capitalize(),
                    "excel_path": item["excel_path"],
                    "pptx_path": item["pptx_path"],
                    "analysis_id": item["analysis_id"],
                    "summary": item["summary"],
                })

        else:
            upload_history = []
            messages.error(request, "Failed to fetch data from API.")

    except Exception as e:
        print("Error:", e)
        upload_history = []
        messages.error(request, "Error connecting to the API.")

    context = {
        "email": request.session.get("email"),
        "upload_history": upload_history
    }

    return render(request, "dashboard.html", context)



def upload_and_analyze(request):
    token = request.session.get("api_token")
    if not token:
        messages.warning(request, "Please log in first.")
        return redirect("login")

    if request.method == "POST":
        uploaded_file = request.FILES.get("uploaded_file")

        if not uploaded_file:
            messages.error(request, "Please select a file to upload.")
            return redirect("dashboard")

        api_url = "https://rbi-api.drivecloud.online/api/v1/analysis/analyze"
        headers = {
            "Authorization": f"Bearer {token}"
        }

        files = {
            "image": (uploaded_file.name, uploaded_file, uploaded_file.content_type)
        }

        try:
            response = requests.post(api_url, headers=headers, files=files)
            print("Upload Response:", response.text)

            if response.status_code == 200:
                result = response.json()
                data = result.get("data", {})

                
                analysis_id = data.get("analysis_id")

               
                excel_url = f"/user/download/{analysis_id}/excel/"
                pptx_url = f"/user/download/{analysis_id}/pptx/"
                image_url = f"/user/download/{analysis_id}/image/"

               
                list_api = "https://rbi-api.drivecloud.online/api/v1/analysis/list?page=1&limit=10&status=completed"
                list_response = requests.get(list_api, headers=headers)
                upload_history = []

                if list_response.status_code == 200:
                    analyses = list_response.json().get("data", {}).get("analyses", [])
                    for item in analyses:
                        upload_history.append({
                            "file_name": item["original_filename"],
                            "created_at": item["createdAt"],
                            "file_type": "Excel + PowerPoint",
                            "status": item["status"].capitalize(),
                            "analysis_id": item["analysis_id"],
                            "summary": item.get("summary"),
                        })

                messages.success(request, "✅ Analysis completed successfully!")

                context = {
                    "email": request.session.get("email"),
                    "summary": data.get("summary"),
                    "processing_time": data.get("processing_time"),
                    "slides_count": data.get("slides_count"),
                    "analysis_id": analysis_id,  
                    "excel_url": excel_url,
                    "pptx_url": pptx_url,
                    "image_url": image_url,
                    "upload_history": upload_history
                }

                return render(request, "dashboard.html", context)

            else:
                print("Error Response:", response.text)
                messages.error(request, f"Error: {response.status_code}")
                return redirect("dashboard")

        except Exception as e:
            print("Upload error:", e)
            messages.error(request, "Error connecting to API.")
            return redirect("dashboard")

    return redirect("dashboard")





def download_file(request, analysis_id, file_type):
    
    token = request.session.get("api_token")
    if not token:
        messages.warning(request, "Please log in first.")
        return redirect("login")


    api_url = f"https://rbi-api.drivecloud.online/api/v1/analysis/download/{analysis_id}/{file_type}"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(api_url, headers=headers, stream=True)
        if response.status_code == 200:
           
            content_disposition = response.headers.get("Content-Disposition", "")
            filename = "downloaded_file"
            if "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[1].strip('"')

           
            file_response = HttpResponse(
                response.content,
                content_type=response.headers.get("Content-Type", "application/octet-stream")
            )
            file_response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return file_response

        else:
            messages.error(request, "Failed to download file from API.")
            return redirect("dashboard")

    except Exception as e:
        print("Download error:", e)
        messages.error(request, "Error connecting to download API.")
        return redirect("dashboard")



from django.http import JsonResponse
import base64

def preview_file(request, analysis_id, file_type):
    token = request.session.get("api_token")
    if not token:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    api_url = f"https://rbi-api.drivecloud.online/api/v1/analysis/download/{analysis_id}/{file_type}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            encoded = base64.b64encode(response.content).decode('utf-8')
            mime = "application/vnd.ms-excel" if file_type == "excel" else "application/vnd.ms-powerpoint"
            return JsonResponse({
                "base64": encoded,
                "mime": mime
            })
        else:
            return JsonResponse({"error": "Failed to fetch file"}, status=response.status_code)
    except Exception as e:
        print("Preview error:", e)
        return JsonResponse({"error": "Error connecting to API"}, status=500)

        
def delete_analysis(request, analysis_id):
    token = request.session.get("api_token")
    if not token:
        return JsonResponse({"error": "Not authenticated."}, status=401)

    api_url = f"https://rbi-api.drivecloud.online/api/v1/analysis/{analysis_id}"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.delete(api_url, headers=headers)
        if response.status_code == 200:
            return JsonResponse({"message": "Analysis deleted successfully!"})
        elif response.status_code == 404:
            return JsonResponse({"error": "Analysis not found."}, status=404)
        elif response.status_code == 401:
            return JsonResponse({"error": "Invalid or expired token."}, status=401)
        else:
            print(response.text)
            return JsonResponse({"error": "Failed to delete analysis."}, status=response.status_code)
    except Exception as e:
        print("Error:", e)
        return JsonResponse({"error": "Error connecting to API."}, status=500)