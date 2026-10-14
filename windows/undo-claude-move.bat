@echo off
setlocal EnableExtensions
title Claude: move everything back to C
echo ==========================================================
echo  Stops Claude and moves its data from D:\Claude back to C.
echo  Your skills, settings and login are kept.
echo ==========================================================
pause

echo.
echo [1/3] Stopping all Claude processes ...
taskkill /F /T /IM claude.exe >nul 2>&1
timeout /t 3 /nobreak >nul
taskkill /F /T /IM claude.exe >nul 2>&1

echo.
echo [2/3] Moving folders back to C ...
call :restore "%APPDATA%\Claude" "D:\Claude\AppData" || goto :fail
call :restore "%USERPROFILE%\.claude" "D:\Claude\.claude" || goto :fail

echo.
echo [3/3] Done.
echo ==========================================================
echo  Everything is back on C. RESTART THE COMPUTER, then open Claude.
echo ==========================================================
pause
exit /b 0

:restore
rem %1 = folder on C (currently a link), %2 = real data on D
set "LINK=%~1"
set "DATA=%~2"
set "ATTR="
if exist "%LINK%" for %%I in ("%LINK%") do set "ATTR=%%~aI"
if defined ATTR (
  echo %ATTR%| find "l" >nul || (echo   %LINK% is already a normal folder, skipping. & exit /b 0)
  rmdir "%LINK%" || (echo   [ERROR] Could not remove link %LINK% & exit /b 1)
)
if not exist "%DATA%" (echo   No data in %DATA%, skipping. & exit /b 0)
robocopy "%DATA%" "%LINK%" /E /MOVE /R:2 /W:2 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (echo   [ERROR] Could not move %DATA% back. Is Claude closed? & exit /b 1)
echo   %DATA%  -^>  %LINK%
exit /b 0

:fail
echo.
echo  Something went wrong. Take a screenshot of this window and send it to Claude.
pause
exit /b 1
