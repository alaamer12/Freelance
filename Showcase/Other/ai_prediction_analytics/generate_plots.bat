@echo off
echo ===============================================
echo    AI Prediction Analytics - Static Generator
echo ===============================================
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Generating static plots...
python static_generator.py
echo.
echo Done! Check the 'static_plots' folder for images.
pause
