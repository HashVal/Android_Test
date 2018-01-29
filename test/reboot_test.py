#!/usr/bin/env python
""" Sample test case
    test target: device could boot to UI
"""

def test(device, logger, result, case_pass, case_fail, **kwargs):
    logger.info("Test case: adb reboot.")
    if device.check_alive():
        result["logs"].append("Device online.")
    else:
        case_fail(result, "Device offline before reboot", logger)
        return
    logger.info("Rebooting...")
    device.reboot(timeout=60, retry_count=2)
    if device.check_alive():
        device.execute_adb_shell_cmd("input tap 400 1000")
        #pass user choose screen
        case_pass(result, "Reboot success.", logger)
    else:
        case_fail(result, "Reboot failed, device offline.", logger)
    return

test(test_device, logger, result, case_pass, case_fail)
