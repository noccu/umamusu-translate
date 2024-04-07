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
        ECHO Can't find python. Likely incorrect install or not installed.
        GOTO quit
    )
)
ECHO Using %snek%
%snek% --version
%snek% -m pip show unitypy  | findstr /B "Version Location"

REM Newline
ECHO.

REM Treat first arg as label call if exists.
IF [%1] NEQ [] ( 
    GOTO %1 
) ELSE (
    ECHO Patching options:
    ECHO 0. Everything
    ECHO 1. UI ^(menus, etc^)
    ECHO 2. MDB ^(skills, misisons, etc^)
    ECHO 3. Dialogue ^(story^)
    SET /P mode=Enter the numbers for the parts you wish to patch, in order ^(eg. 12, not 21^): 
    CALL update.bat
    IF !mode! EQU 123 (
        SET mode=0
    )
    IF !mode! EQU 1 (
        CALL :tlg
    ) ELSE IF !mode! EQU 2 (
        CALL :mdb
    ) ELSE IF !mode! EQU 3 (
        CALL :dialogue
    ) ELSE IF !mode! EQU 12 (
        CALL :tlg
        CALL :mdb
    ) ELSE IF !mode! EQU 13 (
        CALL :tlg
        CALL :dialogue
    ) ELSE IF !mode! EQU 23 (
        CALL :mdb
        CALL :dialogue
    ) ELSE IF !mode! EQU 0 (
        CALL :tlg
        CALL :mdb
        CALL :dialogue
    ) ELSE (
        ECHO Invalid choice
    )
    GOTO quit
)

:install
IF NOT EXIST ".venv" (
    ECHO Creating venv
    %snek% -m venv .venv
    CALL :venv
) ELSE ( ECHO Using pre-existing venv )

ECHO Installing required libraries...
%snek% -m pip install -r src\requirements.txt --find-links=wheels/ --prefer-binary --disable-pip-version-check --upgrade
IF %ERRORLEVEL% NEQ 0 (
    ECHO.
    echo [93mSomething went wrong. Please screenshot as much as possible or copy this whole window when asking for help. You can hide your username if you want.[0m
    GOTO quit
)

%snek% src/post-install.py
GOTO quit

:uninstall
ECHO Uninstalling patch...
%snek% src/restore.py --uninstall
GOTO quit

:dialogue
ECHO Importing all translatable types that are present in your game files...
ECHO By default, already patched files are skipped. To forcefully rewrite all files, set update to false in the config.
REM Or manually import parts, see import.py -h
%snek% src/import.py --full-import --overwrite --read-defaults
ECHO Removing furigana...
%snek% src/ruby-remover.py
ECHO Cleaning up outdated backups...
%snek% src/filecopy.py --remove-old
EXIT /B 0

:mdb
ECHO Attempting mdb backup...
ECHO Original will be stored at \Users\^<name^>\AppData\LocalLow\Cygames\umamusume\master\master.mdb.bak
%snek% src/mdb/import.py --backup
ECHO Importing mdb text...
%snek% src/mdb/import.py --read-defaults
EXIT /B 0

:tlg
%snek% src/manage.py --move
EXIT /B 0

:venv
IF EXIST ".venv" (
    ECHO Using venv
    .venv\Scripts\activate.bat
)
EXIT /B 0

:quit
PAUSE
EXIT /B
