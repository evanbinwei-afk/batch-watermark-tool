@echo off
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name BatchWatermarkToolProV3 app.py
echo.
echo Build complete.
echo EXE: dist\BatchWatermarkToolProV3.exe
pause
