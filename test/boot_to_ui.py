#!/usr/bin/env python
""" Sample test case
    test target: device could boot to UI
    both cflasher flash and fastboot flash are supported
"""

def test(device, logger, result, flash_file, case_pass, case_fail, **kwargs):
    logger.info("Start sample test case boot to UI.")
    if device.check_alive():
        result["logs"].append("Device alive at first.")
    else:
        return case_fail(result, "Device not alive", logger)
    logger.info("Case: flash and boot.")
    img_file = flash_file["file"]
    mode = flash_file["mode"]
    logger.info("Flash mode: %s selected", mode)
    if "auth" in flash_file.keys():
        auth = (flash_file["auth"]["username"], flash_file["auth"]["password"])
        logger.info("Got auth tuple, username: %s", authp[0])
    else:
        auth = None
    config, commands = None, None
    if "config" in flash_file.keys():
        config = flash_file["config"]
    if "commands" in flash_file.keys():
        commands = flash_file["commands"]
    logger.info("Start flash...")
    flash_result = device.flash(img_file,
                                mode=mode,
                                auth=auth,
                                flash_config=config,
                                flash_commands=commands)
    if flash_result:
        return case_pass(result, "Boot to UI finished.", logger)
    else:
        return case_fail(result, "Device did not boot to UI", logger)

test(test_device, logger, result, flash_file, case_pass, case_fail)
