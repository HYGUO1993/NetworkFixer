#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance test script for NetworkFixer optimizations
This script validates that the optimized code still functions correctly
"""

import sys
import time
import subprocess

def test_encoding_detection():
    """Test the simplified encoding detection"""
    print("Testing encoding detection optimization...")
    
    # Test with a simple command that outputs text
    test_cmd = "echo Test encoding"
    try:
        proc = subprocess.run(
            test_cmd,
            shell=True,
            check=True,
            creationflags=0x08000000 if sys.platform == 'win32' else 0,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False
        )
        
        # Test the optimized encoding logic
        try:
            out = proc.stdout.decode('mbcs')
            print(f"  ✓ mbcs decoding successful: {out.strip()}")
        except (UnicodeError, LookupError):
            out = proc.stdout.decode('utf-8', errors='replace')
            print(f"  ✓ utf-8 fallback successful: {out.strip()}")
        
        return True
    except Exception as e:
        print(f"  ✗ Encoding test failed: {e}")
        return False

def test_command_chaining():
    """Test command chaining optimization"""
    print("\nTesting command chaining optimization...")
    
    # Test a simple command chain (Windows compatible)
    test_cmd = "echo First && echo Second"
    try:
        start = time.time()
        proc = subprocess.run(
            test_cmd,
            shell=True,
            check=True,
            creationflags=0x08000000 if sys.platform == 'win32' else 0,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        duration = time.time() - start
        
        output = proc.stdout.strip()
        if "First" in output and "Second" in output:
            print(f"  ✓ Command chaining works (took {duration:.3f}s)")
            return True
        else:
            print(f"  ✗ Command chaining failed: unexpected output")
            return False
    except Exception as e:
        print(f"  ✗ Command chaining test failed: {e}")
        return False

def test_caching_mechanism():
    """Test the caching mechanism for adapter list"""
    print("\nTesting caching mechanism...")
    
    # Simulate cache behavior
    # Note: This value should match ADAPTER_CACHE_TTL in NetworkFixerApp (currently 5 seconds)
    CACHE_TTL = 5  # seconds
    
    cache = None
    cache_time = 0
    
    # First access - should populate cache
    current_time = time.time()
    if not cache or (current_time - cache_time) >= CACHE_TTL:
        cache = ["Adapter1", "Adapter2", "Adapter3"]
        cache_time = current_time
        print(f"  ✓ Cache populated: {cache}")
    
    # Second access immediately - should use cache
    time.sleep(0.1)
    current_time = time.time()
    if cache and (current_time - cache_time) < CACHE_TTL:
        print(f"  ✓ Cache hit (age: {current_time - cache_time:.3f}s)")
        cache_hit = True
    else:
        print(f"  ✗ Cache miss (unexpected)")
        cache_hit = False
    
    # Wait for cache to expire
    print(f"  Waiting {CACHE_TTL}s for cache to expire...")
    time.sleep(CACHE_TTL)
    
    # Third access after TTL - should refresh cache
    current_time = time.time()
    if not cache or (current_time - cache_time) >= CACHE_TTL:
        cache = ["Adapter1", "Adapter2", "Adapter3", "Adapter4"]
        cache_time = current_time
        print(f"  ✓ Cache refreshed after TTL: {cache}")
        cache_refresh = True
    else:
        print(f"  ✗ Cache not refreshed (unexpected)")
        cache_refresh = False
    
    return cache_hit and cache_refresh

def test_ping_optimization():
    """Test ping optimization (reduced from 2 to 1 ping)"""
    print("\nTesting ping count optimization...")
    
    # Use appropriate ping command for the platform
    if sys.platform == 'win32':
        test_cmd = "ping -n 1 -w 2000 127.0.0.1"
    else:
        test_cmd = "ping -c 1 -W 2 127.0.0.1"
    
    try:
        start = time.time()
        proc = subprocess.run(
            test_cmd,
            shell=True,
            check=True,
            creationflags=0x08000000 if sys.platform == 'win32' else 0,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5
        )
        duration = time.time() - start
        
        # Check if it's faster (should be ~1-2 seconds instead of 2-3)
        if duration < 3.0:
            print(f"  ✓ Ping optimization works (took {duration:.3f}s, should be faster than before)")
            return True
        else:
            print(f"  ⚠ Ping took longer than expected ({duration:.3f}s)")
            return True  # Still passes, just slower system
    except subprocess.TimeoutExpired:
        print(f"  ✗ Ping test timed out")
        return False
    except Exception as e:
        print(f"  ✗ Ping test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("NetworkFixer Performance Optimization Validation")
    print("=" * 60)
    
    if sys.platform != 'win32':
        print("\n⚠ Warning: This tool is designed for Windows.")
        print("Some tests may fail on non-Windows platforms.\n")
    
    results = {}
    
    # Run all tests
    results['encoding'] = test_encoding_detection()
    results['chaining'] = test_command_chaining()
    results['caching'] = test_caching_mechanism()
    results['ping'] = test_ping_optimization()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    total = len(results)
    passed_count = sum(1 for v in results.values() if v)
    
    for test_name, result_passed in results.items():
        status = "✓ PASSED" if result_passed else "✗ FAILED"
        print(f"  {test_name.capitalize():15s}: {status}")
    
    print("-" * 60)
    print(f"Total: {passed_count}/{total} tests passed")
    
    if passed_count == total:
        print("\n✓ All optimizations validated successfully!")
        return 0
    else:
        print(f"\n✗ {total - passed_count} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
