from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
import requests
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponse
from datetime import datetime

# Create your views here.
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

def user_registration(request):
    return render(request,"registration.html")

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

       
        api_url = "https://rbi-api.drivecloud.online/api/v1/auth/login"

    
        response = requests.post(api_url, json={
            "email": email,
            "password": password
        })

        if response.status_code == 200:
            result = response.json()
            token = result.get("token")

          
            request.session["api_token"] = token
            request.session["email"] = email

            messages.success(request, "Login successful!")
            return redirect("dashboard")

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

    api_url = "https://rbi-api.drivecloud.online/api/v1/analysis/list?page=1&limit=10&status=completed"
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

                # Ambil ID sebenar
                analysis_id = data.get("analysis_id")

                # ✅ Build URL proxy (guna Django sendiri)
                excel_url = f"/user/download/{analysis_id}/excel/"
                pptx_url = f"/user/download/{analysis_id}/pptx/"
                image_url = f"/user/download/{analysis_id}/image/"

                # ✅ Ambil upload history semasa
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
                    "analysis_id": analysis_id,  # <— PENTING
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

        
