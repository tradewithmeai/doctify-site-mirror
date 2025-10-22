@echo off
setlocal
title Run Schema Extract + Validate
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] venv not found. Run setup.bat first.
  exit /b 1
)
call .venv\Scripts\activate
if exist requirements.txt (
  pip install -q -r requirements.txt
) else (
  pip install -q beautifulsoup4 pyyaml lxml
)
python pipelines\extract.py || exit /b 1
python pipelines\validate.py || exit /b 1
echo.
echo [OK] Extract + Validate complete. See mirror\extracted\validation_report.json
endlocal
