# Building the CasparCG Server

The CasparCG Server source code uses the CMake build system in order to easily
generate build systems for multiple platforms. CMake is basically a build
system for generating build systems.

On Windows we can use CMake to generate a .sln file and .vcproj files. On
Linux CMake can generate make files or ninja files. Qt Creator has support for
loading CMakeLists.txt files directly.

# Dependency caching

CMake will automatically download some dependencies as part of the build process.
These are taken from https://github.com/CasparCG/dependencies/releases (make sure to expand the 'Assets' group under each release to see the files), most of which are direct copies of distributions from upstream.

During the build, you can specify the CMake option `CASPARCG_DOWNLOAD_MIRROR` to download from an alternate HTTP server (such as an internally hosted mirror), or `CASPARCG_DOWNLOAD_CACHE` to use a specific path on disk for the local cache of these files, by default a folder called `external` will be created inside the build directory to cache these files.

If you want to be able to build CasparCG offline, you may need to manually seed this cache. You can do so by placing the correct tar.gz or zip into a folder and using `CASPARCG_DOWNLOAD_CACHE` to tell CMake where to find it.
You can figure out which files you need by looking at each of the `ExternalProject_Add` function calls inside of [Bootstrap_Linux.cmake](./src/CMakeModules/Bootstrap_Linux.cmake) or [Bootstrap_Windows.cmake](./src/CMakeModules/Bootstrap_Windows.cmake). Some of the ones listed are optional, depending on other CMake flags.

# Windows

## Building distributable

1. Install Visual Studio 2022.

