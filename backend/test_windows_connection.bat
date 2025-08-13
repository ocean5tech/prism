@echo off
echo ============================================
echo Prism PostgreSQL Windows Connection Test  
echo ============================================
echo.

echo Step 1: Test Network Connectivity
echo ----------------------------------
echo Testing connection to PostgreSQL port...
powershell -Command "Test-NetConnection -ComputerName 172.20.51.134 -Port 5434"
echo.

echo Step 2: Connection Information
echo ------------------------------
echo Host: 172.20.51.134
echo Port: 5434
echo Database: prism_db
echo Username: prism_user
echo Password: [Enter your password when prompted]
echo.

echo Step 3: Sample psql Connection Command
echo --------------------------------------
echo psql -h 172.20.51.134 -p 5434 -U prism_user -d prism_db
echo.

echo Step 4: pgAdmin Connection Settings
echo -----------------------------------
echo Server Name: Prism Development
echo Host: 172.20.51.134
echo Port: 5434
echo Database: prism_db  
echo Username: prism_user
echo.

echo Step 5: Test with curl (if available)
echo -------------------------------------
curl -v telnet://172.20.51.134:5434 2>&1 | findstr "Connected"
echo.

echo ============================================
echo Copy this file to Windows and run to test
echo ============================================
pause