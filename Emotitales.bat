@echo off

echo 🚀 Starting EmotiTales AI...

:: Django Backend
start cmd /k "cd /d C:\EmotitalesAi\emotitales && myenv\Scripts\activate && python manage.py runserver"

timeout /t 5

:: React Frontend
start cmd /k "cd /d C:\EmotitalesAi\frontend && npm run dev"

timeout /t 8

:: Open Browser
start http://localhost:5173

echo ✅ Project Running!
pause