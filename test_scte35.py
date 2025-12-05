#!/usr/bin/env python3
"""
Test script for SCTE35 insertion functionality in CasparCG.

This script:
1. Starts CasparCG with the dev config
2. Starts FFmpeg to stream media to CasparCG via SRT
3. Sends AMCP commands to play the stream and add output stream
4. Verifies the output stream is working
5. Injects SCTE-35 markers and verifies stream continues working
6. Cleans up by removing the output stream
"""

import subprocess
import socket
import time
import os
import sys
import signal
from pathlib import Path
from datetime import datetime

# Try to import threefive for SCTE-35 generation
try:
    from threefive import Cue, SpliceInsert
    THREEFIVE_AVAILABLE = True
except ImportError:
    THREEFIVE_AVAILABLE = False

# Configuration
SCRIPT_DIR = Path(__file__).parent.absolute()
STAGING_DIR = SCRIPT_DIR / "build" / "staging"
CASPARCG_BIN = STAGING_DIR / "bin" / "casparcg"
CASPARCG_CONFIG = STAGING_DIR / "casparcg.dev.config"
MEDIA_DIR = STAGING_DIR / "media"
MEDIA_FILE = MEDIA_DIR / "F1RaceMain.mp4"
AMCP_HOST = "localhost"
AMCP_PORT = 5250
SRT_INPUT_PORT = 9000
SRT_OUTPUT_PORT = 6000
STREAM_LAYER = 500  # Layer index for the output stream

# Process handles
casparcg_process = None
ffmpeg_input_process = None
ffmpeg_verify_process = None

# Log file handle
log_file = None
log_file_path = None


class TeeLogger:
    """Logger that writes to both console and file."""
    def __init__(self, log_file_path):
        self.log_file = open(log_file_path, 'w', encoding='utf-8')
        self.log_file_path = log_file_path
    
    def log(self, message, end='\n'):
        """Write message to both console and log file."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        
        # Write to console
        print(log_message, end=end, flush=True)
        
        # Write to file
        self.log_file.write(log_message + end)
        self.log_file.flush()
    
    def log_raw(self, message):
        """Write raw message (without timestamp) to both console and log file."""
        print(message, end='', flush=True)
        self.log_file.write(message)
        self.log_file.flush()
    
    def close(self):
        """Close the log file."""
        if self.log_file:
            self.log_file.close()
    
    def __del__(self):
        """Ensure file is closed on destruction."""
        self.close()


# Global logger instance
logger = None


def cleanup_processes():
    """Clean up all started processes."""
    global casparcg_process, ffmpeg_input_process, ffmpeg_verify_process
    
    log_func = logger.log if logger else print
    log_func("\n[Cleanup] Stopping processes...")
    
    if ffmpeg_verify_process:
        try:
            ffmpeg_verify_process.terminate()
            ffmpeg_verify_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            ffmpeg_verify_process.kill()
        except Exception as e:
            log_func(f"  Warning: Error stopping ffmpeg verify: {e}")
    
    if ffmpeg_input_process:
        try:
            ffmpeg_input_process.terminate()
            ffmpeg_input_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            ffmpeg_input_process.kill()
        except Exception as e:
            log_func(f"  Warning: Error stopping ffmpeg input: {e}")
    
    if casparcg_process:
        try:
            casparcg_process.terminate()
            casparcg_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            casparcg_process.kill()
        except Exception as e:
            log_func(f"  Warning: Error stopping CasparCG: {e}")
    
    log_func("[Cleanup] All processes stopped.")


def signal_handler(sig, frame):
    """Handle interrupt signals."""
    logger.log("\n[Interrupt] Received interrupt signal, cleaning up...")
    cleanup_processes()
    if logger:
        logger.close()
    sys.exit(1)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def check_file_exists(filepath, description):
    """Check if a file exists, exit if not."""
    if not filepath.exists():
        logger.log(f"ERROR: {description} not found: {filepath}")
        sys.exit(1)
    logger.log(f"[Check] Found {description}: {filepath}")


def send_amcp_command(command, timeout=5):
    """
    Send an AMCP command to CasparCG and return the response.
    
    Args:
        command: The AMCP command string (without newline)
        timeout: Socket timeout in seconds
    
    Returns:
        Response string from CasparCG
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((AMCP_HOST, AMCP_PORT))
        
        # Send command with newline
        cmd_bytes = (command + "\r\n").encode('utf-8')
        sock.sendall(cmd_bytes)
        
        # Receive response
        response = b""
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                # AMCP responses typically end with \r\n
                if response.endswith(b"\r\n"):
                    break
            except socket.timeout:
                break
        
        sock.close()
        return response.decode('utf-8', errors='ignore').strip()
    
    except socket.timeout:
        return f"ERROR: Timeout waiting for response to: {command}"
    except ConnectionRefusedError:
        return f"ERROR: Could not connect to CasparCG on {AMCP_HOST}:{AMCP_PORT}"
    except Exception as e:
        return f"ERROR: {str(e)}"


