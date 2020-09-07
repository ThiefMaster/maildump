#!/bin/bash

# Delete existing (old) assets
rm -rf maildump/static/.webassets-cache/ maildump/static/assets/bundle.*
# Build current assets
webassets -m maildump.web build
webassets -m maildump.web build --production
# Create release wheel
python setup.py bdist_wheel
# Delete assets again, we don't need them anymore
rm -rf maildump/static/.webassets-cache/ maildump/static/assets/bundle.*
