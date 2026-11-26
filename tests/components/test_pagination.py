"""Tests for the reusable Pagination view."""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from compass.components.pagination import Pagination


def _itx(user_id: int) -> MagicMock:
    itx = MagicMock()
    itx.user.id = user_id
    itx.response.send_message = AsyncMock()
    return itx


def _pages(n_items: int, per_page: int = 10):
    def get_page(page: int):
        return discord.Embed(title=f"Page {page}"), Pagination.compute_total_pages(n_items, per_page)

    return get_page


def test_author_check_is_the_hook_discord_calls():
    # Regression: it was named itx_check, which discord.py never calls, so anyone could turn the pages
    assert Pagination.interaction_check is not discord.ui.View.interaction_check


async def test_author_can_turn_pages():
    author = _itx(1)
    view = Pagination(author, _pages(30))
    assert await view.interaction_check(_itx(1)) is True


async def test_others_are_refused():
    view = Pagination(_itx(1), _pages(30))
    other = _itx(2)

    assert await view.interaction_check(other) is False

    call = other.response.send_message.call_args
    assert "Only the author" in call.kwargs["embed"].description
    assert call.kwargs["ephemeral"] is True


@pytest.mark.parametrize("items, expected", [(0, 1), (1, 1), (10, 1), (11, 2), (25, 3)])
def test_compute_total_pages(items, expected):
    assert Pagination.compute_total_pages(items, 10) == expected


@pytest.mark.parametrize("items", [pytest.param(0, id="empty"), pytest.param(5, id="one page")])
async def test_init_single_page_shows_embed_without_buttons(items):
    # Regression: an empty list gave 0 pages, so init() never edited the message and no result was shown
    itx = _itx(1)
    message = MagicMock(edit=AsyncMock())
    itx.original_response = AsyncMock(return_value=message)

    await Pagination(itx, _pages(items)).init()

    message.edit.assert_awaited_once()
    assert message.edit.call_args.kwargs["embed"].title == "Page 1"
    assert "view" not in message.edit.call_args.kwargs


async def test_init_multiple_pages_adds_buttons():
    itx = _itx(1)
    message = MagicMock(edit=AsyncMock())
    itx.original_response = AsyncMock(return_value=message)

    view = Pagination(itx, _pages(25))
    await view.init()

    assert message.edit.call_args.kwargs["view"] is view
    assert view.children[0].disabled  # "previous" is disabled on page 1
