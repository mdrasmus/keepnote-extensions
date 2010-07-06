#!/usr/bin/env python

import os
from subprocess import call

def make_ext(base, folder):
    print "make", folder
    ext = folder + ".kne"

    olddir = os.getcwd()
    os.chdir(base)

    call(["rm", "-f", ext])
    call(["zip", "-r", ext, folder])

    os.chdir(olddir)


base = "stable"
for ext in os.listdir(base):
    if os.path.isdir(os.path.join(base, ext)):
        make_ext(base, ext)


base = "testing"
for ext in os.listdir(base):
    if os.path.isdir(os.path.join(base, ext)):
        make_ext(base, ext)

