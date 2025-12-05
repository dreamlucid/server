#!/bin/bash
# Comprehensive CEF Build Verification Script for CasparCG Server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "CasparCG CEF Build Verification Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

check_pass() {
    echo -e "${GREEN}[✓]${NC} $1"
    PASSED=$((PASSED + 1))
}

check_fail() {
    echo -e "${RED}[✗]${NC} $1"
    FAILED=$((FAILED + 1))
}

check_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

echo "=== Step 1: CEF Package Installation ==="
echo ""

# Check if CEF packages are installed
if dpkg -l | grep -q "casparcg-cef-131"; then
    check_pass "CEF packages are installed"
    dpkg -l | grep "casparcg-cef-131" | while read line; do
        echo "  $line"
    done
else
    check_fail "CEF packages are NOT installed"
    echo "  Install with: sudo add-apt-repository ppa:casparcg/ppa && sudo apt-get install casparcg-cef-131-dev"
fi

echo ""
echo "=== Step 2: CEF Library Files ==="
echo ""

CEF_LIB_PATH="/usr/lib/casparcg-cef-131"
CEF_INCLUDE_PATH="/usr/include/casparcg-cef-131"

# Check library directory
if [ -d "$CEF_LIB_PATH" ]; then
    check_pass "CEF library directory exists: $CEF_LIB_PATH"
else
    check_fail "CEF library directory missing: $CEF_LIB_PATH"
fi

# Check include directory
if [ -d "$CEF_INCLUDE_PATH" ]; then
    check_pass "CEF include directory exists: $CEF_INCLUDE_PATH"
else
    check_fail "CEF include directory missing: $CEF_INCLUDE_PATH"
fi

# Check critical CEF files
CRITICAL_FILES=(
    "$CEF_LIB_PATH/libcef.so"
    "$CEF_LIB_PATH/libcef_dll_wrapper.a"
    "$CEF_LIB_PATH/chrome-sandbox"
    "$CEF_LIB_PATH/locales"
    "$CEF_LIB_PATH/chrome_100_percent.pak"
    "$CEF_LIB_PATH/chrome_200_percent.pak"
    "$CEF_LIB_PATH/icudtl.dat"
    "$CEF_LIB_PATH/resources.pak"
    "$CEF_LIB_PATH/snapshot_blob.bin"
    "$CEF_LIB_PATH/v8_context_snapshot.bin"
)

echo ""
echo "Checking critical CEF files:"
for file in "${CRITICAL_FILES[@]}"; do
    if [ -e "$file" ]; then
        if [ -f "$file" ]; then
            SIZE=$(stat -c%s "$file" 2>/dev/null || echo "0")
            check_pass "$(basename $file) exists ($(numfmt --to=iec-i --suffix=B $SIZE 2>/dev/null || echo $SIZE))"
        elif [ -d "$file" ]; then
            COUNT=$(find "$file" -type f 2>/dev/null | wc -l)
            check_pass "$(basename $file) directory exists ($COUNT files)"
        fi
    else
        check_fail "$(basename $file) is missing"
    fi
done

# Check libcef.so architecture
if [ -f "$CEF_LIB_PATH/libcef.so" ]; then
    ARCH=$(file "$CEF_LIB_PATH/libcef.so" | grep -o "x86-64" || echo "")
    if [ "$ARCH" = "x86-64" ]; then
        check_pass "libcef.so is 64-bit (x86-64)"
    else
        check_fail "libcef.so architecture mismatch (expected x86-64, got: $ARCH)"
    fi
fi

echo ""
echo "=== Step 3: Build Directory Structure ==="
echo ""

# Check if build directory exists
if [ -d "build" ]; then
    check_pass "Build directory exists"
else
    check_fail "Build directory missing - run cmake first"
fi

# Check if staging directory exists
if [ -d "build/staging" ]; then
    check_pass "Staging directory exists"
    
    # Check staging lib directory
    if [ -d "build/staging/lib" ]; then
        check_pass "Staging lib directory exists"
        
        # Count files in lib directory
        LIB_COUNT=$(find build/staging/lib -type f 2>/dev/null | wc -l)
        if [ "$LIB_COUNT" -gt 0 ]; then
            check_pass "Staging lib directory contains $LIB_COUNT files"
        else
            check_fail "Staging lib directory is empty - CEF resources not installed"
        fi
    else
        check_fail "Staging lib directory missing - CEF resources not installed"
    fi
    
    # Check binary
    if [ -f "build/staging/bin/casparcg" ]; then
        check_pass "Binary exists: build/staging/bin/casparcg"
        
        # Check if binary is executable
        if [ -x "build/staging/bin/casparcg" ]; then
            check_pass "Binary is executable"
        else
            check_fail "Binary is not executable"
        fi
        
        # Check binary architecture
        BIN_ARCH=$(file build/staging/bin/casparcg | grep -o "x86-64\|x86_64\|64-bit" || echo "")
        if [ -n "$BIN_ARCH" ]; then
            check_pass "Binary is 64-bit ($BIN_ARCH)"
        else
            check_fail "Binary architecture mismatch or unknown"
        fi
    else
        check_fail "Binary missing: build/staging/bin/casparcg"
    fi
