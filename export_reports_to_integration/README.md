## Export reports to an integration

This script will allow you to export all alerts from the latest reports from all external cloud provider accounts to an integration. 

Requirements: 
1.  Python3
2. Install the Python SDK: `pip install git+https://github.com/EvidentSecurity/esp-sdk-python.git`
3.  Set environment variables for ESP API keys: https://esp.evident.io/settings/api_keys `export ESP_ACCESS_KEY_ID=<your_access_key>` `export ESP_SECRET_ACCESS_KEY=<your_secret_access_key>`
4. Enter the target integration's name into the `options` section
5. Please note that all external accounts must be added to the integration prior to running this script, or the script will fail