# Uninstall Guide

## Clean Uninstall (Leaves No Junk)

Native Monitor is designed to be **completely removable** without leaving any residue.

### What Gets Stored

All data is stored in your browser's localStorage only:
- `native_monitor_onboarded` - First-time flag
- `native_monitor_refresh` - Refresh interval preference
- `native_monitor_name` - Custom system name
- `native_monitor_alert_cpu` - CPU alert threshold
- `native_monitor_alert_mem` - Memory alert threshold

### Uninstall Steps

1. **Stop the application:**
   ```bash
   # Press Ctrl+C in the terminal where app.py is running
   ```

2. **Remove files:**
   ```bash
   # Delete the entire directory
   cd ..
   rm -rf native-monitoring  # Linux/Mac
   rmdir /s native-monitoring  # Windows
   ```

3. **Clear browser data (optional):**
   - Open browser DevTools (F12)
   - Go to Application > Local Storage
   - Find entries starting with `native_monitor_`
   - Delete them manually, or they'll auto-expire

### What Does NOT Get Modified

✅ No system registry changes  
✅ No system service installations  
✅ No external network connections  
✅ No background processes remain  
✅ No user profile modifications  

### Verification

After uninstall, check that:
- No Python processes named `app.py` are running
- Port 5000 is freed (`netstat -ano | findstr :5000` on Windows)
- All files in `native-monitoring` directory are deleted

---

**That's it!** Clean and simple. No junk left behind.