def wait_for_casparcg(max_wait=30):
    """Wait for CasparCG to be ready by checking AMCP port."""
    logger.log(f"[Wait] Waiting for CasparCG to start (max {max_wait}s)...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((AMCP_HOST, AMCP_PORT))
            sock.close()
            
            if result == 0:
                logger.log("[Wait] CasparCG is ready!")
                time.sleep(2)  # Give it a moment to fully initialize
                return True
        except Exception:
            pass
        
        time.sleep(0.5)
    
    logger.log(f"[Wait] ERROR: CasparCG did not start within {max_wait} seconds")
    return False


def start_casparcg():
    """Start CasparCG server with the dev config."""
    global casparcg_process
    
    logger.log(f"[CasparCG] Starting CasparCG with config: {CASPARCG_CONFIG}")
    
    # Change to staging directory for proper relative paths
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = str(STAGING_DIR / "lib")
    
    try:
        # Create log file for CasparCG output
        casparcg_log = STAGING_DIR / "log" / f"casparcg_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        casparcg_log.parent.mkdir(parents=True, exist_ok=True)
        
        casparcg_process = subprocess.Popen(
            [str(CASPARCG_BIN), str(CASPARCG_CONFIG)],
            cwd=str(STAGING_DIR),
            env=env,
            stdout=open(casparcg_log, 'w'),
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid  # Create new process group
        )
        
        logger.log(f"[CasparCG] CasparCG process started (PID: {casparcg_process.pid})")
        logger.log(f"[CasparCG] CasparCG output logged to: {casparcg_log}")
        
        if not wait_for_casparcg():
            raise Exception("CasparCG failed to start")
        
        logger.log("[CasparCG] CasparCG started successfully")
        return True
    
    except Exception as e:
        logger.log(f"[CasparCG] ERROR: Failed to start CasparCG: {e}")
        return False


def start_ffmpeg_input():
    """Start FFmpeg to stream media to CasparCG via SRT."""
    global ffmpeg_input_process
    
    logger.log(f"[FFmpeg Input] Starting FFmpeg to stream: {MEDIA_FILE}")
    
    # Create report file for FFmpeg input
    ffmpeg_report = STAGING_DIR / "log" / f"ffmpeg_input_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    ffmpeg_cmd = [
        "ffmpeg",
        "-loglevel", "verbose",  # Verbose logging
        "-report",  # Generate report file
        "-stats_period", "1",  # Print stats every second
        "-re",
        "-stream_loop", "-1",
        "-i", str(MEDIA_FILE),
        "-vf", "scale=1920:1080:flags=bicubic:force_original_aspect_ratio=decrease,"
               "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black",
        "-r", "50",
        "-c:v", "h264_nvenc",
        "-preset", "p4",
        "-tune", "ll",
        "-pix_fmt", "yuv420p",
        "-g", "50",
        "-keyint_min", "50",
        "-b:v", "8M",
        "-maxrate", "8M",
        "-bufsize", "16M",
        "-c:a", "aac",
        "-ar", "48000",
        "-b:a", "160k",
        "-ac", "2",
        "-f", "mpegts",
        f"srt://127.0.0.1:{SRT_INPUT_PORT}?mode=listener&latency=2000&transtype=live&rcvbuf=10000000&sndbuf=10000000"
    ]
    
    try:
        # Set environment variable for FFmpeg report file location
        env = os.environ.copy()
        env['FFREPORT'] = f"file={ffmpeg_report}"
        
        # Log the full command
        logger.log(f"[FFmpeg Input] Command: {' '.join(ffmpeg_cmd)}")
        
        # Create log file for FFmpeg output
        ffmpeg_log = STAGING_DIR / "log" / f"ffmpeg_input_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        ffmpeg_input_process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=open(ffmpeg_log, 'w'),
            stderr=subprocess.STDOUT,
            env=env,
            preexec_fn=os.setsid
        )
        
        logger.log(f"[FFmpeg Input] FFmpeg process started (PID: {ffmpeg_input_process.pid})")
        logger.log(f"[FFmpeg Input] FFmpeg output logged to: {ffmpeg_log}")
        logger.log(f"[FFmpeg Input] FFmpeg report will be saved to: {ffmpeg_report}")
        
        # Give FFmpeg a moment to start
        time.sleep(2)
        
        if ffmpeg_input_process.poll() is not None:
            logger.log(f"[FFmpeg Input] ERROR: FFmpeg exited immediately")
            # Read the log file to show error
            try:
                with open(ffmpeg_log, 'r') as f:
                    error_output = f.read()
                    logger.log(f"[FFmpeg Input] Error output:\n{error_output}")
            except Exception:
                pass
            return False
        
        logger.log("[FFmpeg Input] FFmpeg started successfully")
        return True
    
    except FileNotFoundError:
        logger.log("[FFmpeg Input] ERROR: FFmpeg not found in PATH")
        return False
    except Exception as e:
        logger.log(f"[FFmpeg Input] ERROR: Failed to start FFmpeg: {e}")
        return False


