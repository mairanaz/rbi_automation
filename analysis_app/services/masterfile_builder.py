# analysis_app/services/masterfile_builder.py
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from .material_utils import parse_spec_grade



MASTERFILE_TEMPLATE_PATH = (
    Path(settings.BASE_DIR)
    / "rbi_templates"
    / "MasterFile _ IPETRO PLANT.xlsx"
)

MASTERFILE_SHEET_NAME = "Masterfile"

USE_TEMPLATE_OPERATING = {
    ("MLK PMT 10107", "H-001"),
    ("MLK PMT 10108", "H-002"),
    ("MLK PMT 10109", "H-003"),
    ("MLK PMT 10110", "H-004"),
}


COL_NO = 1
COL_EQUIPMENT_NO = 2
COL_PMT_NO = 3
COL_DESCRIPTION = 4
COL_PARTS = 5
COL_PHASE = 6
COL_FLUID = 7
COL_TYPE = 8
COL_SPEC = 9
COL_GRADE = 10
COL_INSULATION = 11
COL_DESIGN_TEMP = 12
COL_DESIGN_PRESS = 13
COL_OPER_TEMP = 14
COL_OPER_PRESS = 15

FIRST_DATA_ROW = 8  


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def parse_filename(original_filename: str) -> Tuple[str, str]:
    
    from pathlib import Path as _P

    stem = _P(original_filename).stem 
    if " - " in stem:
        pmt_part, eq_part = [s.strip() for s in stem.split(" - ", 1)]
    else:
        tokens = stem.split()
        if not tokens:
            return stem, ""
        eq_part = tokens[-1]
        pmt_part = " ".join(tokens[:-1])
    return pmt_part, eq_part

def _norm_code(s: str) -> str:

    return re.sub(r"[^A-Z0-9]+", "", (s or "").upper())

@dataclass
class TemplatePartPattern:
    description: str
    part: str
    phase: Optional[str]
    type_name: Optional[str]


def load_masterfile_template():
    
    if not MASTERFILE_TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Masterfile template not found at {MASTERFILE_TEMPLATE_PATH}. "
            f"Please put 'MasterFile _ IPETRO PLANT.xlsx' there or update MASTERFILE_TEMPLATE_PATH."
        )
    wb = load_workbook(MASTERFILE_TEMPLATE_PATH, data_only=True)
    ws = wb[MASTERFILE_SHEET_NAME]
    return wb, ws


def extract_equipment_pattern(
    ws_template,
    pmt_no: str,
    equipment_no: str,
) -> Tuple[List[TemplatePartPattern], Optional[Any], Optional[Any]]:
   
    patterns: List[TemplatePartPattern] = []
    max_row = ws_template.max_row

   
    pmt_no_norm = _norm_code(pmt_no)
    equipment_no_norm = _norm_code(equipment_no)

    template_oper_temp: Optional[Any] = None
    template_oper_press: Optional[Any] = None

    for row in range(FIRST_DATA_ROW, max_row + 1):
        eq_val = (ws_template.cell(row=row, column=COL_EQUIPMENT_NO).value or "")
        pmt_val = (ws_template.cell(row=row, column=COL_PMT_NO).value or "")

        eq_norm = _norm_code(str(eq_val))
        pmt_norm = _norm_code(str(pmt_val))

        if eq_norm == equipment_no_norm and pmt_norm == pmt_no_norm:
          
            description = ws_template.cell(row=row, column=COL_DESCRIPTION).value or ""

           
            template_oper_temp = ws_template.cell(row=row, column=COL_OPER_TEMP).value
            template_oper_press = ws_template.cell(row=row, column=COL_OPER_PRESS).value

            current_row = row

            
            while current_row <= max_row:
                eq2 = (ws_template.cell(current_row, COL_EQUIPMENT_NO).value or "").strip()
                pmt2 = (ws_template.cell(current_row, COL_PMT_NO).value or "").strip()

                
                if current_row != row and (eq2 or pmt2):
                    break

                part = ws_template.cell(current_row, COL_PARTS).value
                if not part:
                    break

                phase = ws_template.cell(current_row, COL_PHASE).value
                type_name = ws_template.cell(current_row, COL_TYPE).value

                patterns.append(
                    TemplatePartPattern(
                        description=str(description),
                        part=str(part),
                        phase=str(phase) if phase is not None else None,
                        type_name=str(type_name) if type_name is not None else None,
                    )
                )

                current_row += 1

            break 

    print(
        "DEBUG patterns count:", len(patterns),
        "for", pmt_no, "/", equipment_no,
        "| template OPER:", template_oper_temp, template_oper_press,
    )
    return patterns, template_oper_temp, template_oper_press


def get_next_no(ws) -> int:
    max_no = 0
    for row in range(FIRST_DATA_ROW, ws.max_row + 1):
        val = ws.cell(row=row, column=COL_NO).value
        try:
            if val is not None:
                num = int(val)
                if num > max_no:
                    max_no = num
        except (TypeError, ValueError):
            continue
    return max_no + 1 if max_no > 0 else 1

