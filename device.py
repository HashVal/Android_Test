#!/usr/bin/env python
"""ADB wrapper"""

import os
import time
import logging

import adb
import utils

#TODO: add Device().getprop() method

DEFAULT_FLASH_TIMEOUT = 600
#flash timeout including download image, flashing and boot, so it tooks longer
DEFAULT_CONNECT_TIMEOUT = 60
DEFAULT_BOOT_TIMEOUT = 120
DEFAULT_REBOOT_TIMEOUT = 30
REBOOT_RETRY_COUNT = 3

DEFAULT_TESTDATA_DIR = "/data/"

LOG_LVL_DEBUG = 10
LOG_LVL_INFO = 20

class DeviceOfflineError(Exception):
    """ Could not find device """
    pass

class DeviceInitError(Exception):
    """ Device init failed"""
    pass


class Device(object):
    """ Android device instance. """
    def __init__(self, serial, name="Unknown"):
        self.name = name
        self.serial = serial
        self.connected = False
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.INFO)
        self.__set_cmd_prefix(serial)
        self.connect()

    def __set_cmd_prefix(self, serial):
        """set command prefix such as 'adb [-s <SERIAL>']"""
        self.adb_cmd_prefix = 'adb -s %s' %serial if serial else 'adb'
        self.fastboot_cmd_prefix = 'fastboot -s %s' %serial if serial \
                                                            else 'fastboot'
        self.adb_shell_prefix = '%s shell' %self.adb_cmd_prefix

    def __output_lines(self, output_lines, prefix=None, level=LOG_LVL_INFO):
        """output lines to log with level and prefix """
        for line in output_lines:
            if prefix is not None:
                line = "%.8s>>%s" %(prefix, line)
                self.logger.log(level, line)

    def __execute_adb_cmd(self, cmd, prefix):
        """ base method of execute adb command"""
        return adb.execute_adb_cmd(cmd, prefix)

    def __execute_fastboot_cmd(self, cmd, prefix):
        """ base method of execute fastboot command"""
        return adb.execute_fastboot_cmd(cmd, prefix)

    def execute_adb_cmd(self, cmd):
        """ execute adb command with device prefix
            return: return_code, output(list of str)
        """
        ret, out = self.__execute_adb_cmd(cmd, self.adb_cmd_prefix)
        return ret, out

    def execute_fastboot_cmd(self, cmd):
        """ execute fastboot command with device prefix
            return: ret_code and output
        """
        ret, out = self.__execute_fastboot_cmd(cmd, self.fastboot_cmd_prefix)
        return ret, out

    def execute_adb_shell_cmd(self, cmd):
        """ execute adb shell command with device prefix
            return: return_code, output(list of str)
        """
        ret, out = self.__execute_adb_cmd(cmd, self.adb_shell_prefix)
        return ret, out

    def __check_device_connected(self):
        """ Check current device connected or not"""
        return adb.check_device_online(self.serial)

    def __check_device_fastboot_connected(self):
        """ Check current device is fastboot connected or not"""
        r, o = self.__execute_fastboot_cmd("devices", prefix="fastboot")
        return (self.serial in " ".join(o))

    def connect(self, timeout=DEFAULT_CONNECT_TIMEOUT):
        """ Connect to device, update device status"""
        adb.start_adb_server()
        start, current = time.time(), time.time()
        while current - start < timeout:
            if self.__check_device_connected():
                self.connected = True
                self.logger.info("Device %s connected.", self.serial)
                break
            else:
                time.sleep(3)
                self.logger.debug("Device %s offline, looping...", self.serial)
                current = time.time()
        if not self.connected:
            self.logger.error("No device with id %s detected", self.serial)
            self.logger.error("Dump all connected devices.")
            for d in adb.list_all_devices():
                self.logger.error("device: %s", d)
            raise DeviceOfflineError("Device %s not found.", self.serial)
        self.root()
        return

    def check_alive(self):
        """ Check device alive or not """
        return self.__check_device_connected()

    def root(self):
        """ ADB Root """
        r, o = self.execute_adb_cmd("root")
        self.__output_lines(o, prefix="ADB Root")
        time.sleep(2)
        return r

    def push(self, local, remote):
        """ adb push command """
        if not os.path.exists(local):
            self.logger.error("Local path not exist: %s", local)
            raise OSError("Local %s path not found" %local)
        r, o = self.execute_adb_cmd("push %s %s" %(local, remote))
        self.__output_lines(o, prefix="ADB Push")
        return r

    def pull(self, remote, local):
        """ adb pull command wrapper """
        if not os.path.exists(local):
            self.logger.error("Local path not exist: %s", local)
            raise OSError("Local %s path not found" %local)
        r, o = self.execute_adb_cmd("pull %s %s" %(remote, local))
        self.__output_lines(o, prefix="ADB Pull")
        return r

    def screencap(self, filename, path=DEFAULT_TESTDATA_DIR):
        """ adb shell screencap -p path/filename"""
        if not filename.endswith(".png"):
            self.logger.error("Invalid filename: not ended with .png, exit.")
            return
        cmd = "screencap -p %s" %os.path.join(path, filename)
        self.logger.info(cmd)
        r, o = self.execute_adb_shell_cmd(cmd)
        self.__output_lines(o, prefix="screencap")
        return r

    def reboot(self, timeout=DEFAULT_REBOOT_TIMEOUT, retry_count=3):
        """Reboot device and wait for it back"""
        if not self.check_alive():
            self.logger.error("Device offline, could not reboot, exit...")
            return
        self.logger.info("Start reboot device and wait for it wake up in \
%d seconds", timeout)
        _, o = self.execute_adb_cmd("reboot")
        self.connected = False
        self.__output_lines(o, prefix="ADB Reboot")
        count = 1
        while count <= retry_count:
            if self.__check_device_connected():
                self.connected = True
                self.logger.info("Device %s connected.", self.serial)
                break
            else:
                time.sleep(timeout/retry_count)
                self.logger.warning("Device %s offline, looping...",
                                    self.serial)
                count += 1
        if not self.connected:
            self.logger.error("No device with id %s detected", self.serial)
            self.logger.error("Dump all connected devices.")
            for d in adb.list_all_devices():
                self.logger.error("device: %s", d)
            raise DeviceOfflineError("Device %s not found.", self.serial)
        self.root()
        return

    def __download_image(self, url, auth):
        """"""
        if auth is not None:
            user, password = auth
        else:
            user, password = None, None
        self.logger.info("Got image url link, starting download to local.")
        local_image_path = utils.download_image(url, user=user,
                                                password=password)
        return local_image_path

    def __reboot_to_fastboot(self, reboot_timeout=10):
        """ reboot device to fastboot mode, return True if device fastboot
            online
        """
        r, _ = self.execute_adb_cmd("reboot fastboot")
        time.sleep(reboot_timeout)
        return self.__check_device_fastboot_connected()

    def __fastboot_flash(self, image, auth=None, flash_commands=None):
        """ if image is a url link, download it to local, flash with given
            flash_command list, return bool(boot_complete)
            image: url link or local zip file
            auth: (username, password)
        """
        self.logger.info("Use fastboot mode for flash.")
        is_flash_success = False
        if flash_commands is None:
            self.logger.error("No flash commands given! Exit...")
            return is_flash_success
        if image.startswith("http://"):
            local_image_path = self.__download_image(image, auth)
        else:
            local_image_path = image
        self.logger.info("Use fastboot commands to flash.")
        if local_image_path.endswith(".zip"):
            self.logger.info("Local image %s is a zip file, unzip it first",
                             local_image_path)
            unzip_cmd = "unzip -d %s/ %s" %(local_image_path[:-4],
                                            local_image_path)
            self.logger.info("Unzip command: %s", unzip_cmd)
            r, _ = utils.execute_shell_cmd(unzip_cmd, rt_output=True)
            self.logger.info("Unzip command returns %d", r)
            local_image_path = local_image_path[:-4] #remove .zip postfix
        self.logger.info("Reboot device to fastboot mode.")
        device_in_fastboot = self.__reboot_to_fastboot()
        self.logger.info("Device in fastboot mode: %s", str(device_in_fastboot))
        if not device_in_fastboot:
            self.logger.error("Device did not enter fastboot mode, exit")
            return is_flash_success
        self.logger.info("Start using fastboot to flash, working dir: %s",
                         local_image_path)
        prev_dir = os.getcwd()
        work_dir = os.path.join(prev_dir, local_image_path)
        os.chdir(work_dir)
        for command in flash_commands:
            self.logger.info("Run command: %s", command)
            r, _ = self.execute_fastboot_cmd(command)
            if r != 0:
                self.logger.error("Failed to run command: %s, exit", command)
                os.chdir(prev_dir)
                return is_flash_success
            self.logger.info("Command %s success.", command)
        #all command passed successfully
        self.logger.info("All flash command runned successfully.")
        os.chdir(prev_dir)
        is_flash_success = True
        self.logger.info("Flash success: %s", str(is_flash_success))
        return is_flash_success

    def __check_boot_complete(self):
        """ check device boot complete or not"""
        _, o = self.execute_adb_shell_cmd("getprop sys.boot_completed")
        boot_completed = True if '1' in '\n'.join(o) else False
        self.logger.info("Device boot complete: %s", str(boot_completed))
        return boot_completed

    def __wait_for_boot_complete(self, timeout=DEFAULT_BOOT_TIMEOUT):
        """wait for device boot complete"""
        start = current = time.time()
        boot_complete = adb_online = False
        while current - start < timeout:
            adb_online = self.__check_device_connected()
            if adb_online:
                break
            else:
                self.logger.info("Device keep offline, waiting.")
                time.sleep(3)
                current = time.time()
        if not adb_online:
            self.logger.error("Device adb offline for %d seconds, abort!",
                              timeout)
            return boot_complete
        time.sleep(3)
        self.root()
        current = time.time()
        self.logger.info("Device adb online, wait for boot complete.")
        while current - start < timeout:
            boot_complete = self.__check_boot_complete()
            current = time.time()
            if boot_complete:
                break
            else:
                self.logger.info("Did not boot complete, waiting.")
                time.sleep(3)
                current = time.time()
        if not boot_complete:
            self.logger.error("Device did not boot complete, abort.")
        return boot_complete

    def flash(self, image, mode="fastboot", auth=None, flash_commands=None):
        """ Flash image to device and then wait for device to boot completed
            image: url link or local directory or local zip file
            mode: fastboot
            auth: (usernam/password)
            flash_commands: only for fastboot mode
            """
        support_flash_mode = ("cflasher", "fastboot")
        if mode == "fastboot":
            flash_result = self.__fastboot_flash(image, auth, flash_commands)
            if flash_result == False:
                self.logger.error("Flash with mode: %s failed!", mode)
                return flash_result
        else:
            self.logger.error("Flash mode: %s not supported.", mode)
            return False
        self.logger.info("Flash passed, wait for device to boot.")
        if not self.__wait_for_boot_complete():
            return False
        self.logger.info("Capture home screen after 30 seconds.")
        time.sleep(30)
        boot_screen = "first_boot.png"
        self.screencap(boot_screen)
        self.logger.info("Capture done, pull %s from device...", boot_screen)
        self.pull(remote=os.path.join(DEFAULT_TESTDATA_DIR, boot_screen),
                  local=".")
        self.logger.info("Got device boot_screen in current directory.")
        return True

    def play_video(self, video_path):
        """Use Android intent to play video, only for Android O currently"""
        self.logger.info("Playing video %s with intent.", video_path)
        action_view = "android.intent.action.VIEW"
        #video_intent = 'com.google.android.apps.plus/.phone.VideoViewActivity'
        video_intent = 'com.android.gallery3d/.app.MovieActivity'
        #FIXME: This intent only works for Android O
        cmd = "am start -a %s -d %s -n %s -t \"video/*\"" \
              %(action_view, video_path, video_intent)
        r, o = self.execute_adb_shell_cmd(cmd)
        self.__output_lines(o, prefix="am_start")
        return r

    def record_screen(self, file_name,
                      directory=DEFAULT_TESTDATA_DIR, time_limit=20):
        """Record screen and save in device."""
        record_path = os.path.join(directory, file_name)
        cmd = "screenrecord --time-limit %d %s" %(time_limit, record_path)
        r, o = self.execute_adb_shell_cmd(cmd)
        self.__output_lines(o, prefix="scrn_rcd")
        return r





