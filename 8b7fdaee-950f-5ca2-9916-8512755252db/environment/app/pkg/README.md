widgetlib
=========

A tiny pure-Python package used as build input. It exposes ``__version__`` and a
deterministic ``compute(n)`` function that returns the sum of the first ``n``
squares plus a fixed offset. This source tree is the input to an offline
build/index/install pipeline and must not be modified.
