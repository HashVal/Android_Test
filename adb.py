#!/usr/bin/env python
""" ADB related Exceptions and methods """

import re
import time
import socket
import logging

import utils


logger = logging.getLogger("ADBDriver")
logger.setLevel(logging.INFO)

LOCAL_HOST = "127.0.0.1"
ADB_HOST_PORT_DEFAULT = 5037
ADB_DEVICE_PORT_DEFUALT = 5555

DEVICE_STATUS = {"online": "device", "offline": "offline",
                 "all": "device|offline"}


class ADBServerException(Exception):
    """ADB Server start failure exception"""
    pass

class ADBConnectionException(Exception):
    """Device did not connected."""
    pass

def execute_adb_cmd(cmd, prefix="adb"):
    """ Execute adb command with prefix """
    ret, out = utils.execute_shell_cmd("%s %s" %(prefix, cmd))
    return ret, out

def execute_fastboot_cmd(cmd, prefix="fastboot", rt_output=True):
    """ Execute fastboot command with prefix """
    ret, out = utils.execute_shell_cmd("%s %s" %(prefix, cmd),
                                       rt_output=rt_output)
    return ret, out

def check_adb_server_alive(port=ADB_HOST_PORT_DEFAULT, host=LOCAL_HOST):
    """ check adb server started or not"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except Exception as e:
        logger.info("ADB server not started. See %s", str(e))
        return False

def start_adb_server(check_before_start=True):
    """ start adb server
        check_before_start: if True will check adb server started or not.
    """
    if check_before_start:
        if check_adb_server_alive():
            logger.info("ADB server already started.")
            return
    try:
        r, o = execute_adb_cmd('start-server')
        if r == 0:
            logger.info("ADB server started.")
        else:
            logger.error("Failed to start adb server, \
                          please check output below:")
            for l in o:
                logger.error("ADBServer>>>>%s", l)
            raise ADBServerException("ADB server start failed.")
    except Exception as e:
        logger.error("ADB server start exception, see: %s", str(e))
        raise ADBServerException("ADB server start failed.")

def kill_adb_server():
    """ kill adb server """
    logger.warning("Killing ADB server...")
    try:
        r, o = execute_adb_cmd('kill-server')
        if r == 0:
            logger.info("ADB server killed.")
        else:
            logger.error("Failed to kill ADB server.")
            for l in o:
                logger.error("ADBServer>>>>%s", l)
            raise ADBServerException("ADB server kill failed.")
    except Exception as e:
        logger.error("ADB server kill exception, see: %s", str(e))
        raise ADBServerException("ADB server kill failed.")

def list_all_devices(status=DEVICE_STATUS["online"]):
    """ list all device serial numbers that match given status"""
    _, out = execute_adb_cmd("devices")
    device_serials = []
    device_match_re = r'(?P<serial>\S+)\t(?P<status>%s)' %status
    device_re_obj = re.compile(device_match_re)
    for device in out[1:]:
        device_match = device_re_obj.search(device)
        if device_match:
            serial = device_match.group("serial")
            device_serials.append(serial)
            logger.debug("Got device with serial no: %s", serial)
    return device_serials

def find_devices(serial=None, product=None):
    """ find available devices with given serial and product, if both were None,
        return every devices that could be listed, if both were given, will use
        serial.
    """
    device_serials = []
    all_devices = list_all_devices()
    if serial is not None:
        if serial in all_devices:
            logger.debug("Gotcha! Device %s found!", serial)
            device_serials.append(serial)
        else:
            logger.warning("Did not find device with serial %s, \
                            is device online?", serial)
    elif product is not None:
        get_product_cmd = "shell getprop | grep ro.product.name"
        for device in all_devices:
            device_prefix = "adb -s %s" %device
            _, out = execute_adb_cmd(get_product_cmd, prefix=device_prefix)
            out = '\n'.join(out)
            #change out list to str
            if product in out:
                logger.debug("Gotcha! Device %s found!", serial)
                device_serials.append(device)
    else:
        logger.warning("Serial and product both not set, \
                        will return all online devices!")
        device_serials = all_devices
    return device_serials

def check_device_online(serial, retry_count=1, timeout=1):
    """check given device online or not"""
    count = 1
    while count <= retry_count:
        logger.debug("Try to connect to device %s %d time(s)", serial, count)
        if serial in list_all_devices():
            logger.info("Device %s online.", serial)
            return True
        else:
            logger.warning("Device %s offline, wait and retry %d times",
                           serial, retry_count-count)
            time.sleep(timeout/retry_count)
            count += 1
    logger.warning("Device %s keep offline in %d seconds.", serial, timeout)
    return False
