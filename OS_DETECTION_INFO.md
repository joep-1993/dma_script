# OS Detection Feature

## How It Works

The script now automatically detects which operating system it's running on and uses the appropriate Excel file path.

## Detection Logic

```python
def get_excel_path():
    windows_path = "c:/Users/JoepvanSchagen/Downloads/dma_script_ivor.xlsx"
    wsl_path = "/mnt/c/Users/JoepvanSchagen/Downloads/dma_script_ivor.xlsx"

    system = platform.system().lower()

    if system == "windows":
        # Running on native Windows (PyCharm on Windows)
        return windows_path
    elif system == "linux":
        # Check if running on WSL
        if os.path.exists("/proc/version"):
            with open("/proc/version", "r") as f:
                if "microsoft" in f.read().lower():
                    # Running on WSL
                    return wsl_path
        # Running on native Linux
        if os.path.exists(wsl_path):
            return wsl_path
        return windows_path
    else:
        # Default for other systems (macOS, etc.)
        return windows_path
```

## Supported Scenarios

### 1. Running on Windows (PyCharm on Windows)
- **Detected OS**: `Windows`
- **Path Used**: `c:/Users/JoepvanSchagen/Downloads/dma_script_ivor.xlsx`

### 2. Running on WSL (Windows Subsystem for Linux)
- **Detected OS**: `Linux` (with Microsoft in /proc/version)
- **Path Used**: `/mnt/c/Users/JoepvanSchagen/Downloads/dma_script_ivor.xlsx`

### 3. Running on Native Linux
- **Detected OS**: `Linux`
- **Path Used**: `/mnt/c/...` if accessible, otherwise falls back to Windows path

## Current Detection

When you run the script, it will show:
```
======================================================================
DMA SHOP CAMPAIGNS PROCESSOR
======================================================================
Operating System: Linux
Customer ID: 3800751597
Excel File: /mnt/c/Users/JoepvanSchagen/Downloads/dma_script_ivor.xlsx
======================================================================
```

## Customization

To use a different Excel file, update both paths in `campaign_processor.py`:

```python
# Around line 57-58
windows_path = "c:/Users/YourName/path/to/your/file.xlsx"
wsl_path = "/mnt/c/Users/YourName/path/to/your/file.xlsx"
```

## Testing

Test the OS detection without running the full script:

```bash
python3 << 'EOF'
import platform
print(f"Your OS: {platform.system()}")
EOF
```

## Benefits

- ✅ Works seamlessly on both Windows and WSL
- ✅ No manual path changes needed when switching environments
- ✅ Automatically selects the correct path format
- ✅ Falls back gracefully if paths don't exist
