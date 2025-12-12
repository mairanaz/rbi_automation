# analysis_app/services/template_rules.py

from dataclasses import dataclass
from typing import Optional, Dict, Tuple


@dataclass
class DesignTemplateRule:
  
    extra_prompt: Optional[str] = None
    force_null_operating: bool = False


@dataclass
class BomTemplateRule:
 
    extra_prompt: Optional[str] = None


# ---------- DESIGN DATA RULES (ikut file) -----------------

DESIGN_RULES: Dict[Tuple[str, str], DesignTemplateRule] = {
    # ------------------------------------------------------
    # MLK PMT 10101 - V-001
    # ------------------------------------------------------
    ("MLK PMT 10101", "V-001"): DesignTemplateRule(
        extra_prompt=(
            "This drawing is MLK PMT 10101 - V-001 (vertical vessel).\n"
            "In the DESIGN DATA table there are two PRESSURE/TEMPERATURE groups "
            "when reading the table from top to bottom.\n"
            "- The FIRST (upper) pair of PRESSURE and TEMPERATURE corresponds to "
            "the OPERATING condition. Map this to operating.shell and operating.tube.\n"
            "- The SECOND (lower) pair of PRESSURE and TEMPERATURE corresponds to "
            "the DESIGN condition. Map this to design.shell and design.tube.\n"
            "There is only a single process side, so copy the same values to both "
            "shell and tube in the JSON.\n"
            "Use the row labelled 'FLUID NAME' as the process fluid and map it to "
            "fluids.shell, fluids.tube and fluids.header.\n"
            "Use the row labelled 'INSULATION' as the source for the 'insulation' field.\n"
        )
    ),

    # ------------------------------------------------------
    # MLK PMT 10102 - V-002
    # ------------------------------------------------------
    ("MLK PMT 10102", "V-002"): DesignTemplateRule(
        extra_prompt=(
            "This drawing is MLK PMT 10102 - V-002 (vertical vessel with TOP HEAD, SHELL, BOTTOM HEAD).\n"
            "The table provides full OPERATING and DESIGN pressure and temperature.\n"
            "You do not need separate numbers per head vs shell: treat the design and "
            "operating conditions as uniform for all parts of the vessel.\n"
            "- Read the OPERATING pressure and temperature columns and map one "
            "representative set to operating.shell and operating.tube.\n"
            "- Read the DESIGN pressure and temperature columns and map one set to "
            "design.shell and design.tube.\n"
            "Use the 'FLUID NAME' row as the process fluid and map it to "
            "fluids.shell, fluids.tube and fluids.header.\n"
            "Use the 'INSULATION' row as the source for the 'insulation' field.\n"
        )
    ),

    # ------------------------------------------------------
    # MLK PMT 10103 - V-003
    # ------------------------------------------------------
    ("MLK PMT 10103", "V-003"): DesignTemplateRule(
        extra_prompt=(
            "This drawing is MLK PMT 10103 - V-003.\n"
            "The DESIGN DATA table has:\n"
            "- 'WORKING PRESSURE' and 'DESIGN PRESSURE' rows,\n"
            "- 'WORKING TEMPERATURE' and 'DESIGN TEMPERATURE' rows.\n"
            "Map WORKING PRESSURE/TEMPERATURE to operating.shell and operating.tube.\n"
            "Map DESIGN PRESSURE/TEMPERATURE to design.shell and design.tube.\n"
            "Use the same values for shell and tube (one set of conditions for the vessel).\n"
            "Use the 'MEDIUM OF SERVICE' row as the process fluid and map it to "
            "fluids.shell, fluids.tube and fluids.header.\n"
            "Use the row that mentions something like 'FULL/SPOT/NONE RADIOGRAPHY' "
            "as a proxy for insulation and return its text in 'insulation'.\n"
        )
    ),

    # ------------------------------------------------------
    # MLK PMT 10105 - V-005 (shell & tube exchanger)
    # ------------------------------------------------------
    ("MLK PMT 10105", "V-005"): DesignTemplateRule(
        extra_prompt=(
            "This drawing is MLK PMT 10105 - V-005 (shell-and-tube exchanger).\n"
            "The DESIGN DATA table has separate 'SHELL SIDE' and 'TUBE SIDE' columns.\n"
            "- FLUID: use the row labelled 'FLUID'; map SHELL SIDE fluid to "
            "fluids.shell and TUBE SIDE fluid to fluids.tube and fluids.header.\n"
            "- OPERATING PRESSURE / TEMPERATURE:\n"
            "  Sometimes the cell contains compound strings like '0.5 / 8 / 3-4' "
            "or '0.5-2' or '1-5'.\n"
            "  * For SHELL SIDE choose the main middle design value "
            "(for example from '0.5 / 8 / 3-4' return 8).\n"
            "  * For TUBE SIDE choose the maximum value in the range "
            "(for example from '1-5' return 5).\n"
            "  Map the shell-side operating values to operating.shell and the "
            "tube-side operating values to operating.tube.\n"
            "- DESIGN PRESSURE / TEMPERATURE: use the 'DESIGN PRESS' and 'DESIGN TEMP' "
            "values for SHELL SIDE and TUBE SIDE in the same way; map them to "
            "design.shell and design.tube.\n"
            "BOTTOM CHANNEL in Excel will reuse the tube-side values.\n"
            "Use the INSULATION row as the source for the 'insulation' field.\n"
        )
    ),

    # ------------------------------------------------------
    # MLK PMT 10106 - V-006
    # ------------------------------------------------------
    ("MLK PMT 10106", "V-006"): DesignTemplateRule(
        extra_prompt=(
            "This drawing is MLK PMT 10106 - V-006 (vessel with HEAD and SHELL only).\n"
            "The DESIGN DATA table has 'WORKING PRESSURE' and 'WORKING TEMPERATURE' rows; "
            "map these to operating.shell and operating.tube.\n"
            "The 'DESIGN PRESSURE' and 'DESIGN TEMPERATURE' rows map to design.shell "
            "and design.tube.\n"
            "Use the same values for shell and tube; only HEAD and SHELL parts "
            "exist in the Excel template.\n"
            "The 'MEDIUM OF SERVICE' row is the process fluid; map it to "
            "fluids.shell, fluids.tube and fluids.header.\n"
            "Use the row that contains a 'DEGREE OF ...' style text (with separate "
            "values for shell and head) as the insulation indicator and use it as "
            "the raw 'insulation' value.\n"
        )
    ),

    # ------------------------------------------------------
    # MLK PMT 10107 - H-001 (heat exchanger)
    # ------------------------------------------------------
    ("MLK PMT 10107", "H-001"): DesignTemplateRule(
        extra_prompt=(
            "This drawing is MLK PMT 10107 - H-001 (shell-and-tube heat exchanger).\n"
            "Read only DESIGN data (DESIGN PRESSURE and DESIGN TEMPERATURE).\n"
            "Map shell-side design values to design.shell and tube-side design values "
            "to design.tube.\n"
            "Do not infer or return any OPERATING values from the image; "
            "set all operating.* fields to null because operating conditions are "
            "taken from the Excel master template.\n"
            "Use the 'FLUID NAME' row: map SHELL SIDE fluid to fluids.shell and "
            "TUBE SIDE fluid to fluids.tube and fluids.header "
            "(CHANNEL and TUBE BUNDLE reuse the tube-side fluid).\n"
            "Use the INSULATION-related row as the raw 'insulation' value.\n"
        ),
        force_null_operating=True,
    ),

    # ------------------------------------------------------
    # MLK PMT 10108 - H-002
    # ------------------------------------------------------
    ("MLK PMT 10108", "H-002"): DesignTemplateRule(
        extra_prompt=(
            "This drawing is MLK PMT 10108 - H-002 (shell-and-tube heat exchanger).\n"
            "Use only DESIGN PRESSURE and DESIGN TEMPERATURE; map shell-side values "
            "to design.shell and tube-side values to design.tube.\n"
            "Leave all operating.* values as null; operating conditions come from "
            "the Excel template, not from this table.\n"
            "Use the 'FLUID NAME' row: SHELL SIDE → fluids.shell, "
            "TUBE SIDE → fluids.tube and fluids.header (for CHANNEL and TUBE BUNDLE).\n"
            "Use the INSULATION row to produce the 'insulation' value.\n"
        ),
        force_null_operating=True,
    ),

    # ------------------------------------------------------
    # MLK PMT 10109 - H-003
    # ------------------------------------------------------
    ("MLK PMT 10109", "H-003"): DesignTemplateRule(
        extra_prompt=(
            "This drawing is MLK PMT 10109 - H-003.\n"
            "Read DESIGN PRESSURE and DESIGN TEMPERATURE for SHELL SIDE and TUBE SIDE "
            "and map them to design.shell and design.tube.\n"
            "Set all operating.* fields to null because operating conditions "
            "are taken from the Excel template.\n"
            "Use the FLUID/FLUID NAME row to map shell/tube fluids to fluids.shell "
            "and fluids.tube/fluids.header.\n"
            "Use the INSULATION-related row as the raw 'insulation' value "
            "for CHANNEL, SHELL and TUBE BUNDLE.\n"
        ),
        force_null_operating=True,
    ),

   
    ("MLK PMT 10110", "H-004"): DesignTemplateRule(
        extra_prompt=(
            "This drawing is MLK PMT 10110 - H-004 (shell-and-tube heat exchanger).\n"
            "Use DESIGN PRESS(URE) and DESIGN TEMP(ERATURE) for SHELL SIDE and TUBE SIDE; "
            "map them to design.shell and design.tube respectively.\n"
            "Leave all operating.* fields as null; operating data is taken from the "
            "Excel template, not from this table.\n"
            "Use the row labelled FLUID/FLUID NAME: SHELL SIDE fluid → fluids.shell; "
            "TUBE SIDE fluid → fluids.tube and fluids.header (for CHANNEL and TUBE BUNDLE).\n"
            "Use the INSULATION row as the raw 'insulation' value for all three parts.\n"
        ),
        force_null_operating=True,
    ),
}




