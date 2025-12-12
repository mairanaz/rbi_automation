from django.shortcuts import render

# Create your views here.
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Analysis, AnalysisPage, RegionSelection
from .services.cropper import crop_region_from_page
from .services.ai_extractor import extract_design_metadata, extract_bom_materials
from .services.masterfile_builder import append_equipment_to_masterfile, parse_filename


from .services.ppt_builder import get_or_create_pptx, add_images_to_presentation

from core_app.decorators import rbi_login_required



STEP_LABEL = {
    "design_data": "Select Design Data Region",
    "bom": "Select Bill Of Material Region",
    "slide_image": "Select Slide Image Region",
}



@rbi_login_required
def analysis_detail(request, analysis_id):
   
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    regions = analysis.regions.select_related("page").all()

    design_data_region = regions.filter(step_type="design_data").first()
    bom_region = regions.filter(step_type="bom").first()
    slide_regions = regions.filter(step_type="slide_image")

   
    workbook_url = None
    if analysis.workbook_path:
        workbook_url = settings.MEDIA_URL + analysis.workbook_path


    design_rows_preview = []
    bom_rows_preview = []

    try:
        if design_data_region:
            design_crop_rel = crop_region_from_page(
                design_data_region.page.image.name,
                design_data_region.x1,
                design_data_region.y1,
                design_data_region.x2,
                design_data_region.y2,
            )
          
    except Exception as e:
        print("Design data preview error:", e)

    try:
        if bom_region:
            bom_crop_rel = crop_region_from_page(
                bom_region.page.image.name,
                bom_region.x1,
                bom_region.y1,
                bom_region.x2,
                bom_region.y2,
            )
         
    except Exception as e:
        print("BOM preview error:", e)

    context = {
        "analysis": analysis,
        "design_data_region": design_data_region,
        "bom_region": bom_region,
        "slide_regions": slide_regions,
        "workbook_url": workbook_url,
        "design_rows_preview": design_rows_preview,
        "bom_rows_preview": bom_rows_preview,
    }
    return render(request, "detail.html", context)


@rbi_login_required
def upload_analysis(request):
    
    if request.method == "POST":
        pdf_file = request.FILES.get("pdf_file")
        if not pdf_file:
            messages.error(request, "Please select a PDF file.")
            return redirect("analysis_app:upload")

       
        rbi_user = request.session.get("rbi_user") or {}
        external_user_id = rbi_user.get("id")
        external_user_email = rbi_user.get("email")
        external_user_name = rbi_user.get("name")

        if not external_user_id:
            messages.error(request, "Session expired or user not found. Please log in again.")
            return redirect("login")

      
        analysis = Analysis.objects.create(
            user=None,  
            external_user_id=external_user_id,
            external_user_email=external_user_email,
            external_user_name=external_user_name,
            file=pdf_file,
            original_filename=pdf_file.name,
            status="awaiting_regions",
        )

       
        pdf_path = analysis.file.path

        from pdf2image import convert_from_path
        POPPLER_PATH = r"C:\Users\nazrisaidon\Desktop\poppler-25.11.0\Library\bin"

        try:
            pages = convert_from_path(pdf_path, dpi=200, poppler_path=POPPLER_PATH)

            for idx, page_img in enumerate(pages, start=1):
                out_dir = Path(settings.MEDIA_ROOT) / "analysis/pages/"
                out_dir.mkdir(parents=True, exist_ok=True)

                filename = f"analysis_{analysis.id}_p{idx}.png"
                out_path = out_dir / filename
                page_img.save(out_path, "PNG")

                rel_path = str(out_path.relative_to(settings.MEDIA_ROOT))

                AnalysisPage.objects.create(
                    analysis=analysis,
                    page_number=idx,
                    image=rel_path,
                )

        except Exception as e:
            analysis.delete()
            print(f"Error converting PDF: {e}")
            messages.error(request, f"Error processing PDF: {e}")
            return redirect("analysis_app:upload")

        return redirect(
            "analysis_app:select_region",
            analysis_id=analysis.id,
            step_type="design_data",
            page_number=1,
        )

    return render(request, "uploading.html")


