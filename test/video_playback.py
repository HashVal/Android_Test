#!/usr/bin/env python
""" Sample test case for video playback
    test target: device could play H263 video.
"""


def test(device, logger, result, case_pass, case_fail, **kwargs):
    """ Test method for check device audio playback """
    import time
    import os
    logger.info("Start TC H263 video playback.")
    logger.info("Push video sample to device.")
    video_name = "3GPv4_H263_L1.0_BP_QCIF_15fps_AAC_ST_16KHz_reference.mp4"
    video_saving_path = "./tools/video_case/"
    video_sample = video_saving_path + video_name
    video_device_path = "/sdcard/"
    VIDEO_MIN_SIZE = 800000
    r = device.push(local=video_sample, remote=video_device_path)
    if r != 0:
        case_fail(result, "Failed to push video sample to device.", logger)
        return
    video_device_path = "/sdcard/"
    video_on_device = video_device_path + video_name
    r = device.play_video(video_on_device)
    logger.info("Video play started.")
    if r != 0:
        case_fail(result, "Failed to play video.", logger)
        return
    time.sleep(5)
    video_record = "video_record.mp4"
    logger.info("Start to record video after 5 seconds sleep.")
    r = device.record_screen(video_record, directory=video_device_path,
                                time_limit=10)
    logger.info("Record finished.")
    if r != 0:
        case_fail(result, "Failed to record video playback.", logger)
        return
    time.sleep(20)
    device.pull(remote=video_device_path+video_record, local=".")
    video_statinfo = os.stat(video_record)
    logger.info("Record video size is %s", str(video_statinfo.st_size))
    #TODO: opencv-python could not read record video(H264 codec), so here
    #      I made a workaround only check video size.
    if video_statinfo.st_size > VIDEO_MIN_SIZE:
        case_pass(result, "H263 video playback passed.", logger)
    else:
        case_fail(result, "Video record size smaller than required!", logger)
    return

test(test_device, logger, result, case_pass, case_fail)