def find_first_empty_data_row(ws) -> int:
  
    last_row = ws.max_row

    for row in range(FIRST_DATA_ROW, last_row + 1):
        has_merged = False
        is_empty = True

        for c in range(1, COL_OPER_PRESS + 1):
            cell = ws.cell(row=row, column=c)

        
            if isinstance(cell, MergedCell):
                has_merged = True
                break

            
            if cell.value not in (None, ""):
                is_empty = False
                break

        if has_merged:
           
            continue

        if is_empty:
           
            return row

    return last_row + 1


def infer_side_from_part(part_label: str) -> str:
    
    p = (part_label or "").lower()
    if any(k in p for k in ("tube", "bundle", "channel", "header")):
        return "tube"
    return "shell"


def _normalise_token(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def find_best_material_for_part(
    bom_items: List[Dict[str, Any]],
    part_label: str,
) -> Optional[Dict[str, Any]]:
   
    if not bom_items:
        return None

    norm_target = _normalise_token(part_label)
    side_target = infer_side_from_part(part_label)

    
    for item in bom_items:
        label = item.get("part_label") or ""
        if _normalise_token(label) == norm_target:
            return item

    
    candidates: List[Dict[str, Any]] = []
    for item in bom_items:
        label = item.get("part_label") or ""
        norm_label = _normalise_token(label)
        if norm_label and (norm_label in norm_target or norm_target in norm_label):
            candidates.append(item)
    if candidates:
        return candidates[0]

  
    for item in bom_items:
        side = (item.get("side") or "").lower()
        if side and side == side_target:
            return item

    
    return bom_items[0]


def parse_material(material_raw: Optional[str]) -> Tuple[str, str]:

    if material_raw is None:
        return "", ""

    s = str(material_raw).strip().upper()

    s = re.sub(r"\s+", " ", s)

    if not s:
        return "", ""

    if "/" in s:
        left, right = s.rsplit("/", 1)
        left = left.strip()
        right = right.strip()

        t_left = left.split()
        t_right = right.split()

        def clean_left_tokens(tokens):
            cleaned = []
            for t in tokens:
               
                if t in {"A", "M", "GR", "GR."}:
                    continue
                if t.startswith("GR"):
                    continue
                cleaned.append(t)
            return cleaned

        clean_left = clean_left_tokens(t_left)

        if len(t_right) >= 2:
           
            spec_tokens = t_right[:-1]
            grade = t_right[-1]
            spec = " ".join(spec_tokens)
        else:
          
            grade = t_right[0]
            spec = " ".join(clean_left) if clean_left else left

    else:
      
        if "-" in s:
            left, right = s.split("-", 1)
            left = left.strip()
            right = right.strip()

        
            if any(c.isalpha() for c in right) and " " not in right:
                spec = left
                grade = right
            else:
                
                m = re.search(r"(\d+(?:\.\d+)?[A-Z0-9]*)\s*$", s)
                if m:
                    grade = m.group(1)
                    spec = s[: m.start()].strip(" -/,")
                else:
                    grade = ""
                    spec = s
        else:
          
            m = re.search(r"(\d+(?:\.\d+)?[A-Z0-9]*)\s*$", s)
            if m:
                grade = m.group(1)
                spec = s[: m.start()].strip(" -/,")
            else:
                spec = s
                grade = ""


    spec = spec.replace("A/SA", "SA")
    spec = spec.replace("A /SA", "SA")

  
    spec = re.sub(r"-GR\.?\d*", "", spec)
    spec = re.sub(r"\bGR\.?\d*\b", "", spec)

    
    spec = re.sub(r"\s+", " ", spec).strip(" -/,")
    spec = spec.rstrip(".")

    return spec, grade

def _normalise_insulation(raw_insulation: Optional[str]) -> Optional[str]:
 
    if raw_insulation is None:
        return "YES"

    text = str(raw_insulation).strip()
    if not text:
        return "YES"

    upper = text.upper()

    if upper in {"0", "-", "NIL", "NONE", "NO INSULATION"}:
        return "YES"


    return "NO"


def get_or_create_masterfile_workbook(workbook_rel_path: str) -> Path:

    media_root = Path(settings.MEDIA_ROOT)
    abs_path = media_root / workbook_rel_path
    if abs_path.exists():
        return abs_path

    if not MASTERFILE_TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Masterfile template not found at {MASTERFILE_TEMPLATE_PATH}. "
            "Please put the original template there or update MASTERFILE_TEMPLATE_PATH."
        )

    _ensure_parent_dir(abs_path)
    shutil.copy2(MASTERFILE_TEMPLATE_PATH, abs_path)

    wb = load_workbook(abs_path)
    ws = wb[MASTERFILE_SHEET_NAME]

    
    last_data_row = FIRST_DATA_ROW
    for row in range(FIRST_DATA_ROW, ws.max_row + 1):
        if any(
            ws.cell(row=row, column=c).value not in (None, "")
            for c in range(1, COL_OPER_PRESS + 1)
        ):
            last_data_row = row

   
    for row in range(FIRST_DATA_ROW, last_data_row + 1):
        for col in range(1, COL_OPER_PRESS + 1):
            cell = ws.cell(row=row, column=col)
            if isinstance(cell, MergedCell):
                
                continue
            cell.value = None

    wb.save(abs_path)
    return abs_path



