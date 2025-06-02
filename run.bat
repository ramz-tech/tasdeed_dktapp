@echo off
echo Starting Tasdeed ORION application...

:: Check if virtual environment exists
if not exist .venv\Scripts\activate.bat (
    echo Error: Virtual environment not found.
    echo Please make sure the .venv directory exists and is properly set up.
    echo You can create it by running: python -m venv .venv
    echo Then install dependencies: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: Activate the virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

:: Check if activation was successful
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Run the main.py script
echo Running application...
python main.py

:: Check if the application exited with an error
if %ERRORLEVEL% neq 0 (
    echo Application exited with an error. Error code: %ERRORLEVEL%
    pause
)

:: Deactivate the virtual environment
call deactivate
echo Application closed.
pause