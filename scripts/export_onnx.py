#!/usr/bin/env python3
"""ONNX export is model-specific; pre-exported audited Shenava artifacts are used.

This script deliberately never silently exports a different model graph.
"""
import sys
print('Use pre-exported Shenava or Nemotron ONNX from the selected model catalog. See docs/MODELS.md.')
sys.exit(2)
