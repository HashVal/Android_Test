#!/usr/bin/env python
"""
    test target: device test Bluetooth enable/disable test
"""

def test(device, logger, result, case_pass, case_fail, **kwargs):
    import time
    logger.info("Test case: Test Bluetooth")
    enable_true = False
    if device.check_alive():
        result["logs"].append("Device online.")
    else:
        case_fail(result, "Device offline before bluetooth test", logger)
        return
    logger.info("Checking Bluetooth...")

    output_bt_enable = device.execute_adb_shell_cmd("service call bluetooth_manager 6")
    time.sleep(5)
    output_shell = device.execute_adb_shell_cmd("dumpsys bluetooth_manager")
    for i in output_shell[1]:
        if "enabled: true" in str(i):
            enable_true = True
    if enable_true:
        case_pass(result, "Bluetooth Enabled.", logger)
    else:
        case_fail(result, "Bluetooth is not Enabled.", logger)
    time.sleep(5)
    output_bt_disable = device.execute_adb_shell_cmd("service call bluetooth_manager 8")
    return

test(test_device, logger, result, case_pass, case_fail)
