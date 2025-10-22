from django.shortcuts import render

# Create your views here.

def user_registration(request):
    return render(request,"registration.html")