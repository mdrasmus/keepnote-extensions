#!/bin/bash
# install all extensions for testing


for x in $*; do
    y=$(basename ${x/.kne/})
    echo install $y
    keepnote --no-gui --cmd uninstall $y
    keepnote --no-gui --cmd install $x
done



