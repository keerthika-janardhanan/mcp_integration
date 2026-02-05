@echo off
set PATH=%PATH%;C:\Program Files\nodejs
cd /d "c:\Users\2218532\PycharmProjects\guideware_test_script_generation\framework_repos\f870a1343bdd"
call npx playwright install chromium
echo.
echo Browsers installed successfully!
pause
