@echo off
setlocal EnableExtensions
title Claude: move to D and install skills
echo ==========================================================
echo  Moves Claude data and skills to D:\Claude and installs
echo  skills from GitHub. Safe to run again.
echo ==========================================================
echo.
echo  BEFORE YOU CONTINUE: fully quit Claude
echo  (tray icon near the clock -^> right click -^> Quit).
echo.
pause

tasklist /FI "IMAGENAME eq claude.exe" 2>nul | find /I "claude.exe" >nul
if not errorlevel 1 (
  echo.
  echo  [STOP] Claude is still running. Quit it from the tray and run this file again.
  pause
  exit /b 1
)
if not exist D:\ (
  echo  [STOP] Drive D: not found.
  pause
  exit /b 1
)
if not exist "D:\Claude" mkdir "D:\Claude"

echo.
echo [1/4] Moving Claude folders to D:\Claude ...
call :relocate "%USERPROFILE%\.claude" "D:\Claude\.claude" || goto :fail
call :relocate "%APPDATA%\Claude" "D:\Claude\AppData" || goto :fail

echo.
echo [2/4] Checking Git ...
set "PATH=%PATH%;D:\Claude\Git\cmd;C:\Program Files\Git\cmd"
where git >nul 2>&1
if errorlevel 1 (
  echo   Git not found, installing to D:\Claude\Git ...
  winget install --id Git.Git -e --silent --location "D:\Claude\Git" --accept-package-agreements --accept-source-agreements
)
where git >nul 2>&1
if errorlevel 1 (
  echo  [STOP] Git is not available. Install it from https://git-scm.com and run this file again.
  goto :fail
)

echo.
echo [3/4] Installing skills ...
if not exist "%USERPROFILE%\.claude\skills" mkdir "%USERPROFILE%\.claude\skills"
rem ---------- SKILLS LIST: skill name git-url ----------
call :skill humanizer https://github.com/blader/humanizer.git

echo.
echo [4/4] Enabling plugins ...
set "SETTINGS=%USERPROFILE%\.claude\settings.json"
if not exist "%SETTINGS%" (
  > "%SETTINGS%" echo {
  >>"%SETTINGS%" echo   "extraKnownMarketplaces": {
  >>"%SETTINGS%" echo     "anthropic-agent-skills": { "source": { "source": "github", "repo": "anthropics/skills" } }
  >>"%SETTINGS%" echo   },
  >>"%SETTINGS%" echo   "enabledPlugins": { "document-skills@anthropic-agent-skills": true }
  >>"%SETTINGS%" echo }
  echo   document-skills enabled.
) else (
  find "document-skills" "%SETTINGS%" >nul && echo   document-skills already enabled. || echo   [NOTE] settings.json already exists - send it to Claude in chat to add document-skills.
)

echo.
echo ==========================================================
echo  DONE. Everything is in D:\Claude. Start Claude again.
echo ==========================================================
pause
exit /b 0

:relocate
rem %1 = old folder on C, %2 = new folder on D. Leaves a junction on C.
set "SRC=%~1"
set "DST=%~2"
set "ATTR="
if exist "%SRC%" for %%I in ("%SRC%") do set "ATTR=%%~aI"
if defined ATTR (echo %ATTR%| find "l" >nul && (echo   %SRC% already points to D, skipping. & exit /b 0))
if exist "%SRC%" (
  robocopy "%SRC%" "%DST%" /E /MOVE /R:2 /W:2 /NFL /NDL /NJH /NJS /NP >nul
  if errorlevel 8 (echo   [ERROR] Could not move %SRC%. Is Claude closed? & exit /b 1)
  rmdir "%SRC%" 2>nul
  if exist "%SRC%" (echo   [ERROR] %SRC% is not empty after move, nothing deleted. & exit /b 1)
) else (
  if not exist "%DST%" mkdir "%DST%"
)
mklink /J "%SRC%" "%DST%" >nul || (echo   [ERROR] Could not create link %SRC% & exit /b 1)
echo   %SRC%  -^>  %DST%
exit /b 0

:skill
set "DIR=%USERPROFILE%\.claude\skills\%~1"
if exist "%DIR%\.git" (
  git -C "%DIR%" pull -q && echo   %~1 updated.
) else (
  git clone -q --depth 1 %~2 "%DIR%" && echo   %~1 installed.
)
exit /b 0

:fail
echo.
echo  Something went wrong. Take a screenshot of this window and send it to Claude.
pause
exit /b 1
