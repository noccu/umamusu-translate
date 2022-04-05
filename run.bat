@ECHO OFF
REM SET PATH=%PATH%;C:\python3.9;%LOCALAPPDATA%\Programs\Python\Launcher
SETLOCAL
ECHO Checking python...
SET snek=py
WHERE %snek% >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    set snek=python
    WHERE %snek% >nul 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        ECHO Can't find python. Likely not added to PATH ^(google it^) or not installed.
        PAUSE
        EXIT /B
    )
)
ECHO.
ECHO Using %snek%
%snek% --version

IF [%1] NEQ [] (
    IF [%1] EQU [install] GOTO install
) 

:open 
REM %snek% src\ui.py
ECHO Importing all translatable types that are present in your game files. This could take up to 20m.
%snek% src/import.py -O -U
%snek% src/import.py -O -U -t race
%snek% src/import.py -O -U -t home
%snek% src/import.py -O -U -t lyrics
%snek% src/import.py -O -U -t preview
ECHO Imports complete!
PAUSE
EXIT /B

:install
ECHO Installing required libraries...
%snek% -m pip install -r src\requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    ECHO.
    echo [93mSomething went wrong. Please screenshot this window when asking for help. You can hide your username if you want.[0m
    PAUSE
)
