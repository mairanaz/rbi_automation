# analysis_app/services/material_utils.py

import re
from typing import Tuple

def parse_spec_grade(raw: str | None) -> Tuple[str, str]:
  
    if raw is None:
        return "", ""

    s = str(raw).strip().upper()
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
               
                if t in {"A", "GR", "GR.", "M"}:
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
                
                m = re.search(r"(\d+(?:\.\d+)?[A-Z]*)\s*$", s)
                grade = ""
                spec = s
                if m:
                    grade = m.group(1)
                    spec = s[: m.start()].strip(" -")
        else:
           
            m = re.search(r"(\d+(?:\.\d+)?[A-Z]*)\s*$", s)
            grade = ""
            spec = s
            if m:
                grade = m.group(1)
                spec = s[: m.start()].strip(" -")

    
    spec = spec.replace("A/SA", "SA")

    
    spec = re.sub(r"-GR\.?\d*", "", spec)
    spec = re.sub(r"\bGR\.?\d*\b", "", spec)

    spec = re.sub(r"\s+", " ", spec).strip(" -")
    spec = spec.rstrip(".")
    spec = spec.replace(" .", "")
    return spec, grade
