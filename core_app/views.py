from django.shortcuts import render

# Create your views here.

def upload_drawing(request):
    if request.method == "POST":
        pdf = request.FILES["drawing"]

        data = []
        with pdfplumber.open(pdf) as doc:
            for page in doc.pages:
                text = page.extract_text()
                if text:
                    for line in text.split("\n"):
                        if "Equipment" in line or "Tag" in line:
                            data.append(line)

        for line in data:
            Equipment.objects.create(tag_number=line[:80])

        return redirect("equipment_list")

    return render(request, "core_app/upload.html")


def equipment_list(request):
    equipments = Equipment.objects.all().order_by("-uploaded_at")
    return render(request, "core_app/equipment_list.html", {"equipments": equipments})