@rbi_login_required
def select_region(request, analysis_id, step_type, page_number):
   
    if step_type not in ("design_data", "bom", "slide_image"):
        messages.error(request, "Invalid step type.")
        return redirect("analysis_app:history")

    
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    page = get_object_or_404(AnalysisPage, analysis=analysis, page_number=page_number)

    
    all_pages = list(analysis.pages.all())
    page_numbers = [p.page_number for p in all_pages]
    idx = page_numbers.index(page_number)

    prev_page_url = None
    next_page_url = None

    if idx > 0:
        prev_page_url = reverse(
            "analysis_app:select_region",
            kwargs={
                "analysis_id": analysis.id,
                "step_type": step_type,
                "page_number": page_numbers[idx - 1],
            },
        )

    if idx < len(page_numbers) - 1:
        next_page_url = reverse(
            "analysis_app:select_region",
            kwargs={
                "analysis_id": analysis.id,
                "step_type": step_type,
                "page_number": page_numbers[idx + 1],
            },
        )

    
    if request.method == "POST":
        x1 = request.POST.get("x1")
        y1 = request.POST.get("y1")
        x2 = request.POST.get("x2")
        y2 = request.POST.get("y2")

        if not all([x1, y1, x2, y2]):
            messages.error(request, "Please draw a region before confirming.")
        else:
            try:
                x1 = float(x1)
                y1 = float(y1)
                x2 = float(x2)
                y2 = float(y2)
            except ValueError:
                messages.error(request, "Invalid coordinates.")
            else:
                if not (
                    0 <= x1 <= 1
                    and 0 <= x2 <= 1
                    and 0 <= y1 <= 1
                    and 0 <= y2 <= 1
                ):
                    messages.error(request, "Coordinates must be between 0 and 1.")
                else:
                    if step_type in ("design_data", "bom"):
                       
                        RegionSelection.objects.update_or_create(
                            analysis=analysis,
                            step_type=step_type,
                            defaults={
                                "page": page,
                                "x1": x1,
                                "y1": y1,
                                "x2": x2,
                                "y2": y2,
                            },
                        )
                    else:
                   
                        RegionSelection.objects.create(
                            analysis=analysis,
                            page=page,
                            step_type=step_type,
                            x1=x1,
                            y1=y1,
                            x2=x2,
                            y2=y2,
                        )

                    messages.success(request, "Region saved.")

                  
                    if step_type == "design_data":
                        return redirect(
                            "analysis_app:select_region",
                            analysis_id=analysis.id,
                            step_type="bom",
                            page_number=page_number,
                        )
                    elif step_type == "bom":
                        return redirect(
                            "analysis_app:select_region",
                            analysis_id=analysis.id,
                            step_type="slide_image",
                            page_number=page_number,
                        )
                    else:
                        return redirect(
                            "analysis_app:review_analysis",
                            analysis_id=analysis.id,
                        )

    context = {
        "analysis": analysis,
        "page_number": page.page_number,
        "page_image_url": page.image.url
        if hasattr(page.image, "url")
        else settings.MEDIA_URL + page.image.name,
        "step_type": step_type,
        "step_label": STEP_LABEL.get(step_type, "Select Region"),
        "prev_page_url": prev_page_url,
        "next_page_url": next_page_url,
        "total_pages": len(page_numbers), 
    }
 
    return render(request, "select_region.html", context)




# analysis_app/views.py


@rbi_login_required
def review_analysis(request, analysis_id):
    
    analysis = get_object_or_404(Analysis, pk=analysis_id)

    regions = analysis.regions.select_related("page").all()
    design_data_region = regions.filter(step_type="design_data").first()
    bom_region = regions.filter(step_type="bom").first()
    slide_regions = regions.filter(step_type="slide_image")

   
    design_preview_url = None
    bom_preview_url = None
    slide_previews = []  

    if design_data_region:
        design_rel = crop_region_from_page(
            page_image_name=design_data_region.page.image.name,
            x1=design_data_region.x1,
            y1=design_data_region.y1,
            x2=design_data_region.x2,
            y2=design_data_region.y2,
        )
        design_preview_url = settings.MEDIA_URL + design_rel

    if bom_region:
        bom_rel = crop_region_from_page(
            page_image_name=bom_region.page.image.name,
            x1=bom_region.x1,
            y1=bom_region.y1,
            x2=bom_region.x2,
            y2=bom_region.y2,
        )
        bom_preview_url = settings.MEDIA_URL + bom_rel

 
    for r in slide_regions[:3]:
        rel = crop_region_from_page(
            page_image_name=r.page.image.name,
            x1=r.x1,
            y1=r.y1,
            x2=r.x2,
            y2=r.y2,
        )
        slide_previews.append({
            "page": r.page.page_number,
            "url": settings.MEDIA_URL + rel,
        })

    context = {
        "analysis": analysis,
        "design_data_region": design_data_region,
        "bom_region": bom_region,
        "slide_regions": slide_regions,

        # new:
        "design_preview_url": design_preview_url,
        "bom_preview_url": bom_preview_url,
        "slide_previews": slide_previews,
    }
    return render(request, "review.html", context)



