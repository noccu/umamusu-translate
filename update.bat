@ECHO OFF
SETLOCAL ENABLEDELAYEDEXPANSION

IF EXIST ".mingit" (
    ECHO Updating...
    IF EXIST "token.txt" ( 
        ECHO Thank you for supporting the UmaTL project!
        SET /P token=<token.txt
        IF NOT EXIST ".git\refs\heads\supporter" (
            .mingit\mingw64\bin\git.exe fetch !token! master:supporter
            .mingit\mingw64\bin\git.exe checkout -f supporter
        ) ELSE (
            .mingit\mingw64\bin\git.exe pull !token! master
        )
    ) ELSE ( 
        ECHO You are using the Community Edition. Consider supporting us to continue our work and access content faster!
        IF EXIST ".git\refs\heads\supporter" ( 
            .mingit\mingw64\bin\git.exe checkout master 
            .mingit\mingw64\bin\git.exe branch --delete supporter
        )
        .mingit\mingw64\bin\git.exe pull
    )
) ELSE ( ECHO No MinGit found, skipping update. )
EXIT /B