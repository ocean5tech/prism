# Windows to WSL PostgreSQL Connection Testing Checklist

## ✅ Pre-Requirements Verified
- [x] PostgreSQL container running: `prism-postgres`
- [x] Database accessible: `prism_db`
- [x] User configured: `prism_user`
- [x] Port mapping active: `5434:5432`
- [x] WSL IP address: `172.20.51.134`

## 📋 Windows Client Installation Options

### Option 1: pgAdmin (Recommended for GUI)
- [ ] Download from: https://www.pgadmin.org/download/pgadmin-4-windows/
- [ ] Install using .exe installer
- [ ] Launch pgAdmin (opens in browser)

### Option 2: PostgreSQL Command Line Tools
- [ ] Download from: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
- [ ] Select "Command Line Tools Only" during installation
- [ ] Add PostgreSQL bin directory to Windows PATH
- [ ] Test with: `psql --version`

### Option 3: DBeaver (Universal)
- [ ] Download from: https://dbeaver.io/download/
- [ ] Install Community Edition
- [ ] Add PostgreSQL driver if needed

## 🔧 Connection Parameters

**Primary Connection (WSL IP):**
- Host: `172.20.51.134`
- Port: `5434`
- Database: `prism_db`
- Username: `prism_user`
- Password: `[your_password]`

**Backup Connection (if port forwarding configured):**
- Host: `localhost` or `127.0.0.1`
- Port: `5434`
- Database: `prism_db`
- Username: `prism_user`
- Password: `[your_password]`

## 🧪 Connection Testing Steps

### Step 1: Network Connectivity Test
From Windows Command Prompt:
```cmd
telnet 172.20.51.134 5434
```
- [ ] Connection successful (blank screen = success)
- [ ] If fails, check firewall settings

### Step 2: PostgreSQL Client Test
#### Using psql command line:
```cmd
psql -h 172.20.51.134 -p 5434 -U prism_user -d prism_db
```
- [ ] Prompts for password
- [ ] Successfully connects to database
- [ ] Shows `prism_db=#` prompt

#### Using pgAdmin:
1. [ ] Right-click "Servers" → Create → Server
2. [ ] Enter connection details in Connection tab
3. [ ] Click "Save"
4. [ ] Verify server appears in left panel
5. [ ] Expand to see databases

#### Using DBeaver:
1. [ ] Click "New Database Connection"
2. [ ] Select PostgreSQL
3. [ ] Enter connection details
4. [ ] Click "Test Connection"
5. [ ] Verify "Connected" message

### Step 3: Database Functionality Test
Run these SQL commands to verify:

```sql
-- Basic connection info
SELECT version();
SELECT current_database();
SELECT current_user;

-- Database structure
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname = 'public';

-- Connection statistics
SELECT 
    datname as database,
    usename as username,
    client_addr,
    state
FROM pg_stat_activity 
WHERE datname = 'prism_db';
```

- [ ] Version query returns PostgreSQL 15.x
- [ ] Database shows as 'prism_db'
- [ ] User shows as 'prism_user'
- [ ] Can see any existing tables
- [ ] Connection appears in activity log

## 🚨 Troubleshooting Guide

### Problem: "Connection refused" or timeout
**Solutions:**
- [ ] Verify WSL is running: `wsl --list --verbose`
- [ ] Check container status: `podman ps` (in WSL)
- [ ] Verify WSL IP hasn't changed: `hostname -I` (in WSL)
- [ ] Test Windows Firewall: temporarily disable or add exception
- [ ] Try alternative connection: `localhost:5434`

### Problem: "Authentication failed"
**Solutions:**
- [ ] Verify password is correct
- [ ] Check username is exactly 'prism_user'
- [ ] Verify database name is exactly 'prism_db'
- [ ] Check container logs: `podman logs prism-postgres`

### Problem: "Database does not exist"
**Solutions:**
- [ ] Verify database name spelling: 'prism_db'
- [ ] Check available databases: `podman exec prism-postgres psql -U prism_user -l`
- [ ] Ensure container initialization completed successfully

### Problem: WSL IP address changes
**Solutions:**
- [ ] Note: WSL IP can change when WSL restarts
- [ ] Get current IP: `hostname -I` (in WSL)
- [ ] Update connection settings with new IP
- [ ] Consider setting up static IP or port forwarding

## 📁 Test Files Created

1. **Python Test Script**: `/home/wyatt/dev-projects/Prism/backend/test_db_connection.py`
   - Tests multiple connection methods
   - Provides detailed connection diagnostics
   - Run with: `python3 test_db_connection.py`

2. **Windows Batch Script**: `/home/wyatt/dev-projects/Prism/backend/test_windows_connection.bat`
   - Windows-specific connection test
   - Copy to Windows machine and run
   - Tests network and database connectivity

## ✅ Success Criteria

Connection testing is successful when:
- [ ] Network connectivity test passes
- [ ] Database authentication succeeds
- [ ] Can execute basic SQL queries
- [ ] Can browse database structure in GUI client
- [ ] Connection appears stable (no frequent disconnects)
- [ ] Performance is acceptable for development work

## 📊 Performance Benchmarks

Expected performance from Windows to WSL PostgreSQL:
- [ ] Connection time: < 2 seconds
- [ ] Simple query response: < 100ms
- [ ] Complex query response: varies by complexity
- [ ] No connection drops during normal use

## 🔄 Maintenance Notes

**Regular checks:**
- WSL IP address may change after WSL restart
- Container must be running for connections to work
- Windows Firewall updates may block connections
- Monitor connection pool usage for performance

**Quick restart sequence if needed:**
1. `podman stop prism-postgres`
2. `podman start prism-postgres`
3. Update connection settings with new IP if changed
4. Test connection from Windows

---

## Summary

Your PostgreSQL database is properly configured and accessible. The most reliable connection method from Windows is:

**Host:** `172.20.51.134`  
**Port:** `5434`  
**Database:** `prism_db`  
**Username:** `prism_user`  

Use pgAdmin for GUI access or psql for command-line access. Both test scripts are available to verify connectivity.