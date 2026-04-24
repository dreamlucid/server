# Quick Start Guide - CasparCG SRT Development Setup

## Overview

This setup provides a complete testing environment for CasparCG with SRT streaming:

```
MP4 File → FFmpeg → SRT Input → CasparCG → SRT Outputs (Monitoring + Consumption)
```

## Quick Start

### Option 1: All-in-One Setup

Start everything with one command:

```bash
./start_dev_setup.sh media/F1RaceMain.mp4 9000
```

This will:
1. Start CasparCG with dev config
2. Start FFmpeg sending MP4 to SRT input
3. Load SRT stream into CasparCG via AMCP

### Option 2: Manual Setup

1. **Start CasparCG:**
   ```bash
   ./bin/casparcg casparcg.dev.config
   ```

2. **Send MP4 to SRT input:**
   ```bash
   ./send_mp4_to_srt.sh media/F1RaceMain.mp4 localhost 9000
   ```

3. **Load SRT stream into CasparCG:**
   ```bash
   ./load_srt_input.sh srt://localhost:9000?mode=caller 1 1
   ```

## Connect to Outputs

### Monitoring Output (Port 9001)

```bash
# Using FFplay
ffplay "srt://localhost:9001?mode=caller"

# Using VLC
vlc "srt://localhost:9001?mode=caller"
```

### Consumption Output (Port 9002)

```bash
# Using FFplay
ffplay "srt://localhost:9002?mode=caller"

# Using VLC
vlc "srt://localhost:9002?mode=caller"
```

## Ports

- **5250**: AMCP control port
- **8000**: Media server port
- **9000**: SRT input port (FFmpeg sends here)
- **9001**: SRT monitoring output (listener mode)
- **9002**: SRT consumption output (listener mode)

## AMCP Commands

Connect to AMCP:
```bash
nc localhost 5250
```

Common commands:
```
LOAD 1-1 "srt://localhost:9000?mode=caller"
PLAY 1-1
PAUSE 1-1
STOP 1-1
INFO 1
INFO 1-1
```

## Troubleshooting

- **Check if ports are listening:**
  ```bash
  ./test_srt_connection.sh
  ```

- **Check CasparCG logs:**
  ```bash
  tail -f log/caspar_*.log
  ```

- **Verify config:**
  ```bash
  cat casparcg.dev.config
  ```

## Files

- `casparcg.dev.config` - Development configuration
- `start_dev_setup.sh` - All-in-one startup script
- `send_mp4_to_srt.sh` - Send MP4 to SRT input
- `load_srt_input.sh` - Load SRT stream via AMCP
- `test_srt_connection.sh` - Test SRT connections
- [DEV_SETUP.md](DEV_SETUP.md) — full documentation

