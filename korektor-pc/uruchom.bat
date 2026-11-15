@echo off
rem Uruchamia Korektor bez budowania .exe — wystarczy Python 3.10+ z python.org.
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw -3 -m korektor & exit /b)
where pythonw >nul 2>nul && (start "" pythonw -m korektor & exit /b)
echo Nie znaleziono Pythona. Zainstaluj go z https://www.python.org/downloads/ albo pobierz gotowy Korektor.exe.
pause
