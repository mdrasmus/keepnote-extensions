#!/usr/bin/env python
# Script for building KeepNote extensions


import os
from subprocess import call

def make_ext(base, folder):
    ext = folder + ".kne"

    olddir = os.getcwd()
    os.chdir(base)

    call(["rm", "-f", ext])
    call(["zip", "-r", ext, folder])

    os.chdir(olddir)


def make_ext_set(base):
    for ext in os.listdir(base):
        if os.path.isdir(os.path.join(base, ext)):
            print "make", ext
            make_ext(base, ext)


for ext_set in ["builtin", "stable", "testing"]:
    make_ext_set(ext_set)

