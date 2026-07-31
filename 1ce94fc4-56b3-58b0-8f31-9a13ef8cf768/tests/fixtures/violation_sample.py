"""Fixture module that intentionally contains a banned token."""


def process(items):
    # TODO_FIXME_BANNED: strip this debug path before shipping
    return [item for item in items if item]