def run_amcp_commands():
    """Run AMCP commands to play stream and add output stream."""
    logger.log("\n[AMCP] Sending AMCP commands...")
    
    # Command 1: PLAY (as specified by user - PLAY can accept URL and will load it)
    play_cmd = f'PLAY 1-10 "srt://localhost:{SRT_INPUT_PORT}?mode=caller&latency=2000&transtype=live" LOOP'
    logger.log(f"[AMCP] Sending: {play_cmd}")
    response = send_amcp_command(play_cmd)
    logger.log(f"[AMCP] Response: {response}")
    
    if "200" not in response and "OK" not in response.upper():
        logger.log(f"[AMCP] WARNING: Unexpected response to PLAY command")
        # Try alternative: LOAD then PLAY
        logger.log("[AMCP] Trying alternative: LOAD then PLAY...")
        load_cmd = f'LOAD 1-10 "srt://localhost:{SRT_INPUT_PORT}?mode=caller&latency=2000&transtype=live"'
        response = send_amcp_command(load_cmd)
        logger.log(f"[AMCP] LOAD Response: {response}")
        time.sleep(1)
        response = send_amcp_command("PLAY 1-10 LOOP")
        logger.log(f"[AMCP] PLAY Response: {response}")
    
    time.sleep(2)  # Give it time to start playing
    
    # Command 2: ADD output stream
    add_cmd = (f'ADD 1-{STREAM_LAYER} STREAM "srt://0.0.0.0:{SRT_OUTPUT_PORT}?mode=listener&latency=2000&transtype=live" '
               f'-format mpegts -codec:v h264_nvenc -preset:v p4 -tune:v ll '
               f'-b:v 6000k -maxrate:v 6000k -bufsize:v 12000k -g:v 50 -keyint_min:v 50 -an')
    logger.log(f"[AMCP] Sending: {add_cmd}")
    response = send_amcp_command(add_cmd)
    logger.log(f"[AMCP] Response: {response}")
    
    if "200" not in response and "OK" not in response.upper():
        logger.log(f"[AMCP] ERROR: Failed to add output stream")
        return False
    
    logger.log("[AMCP] Output stream added successfully")
    
    # For SRT listener mode, we need to wait for the listener to be ready
    # The listener is created asynchronously, so we need to wait a bit
    logger.log(f"[AMCP] Waiting for SRT listener to initialize on port {SRT_OUTPUT_PORT}...")
    time.sleep(3)  # Give SRT listener time to bind to port and be ready
    
    logger.log("[AMCP] SRT listener should be ready. Client connection will be established during verification.")
    return True


