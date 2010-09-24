#!/usr/bin/env python
# Script for building KeepNote extensions


import os
from subprocess import call, Popen, PIPE

def make_ext(base, folder):
    ext = folder + ".kne"

    olddir = os.getcwd()
    os.chdir(base)

    call(["rm", "-f", ext])
    call(["zip", "-r", ext, folder])

    os.chdir(olddir)


def clear_pyc(base):
    for root, dirs, files in os.walk(base):
        for fn in files:
            if fn.endswith(".pyc"):
                full = os.path.join(root, fn)
                print "remove", full
                os.remove(full)
    


def make_ext_set(base):
    clear_pyc(base)

    for ext in os.listdir(base):
        if os.path.isdir(os.path.join(base, ext)):
            print "make", ext
            make_ext(base, ext)


for ext_set in ["builtin", "stable", "testing"]:
    make_ext_set(ext_set)

