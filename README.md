apidiff
=======

CLI tool for diffing responses of HTTP API endpoints.

Installation:

    python3 setup.py install

Basic usage:

    apidiff https://httpbin.org/status/200 https://httpbin.org/status/404

If the response is a JSON it's possible to run a jq(1) filter on the results before
diffing them, for example to filter-out non-interesting keys:

    apidiff --jq-filter 'del(.now.epoch)|del(.now.rfc3339)' https://now.httpbin.org/ https://now.httpbin.org/
