"""Service layer — thick business logic that thin routers (and later the bot/admin) reuse.

Routers under ``app/api`` stay thin and delegate here so the same logic can be called from
the aiogram bot handlers (Phase 7) without going through HTTP.
"""
