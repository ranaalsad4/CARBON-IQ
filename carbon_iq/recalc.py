"""Portable workbook recalculation (v1.1).

openpyxl writes formulas without cached results. To check the live Excel formulas against Python (and so that viewers
without a calculation engine see numbers), the workbook is opened and re-saved by LibreOffice in headless mode, which
calculates every formula. Works wherever LibreOffice is installed (Linux, macOS, Windows, Google Colab after
`apt-get install -y libreoffice-calc`).

    python -m carbon_iq.recalc CARBON_IQ_Data_Model.xlsx
returns JSON: {"status": "success" | "skipped" | "error", "total_formulas": n, "total_errors": n, ...}
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ERRORS = ("#DIV/0!", "#N/A", "#NAME?", "#NULL!", "#NUM!", "#REF!", "#VALUE!", "Err:")


def find_soffice():
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    for p in ("/Applications/LibreOffice.app/Contents/MacOS/soffice", r"C:\Program Files\LibreOffice\program\soffice.exe"):
        if Path(p).exists():
            return p
    return None


def check(path):
    """Count formulas and error values; report whether cached values are present."""
    import openpyxl
    wf = openpyxl.load_workbook(path)
    wv = openpyxl.load_workbook(path, data_only=True)
    n, errs, missing = 0, [], 0
    for ws in wf.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    if c.value.upper() in ("=TRUE()", "=FALSE()"):
                        continue    # LibreOffice stores boolean constants as =TRUE()/=FALSE(); not model formulas
                    n += 1
                    v = wv[ws.title][c.coordinate].value
                    if v is None:
                        missing += 1
                    elif isinstance(v, str) and v.startswith(ERRORS):
                        errs.append(f"{ws.title}!{c.coordinate}: {v}")
    return {"total_formulas": n, "total_errors": len(errs), "errors": errs[:50], "formulas_without_value": missing}


def recalc(path, timeout=180):
    path = Path(path).resolve()
    soffice = find_soffice()
    if soffice is None:
        return {"status": "skipped", "reason": "LibreOffice (soffice) not found; open the workbook in Excel to recalculate",
                **check(path)}
    with tempfile.TemporaryDirectory() as tmp:
        profile = Path(tmp) / "profile"
        out = Path(tmp) / "out"
        out.mkdir()
        cmd = [soffice, f"-env:UserInstallation={profile.as_uri()}", "--headless", "--norestore", "--calc",
               "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", str(out), str(path)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env={**os.environ, "HOME": tmp})
        except subprocess.TimeoutExpired:
            return {"status": "error", "reason": "LibreOffice timed out", **check(path)}
        res = out / path.name
        if not res.exists():
            return {"status": "error", "reason": (r.stderr or r.stdout)[-500:], **check(path)}
        shutil.copy(res, path)
    info = check(path)
    ok = info["total_errors"] == 0 and info["formulas_without_value"] == 0
    return {"status": "success" if ok else "error", "engine": "LibreOffice", **info}


if __name__ == "__main__":
    print(json.dumps(recalc(sys.argv[1]), indent=1))
