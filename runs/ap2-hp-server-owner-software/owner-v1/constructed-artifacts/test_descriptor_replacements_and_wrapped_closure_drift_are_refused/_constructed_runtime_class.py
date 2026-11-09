class Runtime:
    def __init__(self, value=(True,)):
        self.value = value
    @property
    def readonly(self):
        return True
    @functools.cached_property
    def cached(self):
        return None
    @contextlib.contextmanager
    def signals(self):
        yield None
