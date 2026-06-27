# Phase 7 — Discussion Log

**Date:** 2026-06-24 · Mode: discuss (default) · Human-reference only (not consumed downstream).

## Areas presented
Цены в Stars · Что даёт подписка · Где магазин/покупка · Отмена/возврат (+ «Something else»).

## Turns & decisions

1. **«Something else» → Provider pivot.** Owner: «не хочу оплату в Stars, хочу ЮKassa/ЮMoney».
   - Surfaced the locked-constraint conflict (ТЗ §2.2 Stars-only; Telegram requires Stars for
     digital goods in Mini Apps → external acquirer = ToS / catalog-rejection risk). Owner accepts
     the risk.
   - Q «Провайдер»: options Stars / ЮKassa-via-Telegram-Payments / ЮKassa-direct / обсудить →
     **selected: ЮKassa via Telegram Payments** (initially).

2. **Batch: цены / магазин / подписка / возвраты.**
   - Цены: owner didn't pick a preset — «всё в рублях; экономика приятная для ЦА, но покрывать
     хост+ИИ». → captured as D-15 (recommended seed + economics note; admin-tunable).
   - Магазин: **Paywall-шит + Профиль**.
   - Подписка: **сейчас (recurring)**.
   - Возвраты: **авто-эндпоинт**.

3. **Conflict resolve — recurring needs direct API.** Telegram Payments (ЮKassa provider_token)
   can't do recurring/auto-refund. Q «Интеграция»: options direct-API-all / hybrid / defer-sub →
   **selected: всё через прямой API ЮKassa**.

## Net result
Provider pivot Stars → **ЮKassa direct API (RUB)**: one-time packs + recurring «Лунный доступ»
subscription + refund API; shop in paywall sheet + profile; webhook re-verified server-side;
idempotent grant; consume order free→sub→paid (carried from P6); aiogram bot NOT needed.

## Deferred
Telegram Stars, aiogram bot, extended subscriber history (HIST-06), admin product CRUD + payment
analytics (Phase 8), self-serve refund button.