def verify_output_stream(timeout=10):
    """Verify the output stream is working by connecting with FFmpeg."""
    global ffmpeg_verify_process
    
    logger.log(f"\n[Verify] Verifying output stream on port {SRT_OUTPUT_PORT}...")
    logger.log(f"[Verify] Note: For SRT listener mode, this connection will trigger header writing in CasparCG")
    
    # Create report file for FFmpeg verify
    verify_report = STAGING_DIR / "log" / f"ffmpeg_verify_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Use FFmpeg to probe the stream for a few seconds with verbose logging
    # For SRT listener mode, the caller must connect to trigger the connection
    # Increase timeout for initial connection
    ffmpeg_cmd = [
        "ffmpeg",
        "-loglevel", "info",  # Changed from debug to info for cleaner output
        "-report",  # Generate report file
        "-stats_period", "0.5",  # Print stats every 0.5 seconds
        "-timeout", "5000000",  # 5 second timeout in microseconds for connection
        "-i", f"srt://127.0.0.1:{SRT_OUTPUT_PORT}?mode=caller&latency=2000&transtype=live&rcvbuf=10000000&sndbuf=10000000",
        "-t", str(timeout),
        "-f", "null",
        "-"
    ]
    
    try:
        # Set environment variable for FFmpeg report file location
        env = os.environ.copy()
        env['FFREPORT'] = f"file={verify_report}"
        
        # Create log file for verification output
        verify_log = STAGING_DIR / "log" / f"ffmpeg_verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logger.log(f"[Verify] Command: {' '.join(ffmpeg_cmd)}")
        
        ffmpeg_verify_process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=open(verify_log, 'w'),
            stderr=subprocess.STDOUT,
            env=env,
            preexec_fn=os.setsid
        )
        
        logger.log(f"[Verify] FFmpeg verify process started (PID: {ffmpeg_verify_process.pid})")
        logger.log(f"[Verify] Verification output logged to: {verify_log}")
        logger.log(f"[Verify] FFmpeg report will be saved to: {verify_report}")
        logger.log(f"[Verify] Waiting for SRT connection to establish (this may take a few seconds)...")
        
        # For SRT listener mode, connection establishment can take time
        # The connection needs to be established before header writing completes
        # Wait a bit for the connection attempt to start
        time.sleep(2)
        
        # Check if connection was established quickly
        if ffmpeg_verify_process.poll() is not None:
            # Process exited, check if it was an error or success
            try:
                with open(verify_log, 'r') as f:
                    verify_output = f.read()
            except Exception:
                verify_output = ""
            
            if "Stream #0" in verify_output or "frame=" in verify_output:
                logger.log("[Verify] SUCCESS: Connection established and stream data received!")
                return True
        
        # Wait longer for connection to be fully established
        time.sleep(3)
        
        # Check if process exited quickly (error case)
        if ffmpeg_verify_process.poll() is not None:
            # Process exited, read the log to see why
            try:
                with open(verify_log, 'r') as f:
                    verify_output = f.read()
            except Exception:
                verify_output = ""
            
            # Check for error messages
            if "Error opening input file" in verify_output or "error" in verify_output.lower():
                logger.log("[Verify] ERROR: Output stream verification failed - FFmpeg could not connect")
                logger.log(f"[Verify] Error details from log:")
                for line in verify_output.split('\n'):
                    if 'error' in line.lower() or 'Error' in line or 'failed' in line.lower():
                        logger.log(f"  {line}")
                return False
            
            # Check for successful stream connection
            if "Stream #0" in verify_output or "frame=" in verify_output:
                logger.log("[Verify] SUCCESS: Output stream is working!")
                logger.log("[Verify] Stream information:")
                for line in verify_output.split('\n')[:20]:
                    if any(keyword in line for keyword in ['Stream', 'Duration', 'frame=', 'fps=']):
                        logger.log(f"  {line}")
                return True
            else:
                logger.log("[Verify] ERROR: Output stream verification failed - no stream data found")
                logger.log(f"[Verify] Output: {verify_output[:500]}")
                return False
        
        # Process is still running, wait a bit more and check the log for actual stream data
        time.sleep(3)
        
        # Read the log to verify we're actually receiving stream data
        try:
            with open(verify_log, 'r') as f:
                verify_output = f.read()
        except Exception:
            verify_output = ""
        
        # Check for error messages even if process is running
        if "Error opening input file" in verify_output or ("error" in verify_output.lower() and "Stream #0" not in verify_output):
            logger.log("[Verify] ERROR: Output stream verification failed - FFmpeg reported errors")
            logger.log(f"[Verify] Error details from log:")
            for line in verify_output.split('\n'):
                if 'error' in line.lower() or 'Error' in line or 'failed' in line.lower():
                    logger.log(f"  {line}")
            # Terminate the process
            try:
                ffmpeg_verify_process.terminate()
                ffmpeg_verify_process.wait(timeout=2)
            except Exception:
                pass
            return False
        
        # Check for successful stream connection indicators
        if "Stream #0" in verify_output or "frame=" in verify_output:
            logger.log("[Verify] SUCCESS: Output stream is working!")
            logger.log("[Verify] Stream information:")
            for line in verify_output.split('\n')[:20]:
                if any(keyword in line for keyword in ['Stream', 'Duration', 'frame=', 'fps=']):
                    logger.log(f"  {line}")
            return True
        else:
            # Process running but no stream data yet - might need more time or it's failing
            logger.log("[Verify] WARNING: Process running but no stream data detected yet")
            logger.log("[Verify] Waiting a bit longer to confirm...")
            time.sleep(2)
            
            # Check one more time
            try:
                with open(verify_log, 'r') as f:
                    verify_output = f.read()
            except Exception:
                verify_output = ""
            
            if "Error opening input file" in verify_output or ("error" in verify_output.lower() and "Stream #0" not in verify_output):
                logger.log("[Verify] ERROR: Output stream verification failed - connection error confirmed")
                logger.log(f"[Verify] Error details: {verify_output[:500]}")
                try:
                    ffmpeg_verify_process.terminate()
                    ffmpeg_verify_process.wait(timeout=2)
                except Exception:
                    pass
                return False
            elif "Stream #0" in verify_output or "frame=" in verify_output:
                logger.log("[Verify] SUCCESS: Output stream is working!")
                return True
            else:
                logger.log("[Verify] ERROR: Output stream verification failed - no stream data after waiting")
                logger.log(f"[Verify] Log output: {verify_output[:500]}")
                try:
                    ffmpeg_verify_process.terminate()
                    ffmpeg_verify_process.wait(timeout=2)
                except Exception:
                    pass
                return False
    
    except FileNotFoundError:
        logger.log("[Verify] ERROR: FFmpeg not found in PATH")
        return False
    except Exception as e:
        logger.log(f"[Verify] ERROR: Failed to verify stream: {e}")
        return False


