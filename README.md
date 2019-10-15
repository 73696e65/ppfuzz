# ppfuzz

Python Protocol Buffers Fuzzer, based on https://www.fuzzingbook.org/html/GrammarFuzzer.html. It automatically creates a grammar from `.proto` files and constructs a random derivation tree, denoting sections where it is possible to inject the payload. By default the runner uses HTTP requests, but the transport could be easily adjusted.

# Installation

```
virtualenv -p /usr/bin/python3.7 venv
. venv/bin/activate
pip install -r requirements.txt
```

# Usage

```
cp config.py.default config.py
vim config.py # edit the services, replace and delete variables
vim fuzzer.py # edit the inject_ methods
vim ppfuzz.py # edit the number of invocations

./ppfuzz.py # fuzzer

./probe.py # to replay some message
```

# License

MIT License

Copyright (c) 2019 Norbert Szetei

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
