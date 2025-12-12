# analysis_app/services/ai_extractor.py
from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from .template_rules import get_design_rule, get_bom_rule


from django.conf import settings

try:
    from groq import Groq
except ImportError:  
    Groq = None  




def _get_groq_client() -> Any:
    
    if Groq is None:
        raise RuntimeError("groq-python package is not installed")
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")
    return Groq(api_key=api_key)


def _image_rel_to_data_url(image_rel_path: str, mime_type: str = "image/png") -> str:
    
    abs_path = Path(settings.MEDIA_ROOT) / image_rel_path
    with abs_path.open("rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def _extract_json_from_text(text: str) -> Optional[dict]:
   
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        print("Groq content not JSON-like:", text[:200])
        return None
    json_str = text[start : end + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as exc:
        print("Failed to parse JSON from Groq:", exc)
        print("Raw JSON candidate:", json_str[:400])
        return None


def _call_groq_vision_json(image_rel_path: str, instruction: str) -> Optional[dict]:
   
    client = _get_groq_client()
    image_url = _image_rel_to_data_url(image_rel_path)

    try:
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an OCR/table extraction assistant for engineering drawings.\n"
                        "You MUST return ONLY a single valid JSON object.\n"
                        "Do not include explanations, comments, markdown or any text outside the JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
            max_completion_tokens=2048,
            temperature=0.0,
        )
    except Exception as exc:
        print("Groq Vision error (request failed):", exc)
        return None

    message = completion.choices[0].message
    content = getattr(message, "content", "") or ""

    print("\n========= GROQ RAW RESPONSE (first 400 chars) =========")
    print(str(content)[:400])
    print("=====================================================\n")

    if not isinstance(content, str):
        try:
            content = str(content)
        except Exception:
            print("Groq content could not be converted to string")
            return None

    data = _extract_json_from_text(content)
    print("🔍 Parsed JSON keys:", list(data.keys()) if isinstance(data, dict) else data)
    return data


def _to_float_maybe(value: Any) -> Optional[float]:
    
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if not s:
        return None

    
    s = s.replace(",", ".")
    m = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None




def extract_design_metadata(
    image_rel_path: str,
    pmt_no: Optional[str] = None,
    equipment_no: Optional[str] = None,
) -> Dict[str, Any]:
   
    base_instruction = (
        "The image is a DESIGN DATA (or similar) table from a pressure vessel or heat exchanger drawing.\n"
        "Identify ONLY the main DESIGN / OPERATING data table and ignore any BOM / bill of materials.\n\n"
        "You MUST return ONLY a JSON object with exactly this structure:\n"
        "{\n"
        '  \"fluids\": {\n'
        '    \"shell\": string or null,\n'
        '    \"tube\": string or null,\n'
        '    \"header\": string or null\n'
        "  },\n"
        '  \"insulation\": string or null,\n'
        '  \"design\": {\n'
        '    \"shell\": { \"temp_c\": number or null, \"pressure_mpa\": number or null },\n'
        '    \"tube\":  { \"temp_c\": number or null, \"pressure_mpa\": number or null }\n'
        "  },\n"
        '  \"operating\": {\n'
        '    \"shell\": { \"temp_c\": number or null, \"pressure_mpa\": number or null },\n'
        '    \"tube\":  { \"temp_c\": number or null, \"pressure_mpa\": number or null }\n'
        "  }\n"
        "}\n\n"
        "INTERPRETATION RULES (VERY IMPORTANT):\n"
        "- Tables may use labels like OPERATING, OPERATION, WORKING, or WKG:\n"
        "  * Anything labelled WORKING PRESSURE / WORKING TEMPERATURE or similar = OPERATING conditions.\n"
        "  * Anything labelled OPERATING PRESSURE / OPERATING TEMPERATURE = OPERATING conditions.\n"
        "  * Anything labelled DESIGN PRESSURE / DESIGN TEMPERATURE = DESIGN conditions.\n"
        "  * If there are TWO repeated blocks of PRESSURE/TEMPERATURE rows without clear labels,\n"
        "    assume the FIRST block is OPERATING and the SECOND block is DESIGN.\n"
        "\n"
        "- Column headings may be SHELL SIDE / TUBE SIDE / CHANNEL / TUBE BUNDLE / HEAD, etc.:\n"
        "  * Map anything clearly belonging to SHELL, SHELL SIDE, SHELL PART → shell.\n"
        "  * Map anything clearly belonging to TUBE, TUBE SIDE, CHANNEL, TUBE BUNDLE, HEADER → tube.\n"
        "  * If only a single value is given (no split), use the same value for both shell and tube.\n"
        "\n"
        "- Pressure units:\n"
        "  * Convert kg/cm2, bar, kPa, etc. to MPa if possible.\n"
        "  * If unit is not obvious but looks like e.g. \"1.00 KPDG\" or similar, treat it as 1.00 MPa.\n"
        "  * If you cannot confidently convert, copy the numeric value and assume it is already MPa.\n"
        "\n"
        "- Temperature units:\n"
        "  * Assume °C unless clearly specified otherwise.\n"
        "\n"
        "- FLUID / MEDIUM mapping:\n"
        "  * Use rows labelled FLUID, FLUID NAME, MEDIUM OF SERVICE, or similar.\n"
        "  * If there are separate columns for SHELL SIDE and TUBE SIDE, map them to fluids.shell and fluids.tube.\n"
        "  * If there is only one fluid name for the whole equipment, put it into fluids.shell and fluids.tube.\n"
        "  * If there is a separate HEADER/CHANNEL/TUBE BUNDLE fluid, you may put that into fluids.header.\n"
        "\n"
        "- INSULATION mapping:\n"
        "  * Look for rows labelled INSULATION, DEGREE OF INSULATION, or similar.\n"
        "  * Also consider rows like FULL/SPOT/NONE RADIOGRAPHY or DEGREE OF RADIOGRAPHY if there is\n"
        "    no explicit INSULATION row; in that case copy the most relevant text as insulation.\n"
        "  * If the table clearly indicates NO INSULATION (NIL, NONE, NO INSULATION, '-' etc.),\n"
        "    set insulation to that text (e.g. \"NIL\" or \"NO INSULATION\").\n"
        "\n"
        "- If a value is missing / unreadable, use null.\n"
        "- Do NOT add extra keys or nested structures beyond the JSON schema above.\n"
    )

   
    rule = None
    if pmt_no and equipment_no:
        rule = get_design_rule(pmt_no, equipment_no)

    instruction = base_instruction
    if rule and rule.extra_prompt:
        instruction += "\n\nTEMPLATE-SPECIFIC NOTES FOR THIS DRAWING:\n" + rule.extra_prompt

    data = _call_groq_vision_json(image_rel_path, instruction) or {}
    print("DEBUG design raw data:", data)

    fluids = data.get("fluids") or {}
    design = data.get("design") or {}
    operating = data.get("operating") or {}

    result: Dict[str, Any] = {
        "fluids": {
            "shell": (fluids.get("shell") or None),
            "tube": (fluids.get("tube") or None),
            "header": (fluids.get("header") or None),
        },
        "insulation": data.get("insulation") or None,
        "design": {
            "shell": {
                "temp_c": _to_float_maybe((design.get("shell") or {}).get("temp_c")),
                "pressure_mpa": _to_float_maybe(
                    (design.get("shell") or {}).get("pressure_mpa")
                ),
            },
            "tube": {
                "temp_c": _to_float_maybe((design.get("tube") or {}).get("temp_c")),
                "pressure_mpa": _to_float_maybe(
                    (design.get("tube") or {}).get("pressure_mpa")
                ),
            },
        },
        "operating": {
            "shell": {
                "temp_c": _to_float_maybe(
                    (operating.get("shell") or {}).get("temp_c")
                ),
                "pressure_mpa": _to_float_maybe(
                    (operating.get("shell") or {}).get("pressure_mpa")
                ),
            },
            "tube": {
                "temp_c": _to_float_maybe(
                    (operating.get("tube") or {}).get("temp_c")
                ),
                "pressure_mpa": _to_float_maybe(
                    (operating.get("tube") or {}).get("pressure_mpa")
                ),
            },
        },
    }

    
    for key in ("design", "operating"):
        block = result[key]
        shell = block["shell"]
        tube = block["tube"]
        if not shell["temp_c"] and tube["temp_c"]:
            shell["temp_c"] = tube["temp_c"]
        if not tube["temp_c"] and shell["temp_c"]:
            tube["temp_c"] = shell["temp_c"]
        if not shell["pressure_mpa"] and tube["pressure_mpa"]:
            shell["pressure_mpa"] = tube["pressure_mpa"]
        if not tube["pressure_mpa"] and shell["pressure_mpa"]:
            tube["pressure_mpa"] = shell["pressure_mpa"]

  
    if rule and rule.force_null_operating:
        for side in ("shell", "tube"):
            result["operating"][side]["temp_c"] = None
            result["operating"][side]["pressure_mpa"] = None

    print("DEBUG design_meta final:", result)
    return result



def extract_bom_materials(
    image_rel_path: str,
    pmt_no: Optional[str] = None,
    equipment_no: Optional[str] = None,
) -> List[Dict[str, Any]]:
    
    base_instruction = (
        "The image is a BILL OF MATERIAL (BOM) table from an engineering drawing.\n"
        "Identify ONLY the main BOM table and ignore DESIGN DATA or other tables.\n\n"
        "You MUST return ONLY a JSON object with this structure:\n"
        "{\n"
        '  \"items\": [\n'
        '    { \"part_label\": string, \"material_raw\": string, \"side\": string or null },\n'
        "    ...\n"
        "  ]\n"
        "}\n\n"
        "General rules:\n"
        "- Each row for a real pressure part (HEAD, SHELL, BOTTOM HEAD, CHANNEL, "
        "TUBE BUNDLE, etc.) becomes one item.\n"
        "- part_label: a clean logical name such as 'Shell', 'Head', 'Bottom Head', "
        "'Channel', or 'Tube Bundle' that can be matched against Excel part names.\n"
        "- material_raw: the full material string (for example 'SA-516-70', "
        "'SA-240 316', 'A/SA 516 Gr 70', 'FE-560-Gr912/789L', 'ZY-982-GR.212/678K').\n"
        "- side: if there is shell/tube information, set side to 'shell' or 'tube'. "
        "If not clear, infer (heads/shells → 'shell', channels/tube bundles/headers → 'tube').\n"
        "- Ignore bolts, nuts, gaskets and other non-primary pressure parts.\n"
        "- Do NOT add extra keys.\n"
    )

    rule = None
    if pmt_no and equipment_no:
        rule = get_bom_rule(pmt_no, equipment_no)

    instruction = base_instruction
    if rule and rule.extra_prompt:
        instruction += "\n\nTEMPLATE-SPECIFIC NOTES FOR THIS DRAWING:\n" + rule.extra_prompt

    data = _call_groq_vision_json(image_rel_path, instruction) or {}
    print("DEBUG bom raw data:", data)
    items = data.get("items") or []

    result: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        part_label = (item.get("part_label") or "").strip()
        material_raw = (item.get("material_raw") or "").strip()
        side = item.get("side") or None
        if not part_label and not material_raw:
            continue
        result.append(
            {
                "part_label": part_label,
                "material_raw": material_raw,
                "side": side,
            }
        )

    print("DEBUG bom_items final:", result)
    return result