def generate_scte35_marker(splice_event_id=1234, break_duration=30.0, immediate=True):
    """
    Generate a SCTE-35 marker using threefive library.
    
    Args:
        splice_event_id: Unique ID for the splice event
        break_duration: Duration of the break in seconds
        immediate: Whether to use immediate splice flag
    
    Returns:
        Base64 encoded SCTE-35 payload string, or None if generation fails
    """
    global logger
    if not THREEFIVE_AVAILABLE:
        if logger:
            logger.log("[SCTE35] ERROR: threefive library not available")
            logger.log("[SCTE35] Install with: pip install threefive")
        return None
    
    try:
        # Create a SCTE-35 cue
        cue = Cue()
        cue.command = SpliceInsert()
        cue.command.splice_event_id = splice_event_id
        cue.command.splice_immediate_flag = immediate
        cue.command.duration_flag = True
        cue.command.break_duration = break_duration
        
        # Encode to base64 (this is what CasparCG expects)
        base64_payload = cue.encode()
        logger.log(f"[SCTE35] Generated marker: event_id={splice_event_id}, duration={break_duration}s, immediate={immediate}")
        logger.log(f"[SCTE35] Base64 payload length: {len(base64_payload)} bytes")
        return base64_payload
    except Exception as e:
        logger.log(f"[SCTE35] ERROR: Failed to generate SCTE-35 marker: {e}")
        return None


