#!/bin/bash
python3 -m grpc_tools.protoc -I. --python_out=generated --grpc_python_out=generated qir.proto
