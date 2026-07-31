@echo off
FOR /F "tokens=5" %%a in ('netstat -a -n -o ^| findstr :8000') do taskkill /F /PID %%a
FOR /F "tokens=5" %%a in ('netstat -a -n -o ^| findstr :3000') do taskkill /F /PID %%a
exit /b 0
