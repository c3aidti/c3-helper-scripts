# C3 Helper Scripts

These scripts help with some aspects of working with C3.

## `send-file.py`

Rather than using curl (Which didn't show progress for me with respect to PUT operations), or Postman, here, I've made a requests based python script to help. All necessary options are clearly outlined in the help and should help users send data right away.

`python send-file.py --vanity-url http://0.0.0.0:8080 --tenant 'test' --tag 'prod' --auth-token "3033d31a5522f36e1e6725285fd10f98c28ee4c6f599478fb8b1862a455ee1d50a88" --api-endpoint CanonicalSmartBulbMeasurement/SmartBulbMeasurement.csv --file ../Exercises-Data-Resources/Data\ Files/SmartBulbMeasurement.csv`
