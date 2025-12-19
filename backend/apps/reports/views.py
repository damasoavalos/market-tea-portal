from __future__ import annotations

import tempfile
from pathlib import Path

from django.http import FileResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .configs import CFG_RESTOCKING_REPORT
from .engine import generate_report


@require_http_methods(["GET"])
def upload_form(request):
    return render(request, "reports/upload.html")


@require_http_methods(["POST"])
def generate_from_upload(request):
    upload = request.FILES.get("file")
    if not upload:
        return render(request, "reports/upload.html", {"error": "Please select an Excel file."})

    suffix = Path(upload.name).suffix.lower()
    if suffix not in [".xlsx", ".xlsm", ".xls"]:
        return render(request, "reports/upload.html", {"error": "Please upload an Excel file (.xlsx/.xlsm/.xls)."} )

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            excel_path = tmpdir_path / upload.name

            with excel_path.open("wb") as f:
                for chunk in upload.chunks():
                    f.write(chunk)

            out_dir = tmpdir_path / "out"
            cfg = CFG_RESTOCKING_REPORT
            report_path = generate_report(excel_path, out_dir, cfg)

            return FileResponse(
                report_path.open("rb"),
                as_attachment=True,
                filename=f"{cfg.output_excel_name}.xlsx",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    except Exception as e:
        return render(request, "reports/upload.html", {"error": str(e)})
