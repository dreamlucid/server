# CasparCG Development/Testing Setup

This setup provides a complete testing and development environment for CasparCG with SRT streaming support.

## Overview

The setup implements the following flow:

```
Input SRT → CasparCG + FFmpeg + Graphics → SRT (monitoring + consumption)
```

### Components

1. **CasparCG** - Main playout server configured for 1080p50
2. **FFmpeg Producer** - Accepts SRT input stream (listener mode)
3. **FFmpeg Consumer (Monitoring)** - Outputs to SRT for monitoring (port 9001)
4. **FFmpeg Consumer (Consumption)** - Outputs to SRT for production use (port 9002)

## Configuration

### Main Config File: `casparcg.dev.config`

- **Video Mode**: `1080p5000` (1080p50, 50fps)
- **SRT Input**: Listener mode on port 9000 (configured via AMCP commands)
- **SRT Output (Monitoring)**: Listener mode on port 9001
- **SRT Output (Consumption)**: Listener mode on port 9002

## Usage

### Quick Start

1. **Start the complete setup** (CasparCG + FFmpeg input):
   ```bash
   ./start_dev_setup.sh [input_file.mp4] [srt_input_port]
   ```

   Example:
   ```bash
   ./start_dev_setup.sh media/F1RaceMain.mp4 9000
   ```

2. **Or start components separately**:

   a. Start CasparCG:
   ```bash
   ./bin/casparcg casparcg.dev.config
   ```

   b. Send MP4 file to SRT input:
   ```bash
   ./send_mp4_to_srt.sh media/F1RaceMain.mp4 localhost 9000
   ```

### Loading SRT Input into CasparCG

Once CasparCG is running and the SRT stream is available, load it into channel 1, layer 1 using AMCP:

```bash
# Connect to CasparCG AMCP (port 5250)
telnet localhost 5250

# Or use netcat
nc localhost 5250

# Load the SRT stream
LOAD 1-1 "srt://localhost:9000?mode=caller"
PLAY 1-1
```

### Connecting to SRT Outputs

#### Monitoring Output (Port 9001)

Connect to the monitoring SRT stream:

```bash
# Using FFplay
ffplay "srt://localhost:9001?mode=caller"

# Using FFmpeg to record
ffmpeg -i "srt://localhost:9001?mode=caller" -c copy monitoring_output.ts

# Using VLC
vlc "srt://localhost:9001?mode=caller"
```

#### Consumption Output (Port 9002)

Connect to the production SRT stream:

```bash
# Using FFplay
ffplay "srt://localhost:9002?mode=caller"

# Using FFmpeg to record
ffmpeg -i "srt://localhost:9002?mode=caller" -c copy production_output.ts

# Using VLC
vlc "srt://localhost:9002?mode=caller"
```

## AMCP Commands Reference

Common AMCP commands for testing:

```bash
# Load SRT input stream
LOAD 1-1 "srt://localhost:9000?mode=caller"

# Play loaded content
PLAY 1-1

# Pause
PAUSE 1-1

# Resume
RESUME 1-1

# Stop
STOP 1-1

# Clear
CLEAR 1-1

# Get channel info
INFO 1

# Get layer info
INFO 1-1
```

## Port Configuration

Default ports used in this setup:

- **5250**: CasparCG AMCP control port
- **8000**: CasparCG media server port
- **9000**: SRT input port (for receiving input stream)
- **9001**: SRT monitoring output port (listener mode)
- **9002**: SRT consumption output port (listener mode)

## SRT Listener Mode

Both output consumers are configured in **listener mode**, which means:

- CasparCG listens on the specified ports (9001, 9002)
- External clients connect to these ports using **caller mode**
- Multiple clients can connect to the same listener (for monitoring)

### Example: Connecting Multiple Monitoring Clients

```bash
# Terminal 1
ffplay "srt://localhost:9001?mode=caller"

# Terminal 2 (another monitoring client)
ffplay "srt://localhost:9001?mode=caller"
```

## Troubleshooting

### CasparCG won't start

- Check if ports 5250, 8000, 9001, 9002 are available
- Verify the config file syntax: `xmllint --noout casparcg.dev.config`
- Check logs in `log/` directory

### SRT stream not connecting

- Verify FFmpeg is sending to the correct port
- Check firewall settings
- Ensure SRT URL format is correct: `srt://host:port?mode=caller`

### Video quality issues

- Adjust bitrate in `casparcg.dev.config` consumer args
- Modify FFmpeg encoding parameters in `send_mp4_to_srt.sh`
- Check network bandwidth

### Audio sync issues

- Adjust SRT latency: `?mode=caller&latency=0`
- Check audio codec settings (AAC, 48kHz recommended)

## Advanced Configuration

### Customizing Video Encoding

Edit `casparcg.dev.config` to modify consumer encoding:

```xml
<ffmpeg>
    <path>srt://0.0.0.0:9001?mode=listener</path>
    <args>-c:v libx264 -preset veryfast -tune zerolatency -g 50 -keyint_min 50 -b:v 5M -maxrate 5M -bufsize 10M -c:a aac -b:a 128k -ar 48000 -f mpegts</args>
</ffmpeg>
```

### Customizing Input Stream

Edit `send_mp4_to_srt.sh` to modify input encoding parameters.

### Adding More Consumers

Add additional `<ffmpeg>` blocks in the `<consumers>` section of `casparcg.dev.config`.

## Network Configuration

For remote access, modify the SRT URLs:

- **Input**: Change `localhost` to the server's IP address
- **Outputs**: Change `0.0.0.0` to specific IP or keep `0.0.0.0` to listen on all interfaces

Example for remote access:
```xml
<path>srt://192.168.1.100:9001?mode=listener</path>
```

## Testing Checklist

- [ ] CasparCG starts successfully
- [ ] FFmpeg input stream connects
- [ ] SRT input loads into CasparCG via AMCP
- [ ] Monitoring output (9001) is accessible
- [ ] Consumption output (9002) is accessible
- [ ] Video quality is acceptable
- [ ] Audio is in sync
- [ ] Multiple monitoring clients can connect simultaneously

## Notes

- The setup uses **listener mode** for outputs, allowing multiple clients to connect
- Input uses **caller mode** (FFmpeg connects to CasparCG)
- All SRT streams use MPEG-TS container format
- Video encoding uses H.264 with low-latency settings
- Audio encoding uses AAC at 128kbps (monitoring) and 192kbps (consumption)

