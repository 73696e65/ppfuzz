#!/usr/bin/env python3

import re

from sys import argv

from lib import helper
from config import *
from fuzzer import ProtoFuzzer

if __name__ == "__main__":
    
    if "-C" in argv[1:]:
        helper.pb_compile(helper.get_proto_files(), proto_out)
        exit()

    # fuzzer = ProtoFuzzer(disp=True, log=True)
    fuzzer = ProtoFuzzer()
    for _ in range(1):
        fuzzer.run()
