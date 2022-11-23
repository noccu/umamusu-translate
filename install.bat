@ECHO OFF
SETLOCAL
SET /P usemingit=Download MinGit (~20MB) to enable use of update.bat for easy updating? Enter first letter [y]es, [n]o: 
IF %usemingit% EQU y ( CALL :mingit ) ELSE ( ECHO Skipping MinGit. )

CALL run.bat install
EXIT /B

REM FUNCTIONS

:mingit
IF NOT EXIST ".mingit" (
    ECHO Installing MinGit (https://github.com/git-for-windows/git/releases)...
    powershell -command "Start-BitsTransfer -Source https://github.com/git-for-windows/git/releases/download/v2.38.1.windows.1/MinGit-2.38.1-64-bit.zip -Destination mingit.zip"
    powershell -command "Expand-Archive mingit.zip .mingit"
    del mingit.zip
) ELSE ( ECHO MinGit already installed. )
EXIT /B 0