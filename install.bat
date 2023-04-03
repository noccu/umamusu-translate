@ECHO OFF
SETLOCAL
SET /P usemingit=Download MinGit (~20MB) to enable auto-updating? Enter first letter [y]es, [n]o: 
IF /I %usemingit% EQU y ( CALL :mingit ) ELSE ( ECHO Skipping MinGit. )

CALL run.bat install
EXIT /B

REM FUNCTIONS

:mingit
IF NOT EXIST ".mingit" (
    ECHO Installing MinGit ^(https://github.com/git-for-windows/git/releases^)...
    powershell -command "Start-BitsTransfer -Source https://github.com/git-for-windows/git/releases/download/v2.38.1.windows.1/MinGit-2.38.1-64-bit.zip -Destination mingit.zip; Expand-Archive mingit.zip .mingit"
    del mingit.zip
) ELSE ( ECHO MinGit already installed. )
CALL :initgit
EXIT /B 0

:initgit
IF NOT EXIST ".git" (
    ECHO Initializing git repo...
    .mingit\mingw64\bin\git.exe clone --no-checkout https://github.com/noccu/umamusu-translate.git gittmp
    powershell -command "mv gittmp\.git .git"
    DEL /Q gittmp
) ELSE ( ECHO Already a Git repo. )
EXIT /B 0