# Production Deployment Guide

## Overview

This guide covers deploying the Bitcoin Address Hunter for 24/7 autonomous operation.

## Two Versions Available

### 1. `scanner.py` - Interactive Version
- Requires user input to start
- Good for manual testing
- **Not suitable for 24/7 operation**

### 2. `scanner_daemon.py` - Production Version ✅
- No user input required
- Comprehensive error handling
- Auto-reconnects to database
- Rotating log files
- Signal handling (SIGTERM, SIGINT, SIGHUP)
- **Ready for 24/7 autonomous operation**

---

## Quick Start (24/7 Operation)

### Option 1: Direct Execution
```bash
cd ~/bitcoin-hunter
nohup python3 scanner_daemon.py > /dev/null 2>&1 &
```

Monitor logs:
```bash
tail -f logs/stats.log
tail -f logs/errors.log
```

### Option 2: Systemd Service (Recommended)
```bash
# Copy service file
sudo cp bitcoin-hunter.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable bitcoin-hunter

# Start the service
sudo systemctl start bitcoin-hunter

# Check status
sudo systemctl status bitcoin-hunter

# View logs
sudo journalctl -u bitcoin-hunter -f
```

---

## Features Comparison

| Feature | scanner.py | scanner_daemon.py |
|---------|-----------|-------------------|
| User input required | ✅ Yes | ❌ No |
| Error handling | ❌ Basic | ✅ Comprehensive |
| Database reconnection | ❌ No | ✅ Yes |
| Signal handling | ⚠️ Partial | ✅ Full |
| File I/O protection | ❌ No | ✅ Yes |
| Logging | ⚠️ Print only | ✅ Rotating files |
| 24/7 ready | ❌ No | ✅ Yes |
| Auto-restart | ❌ No | ✅ With systemd |

---

## Production Daemon Features

### 1. Autonomous Operation
- Starts immediately (no keyboard input)
- Runs indefinitely until stopped
- Survives temporary errors

### 2. Error Handling
- Try/except around all critical operations
- Automatic database reconnection
- Graceful degradation (continues after recoverable errors)
- Stops cleanly after 100 consecutive errors

### 3. Signal Handling
```bash
# Graceful shutdown
kill -TERM <pid>   # or: systemctl stop bitcoin-hunter

# Also handles
kill -INT <pid>    # Ctrl+C
kill -HUP <pid>    # Reload signal
```

### 4. Logging

**Three log files:**

1. **logs/stats.log** - Performance metrics
   - Logged every 60 seconds
   - Rotating: 50MB max, keeps 3 files
   - Format: `timestamp - Stats: X keys, Y addrs, Z k/s avg`

2. **logs/errors.log** - Error messages
   - All errors and warnings
   - Rotating: 10MB max, keeps 5 files
   - Detailed stack traces

3. **logs/found.txt** - Found addresses
   - Append-only
   - Contains full key details
   - **BACKUP THIS FILE!**

### 5. Database Health Checks
- Checks connection every 5 minutes
- Auto-reconnects if connection lost
- Retries failed queries once

### 6. Performance Monitoring
- Real-time console stats (every 1 second)
- File-logged stats (every 60 seconds)
- Tracks:
  - Keys generated
  - Addresses checked
  - Current rate (keys/sec, addrs/sec)
  - Found count
  - Error count
  - Total runtime

---

## Monitoring

### Check if Running
```bash
# Systemd
sudo systemctl status bitcoin-hunter

# Direct process
ps aux | grep scanner_daemon
```

### View Real-time Stats
```bash
# Systemd logs
sudo journalctl -u bitcoin-hunter -f

# File logs
tail -f logs/stats.log
```

### Check Performance
```bash
# Recent stats
tail -50 logs/stats.log

# Error count
grep -c "ERROR" logs/errors.log
```

### Check for Finds (Will Never Happen, But...)
```bash
# Check found log
cat logs/found.txt

# Or monitor in real-time
tail -f logs/found.txt
```

---

## Troubleshooting

### Scanner Won't Start

**Check database exists:**
```bash
ls -lh data/addresses.db
```
If missing:
```bash
python3 download_blockchair.py
python3 import_db.py
```

**Check permissions:**
```bash
ls -la scanner_daemon.py
chmod +x scanner_daemon.py
```

**Check Python version:**
```bash
python3 --version  # Should be 3.6+
```

### High Error Rate

**Check error log:**
```bash
tail -100 logs/errors.log
```

**Common issues:**
- Database locked → reduce concurrent access
- Disk full → check `df -h`
- Permissions → check log directory writeable

### Performance Degradation

**Check system resources:**
```bash
# CPU usage
top -p $(pgrep -f scanner_daemon)

# Memory usage
ps aux | grep scanner_daemon

# Disk I/O
iotop
```

**Database optimization:**
```bash
cd ~/bitcoin-hunter
sqlite3 data/addresses.db "VACUUM; ANALYZE;"
```

### Scanner Stops Unexpectedly

**Check logs for reason:**
```bash
tail -100 logs/errors.log
sudo journalctl -u bitcoin-hunter -n 100
```

**Common causes:**
- 100 consecutive errors hit
- Database file deleted/corrupted
- Out of memory (OOM killer)
- Disk full

---

## Maintenance

