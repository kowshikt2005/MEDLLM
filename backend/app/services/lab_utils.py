"""
Lab report detection and parsing utilities.

Detects lab PDFs and extracts structured test data:
  - Test name
  - Value  
  - Unit
  - Reference range
  - Abnormality flags

This enables precise handling of lab data vs. narrative text.
"""

import re
import json
from dataclasses import dataclass


@dataclass
class LabTest:
    """A single lab test result."""
    test_name: str
    value: str
    unit: str = ""
    reference_range: str = ""
    is_abnormal: bool = False
    abnormality_type: str = ""  # "HIGH", "LOW", "CRITICAL"
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "test_name": self.test_name,
            "value": self.value,
            "unit": self.unit,
            "reference_range": self.reference_range,
            "is_abnormal": self.is_abnormal,
            "abnormality_type": self.abnormality_type,
        }


# ────────────────────────────────────────────────────────────────────────
# LAB PDF DETECTION
# ────────────────────────────────────────────────────────────────────────

LAB_INDICATORS = [
    "lab result", "laboratory result", "test result",
    "reference range", "reference interval",
    "hemoglobin", "hematocrit", "white blood cell", "wbc",
    "glucose", "creatinine", "albumin", "bilirubin",
    "ast", "alt", "gpt", "alkaline phosphatase",
    "sodium", "potassium", "chloride", "bicarbonate",
    "calcium", "phosphate", "magnesium",
    "b12", "folate", "vitamin d", "ferritin",
    "tsh", "free t4", "t3",
    "triglyceride", "cholesterol", "ldl", "hdl",
    "psa", "testosterone", "estrogen",
    "normal range", "low-normal", "high-normal",
    "abnormal", "critical value", "flag",
]

CRITICAL_VALUES = {
    "b12": (200, None),  # < 200 is critical low
    "vitamin d": (20, None),  # < 20 is critical low
    "glucose": (40, 600),  # < 40 or > 600 are critical
    "potassium": (2.5, 6.5),  # Outside this range is critical
    "sodium": (125, 155),  # Outside this range is critical
    "hemoglobin": (5.0, None),  # < 5.0 is critical low
    "creatinine": (None, 10.0),  # > 10.0 is critical high
    "bilirubin": (None, 20.0),  # > 20.0 is critical
    "alt": (None, 5000),  # > 5000 is critical
    "ast": (None, 5000),  # > 5000 is critical
}


def is_lab_pdf(text: str) -> bool:
    """
    Detect if the document is a lab report.
    
    Returns True if text contains multiple lab-related keywords.
    Prevents false positives by requiring at least 2 indicators.
    """
    if not text:
        return False
    
    lower_text = text.lower()
    matches = sum(1 for indicator in LAB_INDICATORS if indicator in lower_text)
    
    # Need at least 2 lab indicators to be confident
    return matches >= 2


def extract_lab_tests(text: str) -> list[LabTest]:
    """
    Extract structured lab test data from text.
    
    Uses regex patterns to find:
      - Test name
      - Value
      - Unit
      - Reference range
    
    Marks abnormal values based on reference ranges.
    """
    tests = []
    
    # Pattern 1: "Test Name: value unit (ref: range)" or similar
    # Captures: test name, value, unit, reference range
    pattern1 = r"([A-Za-z\s,/\-]+?):\s*([\d.]+|<[\d.]+|>[\d.]+)\s*([a-zA-Z/%]*)\s*(?:\(.*?ref.*?([0-9.]+\s*[-–—]\s*[0-9.]+)[^)]*\))?(?:\s*\[.*?\])?(?:\s*L|H|C)?"
    
    # Pattern 2: Test name on one line, value and range on next
    # Harder to catch but common in lab reports
    pattern2 = r"([A-Za-z\s,/]+?)\n\s*([\d.]+|<[\d.]+|>[\d.]+)\s*([a-zA-Z/%]*)\s*([0-9.]+\s*[-–—]\s*[0-9.]+)?"
    
    matches = re.finditer(pattern1, text, re.IGNORECASE | re.MULTILINE)
    
    for match in matches:
        test_name = match.group(1).strip()
        value_str = match.group(2).strip()
        unit = match.group(3).strip() if match.group(3) else ""
        ref_range = match.group(4).strip() if match.group(4) else ""
        
        # Skip very generic or empty test names
        if len(test_name) < 3 or test_name.lower() in ("the", "and", "test"):
            continue
        
        # Parse the value
        try:
            if value_str.startswith("<"):
                value = float(value_str[1:])
            elif value_str.startswith(">"):
                value = float(value_str[1:])
            else:
                value = float(value_str)
        except ValueError:
            continue
        
        # Check if abnormal based on reference range or critical values
        is_abnormal, abnormality_type = _check_abnormal(
            test_name, value, ref_range
        )
        
        test = LabTest(
            test_name=test_name,
            value=value_str,
            unit=unit,
            reference_range=ref_range,
            is_abnormal=is_abnormal,
            abnormality_type=abnormality_type,
        )
        tests.append(test)
    
    return tests


def _check_abnormal(test_name: str, value: float, ref_range: str) -> tuple[bool, str]:
    """
    Determine if a value is abnormal.
    
    Returns: (is_abnormal, type) where type is "", "HIGH", "LOW", or "CRITICAL"
    """
    test_lower = test_name.lower()
    
    # Check critical values first
    for critical_test, (critical_low, critical_high) in CRITICAL_VALUES.items():
        if critical_test in test_lower:
            if critical_low and value < critical_low:
                return True, "CRITICAL"
            if critical_high and value > critical_high:
                return True, "CRITICAL"
    
    # Check reference range
    if ref_range:
        # Try to parse reference range like "70-100" or "4.5-5.5"
        match = re.search(r"([\d.]+)\s*[-–—]\s*([\d.]+)", ref_range)
        if match:
            try:
                low = float(match.group(1))
                high = float(match.group(2))
                
                if value < low:
                    return True, "LOW"
                elif value > high:
                    return True, "HIGH"
            except ValueError:
                pass
    
    return False, ""


def format_lab_summary(tests: list[LabTest]) -> str:
    """
    Format extracted lab tests as a structured summary.
    
    Creates a markdown-style table for display.
    """
    if not tests:
        return ""
    
    lines = [
        "\n## Lab Results Summary\n",
        "| Test | Value | Unit | Reference | Status |",
        "|------|-------|------|-----------|--------|",
    ]
    
    for test in tests:
        status = "⚠️ ABNORMAL" if test.is_abnormal else "✓ Normal"
        if test.abnormality_type == "CRITICAL":
            status = "🚨 CRITICAL"
        
        lines.append(
            f"| {test.test_name} | {test.value} | {test.unit} | "
            f"{test.reference_range} | {status} |"
        )
    
    return "\n".join(lines)


def format_lab_json(tests: list[LabTest]) -> str:
    """Format lab tests as JSON for programmatic use."""
    return json.dumps([t.to_dict() for t in tests], indent=2)
