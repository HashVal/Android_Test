#!/usr/bin/env python
"""
Testcase runner from Production Kernel. This runner read test case lists
from config file, then run each test case and return result, output result as
csv/yaml file.
"""

import logging
import yaml
import os
import time
import datetime
import importlib

import utils
import adb
from device import Device

#TODO: add test data directory

UTF8 = 'utf-8'

DEFAULT_CASE_RETRY_COUNT = 2
DEFAULT_CASE_TIMEOUT = 60
DEFAULT_CASE_TYPE = 'auto'
MANUAL_TYPE = 'manual'
#manual case will not be executed and only return result as empty

class SuiteNotFoundError(Exception):
    """Suite not found or did not parse successfully."""
    pass

class SuiteFailToStartError(Exception):
    """Suite did not start."""
    pass

class CaseNotImplementedError(Exception):
    """Could not read case file"""
    pass

def case_fail(result, msg, logger, logs=None):
    """fail current case and update result"""
    if logs is not None:
        for l in logs:
            logger.error(l)
        result["logs"].extend(logs)
    result["errors"].append(msg)
    logger.error("Case fail > %s", msg)
    result["result"] = "fail"
    return result

def case_pass(result, msg, logger, logs=None):
    """pass current case and update result"""
    if logs is not None:
        for l in logs:
            logger.info(l)
        result["logs"].extend(logs)
    result["logs"].append(msg)
    logger.info("Case pass > %s", msg)
    result["result"] = "pass"
    return result

class TestCase(object):
    """Test case"""
    def __init__(self, case_dict):
        self.name = case_dict.keys()[0]
        self.logger = logging.getLogger("TC_%s" %self.name)
        self.full_name = case_dict[self.name]['name']
        self.result = {"name": self.full_name, "result": "empty",
                       "logs": [], "errors": []}
        #TODO: use a dynamic loading method...too much repeat code!
        if 'retry_count' in case_dict[self.name]:
            self.retry_count = case_dict[self.name]['retry_count']
        else:
            self.retry_count = DEFAULT_CASE_RETRY_COUNT
        if 'timeout' in case_dict[self.name]:
            self.timeout = case_dict[self.name]['timeout']
        else:
            self.timeout = DEFAULT_CASE_TIMEOUT
        if 'type' in case_dict[self.name]:
            self.type = case_dict[self.name]['type']
        else:
            self.type = DEFAULT_CASE_TYPE
        if self.type != 'manual':
            self.__path = os.path.join(os.getcwd(),
                                       case_dict[self.name]['path'])
        self.__code = self.__read_case()
        if self.__code is None:
            self.logger.error("Automation case %s not implemented!",
                              self.full_name)
            raise CaseNotImplementedError()

    def __read_case(self):
        if self.type == 'manual':
            return "This is a manual case and will be skippped."
        elif not os.path.exists(self.__path):
            self.logger.error("Case %s path %s doesn't exists.",
                        self.name, self.__path)
            return None
        else:
            with open(self.__path, 'r') as case_fd:
                case_code = case_fd.read()
            return case_code

    def execute(self, local_context, global_context):
        """ case executor"""
        #TODO: implement timeout
        if self.type == MANUAL_TYPE:
            self.logger.info("Case %s is a manual case, set result to empty.",
                             self.full_name)
            self.result['errors'] = []
            self.result['logs'] = ['Case %s is manual and will be skipped, \
result set to empty' %self.full_name]
        else:
            run_count = 1
            while run_count <= self.retry_count:
                self.logger.info("Start to run case %s, round %d.",
                                 self.full_name, run_count)
                r = self.__execute(local_context, global_context)
                if r['result'] == 'pass':
                    break
                else:
                    time.sleep(1)
                    self.logger.warning("Case failed, start to re-run current \
case, retry counts: %d", self.retry_count-run_count)
                    run_count += 1
            self.result.update(r)
            self.logger.info("Case %s result %s.",
                             self.full_name, self.result['result'])
        return self.result

    def __execute(self, local_context, global_context=None):
        """ atomic executor of test script"""
        #TODO: implement subprocess exec for timer
        self.logger.info("Start execute case %s." %self.full_name)
        result = {"result": "empty", "errors": [], "logs": []}
        if global_context is None:
            global_context = {}
        try:
            exec(self.__code, global_context, local_context)
            result = local_context.get("result")
            self.logger.info("Case %s finished run, result %s.",
                             self.full_name, result["result"])
            self.logger.debug("Generated %d errors, %d logs.",
                              len(result["errors"]), len(result["logs"]))
        except Exception as e:
            self.logger.error("Exception raised in case <%s> execution, \
saved into errors, see %s", self.full_name, str(e))
            result["result"] = "fail"
            result["errors"].append(str(e))
        finally:
            result["logs"].append("Case %s runned result %s."
                                  %(self.full_name, result["result"]))
            return result


