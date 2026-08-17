# Fast Rebound production setup checklist

1. In repository **Settings → Actions → General**, set workflow permissions to
   **Read and write permissions**.
2. Ensure branch protection permits the GitHub Actions bot to commit non-secret
   state to the default branch.
3. Create a Telegram bot with BotFather and send the bot one initial message in
   the intended destination.
4. In **Settings → Secrets and variables → Actions**, create exactly:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. Do not commit a populated `.env`; `.env*` is ignored except the blank
   `.env.example` template.
6. Run `python -m pytest` locally.
7. Run the non-persisting offline verification:
   `python run_daily_scan.py --dry-run --no-telegram --cache-mode cached`.
8. Optionally test Telegram only:
   `python run_daily_scan.py --telegram-test` with both environment variables set.
9. Open **Actions → Fast Rebound Daily Scanner → Run workflow** for the first
   manual production run.
10. Confirm a new audit record under `state/run_history/`, a recommendation
    snapshot under `state/recommendation_history/`, and the bot's `[skip ci]`
    state commit. The automatic schedule is 09:10 Asia/Seoul daily; the NYSE
    calendar safely skips dates with no new completed U.S. session.

No brokerage or IBKR credentials are used. This system cannot place real orders.
