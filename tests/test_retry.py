"""Tests for retry_with_backoff utility."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from rpothin_powerplatform.utils import HttpError, retry_with_backoff


class TestRetryWithBackoff:
    """Tests for the retry_with_backoff helper."""

    @pytest.mark.asyncio
    async def test_success_on_first_call(self):
        fn = AsyncMock(return_value="ok")
        result = await retry_with_backoff(fn, max_retries=3, base_delay=0.01)
        assert result == "ok"
        fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retries_on_429(self):
        sleep = AsyncMock()
        fn = AsyncMock(
            side_effect=[HttpError(429, "rate limited"), "ok"],
        )
        result = await retry_with_backoff(fn, max_retries=3, base_delay=0.01, _sleep=sleep)
        assert result == "ok"
        assert fn.await_count == 2
        sleep.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retries_on_500(self):
        sleep = AsyncMock()
        fn = AsyncMock(
            side_effect=[HttpError(500, "server error"), "ok"],
        )
        result = await retry_with_backoff(fn, max_retries=3, base_delay=0.01, _sleep=sleep)
        assert result == "ok"
        assert fn.await_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_502(self):
        sleep = AsyncMock()
        fn = AsyncMock(
            side_effect=[HttpError(502, "bad gateway"), "ok"],
        )
        result = await retry_with_backoff(fn, max_retries=3, base_delay=0.01, _sleep=sleep)
        assert result == "ok"
        assert fn.await_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_503(self):
        sleep = AsyncMock()
        fn = AsyncMock(
            side_effect=[HttpError(503, "service unavailable"), "ok"],
        )
        result = await retry_with_backoff(fn, max_retries=3, base_delay=0.01, _sleep=sleep)
        assert result == "ok"
        assert fn.await_count == 2

    @pytest.mark.asyncio
    async def test_does_not_retry_on_400(self):
        fn = AsyncMock(side_effect=HttpError(400, "bad request"))
        with pytest.raises(HttpError) as exc_info:
            await retry_with_backoff(fn, max_retries=3, base_delay=0.01)
        assert exc_info.value.status_code == 400
        fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_does_not_retry_on_404(self):
        fn = AsyncMock(side_effect=HttpError(404, "not found"))
        with pytest.raises(HttpError) as exc_info:
            await retry_with_backoff(fn, max_retries=3, base_delay=0.01)
        assert exc_info.value.status_code == 404
        fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_does_not_retry_on_non_http_error(self):
        fn = AsyncMock(side_effect=ValueError("bad value"))
        with pytest.raises(ValueError):
            await retry_with_backoff(fn, max_retries=3, base_delay=0.01)
        fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stops_after_max_retries(self):
        sleep = AsyncMock()
        fn = AsyncMock(side_effect=HttpError(429, "rate limited"))
        with pytest.raises(HttpError) as exc_info:
            await retry_with_backoff(fn, max_retries=3, base_delay=0.01, _sleep=sleep)
        assert exc_info.value.status_code == 429
        # Called max_retries + 1 times total (initial + 3 retries)
        assert fn.await_count == 4
        assert sleep.await_count == 3

    @pytest.mark.asyncio
    async def test_respects_retry_after_header(self):
        sleep = AsyncMock()
        fn = AsyncMock(
            side_effect=[
                HttpError(429, "rate limited", headers={"Retry-After": "2.5"}),
                "ok",
            ],
        )
        result = await retry_with_backoff(fn, max_retries=3, base_delay=0.01, _sleep=sleep)
        assert result == "ok"
        # Should use the Retry-After value (2.5s) instead of computed backoff
        sleep.assert_awaited_once()
        actual_delay = sleep.call_args[0][0]
        assert actual_delay == 2.5

    @pytest.mark.asyncio
    async def test_exponential_backoff_increases(self):
        sleep = AsyncMock()
        fn = AsyncMock(
            side_effect=[
                HttpError(500, "error"),
                HttpError(500, "error"),
                HttpError(500, "error"),
                "ok",
            ],
        )
        result = await retry_with_backoff(fn, max_retries=5, base_delay=1.0, _sleep=sleep)
        assert result == "ok"
        assert sleep.await_count == 3
        delays = [call[0][0] for call in sleep.call_args_list]
        # Each delay should be at least base_delay * 2^attempt (before jitter)
        # attempt 0: >= 1.0, attempt 1: >= 2.0, attempt 2: >= 4.0
        assert delays[0] >= 1.0
        assert delays[1] >= 2.0
        assert delays[2] >= 4.0

    @pytest.mark.asyncio
    async def test_success_after_multiple_retries(self):
        sleep = AsyncMock()
        fn = AsyncMock(
            side_effect=[
                HttpError(429, "rate limited"),
                HttpError(503, "unavailable"),
                HttpError(500, "error"),
                "finally ok",
            ],
        )
        result = await retry_with_backoff(fn, max_retries=5, base_delay=0.01, _sleep=sleep)
        assert result == "finally ok"
        assert fn.await_count == 4
        assert sleep.await_count == 3

    @pytest.mark.asyncio
    async def test_zero_retries_means_single_attempt(self):
        fn = AsyncMock(side_effect=HttpError(429, "rate limited"))
        with pytest.raises(HttpError):
            await retry_with_backoff(fn, max_retries=0, base_delay=0.01)
        fn.assert_awaited_once()


class TestHttpError:
    """Tests for the HttpError class."""

    def test_status_code_and_message(self):
        err = HttpError(429, "rate limited")
        assert err.status_code == 429
        assert str(err) == "rate limited"
        assert err.headers == {}

    def test_headers(self):
        err = HttpError(429, "rate limited", headers={"Retry-After": "10"})
        assert err.headers["Retry-After"] == "10"
