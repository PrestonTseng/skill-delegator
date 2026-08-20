"""Repository-wide pytest configuration.

Checked-out configuration is validated by a read-only integration test. Mutation-capable tests
must instead use the confined helpers in :mod:`tests.fixture_safety`.
"""
