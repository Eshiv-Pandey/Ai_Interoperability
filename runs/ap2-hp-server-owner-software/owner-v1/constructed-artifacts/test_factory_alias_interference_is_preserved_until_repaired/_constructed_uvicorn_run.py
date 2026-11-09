def run(app, **kwargs):
    config = Config(app, **kwargs)
    server = Server(config=config)
    return server.run()
