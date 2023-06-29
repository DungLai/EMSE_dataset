import requests
import urllib.request
import json


token = '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'

import os
result = os.popen("curl \
  -H 'Accept: application/vnd.github+json' \
  -H 'Authorization: Bearer {}'\
  -H 'X-GitHub-Api-Version: 2022-11-28' \
  https://api.github.com/rate_limit".format(token)).read()
print(result)

