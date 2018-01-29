#!/usr/bin/env python
""" Sample test case
    test target: device audio playback works good
"""

def test(device, logger, result, case_pass, case_fail, **kwargs):
    """ Test method for check device audio playback """
    logger.info("Start TC audio_playback_check.")
    logger.info("Try to list ALSA devices.")
    r, o = device.execute_adb_shell_cmd("alsa_aplay -l")
    if r != 0:
        #command not executed successfully
        case_fail(result, "List command failed.", logger, logs=o)
    else:
        if len(o) == 0:
            #TODO: Findout why below error msg won't print via stdout and stderr
            err_msg = "aplay: device_list:268: no soundcards found..."
            case_fail(result, err_msg, logger)
        else:
            o = o[1:]
            for l in o:
                logger.debug("ALSA_list>>%s", l)
            case_pass(result, "ALSA_list detected sound cards.",
                      logger, logs=o)
    return

test(test_device, logger, result, case_pass, case_fail)

