from fastapi import Request

from sentriflow.application import Runtime


def runtime(request: Request) -> Runtime:
    return request.app.state.runtime  # type: ignore[no-any-return]
