from fastapi import Request

from sentriflow.runtime import Runtime


def get_runtime(request: Request) -> Runtime:
    return request.app.state.runtime