BOM_RULES: Dict[Tuple[str, str], BomTemplateRule] = {
    
    ("MLK PMT 10101", "V-001"): BomTemplateRule(
        extra_prompt=(
            "For MLK PMT 10101 - V-001 the BOM has rows like 'PLATE (SHELL)' and 'PLATE HEAD'.\n"
            "Create one item with part_label='Shell' using the material for the PLATE(SHELL) row, "
            "and one item with part_label='Head' using the material for the PLATE HEAD row.\n"
            "The same HEAD material will be reused for both TOP HEAD and BOTTOM HEAD in Excel."
        )
    ),

   
    ("MLK PMT 10102", "V-002"): BomTemplateRule(
        extra_prompt=(
            "For MLK PMT 10102 - V-002 treat the row whose description mentions 'PLATE SHELL' "
            "as the shell item (part_label='Shell').\n"
            "Treat the row whose description mentions both 'DISH' and 'HEAD' as the head item "
            "(part_label='Head').\n"
            "If the material cell contains two materials such as "
            "'SA 240 M 316L/ SA 240 316', use only the main head material "
            "'SA 240 316' as material_raw for the head item."
        )
    ),

    
    ("MLK PMT 10103", "V-003"): BomTemplateRule(
        extra_prompt=(
            "For MLK PMT 10103 - V-003 there is a single BOM row covering 'SHELL & DISHED END'.\n"
            "Create two items from this row: one with part_label='Shell' and one with "
            "part_label='Head', both sharing the same material_raw "
            "(for example 'A/SA 516 Gr 70')."
        )
    ),

    
    ("MLK PMT 10105", "V-005"): BomTemplateRule(
        extra_prompt=(
            "For MLK PMT 10105 - V-005 the BOM description row that mentions 'SHELL & CHANNEL' "
            "provides the material for the shell and for both channels.\n"
            "Create two items from that row: one with part_label='Shell' and one with "
            "part_label='Channel'.\n"
            "If the material text looks like 'FE-560-Gr912/789L', keep the full string "
            "as material_raw; the system will split SPEC and GRADE later."
        )
    ),

    
    ("MLK PMT 10106", "V-006"): BomTemplateRule(
        extra_prompt=(
            "For MLK PMT 10106 - V-006 the BOM has separate rows for SHELL and for DISHED END.\n"
            "Map the SHELL row to part_label='Shell' and the DISHED END row to "
            "part_label='Head'.\n"
            "Materials may look like 'TY567 GR.8'; store the full string as material_raw."
        )
    ),

    # 10107: HEAD, SHELL, TUBE → Channel, Shell, Tube Bundle
    ("MLK PMT 10107", "H-001"): BomTemplateRule(
        extra_prompt=(
            "For MLK PMT 10107 - H-001 the BOM has rows for HEAD, SHELL and TUBE.\n"
            "Map HEAD to part_label='Channel', SHELL to part_label='Shell', "
            "and TUBE to part_label='Tube Bundle'.\n"
            "Keep material strings such as 'PQ999-ZR312' as a single material_raw value."
        )
    ),

    # 10108
    ("MLK PMT 10108", "H-002"): BomTemplateRule(
        extra_prompt=(
            "For MLK PMT 10108 - H-002 the BOM also has HEAD, SHELL and TUBE rows.\n"
            "Again map HEAD→'Channel', SHELL→'Shell', and TUBE→'Tube Bundle'.\n"
            "Keep strings like 'JK981-IO827' as material_raw."
        )
    ),

    # 10109
    ("MLK PMT 10109", "H-003"): BomTemplateRule(
        extra_prompt=(
            "For MLK PMT 10109 - H-003 map HEAD to part_label='Channel', SHELL to 'Shell' "
            "and TUBE to 'Tube Bundle'.\n"
            "Keep materials such as 'JU923-YT726' as material_raw."
        )
    ),

    # 10110
    ("MLK PMT 10110", "H-004"): BomTemplateRule(
        extra_prompt=(
            "For MLK PMT 10110 - H-004 the BOM includes SHELL, a semi-elliptical head and TUBE rows.\n"
            "Map the SHELL row to part_label='Shell', the semi-elliptical head-style row "
            "to part_label='Channel', and the TUBE row to part_label='Tube Bundle'.\n"
            "Material strings like 'ZY-982-GR.212/678K' should be stored whole as material_raw."
        )
    ),
}


def get_design_rule(pmt_no: str, equipment_no: str) -> Optional[DesignTemplateRule]:
    key = (pmt_no.strip(), equipment_no.strip())
    return DESIGN_RULES.get(key)


def get_bom_rule(pmt_no: str, equipment_no: str) -> Optional[BomTemplateRule]:
    key = (pmt_no.strip(), equipment_no.strip())
    return BOM_RULES.get(key)
