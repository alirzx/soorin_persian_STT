# No exporter dependency is loaded in core runtime. Plug a privacy-reviewed OTel exporter here.
from contextlib import contextmanager
@contextmanager
def trace_span(name:str):
    yield
