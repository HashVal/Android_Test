#!/usr/bin/env python
""" Utils module, including:
    Exception classes,
    timeout decorator,
    shell_cmd_executor
"""

import subprocess
import logging
import requests
import time
import os

logger = logging.getLogger("Utils")
logger.setLevel(logging.INFO)


class TimeoutException(Exception):
    """Timeout exception"""
    pass

def execute_shell_cmd(command, use_shell=False,
                      decoder="utf-8", rt_output=False):
    """ shell command executor
        params: command(str), use_shell(bool)
        return: (return_code(int), output(list of strs))
    """
    logger.debug("Execute shell command: %s", command)
    if use_shell:
        logger.info("Command execution use shell = %s", str(use_shell))
    process_cmd = command if use_shell else command.split()
    ret_code, output = 1, ''
    try:
        process = subprocess.Popen(process_cmd, shell=use_shell,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        while True:
            tmp_out = process.stdout.readline()
            if tmp_out == '' and process.poll() is not None:
                #End of output
                break
            if tmp_out:
                if rt_output:
                    logger.info("Shell_RT>%s", tmp_out)
                output += tmp_out
        ret_code = process.poll()
    except (OSError, ValueError) as e:
        logger.error("Exception raised when execute command %s. See %s",
                     command, str(e))
        ret_code, output = 1, str(e)
    finally:
        output = output.decode(decoder).split("\n")
        if output[-1] == '':
            output = output[:-1]
        return ret_code, output

def download_image(url, path=None, user=None, password=None, ssl_verify=False):
    filename = url.split('/')[-1]
    if not filename or not filename.endswith(".zip"):
        logger.error("Looks like this is not a image url, please check!")
        logger.error(url)
    else:
        logger.info("Donwload image from url %s", url)
    s = requests.Session()
    if user is not None and password is not None:
        s.auth = (user, password)
        logger.info("Login session with user %s and password.", user)
    start_time = time.time()
    r = s.get(url, stream=True, verify=ssl_verify)
    local_file = os.path.join(path, filename) if path else filename
    with open(local_file, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                fd.write(chunk)
    end_time = time.time()
    logger.info("Download finished, file here %s, cost %s seconds.",
                local_file, str(end_time-start_time))
    return local_file
