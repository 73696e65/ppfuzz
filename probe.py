#!/usr/bin/env python3

from sys import argv
import google.protobuf.text_format as tf
import re
from importlib import import_module
from fuzzer import Runner

if len(argv) < 5:
    print(f'Syntax: {argv[0]} <url> <endpoint> <proto_file.py> <msg_file>')
    exit()

url, endpoint, pb2_file, msg_file = argv[1:]

mod_name = re.sub("/", ".", pb2_file)
mod_name = re.sub(".py$", '', mod_name)
pb2 = import_module(mod_name)

with open(msg_file, "rb") as f:
    msg = getattr(pb2, endpoint)()
    tf.Parse(f.read(), msg)    

runner = Runner()
serialized = msg.SerializeToString()
runner.run(url, serialized)