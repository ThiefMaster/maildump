#!/bin/bash

# Build assets
npm run build
# Create release wheel
python setup.py bdist_wheel
