from fastapi import FastAPI
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.domain.exceptions import (
    ExperimentNotFoundError,
    FeatureFlagAlreadyExistsError,
    FeatureFlagNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from src.domain.exceptions.experiment import CannotReviewExperimentError


def setup_exc_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValueError)
    async def value_error_exception_handler(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": str(exc)},
        )

    @app.exception_handler(UserNotFoundError)
    async def user_not_found_exception_handler(
        request: Request, exc: UserNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": exc.message},
        )

    @app.exception_handler(UserAlreadyExistsError)
    async def user_already_exists_exception_handler(
        request: Request, exc: UserAlreadyExistsError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": exc.message},
        )

    @app.exception_handler(FeatureFlagNotFoundError)
    async def feature_flag_not_found_exception_handler(
        request: Request, exc: FeatureFlagNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": exc.message},
        )

    @app.exception_handler(FeatureFlagAlreadyExistsError)
    async def feature_flag_already_exists_exception_handler(
        request: Request, exc: FeatureFlagAlreadyExistsError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": exc.message},
        )

    @app.exception_handler(ExperimentNotFoundError)
    async def experiment_not_found_exception_handler(
        request: Request, exc: ExperimentNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": exc.message},
        )

    @app.exception_handler(CannotReviewExperimentError)
    async def cannot_review_experiment_exception_handler(
        request: Request, exc: CannotReviewExperimentError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": exc.message},
        )
