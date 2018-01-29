## Android BAT test case executor and test cases

### Functions

* Could dynamic load test script instead of hard code in test framework.
* Basic ADB function wrappers.
* Sample case about boot, reboot, video playback
* Command level testing
* Test context could be customized
* Dynamic load library to test context


### Usage

```
python runner.py [-h] -t TEST_SUITE [-l]
  -h, --help            show this help message and exit
  -t TEST_SUITE, --test-suite TEST_SUITE
                        test_suite yaml file
  -l, --lava            generate lava output
```

Dependencies:

PIL library: install with ```pip install pillow```

### TODOs

* Logcat capture
* Timeout method