### Daily
- Check scanner is running: `systemctl status bitcoin-hunter`
- Verify no errors: `tail -20 logs/errors.log`

### Weekly
- Review performance: `tail -100 logs/stats.log`
- Check disk space: `df -h`
- Check log sizes: `du -sh logs/`

### Monthly
- Rotate logs manually if needed
- Update address database:
  ```bash
  systemctl stop bitcoin-hunter
  python3 download_blockchair.py
  python3 import_db.py
  systemctl start bitcoin-hunter
  ```
- Review system resources

### Quarterly
- Audit found.txt (will be empty, but check)
- Review error patterns
- Consider performance optimizations

---

## Security Considerations

### File Permissions
```bash
# Restrict access to found.txt (contains private keys if anything found)
chmod 600 logs/found.txt

# Read-only database
chmod 444 data/addresses.db
```

### Network Isolation
- Scanner doesn't need internet access after database download
- Consider firewall rules if running on public server

### Resource Limits
Edit `bitcoin-hunter.service`:
```ini
[Service]
MemoryMax=2G      # Limit RAM
CPUQuota=80%      # Limit CPU
```

---

## Backup Strategy

### What to Backup
1. **logs/found.txt** - Contains any found keys (will be empty, but backup anyway)
2. **logs/stats.log** - Performance history
3. **data/addresses.db** - Address database (can re-download, but slow)

### Backup Commands
```bash
# Compress and backup logs
tar czf backup-$(date +%Y%m%d).tar.gz logs/found.txt logs/stats.log

# Optionally backup database
tar czf db-backup-$(date +%Y%m%d).tar.gz data/addresses.db
```

---

## Performance Tuning

### Current Performance
- **775 keys/sec** on Oracle ARM (4 cores, 24GB RAM)
- **148,000 DB lookups/sec**
- Bottleneck: Key generation (CPU-bound)

### Optimization Options

**1. Multi-processing (Not Implemented)**
- Could achieve ~2,000-3,000 keys/sec
- Complexity: Shared database access

**2. Compiled Language (Future)**
- Rust/C implementation: 10,000-50,000 keys/sec
- GPU acceleration: 1,000,000+ keys/sec

**3. Database Tuning**
```bash
# Already optimized, but you could experiment with:
sqlite3 data/addresses.db "PRAGMA journal_mode=WAL;"
sqlite3 data/addresses.db "PRAGMA synchronous=NORMAL;"
```

---

## Stopping the Scanner

### Graceful Shutdown
```bash
# Systemd
sudo systemctl stop bitcoin-hunter

# Direct process
kill -TERM $(pgrep -f scanner_daemon)
```

Graceful shutdown will:
- Finish current key check
- Display final statistics
- Close database connection
- Exit cleanly

### Force Stop (Not Recommended)
```bash
# Systemd
sudo systemctl kill bitcoin-hunter

# Direct
kill -9 $(pgrep -f scanner_daemon)
```

---

## Disaster Recovery

### Scanner Crashed
**Systemd auto-restarts** (if enabled)

**Manual restart:**
```bash
sudo systemctl restart bitcoin-hunter
```

### Database Corrupted
```bash
# Stop scanner
sudo systemctl stop bitcoin-hunter

# Remove corrupted database
rm data/addresses.db

# Re-download and import
python3 download_blockchair.py
python3 import_db.py

# Restart scanner
sudo systemctl start bitcoin-hunter
```

### Logs Filling Disk
```bash
# Stop scanner
sudo systemctl stop bitcoin-hunter

# Clean old logs
cd ~/bitcoin-hunter/logs
rm *.log.*  # Remove rotated logs

# Truncate current logs
> stats.log
> errors.log

# Restart
sudo systemctl start bitcoin-hunter
```

---

## FAQ

**Q: Will this ever find a funded address?**
A: Statistically, no. You'd need to run for 10^30 years. This is educational.

**Q: Can I run multiple scanners?**
A: Yes, but they'll compete for CPU. Better to optimize single scanner.

**Q: Does it need internet?**
A: No, after database is downloaded, works fully offline.

**Q: How much electricity does this use?**
A: ~10-15W (Oracle ARM). On AWS/cloud, focus on CPU costs.

**Q: Should I update the address database?**
A: Monthly updates capture newly funded addresses. Not critical.

**Q: Can I run this on Raspberry Pi?**
A: Yes, but slower. Expect 100-300 keys/sec on Pi 4.

---

## Getting Help

**Check logs first:**
```bash
tail -100 logs/errors.log
sudo journalctl -u bitcoin-hunter -n 100
```

**Common issues covered in AUDIT.md**

**For bugs/features: GitHub issues**

---

## Summary

**For 24/7 autonomous operation:**
```bash
# One-time setup
cd ~/bitcoin-hunter
python3 download_blockchair.py  # Wait 1-2 hours
python3 import_db.py            # Wait 10-30 min
sudo cp bitcoin-hunter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bitcoin-hunter
sudo systemctl start bitcoin-hunter

# Monitor
sudo journalctl -u bitcoin-hunter -f

# Stop
sudo systemctl stop bitcoin-hunter
```

**For manual testing:**
```bash
python3 scanner.py  # Interactive version
```

✅ **scanner_daemon.py is production-ready for 24/7 operation!**
