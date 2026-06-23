@echo off
setlocal

echo Checking for Python...
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python not found. Downloading Python installer...
    curl -L -o python_installer.exe https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe
    echo Installing Python silently...
    python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    del python_installer.exe
    echo Python installed. Please wait for PATH to refresh...
    timeout /t 5 /nobreak >nul
)

echo Installing PseudoHunter Python dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install sherlock-project maigret holehe --quiet

echo Done.
endlocal
