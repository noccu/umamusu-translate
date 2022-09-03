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
        goto quit
    )
)
ECHO Using %snek%
%snek% --version
%snek% -m pip show unitypy

ECHO(

IF [%1] NEQ [] (
    IF [%1] EQU [install] GOTO install
    IF [%1] EQU [uninstall] GOTO uninstall
    IF [%1] EQU [mdb] GOTO mdb
)

:open
%snek% src/filecopy.py --backup
ECHO Importing all translatable types that are present in your game files...
ECHO Update-only mode is default. To forcefully rewrite all files, remove -U in this .bat
REM Or manually import parts, see import.py -h
%snek% src/import.py --full-import --overwrite --update --silent
REM Copying TLG translation files...
%snek% src/manage.py --move
ECHO Imports complete!
ECHO Removing furigana...
%snek% src/ruby-remover.py
ECHO All done!
GOTO quit

:install
ECHO Installing required libraries...
%snek% -m pip install -r src\requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    ECHO.
    echo [93mSomething went wrong. Please screenshot this window when asking for help. You can hide your username if you want.[0m
    PAUSE
)
GOTO quit

:mdb
ECHO Importing mdb text...
%snek% src/mdb/import.py %2
GOTO quit

:uninstall
ECHO Uninstalling patch...
%snek% src/restore.py --uninstall

:quit
PAUSE
EXIT /B
