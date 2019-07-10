from ._executor import ProxyExecutor


def run(executor: dict):
    return {
        'executor': ProxyExecutor(**executor)
    }
