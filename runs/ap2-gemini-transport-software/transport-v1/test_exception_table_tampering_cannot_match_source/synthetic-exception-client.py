class Synthetic:
    def send(self, request):
        try:
            return request
        finally:
            self.finished = True
