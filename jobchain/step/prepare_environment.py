from ._executor import ProxyExecutor


def run(executor: dict = None):
    return {
        'executor': ProxyExecutor(**executor or {})
    }
