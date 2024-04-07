@ECHO OFF
SETLOCAL ENABLEDELAYEDEXPANSION
REM This script is intended to be run where you want the patch to live, not from its source folder.
IF EXIST "UmaTL" (
    SET /P reinstall=An UmaTL folder already exists. Replace it? [y]es, [n]o, [u]pdate: 
    IF /I !reinstall! EQU y (
        RMDIR /S /Q UmaTL
        CALL :install
    ) ELSE IF /I !reinstall! EQU u (
        CALL patch.bat install
        EXIT /B
    ) ELSE ( 
        ECHO No actions required, exiting.
    )
) ELSE (
    CALL :install
)
PAUSE
EXIT /B

REM FUNCTIONS

:install
CALL :mingit
CALL :initgit
MOVE uma-temp-mingit UmaTL\.mingit
CD UmaTL
CALL patch.bat install
EXIT /B 0

:mingit
ECHO Installing MinGit ^(https://github.com/git-for-windows/git/releases^)...
MKDIR uma-temp-mingit
curl -L -o uma-temp-mingit.zip "https://github.com/git-for-windows/git/releases/download/v2.38.1.windows.1/MinGit-2.38.1-64-bit.zip"
tar -xf uma-temp-mingit.zip -C uma-temp-mingit
DEL uma-temp-mingit.zip
EXIT /B 0

:initgit
SET mingit=uma-temp-mingit\mingw64\bin\git.exe
REM Ensure CA certs for temp dir
%mingit% config --system http.sslcainfo uma-temp-mingit\mingw64\ssl\certs\ca-bundle.crt
REM Ensure this setting is set correctly
%mingit% config --system credential.helper manager-core
ECHO Downloading UmaTL ^(initializing git repo^)...
%mingit% clone https://github.com/noccu/umamusu-translate.git UmaTL
REM Ensure CA certs are found. Set mingit's default config to use its own certs (why does it not?)
%mingit% config --system http.sslcainfo .mingit\mingw64\ssl\certs\ca-bundle.crt
EXIT /B 0