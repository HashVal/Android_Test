#!/usr/bin/env python
import time
"""
    test target: device test Ethernet ping site test
"""

def test(device, logger, result, case_pass, case_fail, **kwargs):
    logger.info("Test case: Test ethernet ping")
    enable_true = False
    if device.check_alive():
        result["logs"].append("Device online.")
    else:
        case_fail(result, "Device offline before ethernet ping test", logger)
        return
    logger.info("Checking Ethernet...")
    output_shell = device.execute_adb_shell_cmd("ping -c 3 \"www.google.com\"")
    for i in output_shell[1]:
        if "3 packets transmitted" in str(i):
            enable_true = True
    if enable_true:
        case_pass(result, "Ethernet transmitted Packets.", logger)
    else:
        case_fail(result, "Ethernet DID NOT Transmitted Packets.", logger)
    return

test(test_device, logger, result, case_pass, case_fail)