@rbi_login_required
@require_POST
def generate_analysis(request, analysis_id):

    analysis = get_object_or_404(Analysis, pk=analysis_id)
    regions = analysis.regions.select_related("page").all()

    
    design_region = regions.filter(step_type="design_data").first()
    bom_region = regions.filter(step_type="bom").first()
    slide_regions = list(regions.filter(step_type="slide_image"))

    if not design_region or not bom_region:
        messages.error(request, "Design Data and BOM regions are required.")
        return redirect("analysis_app:review_analysis", analysis_id=analysis.id)

   
    analysis.status = "in_progress"
    analysis.save()

  
    if not analysis.workbook_path:
        user_key = analysis.external_user_id or "anon"
       
        analysis.workbook_path = f"analysis/workbooks/{user_key}_IPETRO_Masterfile.xlsx"
        analysis.save()

    pmt_no, equipment_no = parse_filename(analysis.original_filename)
  

    design_crop_rel = crop_region_from_page(
        design_region.page.image.name,
        design_region.x1,
        design_region.y1,
        design_region.x2,
        design_region.y2,
    )

  
    bom_crop_rel = crop_region_from_page(
        bom_region.page.image.name,
        bom_region.x1,
        bom_region.y1,
        bom_region.x2,
        bom_region.y2,
    )

 
    design_meta = {}
    try:
        design_meta = extract_design_metadata(
            design_crop_rel,
            pmt_no=pmt_no,
            equipment_no=equipment_no,
        ) or {}
    except Exception as e:
        print("Design metadata extraction failed:", e)

  
    bom_items = []
    try:
        bom_items = extract_bom_materials(
            bom_crop_rel,
            pmt_no=pmt_no,
            equipment_no=equipment_no,
        ) or []
    except Exception as e:
        print("BOM materials extraction failed:", e)

    try:
        append_equipment_to_masterfile(
            workbook_rel_path=analysis.workbook_path,
            original_filename=analysis.original_filename,
            design_meta=design_meta,
            bom_items=bom_items,
        )
    except Exception as e:
        print("Append to Masterfile failed:", e)


    if not analysis.pptx_path:
        safe_name = Path(analysis.original_filename).stem[:30]
        analysis.pptx_path = (
            f"analysis/ppt/{analysis.user_id or 'anon'}_{analysis.id}_{safe_name}.pptx"
        )
        analysis.save()

    abs_pptx = get_or_create_pptx(analysis.pptx_path)

    slide_image_paths = []
    for r in slide_regions:
        crop_rel = crop_region_from_page(
            r.page.image.name,
            r.x1,
            r.y1,
            r.x2,
            r.y2,
        )
        slide_image_paths.append(crop_rel)

    if slide_image_paths:
        add_images_to_presentation(abs_pptx, slide_image_paths)

 
    analysis.status = "completed"
    analysis.save()

    messages.success(request, "Excel Masterfile and PowerPoint generated successfully.")
    return redirect("analysis_app:analysis_detail", analysis_id=analysis.id)



@rbi_login_required
def analysis_history(request):
    rbi_user = request.session.get("rbi_user") or {}
    external_user_id = rbi_user.get("id")

    qs = Analysis.objects.all().order_by("-created_at")

    if external_user_id:
        qs = qs.filter(external_user_id=external_user_id)

    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page")
    analyses = paginator.get_page(page_number)

    return render(request, "history.html", {"analyses": analyses})