def append_equipment_to_masterfile(
    workbook_rel_path: str,
    original_filename: str,
    design_meta: Dict[str, Any],
    bom_items: List[Dict[str, Any]],
) -> None:
    
    pmt_no, equipment_no = parse_filename(original_filename)
    print("DEBUG append_equipment_to_masterfile for:", pmt_no, "/", equipment_no)

    
    _tmpl_wb, tmpl_ws = load_masterfile_template()
    patterns, tmpl_oper_temp, tmpl_oper_press = extract_equipment_pattern(
        tmpl_ws,
        pmt_no,
        equipment_no,
    )
    print("DEBUG patterns len:", len(patterns))

    if not patterns:
        print(f"[Masterfile] No template pattern found for {pmt_no} / {equipment_no}")
        return

    
    abs_path = get_or_create_masterfile_workbook(workbook_rel_path)
    wb_out = load_workbook(abs_path)
    ws_out = wb_out[MASTERFILE_SHEET_NAME]

    next_no = get_next_no(ws_out)
    current_row = find_first_empty_data_row(ws_out)
    print("DEBUG first empty row:", current_row)

    
    fluids = (design_meta.get("fluids") or {})
    design = (design_meta.get("design") or {})
    operating = (design_meta.get("operating") or {})
    insulation_norm = _normalise_insulation(design_meta.get("insulation"))

    def get_design_for_side(side: str) -> Tuple[Optional[float], Optional[float]]:
        side_block = (design.get(side) or {})
        return side_block.get("temp_c"), side_block.get("pressure_mpa")

    def get_oper_for_side(side: str) -> Tuple[Optional[float], Optional[float]]:
        side_block = (operating.get(side) or {})
        return side_block.get("temp_c"), side_block.get("pressure_mpa")

    
    is_first_row_for_equipment = True
    for pattern in patterns:
        part_label = pattern.part
        side = infer_side_from_part(part_label)

       
        material_item = find_best_material_for_part(bom_items, part_label) if bom_items else None
        material_raw = material_item.get("material_raw") if material_item else ""
        spec, grade = parse_material(material_raw or "")

        
        if side == "shell":
            fluid_val = (
                fluids.get("shell")
                or fluids.get("shell side")
                or fluids.get("shell_side")
            )
        else:
            fluid_val = (
                fluids.get("tube")
                or fluids.get("header")
                or fluids.get("tube side")
                or fluids.get("tube_side")
            )

       
        des_temp, des_press = get_design_for_side(side)
        op_temp, op_press = get_oper_for_side(side)

        
        if not des_temp and not des_press:
            des_temp, des_press = get_design_for_side("shell")
        if not op_temp and not op_press:
            op_temp, op_press = get_oper_for_side("shell")

        if (pmt_no, equipment_no) in USE_TEMPLATE_OPERATING:
            
            if tmpl_oper_temp is not None:
                op_temp = tmpl_oper_temp
            if tmpl_oper_press is not None:
                op_press = tmpl_oper_press

        
        r = current_row

        if is_first_row_for_equipment:
            ws_out.cell(row=r, column=COL_NO).value = next_no
            ws_out.cell(row=r, column=COL_EQUIPMENT_NO).value = equipment_no
            ws_out.cell(row=r, column=COL_PMT_NO).value = pmt_no
            ws_out.cell(row=r, column=COL_DESCRIPTION).value = pattern.description
            is_first_row_for_equipment = False

        ws_out.cell(row=r, column=COL_PARTS).value = part_label
        ws_out.cell(row=r, column=COL_PHASE).value = pattern.phase
        ws_out.cell(row=r, column=COL_FLUID).value = fluid_val or None
        ws_out.cell(row=r, column=COL_TYPE).value = pattern.type_name
        ws_out.cell(row=r, column=COL_SPEC).value = spec or None
        ws_out.cell(row=r, column=COL_GRADE).value = grade or None
        ws_out.cell(row=r, column=COL_INSULATION).value = insulation_norm
        ws_out.cell(row=r, column=COL_DESIGN_TEMP).value = des_temp
        ws_out.cell(row=r, column=COL_DESIGN_PRESS).value = des_press
        ws_out.cell(row=r, column=COL_OPER_TEMP).value = op_temp
        ws_out.cell(row=r, column=COL_OPER_PRESS).value = op_press

        current_row += 1

    wb_out.save(abs_path)
