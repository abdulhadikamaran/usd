@echo off
echo ===================================================
echo Opening Windows Firewall for Port 8000
echo ===================================================
netsh advfirewall firewall add rule name="Allow Uvicorn Port 8000" dir=in action=allow protocol=TCP localport=8000 profile=any
echo.
echo Firewall rule created successfully!
pause
