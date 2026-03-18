@echo off
chcp 65001 > nul
echo.
echo  ================================
echo   Growth OS v2 — Production
echo  ================================
echo.
pip install flask waitress -q
echo  Запуск сервера...
echo  Открой браузер: http://localhost:5000
echo.
python app.py
pause
