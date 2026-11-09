def run_agent_blocking(port, supplied):
    app = supplied
    return uvicorn.run(app, host='127.0.0.1', port=port, log_level='info', timeout_keep_alive=120)