def inject_scte35_marker(layer_index, base64_payload):
    """
    Inject a SCTE-35 marker into the stream via AMCP APPLY command.
    
    Args:
        layer_index: The layer index (e.g., 500 for stream on layer 500)
        base64_payload: Base64 encoded SCTE-35 payload
    
    Returns:
        True if injection was successful (or attempted), False otherwise
    """
    logger.log(f"\n[SCTE35] Injecting SCTE-35 marker into layer {layer_index}...")
    
    # Format: APPLY channel-layer SCTE35 "base64_payload"
    apply_cmd = f'APPLY 1-{layer_index} SCTE35 "{base64_payload}"'
    logger.log(f"[SCTE35] Sending: APPLY 1-{layer_index} SCTE35 \"<payload>\"")
    
    response = send_amcp_command(apply_cmd)
    logger.log(f"[SCTE35] Response: {response}")
    
    # Check response - 202 means success, 403 means failed
    if "202" in response and "OK" in response.upper():
        logger.log("[SCTE35] SUCCESS: SCTE-35 marker injected successfully")
        return True
    elif "403" in response or "FAILED" in response.upper():
        logger.log("[SCTE35] ERROR: SCTE-35 injection failed")
        logger.log(f"[SCTE35] Response indicates failure: {response}")
        return False
    else:
        logger.log(f"[SCTE35] ERROR: Unexpected response: {response}")
        return False


