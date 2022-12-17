@ECHO OFF
SETLOCAL ENABLEDELAYEDEXPANSION
ECHO Checking python...
CALL :venv
SET snek=py
WHERE %snek% >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    SET snek=python
    WHERE !snek! >nul 2>&1
    IF !ERRORLEVEL! NEQ 0 (
        ECHO Can't find python. Likely not added to PATH ^(google it^) or not installed.
        GOTO quit
    )
)
ECHO Using %snek%
%snek% --version
%snek% -m pip show unitypy

ECHO(

IF [%1] NEQ [] ( GOTO %1 )

:open
CALL update.bat
%snek% src/filecopy.py --backup
ECHO Importing all translatable types that are present in your game files...
ECHO Update-only mode is default. To forcefully rewrite all files, remove -U in this .bat
REM Or manually import parts, see import.py -h
%snek% src/import.py --full-import --overwrite --update --write-log
REM Copying TLG translation files...
%snek% src/manage.py --move
ECHO Imports complete!
ECHO Removing furigana...
%snek% src/ruby-remover.py
ECHO All done!
GOTO quit

:install
IF NOT EXIST ".venv" (
    ECHO Creating venv
    %snek% -m venv .venv
    CALL :venv
) ELSE ( ECHO Using pre-existing venv )

ECHO Installing required libraries...
%snek% -m pip install -r src\requirements.txt --find-links=wheels/ --prefer-binary --disable-pip-version-check
IF %ERRORLEVEL% NEQ 0 (
    ECHO.
    echo [93mSomething went wrong. Please screenshot as much as possible or copy this whole window when asking for help. You can hide your username if you want.[0m
    PAUSE
)
GOTO quit

:mdb
CALL update.bat
ECHO Attempting mdb backup...
ECHO Original will be stored at \Users^<name^>\AppData\LocalLow\Cygames\umamusume\master\master.mdb.bak
%snek% src/mdb/import.py --backup
ECHO Importing mdb text...
%snek% src/mdb/import.py %2
GOTO quit

:uninstall
ECHO Uninstalling patch...
%snek% src/restore.py --uninstall

:quit
PAUSE
EXIT /B

REM FUNCTIONS

:venv
IF EXIST ".venv" (
    ECHO Using venv
    .venv\Scripts\activate.bat
)
EXIT /B 0