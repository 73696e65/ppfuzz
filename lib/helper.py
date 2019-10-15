import subprocess
import re
import os.path
import sys

from os import mkdir
from importlib import import_module

sys.path.append("..")
from config import *


def get_proto_files():
    """
    Extract .proto files from the services
    """
    proto_files = set()
    [proto_files.add(p) for _, _, p in services]
    return proto_files

def get_proto_libs(proto_files):
    """
    Dynamically import the compiled protobuf files
    """
    libs = dict()
    for pf in proto_files:
        proto_lib = re.sub(r'.proto$', '_pb2', os.path.basename(pf))
        libs[pf] = import_module(f"{proto_out}.{proto_lib}")
    return libs

def create_vectors(libs):
    """
    Create attack vectors - list of dictionaries containing url, request 
    and protobuf message. Later each entry will be expanded with grammar.
    """
    vectors = list()
    for url, request, proto in services:
        msg = getattr(libs[proto], request)
        entry = dict()
        entry['url'] = url
        entry['request'] = request
        entry['msg'] = msg 
        vectors.append(entry)
    return vectors
    
def pb_compile(files, dest):
    """
    Compile the protobuf files running the external 'protoc' compiler
    """
    if not os.path.exists(dest):
        mkdir(dest)

    for file in files:
        args = f'protoc -I={os.path.dirname(file)} --python_out={dest} {file}'
        print(f"Running '{args}'")

        ret = subprocess.call(args, shell=True)
        if ret:
            exit()

__all__ = ["create_vectors", "get_proto_files", "get_proto_libs", "pb_compile"]