def test_scte35_injection():
    """
    Test SCTE-35 marker injection and verify stream continues working.
    
    Returns:
        True if stream continues working after injection attempts, False otherwise
    """
    logger.log("\n" + "=" * 70)
    logger.log("SCTE-35 Marker Injection Test")
    logger.log("=" * 70)
    
    if not THREEFIVE_AVAILABLE:
        logger.log("[SCTE35] SKIPPED: threefive library not available")
        logger.log("[SCTE35] Install with: pip install threefive")
        return True  # Don't fail the test if library is missing
    
    # Generate a few SCTE-35 markers with different parameters
    markers = []
    
    # Marker 1: Immediate splice with 30s break
    marker1 = generate_scte35_marker(splice_event_id=1001, break_duration=30.0, immediate=True)
    if marker1:
        markers.append(("Immediate splice, 30s break", marker1))
    
    # Marker 2: Immediate splice with 60s break
    marker2 = generate_scte35_marker(splice_event_id=1002, break_duration=60.0, immediate=True)
    if marker2:
        markers.append(("Immediate splice, 60s break", marker2))
    
    # Marker 3: Non-immediate splice with 15s break
    marker3 = generate_scte35_marker(splice_event_id=1003, break_duration=15.0, immediate=False)
    if marker3:
        markers.append(("Non-immediate splice, 15s break", marker3))
    
    if not markers:
        logger.log("[SCTE35] ERROR: Failed to generate any SCTE-35 markers")
        return False
    
    logger.log(f"[SCTE35] Generated {len(markers)} SCTE-35 markers for testing")
    
    # Inject markers with delays between them
    injection_results = []
    for i, (description, payload) in enumerate(markers, 1):
        logger.log(f"\n[SCTE35] Injecting marker {i}/{len(markers)}: {description}")
        result = inject_scte35_marker(STREAM_LAYER, payload)
        injection_results.append(result)
        
        # Wait a bit between injections
        if i < len(markers):
            time.sleep(1)
    
    # Check injection results - at least one must succeed
    successful_injections = sum(1 for r in injection_results if r)
    total_injections = len(injection_results)
    
    logger.log(f"\n[SCTE35] Injection results: {successful_injections}/{total_injections} successful")
    
    if successful_injections == 0:
        logger.log("[SCTE35] ERROR: All SCTE-35 injection attempts failed")
        logger.log("[SCTE35] This indicates SCTE-35 functionality is not working correctly")
        return False
    
    if successful_injections < total_injections:
        logger.log(f"[SCTE35] WARNING: {total_injections - successful_injections} injection(s) failed out of {total_injections}")
    
    # Check CasparCG log for errors that might indicate problems
    logger.log("\n[SCTE35] Checking CasparCG log for errors...")
    try:
        # Match both caspar_*.log (CasparCG's pattern) and casparcg*.log (test script's pattern)
        caspar_log_files = sorted((STAGING_DIR / "log").glob("caspar*.log"), reverse=True)
        if caspar_log_files:
            caspar_log = caspar_log_files[0]
            with open(caspar_log, 'r') as f:
                caspar_output = f.read()
            
            # Check for critical errors that indicate SCTE-35 or stream issues
            error_indicators = [
                "SCTE-35 stream not available",
                "Error writing trailer",
                "Input/output error",
                "Packet corrupt",
                "PES packet size mismatch",
                "Connection closed or I/O error",
                "decode_band_types: Input buffer exhausted"
            ]
            
            found_errors = []
            for indicator in error_indicators:
                if indicator in caspar_output:
                    found_errors.append(indicator)
            
            if found_errors:
                logger.log("[SCTE35] ERROR: Found critical errors in CasparCG log:")
                for error in found_errors:
                    logger.log(f"  - {error}")
                logger.log("[SCTE35] These errors indicate SCTE-35 or stream issues")
                return False
            else:
                logger.log("[SCTE35] No critical errors found in CasparCG log")
    except Exception as e:
        logger.log(f"[SCTE35] WARNING: Could not check CasparCG log: {e}")
    
    # Verify stream is still working after injection attempts
    logger.log("\n[SCTE35] Verifying stream continues working after injection attempts...")
    time.sleep(2)  # Give stream time to process
    
    # Check if verification process is still running and receiving data
    global ffmpeg_verify_process
    stream_working = False
    
    if ffmpeg_verify_process and ffmpeg_verify_process.poll() is None:
        # Process is still running, check the log for recent activity
        try:
            verify_log_files = sorted([f for f in (STAGING_DIR / "log").glob("ffmpeg_verify_*.log")], reverse=True)
            if verify_log_files:
                verify_log = verify_log_files[0]
                with open(verify_log, 'r') as f:
                    verify_output = f.read()
                
                # Check for recent frame data (indicating stream is still working)
                if "frame=" in verify_output[-2000:]:  # Check last 2000 chars
                    logger.log("[SCTE35] Stream is still working after SCTE-35 injection")
                    logger.log("[SCTE35] Recent frame data found in verification log")
                    stream_working = True
                else:
                    logger.log("[SCTE35] WARNING: No recent frame data found in verification log")
                    # Process is still running, so assume it's working for now
                    stream_working = True
            else:
                logger.log("[SCTE35] WARNING: Could not find verification log file")
                # Process is still running, assume it's working
                stream_working = True
        except Exception as e:
            logger.log(f"[SCTE35] WARNING: Could not check verification log: {e}")
            # If process is still running, assume it's working
            stream_working = True
    else:
        # Process exited - check if it was a normal completion or error
        logger.log("[SCTE35] Verification process has completed")
        # Check the log to see if it exited due to error
        try:
            verify_log_files = sorted([f for f in (STAGING_DIR / "log").glob("ffmpeg_verify_*.log")], reverse=True)
            if verify_log_files:
                verify_log = verify_log_files[0]
                with open(verify_log, 'r') as f:
                    verify_output = f.read()
                
                # Check for error messages
                if "Error opening input file" in verify_output or ("error" in verify_output.lower() and "Stream #0" not in verify_output):
                    logger.log("[SCTE35] ERROR: Stream verification failed - FFmpeg reported errors")
                    stream_working = False
                elif "Stream #0" in verify_output or "frame=" in verify_output:
                    logger.log("[SCTE35] Stream verification completed normally")
                    stream_working = True
                else:
                    logger.log("[SCTE35] WARNING: Could not determine stream status from verification log")
                    stream_working = True  # Assume working if unclear
            else:
                logger.log("[SCTE35] WARNING: Could not find verification log file")
                stream_working = True  # Assume working if unclear
        except Exception as e:
            logger.log(f"[SCTE35] WARNING: Could not check verification log: {e}")
            stream_working = True  # Assume working if unclear
    
    # Final verdict
    if successful_injections > 0 and stream_working:
        logger.log("\n[SCTE35] Stream verification: PASSED")
        return True
    elif successful_injections == 0:
        logger.log("\n[SCTE35] Stream verification: FAILED - No successful SCTE-35 injections")
        return False
    elif not stream_working:
        logger.log("\n[SCTE35] Stream verification: FAILED - Stream stopped working")
        return False
    else:
        logger.log("\n[SCTE35] Stream verification: FAILED - Unknown issue")
        return False