else
    check_fail "Staging directory missing - run cmake --install"
fi

echo ""
echo "=== Step 4: Binary Linkage Analysis ==="
echo ""

if [ -f "build/staging/bin/casparcg" ]; then
    echo "Checking binary dependencies:"
    
    # Check if binary links to libcef.so
    if ldd build/staging/bin/casparcg 2>/dev/null | grep -q "libcef.so"; then
        check_pass "Binary links to libcef.so"
        CEF_LINK=$(ldd build/staging/bin/casparcg 2>/dev/null | grep "libcef.so")
        echo "  $CEF_LINK"
    else
        check_fail "Binary does NOT link to libcef.so"
    fi
    
    # Check for missing dependencies
    MISSING=$(ldd build/staging/bin/casparcg 2>/dev/null | grep "not found" || true)
    if [ -z "$MISSING" ]; then
        check_pass "All dynamic library dependencies are found"
    else
        check_fail "Missing dynamic library dependencies:"
        echo "$MISSING" | while read line; do
            echo "  $line"
        done
    fi
    
    # Check if libcef_dll_wrapper is statically linked
    if nm build/staging/bin/casparcg 2>/dev/null | grep -q "CefExecuteProcess\|CefInitialize"; then
        check_pass "Binary contains CEF wrapper symbols (libcef_dll_wrapper linked)"
    else
        check_warn "Could not verify libcef_dll_wrapper linkage (may need debug symbols)"
    fi
fi

echo ""
echo "=== Step 5: CMake Configuration Check ==="
echo ""

if [ -f "build/CMakeCache.txt" ]; then
    check_pass "CMakeCache.txt exists"
    
    # Check USE_SYSTEM_CEF setting
    if grep -q "USE_SYSTEM_CEF:BOOL=ON" build/CMakeCache.txt; then
        check_pass "USE_SYSTEM_CEF is ON"
    elif grep -q "USE_SYSTEM_CEF:BOOL=OFF" build/CMakeCache.txt; then
        check_fail "USE_SYSTEM_CEF is OFF (should be ON for system CEF)"
    else
        check_warn "USE_SYSTEM_CEF setting not found in CMakeCache.txt"
    fi
    
    # Check ENABLE_HTML setting
    if grep -q "ENABLE_HTML:BOOL=ON" build/CMakeCache.txt; then
        check_pass "ENABLE_HTML is ON"
    elif grep -q "ENABLE_HTML:BOOL=OFF" build/CMakeCache.txt; then
        check_fail "ENABLE_HTML is OFF (HTML module disabled)"
    fi
else
    check_fail "CMakeCache.txt missing - run cmake first"
fi

echo ""
echo "=== Step 6: Environment Setup ==="
echo ""

# Check LD_LIBRARY_PATH setup
if [ -d "build/staging/lib" ]; then
    echo "For running the binary, LD_LIBRARY_PATH should include:"
    echo "  1. build/staging/lib (for CEF resources)"
    echo "  2. /usr/lib/casparcg-cef-131 (for libcef.so)"
    echo ""
    echo "Recommended: export LD_LIBRARY_PATH=build/staging/lib:/usr/lib/casparcg-cef-131:\${LD_LIBRARY_PATH}"
    check_pass "Environment setup instructions provided"
fi

echo ""
echo "=== Step 7: CEF Resource Verification ==="
echo ""

if [ -d "build/staging/lib" ]; then
    # Check if critical CEF resources are in staging/lib
    STAGING_CRITICAL=(
        "build/staging/lib/locales"
        "build/staging/lib/chrome_100_percent.pak"
        "build/staging/lib/chrome_200_percent.pak"
        "build/staging/lib/icudtl.dat"
        "build/staging/lib/resources.pak"
        "build/staging/lib/snapshot_blob.bin"
        "build/staging/lib/v8_context_snapshot.bin"
    )
    
    echo "Checking CEF resources in staging/lib:"
    for file in "${STAGING_CRITICAL[@]}"; do
        if [ -e "$file" ]; then
            check_pass "$(basename $file) exists in staging/lib"
        else
            check_fail "$(basename $file) missing from staging/lib"
        fi
    done
fi

echo ""
echo "=== Summary ==="
echo ""
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. cd build/staging"
    echo "2. export LD_LIBRARY_PATH=lib:/usr/lib/casparcg-cef-131:\${LD_LIBRARY_PATH}"
    echo "3. ./run.sh"
    exit 0
else
    echo -e "${RED}Some checks failed. Please fix the issues above.${NC}"
    exit 1
fi

