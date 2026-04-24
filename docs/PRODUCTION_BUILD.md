# CasparCG Server Production Build Guide

This document provides comprehensive guidance for building CasparCG Server for production use cases, including best practices, optimizations, and deployment considerations.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Windows Production Build](#windows-production-build)
4. [Linux Production Build](#linux-production-build)
5. [Build Optimizations](#build-optimizations)
6. [Production Deployment](#production-deployment)
7. [Security Hardening](#security-hardening)
8. [Performance Tuning](#performance-tuning)
9. [Monitoring and Maintenance](#monitoring-and-maintenance)
10. [Troubleshooting](#troubleshooting)

---

## Overview

CasparCG Server is professional broadcast software used to play out graphics, audio, and video to multiple outputs. It has been in 24/7 broadcast production since 2006 and supports both Windows and Linux platforms.

### Key Production Considerations

- **Stability**: Use stable releases (v2.4.3 or later) rather than building from source when possible
- **Hardware**: Dedicated graphics hardware (GPU with OpenGL 4.5 support) is required
- **Reliability**: The software is designed for 24/7 operation in broadcast environments
- **Performance**: Proper build optimizations are critical for production workloads

---

## Prerequisites

### System Requirements

#### Windows
- **OS**: Windows 11 (recommended) or Windows 10 (best effort)
- **GPU**: Graphics card with OpenGL 4.5 support (NVIDIA recommended)
- **CPU**: Intel or AMD processors with AVX2 support (recommended)
- **PCIe**: Adequate bandwidth between GPU, CPU, and DeckLink cards

#### Linux
- **OS**: Ubuntu 22.04 LTS or 24.04 LTS (recommended)
- **GPU**: Graphics card with OpenGL 4.5 support (NVIDIA recommended)
- **CPU**: Intel or AMD processors with AVX2 support (recommended)
- **PCIe**: Adequate bandwidth between GPU, CPU, and DeckLink cards

### Build Tools

#### Windows
- Visual Studio 2022 (Community or Enterprise)
- 7-Zip (for packaging)
- CMake 3.16 or later
- Git

#### Linux
- CMake 3.16 or later
- Ninja build system
- GCC or Clang compiler
- Git
- All dependencies from `tools/linux/install-dependencies`

---

## Windows Production Build

### Automated Build Script

The recommended approach for production builds on Windows is to use the provided build script:

```batch
.\tools\windows\build.bat
```

This script:
1. Cleans previous build artifacts
2. Sets up Visual Studio 2022 environment
3. Configures CMake with Release configuration
4. Builds with MSBuild using all available processors
5. Packages the server into `dist/casparcg_server.zip`

### Manual Build Steps

For more control over the build process:

1. **Clone the repository**:
   ```batch
   git clone --single-branch --branch master https://github.com/CasparCG/server casparcg-server-master
   cd casparcg-server-master
   ```

2. **Set up Visual Studio environment**:
   ```batch
   "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" amd64
   ```

3. **Configure CMake**:
   ```batch
   mkdir build
   cd build
   cmake -G "Visual Studio 17 2022" -A x64 ..\src
   ```

4. **Build Release configuration**:
   ```batch
   msbuild "CasparCG Server.sln" /p:Configuration=Release /m:%NUMBER_OF_PROCESSORS%
   ```

5. **Package the build**:
   ```batch
   cd ..
   call tools\windows\package.bat .
   ```

### Windows Build Optimizations

The Windows build automatically applies these optimizations in Release mode:

- **Compiler flags**:
  - `/O2` - Maximum optimization
  - `/Oi` - Intrinsic functions
  - `/Ot` - Favor fast code
  - `/Gy` - Enable function-level linking
  - `/arch:AVX2` - AVX2 instruction set
  - `/fp:fast` - Fast floating-point model
  - `/MP` - Multi-processor compilation

- **Linker optimizations**:
  - Function-level linking for smaller binaries
  - Dead code elimination

---

## Linux Production Build

### Recommended: Development Build (For Production)

This is the recommended approach for production builds on Linux:

1. **Clone the repository**:
   ```bash
   git clone --single-branch --branch master https://github.com/CasparCG/server casparcg-server-master
   cd casparcg-server-master
   ```

2. **Install dependencies**:
   ```bash
   sudo ./tools/linux/install-dependencies
   ```

3. **Install CEF (recommended for HTML support)**:
   ```bash
   sudo add-apt-repository ppa:casparcg/ppa
   sudo apt-get update
   sudo apt-get install casparcg-cef-142-dev
   ```

4. **Configure and build**:
   ```bash
   mkdir build && cd build
   cmake ../src \
     -DCMAKE_BUILD_TYPE=Release \
     -DUSE_STATIC_BOOST=ON \
     -DUSE_SYSTEM_CEF=ON \
     -DENABLE_AVX2=ON \
     -DENABLE_HTML=ON
   cmake --build . --parallel $(nproc)
   cmake --install . --prefix staging
   ```

5. **Result**: The `staging` folder contains everything needed to run CasparCG Server.

### Alternative: Docker Build (Not Recommended for Production)

The Docker build is available but not recommended for production due to potential brittleness:

```bash
./tools/linux/build-in-docker
./tools/linux/extract-from-docker
```

**Note**: If you use Docker with sudo, you'll need to change ownership:
```bash
sudo chown -R $USER:$USER casparcg_server
```

### Linux Build Optimizations

The Linux build applies these optimizations:

- **Compiler flags**:
  - `-O3` - Maximum optimization
  - `-msse3`, `-mssse3`, `-msse4.1` - SSE instruction sets
  - `-mavx`, `-mavx2`, `-mfma` - AVX2 instruction sets (if enabled)
  - `-fopenmp-simd` - OpenMP SIMD support
  - `-fnon-call-exceptions` - Allow signal handlers to throw exceptions

- **Static linking** (optional):
  - `-DUSE_STATIC_BOOST=ON` - Statically link Boost libraries (recommended for production)

---

## Build Optimizations

### CMake Build Options

#### Essential Production Options

- **`-DCMAKE_BUILD_TYPE=Release`** (Linux) or `/p:Configuration=Release` (Windows)
  - Enables all optimizations
  - Removes debug symbols (use RelWithDebInfo if you need symbols)

- **`-DENABLE_AVX2=ON`** (Linux, default ON)
  - Enables AVX and AVX2 instruction sets
  - Requires CPU support (most modern CPUs)
  - Significantly improves performance

- **`-DUSE_STATIC_BOOST=ON`** (Linux only, default OFF)
  - Statically links Boost libraries
  - Reduces runtime dependencies
  - Recommended for production deployments

#### Optional Production Options

- **`-DUSE_SYSTEM_CEF=ON`** (Linux, default ON)
  - Uses system-installed CEF from PPA
  - Recommended for easier updates
  - Use `OFF` to bundle CEF (larger but self-contained)

- **`-DENABLE_HTML=ON`** (default ON)
  - Enables HTML template support
  - Requires CEF
  - Set to `OFF` if HTML support is not needed

- **`-DCASPARCG_BINARY_NAME=casparcg-server`** (Linux only)
  - Custom binary name
  - Useful for system package managers

- **`-DDIAG_FONT_PATH=/path/to/font.ttf`**
  - Specify font for diagnostic window
  - Use absolute path on Linux

### Dependency Caching

For offline builds or faster CI/CD:

1. **Set download cache**:
   ```bash
   cmake ../src -DCASPARCG_DOWNLOAD_CACHE=/path/to/cache
   ```

2. **Use internal mirror**:
   ```bash
   cmake ../src -DCASPARCG_DOWNLOAD_MIRROR=http://internal-mirror/
   ```

3. **Pre-seed cache**: Download dependencies from https://github.com/CasparCG/dependencies/releases and place in cache directory.

---

## Production Deployment

### File Structure

After building, your production deployment should include:

```
casparcg_server/
├── casparcg.exe (or casparcg on Linux)
├── scanner.exe (Windows) or scanner (Linux)
├── casparcg.config
├── casparcg_auto_restart.bat (Windows) or run.sh (Linux)
├── lib/ (Linux - shared libraries)
├── template/ (template files)
├── media/ (media files)
├── log/ (log files)
└── data/ (data files)
```

### Configuration

#### Essential Production Settings

Edit `casparcg.config` with these production considerations:

1. **Disable debug logging**:
   ```xml
   <log-level>info</log-level>
   ```

2. **Configure paths** (use absolute paths for production):
   ```xml
   <paths>
       <media-path>/opt/casparcg/media/</media-path>
       <log-path>/var/log/casparcg/</log-path>
       <data-path>/opt/casparcg/data/</data-path>
       <template-path>/opt/casparcg/template/</template-path>
   </paths>
   ```

3. **Set secure lock phrase**:
   ```xml
   <lock-clear-phrase>your-secure-phrase-here</lock-clear-phrase>
   ```

4. **Configure channels** for your hardware:
   - Match video modes to your DeckLink cards
   - Configure appropriate consumers (decklink, screen, etc.)

5. **Network settings**:
   ```xml
   <controllers>
       <tcp>
           <port>5250</port>
           <protocol>AMCP</protocol>
       </tcp>
   </controllers>
   ```

### Deployment Checklist

- [ ] Build with Release configuration
- [ ] Enable AVX2 optimizations (if CPU supports it)
- [ ] Use static Boost linking (Linux)
- [ ] Configure absolute paths in `casparcg.config`
- [ ] Set secure lock-clear-phrase
- [ ] Disable debug logging
- [ ] Test with production hardware (DeckLink cards, etc.)
- [ ] Verify all dependencies are included
- [ ] Set up auto-restart mechanism
- [ ] Configure log rotation
- [ ] Set up monitoring

---

## Security Hardening

### Network Security

1. **Firewall Configuration**:
   - Restrict AMCP port (default 5250) to trusted networks
   - Restrict LOG port (default 3250) to monitoring systems
   - Block unnecessary ports

2. **Access Control**:
   - Use strong lock-clear-phrase
   - Implement network-level access controls
   - Consider VPN for remote access

### File System Security

1. **Permissions** (Linux):
   ```bash
   # Create dedicated user
   sudo useradd -r -s /bin/false casparcg
   
   # Set ownership
   sudo chown -R casparcg:casparcg /opt/casparcg
   
   # Set permissions
   sudo chmod 750 /opt/casparcg
   sudo chmod 640 /opt/casparcg/casparcg.config
   ```

2. **Run as non-root**:
   - Never run CasparCG Server as root
   - Use dedicated user account
   - Grant minimal necessary permissions

### Application Security

1. **Disable unnecessary features**:
   - Set `ENABLE_HTML=OFF` if HTML templates are not needed
   - Disable Flash support if not required

2. **Log Management**:
   - Configure log rotation
   - Monitor logs for suspicious activity
   - Store logs securely

3. **Update Management**:
   - Keep CasparCG Server updated
   - Monitor security advisories
   - Test updates in staging before production

---

## Performance Tuning

### System-Level Optimizations

#### Linux

1. **CPU Governor**:
   ```bash
   # Set to performance mode
   sudo cpupower frequency-set -g performance
   ```

2. **IRQ Affinity**:
   - Pin DeckLink card IRQs to specific CPU cores
   - Avoid CPU 0 for critical interrupts

3. **I/O Scheduler**:
   ```bash
   # Use deadline or noop scheduler for SSDs
   echo deadline > /sys/block/sda/queue/scheduler
   ```

4. **Memory**:
   - Ensure adequate RAM (16GB+ recommended)
   - Configure swap appropriately
   - Use huge pages if needed

#### Windows

1. **Power Plan**: Set to "High Performance"
2. **Visual Effects**: Disable unnecessary visual effects
3. **Background Services**: Disable unnecessary services
4. **CPU Affinity**: Set process affinity if needed

### Application-Level Optimizations

1. **FFmpeg Threading**:
   ```xml
   <ffmpeg>
       <producer>
           <threads>4</threads>
       </producer>
   </ffmpeg>
   ```
   Adjust based on CPU cores and workload.

2. **Buffer Depths**:
   - DeckLink: `buffer-depth` (default 3)
   - Flash: `buffer-depth` (default auto)
   - Adjust based on latency requirements

3. **Video Mode Selection**:
   - Use native video modes when possible
   - Match channel and consumer video modes
   - Consider cadence settings for frame rates

4. **GPU Optimization**:
   - Ensure latest GPU drivers
   - Configure GPU power management
   - Monitor GPU temperature and utilization

### Hardware Considerations

1. **PCIe Configuration**:
   - Use CPU-attached PCIe slots (not chipset)
   - Ensure adequate PCIe bandwidth
   - Consider PCIe 3.0 x8 or better for DeckLink cards

2. **Storage**:
   - Use fast storage for media (SSD recommended)
   - Separate media storage from OS
   - Consider RAID for redundancy

3. **Network**:
   - Use dedicated network for control traffic
   - Consider 10GbE for high-bandwidth scenarios
   - Minimize network latency

---

## Monitoring and Maintenance

### Logging

1. **Log Levels**:
   - Production: `info` or `warning`
   - Debugging: `debug` or `trace` (temporary)

2. **Log Rotation**:
   - Configure system log rotation
   - Monitor log file sizes
   - Archive old logs

3. **Log Analysis**:
   - Monitor for errors and warnings
   - Track performance metrics
   - Set up alerts for critical errors

### Health Monitoring

1. **Process Monitoring**:
   - Monitor CasparCG Server process
   - Set up auto-restart on failure
   - Monitor resource usage (CPU, memory, GPU)

2. **Hardware Monitoring**:
   - GPU temperature and utilization
   - CPU temperature
   - Disk I/O and space
   - Network utilization

3. **Application Monitoring**:
   - Channel status
   - Frame drops
   - Audio/video sync
   - DeckLink card status

### Maintenance Schedule

1. **Regular Tasks**:
   - Review logs weekly
   - Check disk space
   - Update system packages (test first)
   - Verify backup integrity

2. **Periodic Tasks**:
   - Test failover procedures
   - Review and update configuration
   - Performance benchmarking
   - Security audit

---

## Troubleshooting

### Common Build Issues

1. **Missing Dependencies**:
   - Verify all dependencies are installed
   - Check CMake output for missing packages
   - Review `install-dependencies` script

2. **CEF Issues** (Linux):
   - Ensure CEF is installed from PPA
   - Check CEF version compatibility
   - Verify library paths

3. **AVX2 Errors**:
   - Verify CPU supports AVX2
   - Build with `-DENABLE_AVX2=OFF` if needed
   - Check CPU flags: `cat /proc/cpuinfo | grep avx2`

### Common Runtime Issues

1. **OpenGL Errors**:
   - Verify GPU drivers are installed
   - Check OpenGL version: `glxinfo | grep "OpenGL version"`
   - Ensure GPU supports OpenGL 4.5

2. **DeckLink Issues**:
   - Verify DeckLink drivers are installed
   - Check device enumeration
   - Verify PCIe slot and bandwidth

3. **Performance Issues**:
   - Check CPU/GPU utilization
   - Monitor frame drops
   - Review buffer depths
   - Verify video mode settings

### Getting Help

- **Documentation**: https://github.com/CasparCG/help/wiki
- **Forum**: https://casparcgforum.org/
- **GitHub Issues**: https://github.com/CasparCG/server/issues
- **Releases**: https://github.com/CasparCG/server/releases

---

## Best Practices Summary

### Build Best Practices

1. ✅ Always use Release configuration for production
2. ✅ Enable AVX2 if CPU supports it
3. ✅ Use static Boost linking on Linux
4. ✅ Test builds on staging hardware before production
5. ✅ Version control your build configuration
6. ✅ Document any custom build options

### Deployment Best Practices

1. ✅ Use absolute paths in configuration
2. ✅ Run as non-root user
3. ✅ Set up auto-restart mechanism
4. ✅ Configure log rotation
5. ✅ Implement monitoring and alerting
6. ✅ Test failover procedures
7. ✅ Keep backups of configuration

### Operational Best Practices

1. ✅ Monitor logs regularly
2. ✅ Keep system and drivers updated
3. ✅ Test updates in staging first
4. ✅ Document any custom configurations
5. ✅ Maintain hardware inventory
6. ✅ Plan for disaster recovery

---

## Additional Resources

- **Official Documentation**: https://github.com/CasparCG/help/wiki
- **Building Guide**: [BUILDING.md](../BUILDING.md)
- **Quick Start**: [QUICK_START.md](QUICK_START.md)
- **Changelog**: [CHANGELOG.md](../CHANGELOG.md)
- **Releases**: https://github.com/CasparCG/server/releases
- **Dependencies**: https://github.com/CasparCG/dependencies/releases

---

**Last Updated**: Based on CasparCG Server v2.5.0-dev and build system as of 2024

**Note**: This guide is based on the current build system and best practices. Always refer to the official documentation and release notes for the most up-to-date information.
