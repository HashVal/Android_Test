#!/usr/bin/env python
"""Test runner"""

import os
import sys
import logging
import argparse

from framework import TestSuite

LOG_FMT = '%(asctime)-15s Android_BAT %(name)-10s %(levelname)-8s %(message)s'

def parse_args(arg_list):
    """parser arguments"""
    parser = argparse.ArgumentParser(description="Android Mini test framework",
                                     epilog="Don't panic!")
    parser.add_argument("-t", "--test-suite", dest="test_suite",
                        required=True, action="store",
                        help="test_suite yaml file")
    parser.add_argument("-l", "--lava", dest="lava_output",
                        action="store_true", help="generate lava output")
    return parser.parse_args(arg_list)

def main(arg_list):
    """entry of test runner"""
    logging.basicConfig(format=LOG_FMT, level=logging.DEBUG)
    args = parse_args(arg_list)
    test_suite = args.test_suite
    suite = TestSuite(suite_path=test_suite)
    suite.run()
    result_path = os.path.join(os.getcwd(), "results")
    suite.generate_report(path=result_path)
    if args.lava_output:
        suite.generate_lava_output()
    return

if __name__ == "__main__":
    main(sys.argv[1:])