2. Install 7-zip (https://www.7-zip.org/).

3. `git clone --single-branch --branch master https://github.com/CasparCG/server casparcg-server-master`

4. `cd casparcg-server-master`

5. `.\tools\windows\build.bat`

6. Copy the `dist\casparcg_server.zip` file for distribution

## Development using Visual Studio

1. Install Visual Studio 2022.

2. `git clone --single-branch --branch master https://github.com/CasparCG/server casparcg-server-master`

3. Open the cloned folder in Visual Studio.

4. Build All and ensure it builds successfully

# Linux

## Building on your system

We only officially support Ubuntu LTS releases, other distros may work but often run into build issues. We are happy to accept PRs to resolve these issues, but are unlikely to write fixes ourselves.

We currently document two approaches to building CasparCG. The recommended way is to use the `deb` packaging we have in the repository, but we only provide that for Ubuntu LTS releases.
Other deb based distros can work with some tweaks to one of those, other distros will need something else which is not documented here.

We also provide a script to produce a build in docker, but this is not recommended unless absolutely necessary. The resulting builds are often rather brittle depending on where they are used.

To perform a custom build, follow the Development steps below, and you may need to do some extra packaging steps, or install steps on the target systems.

### Building inside Docker

1. `git clone --single-branch --branch master https://github.com/CasparCG/server casparcg-server-master`
2. `cd casparcg-server-master`
3. `./tools/linux/build-in-docker`

If all goes to plan, a docker image `casparcg/server` has been created containing CasparCG Server.

### Extracting CasparCG Server from Docker

1. `./tools/linux/extract-from-docker`

You will then find a folder called `casparcg_server` which should contain everything you need to run CasparCG Server.

_Note: if you ran docker with sudo, CasparCG server will not be able to run without sudo out of the box. For security reasons we do not recommend to run CasparCG with sudo. Instead you can use chown to change the ownership of the CasparCG Server folder._

## Development

Before beginning, check the build options section below, to decide if you want to use any to simplify or customise your build.

1. `git clone --single-branch --branch master https://github.com/CasparCG/server casparcg-server-master`
2. `cd casparcg-server-master`
3. Install dependencies, this can be done with `sudo ./tools/linux/install-dependencies`
4. If using system CEF (default & recommended), `sudo add-apt-repository ppa:casparcg/ppa` and `sudo apt-get install casparcg-cef-142-dev`
5. `mkdir build && cd build`
6. `cmake ../src` You can add any of the build options from below to this command
7. `cmake --build . --parallel`
8. `cmake --install . --prefix staging`

If all goes to plan, a folder called 'staging' has been created with everything you need to run CasparCG server.

## Build options

-DENABLE_HTML=OFF - useful if you lack CEF, and would like to build without that module.

-DUSE_STATIC_BOOST=ON - (Linux only, default OFF) statically link against Boost.

-DUSE_SYSTEM_CEF=OFF - (Linux only, default ON) use the version of CEF from your OS. This expects to be using builds from https://launchpad.net/~casparcg/+archive/ubuntu/ppa

-DENABLE_AVX2=ON (Linux only, default ON) Enable the AVX and AVX2 instruction sets (requires a CPU that supports it)

-DDIAG_FONT_PATH - Specify an alternate path/font to use for the DIAG window. On linux, this will often want to be set to an absolute path of a font

-DCASPARCG_BINARY_NAME=casparcg-server - (Linux only) generate the executable with the specified name. This also reconfigures the install target to be a bit more friendly with system package managers.

## Troubleshooting: Segmentation fault when running (Linux with CEF)

If `./run.sh` or `bin/casparcg` exits immediately with **Segmentation fault (core dumped)**, the cause is almost always CEF (Chromium Embedded Framework) not being available or compatible.

- **Why it happens:** With `ENABLE_HTML=ON` (default), the HTML module is linked and CEF is invoked at the very start of `main()` via `CefExecuteProcess()`. If the CEF library is missing, wrong version, or incompatible (e.g. different ABI), or if the executable is run with a **relative** `argv[0]` (e.g. `bin/casparcg`), the process can segfault before any log output.

- **run.sh** is set up to launch the binary with an **absolute path** so CEF on Linux sees a proper executable path; always use `./run.sh` from the staging folder rather than calling `bin/casparcg` directly with a relative path.

**Fix A – Use system CEF (recommended):**

1. Add the CasparCG PPA and install the CEF package used by the build:
   ```bash
   sudo add-apt-repository ppa:casparcg/ppa
   sudo apt-get update
   sudo apt-get install casparcg-cef-142-dev
   ```
2. Rebuild and install:
   ```bash
   cd build
   cmake ../src
   cmake --build . --parallel
   cmake --install . --prefix staging
   ```
3. Run from the staging folder: `cd staging && ./run.sh`

**Fix B – Use bundled CEF (no PPA):**

1. Configure with system CEF disabled so CMake downloads and builds CEF:
   ```bash
   cd build
   cmake ../src -DUSE_SYSTEM_CEF=OFF
   cmake --build . --parallel
   cmake --install . --prefix staging
   ```
2. The first build will download CEF (large) and compile it; install will put CEF libraries and resources under `staging/lib/`. Run with: `cd staging && ./run.sh` (run.sh sets `LD_LIBRARY_PATH=lib` so the bundled CEF is found).

**If segfault persists after system CEF and run.sh:**

1. **Get a backtrace** to see where it crashes:
   ```bash
   cd staging
   LD_LIBRARY_PATH=lib gdb -batch -ex "run" -ex "bt full" -ex "x/i \$pc" -ex "info registers" -ex "quit" --args ./bin/casparcg
   ```
   Or interactively: `LD_LIBRARY_PATH=lib gdb --args ./bin/casparcg`, then in GDB: `run`, then after the segfault: `bt`, `x/i $pc`, `info registers`.

   If the crash is in `CefExecuteProcess` with `mov (%rdi),%rax` and `%rdi` holds an invalid address (e.g. `0x63ce...`), the cause is usually **Clang vs GCC ABI**: the system CEF package’s `libcef_dll_wrapper.a` is built with GCC; when CasparCG is built with Clang, the `scoped_refptr<CefApp>` is passed incorrectly and the wrapper dereferences a garbage pointer. **Fix: build CasparCG with GCC** (see step 3).

2. **Headless / no display:** On servers (e.g. GCP) without X11, CEF may still crash during early init. Try:
   ```bash
   DISPLAY=:0 ./run.sh   # if you have a display
   # or install xvfb and run: xvfb-run ./run.sh
   ```

3. **Compiler ABI (recommended if backtrace shows CefExecuteProcess + bad %rdi):** Build CasparCG with the same compiler used by the system CEF package (GCC):
   ```bash
   cd build
   rm -rf *   # clean so compiler change takes effect
   cmake ../src -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++
   cmake --build . --parallel
   cmake --install . --prefix staging
   cd staging && ./run.sh
   ```

**CEF log messages when running headless (no display):**

- **UPower / org.freedesktop.DBus** – CEF querying power/display over D-Bus. Harmless on headless (no UPower). Safe to ignore.
- **DEPRECATED_ENDPOINT** – Chromium’s GCM using a deprecated Google API. Harmless. Safe to ignore.
- **Unable to get gpu adapter** – When GPU is disabled, expected on headless. When GPU is enabled, see “Using GPU headless (NVIDIA)” below.
- **Stack smashing detected ***: terminated** – Serious: a CEF subprocess (e.g. GPU process) crashed. The code now passes `disable-gpu` to all CEF processes when GPU is disabled, which should avoid this on headless. If it still happens, run with `configuration.html.enable-gpu` set to `false` and rebuild; report the issue if it persists.

**Using GPU headless (e.g. NVIDIA):**

To use an NVIDIA GPU for CEF/HTML when there is no display (headless server):

- **Vulkan vs OpenGL:** CasparCG’s HTML templates use **WebGL (OpenGL)** as before. On headless Linux, Chromium/CEF cannot use OpenGL/EGL without an X11 display (it fails). So we use **Vulkan only as the low-level backend** for CEF to talk to the GPU when there is no display; WebGL in your templates still runs on the GPU via ANGLE. You do not need to change templates or “support Vulkan” in your app—only the system needs Vulkan libraries and the NVIDIA Vulkan driver.

1. **System:** Install NVIDIA driver (you have it) and Vulkan libraries + ICD so CEF can use the GPU:
   ```bash
   nvidia-smi   # confirm driver (you already have this)
   sudo apt install -y libvulkan1 vulkan-tools
   vulkaninfo --summary   # should list your NVIDIA GPU
   ```
   If `vulkaninfo` does not show an NVIDIA device, install the NVIDIA Vulkan ICD if needed (e.g. `libnvidia-gl-<version>` matching your driver; on many setups the driver already provides Vulkan).

2. **Config:** In `casparcg.config`, enable GPU for the HTML module:
   ```xml
   <html>
     <enable-gpu>true</enable-gpu>
     <angle-backend>vulkan</angle-backend>
     ...
   </html>
   ```

3. **Behaviour:** When `DISPLAY` is unset and `enable-gpu` is true, CasparCG passes `--use-angle=vulkan`, `--enable-features=Vulkan`, and `--disable-vulkan-surface` to CEF so it uses the GPU headless (per [Chromium server-side headless GPU docs](https://chromium.googlesource.com/chromium/src/+/main/docs/gpu/using-gpu-hardware-in-headless-chrome.md)). If you still see “Unable to get gpu adapter” or crashes, try `enable-gpu` false (software rendering) or ensure Vulkan works (`vulkaninfo --summary`).

**Build without CEF (no HTML module):**

To run CasparCG without the HTML/CEF module at all (e.g. to confirm the rest of the app works):

```bash
cmake ../src -DENABLE_HTML=OFF
```
Then build and install as above. The HTML producer will not be available.
