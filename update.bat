@ECHO OFF
SETLOCAL

IF EXIST ".mingit" (
    ECHO Updating...
    .mingit\mingw64\bin\git.exe pull
) ELSE ( ECHO No MinGit found, skipping update. )
EXIT /B