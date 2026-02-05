@echo off
set PATH=%PATH%;C:\Program Files\nodejs
cd /d "c:\Users\2218532\PycharmProjects\guideware_test_script_generation\frontend"
call npm run build
echo.
echo Frontend rebuilt successfully!
pause