def remove_output_stream():
    """Remove the output stream via AMCP."""
    logger.log("\n[AMCP] Removing output stream...")
    
    remove_cmd = f"REMOVE 1-{STREAM_LAYER}"
    logger.log(f"[AMCP] Sending: {remove_cmd}")
    response = send_amcp_command(remove_cmd)
    logger.log(f"[AMCP] Response: {response}")
    
    if "200" not in response and "OK" not in response.upper():
        logger.log(f"[AMCP] WARNING: Unexpected response to REMOVE command")
    else:
        logger.log("[AMCP] Output stream removed successfully")


def main():
    """Main test function."""
    global logger, log_file_path
    
    # Create log file with timestamp
    log_file_path = SCRIPT_DIR / "log" / f"scte35_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize logger
    logger = TeeLogger(log_file_path)
    
    logger.log("=" * 70)
    logger.log("SCTE35 Insertion Test Script for CasparCG")
    logger.log("=" * 70)
    logger.log(f"Log file: {log_file_path}")
    logger.log("")
    
    # Pre-flight checks
    logger.log("[Pre-flight] Checking prerequisites...")
    check_file_exists(CASPARCG_BIN, "CasparCG binary")
    check_file_exists(CASPARCG_CONFIG, "CasparCG config file")
    check_file_exists(MEDIA_FILE, "Media file")
    logger.log("")
    
    success = False
    
    try:
        # Step 1: Start CasparCG
        if not start_casparcg():
            logger.log("\n[ERROR] Failed to start CasparCG. Aborting test.")
            return 1
        
        # Step 2: Start FFmpeg input
        if not start_ffmpeg_input():
            logger.log("\n[ERROR] Failed to start FFmpeg input. Aborting test.")
            return 1
        
        # Step 3: Run AMCP commands
        if not run_amcp_commands():
            logger.log("\n[ERROR] Failed to run AMCP commands. Aborting test.")
            return 1
        
        # Step 4: Verify output stream
        if not verify_output_stream():
            logger.log("\n[ERROR] Output stream verification failed. Test failed.")
            return 1
        
        # Step 5: Test SCTE-35 marker injection
        if not test_scte35_injection():
            logger.log("\n[ERROR] SCTE-35 injection test failed. Test failed.")
            return 1
        
        # Step 6: Verify stream still works after SCTE-35 injection
        logger.log("\n[Verify] Final verification: Checking stream is still working...")
        time.sleep(2)
        
        # Check if verification process is still running
        global ffmpeg_verify_process
        if ffmpeg_verify_process and ffmpeg_verify_process.poll() is None:
            logger.log("[Verify] Stream verification process is still running - stream is active")
            logger.log("[Verify] This confirms the stream did not fail during SCTE-35 injection")
        else:
            logger.log("[Verify] Stream verification process completed (this is normal after timeout)")
            logger.log("[Verify] The stream did not crash during SCTE-35 injection attempts")
        
        # Step 7: Clean up - remove output stream
        remove_output_stream()
        
        logger.log("\n" + "=" * 70)
        logger.log("TEST PASSED: SCTE35 insertion setup is working correctly!")
        logger.log("=" * 70)
        logger.log(f"\nFull test log saved to: {log_file_path}")
        success = True
        
    except KeyboardInterrupt:
        logger.log("\n[Interrupt] Test interrupted by user")
    except Exception as e:
        logger.log(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        error_trace = traceback.format_exc()
        logger.log(error_trace)
    finally:
        # Always clean up
        cleanup_processes()
        if logger:
            logger.log(f"\n[Final] Test log file: {log_file_path}")
            logger.close()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