class TestSuite(object):
    """ Test suite instance"""
    def __init__(self, suite_path):
        self.logger = logging.getLogger("TestSuite")
        self.result = {}
        if not os.path.exists(suite_path):
            self.logger.error("Could not found suite file %s, \
does it really exists?", suite_path)
            raise SuiteNotFoundError()
        try:
            with open(suite_path, 'r') as suite_fd:
                self.__raw_config = yaml.load(suite_fd.read())
            self.name = self.__raw_config["suite_name"]
            self.device_type = self.__raw_config["test_device"]
            if "flash_file" in self.__raw_config:
                self.logger.info("Got flash file.")
                self.flash_file = self.__raw_config["flash_file"]
            else:
                self.logger.info("Flash file not provided in yaml file.")
                self.flash_file = None
            if "external_lib" in self.__raw_config:
                self.logger.info("Got external libraries to load.")
                self.external_lib = self.__raw_config["external_lib"]
            else:
                self.logger.info("No external library to load.")
                self.external_lib = None
            self.mods = self.load_external_libraries() if self.external_lib \
                                                       else None
            self.device = None
            self.case_queue = [TestCase(c) for c in self.__raw_config["case"]]
            self.result['count'] = {'pass':0, 'fail': 0,
                                    'empty': 0, 'block': 0,
                                    'total': len(self.case_queue)}
            self.result['cases'] = []
            self.current_case = None
            self.test_context = None
            self.logger.info("Test suite %s, test device %s, case count %s",
                             self.name, self.device_type["name"],
                             len(self.case_queue))
        except Exception as e:
            self.logger.error("Found exception in creating test suite, see %s",
                               str(e))
            error_name = "TestSuite.__init__(self, suite_path=%s)" %suite_path
            self.logger.error("In function name %s", error_name)
            raise SuiteNotFoundError(str(e))

    def detect_device(self, device_type):
        """ find device with given device type or serial number, normally
            'device_type' will be like below, priority: "serial" > "product"
            {"name": "xxx", "product": "xxx", "serial": "xxx"}
            return instance of class Device() if found else None
        """
        device = product = serial = None
        if "product" in device_type:
            product = device_type["product"]
        if "serial" in device_type:
            serial = device_type["serial"]
        devices = adb.find_devices(serial=serial, product=product)
        if len(devices) == 0:
            self.logger.error("Did not find any device match \
serial=%s and product=%s", serial, product)
        else:
            self.logger.info("Got %d devices, will use first one, serial: %s",
                             len(devices), devices[0])
            device = Device(serial=devices[0], name=device_type["name"])
        return device

    def create_test_context(self, **kwargs):
        """ create local test context dictionary, below are defaults:
            {'result': 'empty', 'errors': [], 'logs': []}
        """
        context = kwargs
        context['result'] = {"result": "empty", "logs": [], "errors": []}
        self.logger.info("Dump test context: %s", str(context.keys()))
        return context

    def load_external_libraries(self):
        """ load external libraries to mods dictionary """
        mods = {}
        for m in self.external_lib:
            #TODO: remove this hack
            mod = m[m.keys()[0]]
            rel_path = mod["path"][:-3].replace('/', '.')
            self.logger.info("Import library from %s", mod["path"])
            mods[mod["name"]] = importlib.import_module(rel_path, __package__)
            self.logger.info("External library %s imported from"
                             "relative path %s", mod["name"], rel_path)
        return mods

    def handle_case_result(self, case):
        """Merge case result """
        self.result['cases'].append(case)
        self.result['count'][case['result']] += 1
        return

    def generate_report(self, path, report_type="yaml"):
        """Generate test report"""
        #TODO: support other format report files
        report = {"name": self.name,
                  "device": {"serial": self.device.serial,
                             "type": self.device.name,
                             "product_name": self.device_type['product']
                            },
                  "result": self.result['count'],
                  "cases": [{c['name']: c} for c in self.result['cases']]
                 }
        time_stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        report_name = "%s_%s.%s" %(time_stamp, self.name, report_type)
        if report_type == "yaml":
            with open(os.path.join(path, report_name), "w") as report_fd:
                yaml.dump(report, report_fd, default_flow_style=False)
        else:
            self.logger.error("Unsupported report format: %s!", report_type)
            self.logger.error("Dump report as below.")
            self.logger.error(str(report))
        return

    def generate_lava_output(self):
        """Generate LAVA output to let LAVA know test results"""
        #Current case result mapping to LAVA case result mapping
        result2LAVA_result = {'pass': 'pass', 'fail': 'fail',
                              'skip': 'block', 'empty': 'unknown'}
        for c in self.result['cases']:
            case_lava_result = result2LAVA_result[c['result']]
            case_name = c['name']
            self.logger.info("Generate case %s LAVA result %s",
                             case_name, case_lava_result)
            cmd = 'lava-test-case %s --result %s' %(case_name,
                                                    case_lava_result)
            _, o = utils.execute_shell_cmd(cmd)
            _ = [self.logger.info(l) for l in o]
        self.logger.info("LAVA result for all cases generated!")

    def run(self):
        """Run current test suite"""
        #TODO: Add suite timeout
        self.logger.info("Start running test suite %s.", self.name)
        self.device = self.detect_device(self.device_type)
        if self.device is None:
            self.logger.error("Available %s device not found, stop running.",
                               self.device_type["name"])
            raise SuiteFailToStartError()
        while len(self.case_queue) != 0:
            self.logger.info("%d cases to be executed.", len(self.case_queue))
            current_case = self.case_queue.pop(0)
            self.logger.info("Start executing case %s", current_case.name)
            if not self.device.check_alive():
                #device offline, so skip and mark this case as block
                self.logger.error("Device %s not alive, skip current case",
                                  str(self.device))
                current_result = {"name": current_case.full_name,
                                  "result": "block",
                                  "errors": ["Device %s offline."
                                             %self.device.serial],
                                  "logs": []
                                 }
            else:
                #normal automated case
                self.test_context = self.create_test_context(
                                            test_device=self.device,
                                            logger=current_case.logger,
                                            flash_file=self.flash_file,
                                            case_pass=case_pass,
                                            case_fail=case_fail,
                                            mods=self.mods)
                current_result = current_case.execute(self.test_context, {})
            self.handle_case_result(current_result)
        self.logger.info("Total %d cases of suite has been executed.",
                         self.result['count']['total'])
        self.logger.info("Total pass: %d", self.result['count']['pass'])
        self.logger.info("Total fail: %d", self.result['count']['fail'])
        self.logger.info("Total block: %d", self.result['count']['block'])
        self.logger.info("Total empty: %d", self.result['count']['empty'])
        return
