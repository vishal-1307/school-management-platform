"""Certificate generation service — TC and Bonafide using Jinja2 templates."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader

# Template directory lives alongside this module
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)


async def generate_tc(student_data: Dict[str, Any], school_data: Dict[str, Any]) -> str:
    """Render a Transfer Certificate (TC) as HTML.

    Args:
        student_data: Dict with keys like ``name``, ``admission_number``,
            ``class_name``, ``dob``, ``father_name``, ``join_date``, ``leave_date``.
        school_data: Dict with ``name``, ``address``, ``affiliation_number``.

    Returns:
        Rendered HTML string.
    """
    template = _env.get_template("tc.html")
    return template.render(
        student=student_data,
        school=school_data,
        issue_date=date.today().isoformat(),
    )


async def generate_bonafide(student_data: Dict[str, Any], school_data: Dict[str, Any]) -> str:
    """Render a Bonafide Certificate as HTML.

    Args:
        student_data: Dict with ``name``, ``admission_number``, ``class_name``,
            ``dob``, ``father_name``.
        school_data: Dict with ``name``, ``address``, ``affiliation_number``.

    Returns:
        Rendered HTML string.
    """
    template = _env.get_template("bonafide.html")
    return template.render(
        student=student_data,
        school=school_data,
        issue_date=date.today().isoformat(),
    )
