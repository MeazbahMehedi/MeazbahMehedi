# Automatic account sync

All automation lives in `MeazbahMehedi/MeazbahMehedi`. The profile reads account activity and updates only this repository. No source-project workflows, webhooks or edits are needed.

## Current work and status

The four latest default-branch commit dates determine the current-work entries. New public repositories are discovered automatically on each refresh. A reported repository size of zero no longer excludes a project; the sync checks for actual commits. Truly empty repositories are skipped. Forks, archived repositories, disabled repositories, and the profile itself are excluded.

A commit less than seven full days old is **Working on**. At seven days (168 hours) the project becomes **Under future development**. A new default-branch commit restores **Working on**. This is an inactivity rule, not a claim of verified completion. Description edits and tag pushes do not reset the timer.

The displayed time uses **Asia/Shanghai — China Standard Time (UTC+08:00)**. Elapsed-day calculations use absolute timestamps, keeping the seven-day boundary consistent.

## Refresh schedule

The profile checks account activity every five minutes. A lightweight comparison covers public repository metadata, default-branch commits, releases, contribution counts, approved private summaries, and elapsed-day status changes. It runs the full generators and publishes only when those inputs change. Manual runs and profile code changes force a full refresh. Unchanged checks do not create commits merely to advance a timestamp. GitHub may delay or drop scheduled executions, so these are requested times, not a guaranteed maximum delay. For an immediate refresh use **Actions → Refresh profile animations → Run workflow** in this repository. No cross-repository push triggers are used.

## Private summaries

Only **scholarsend** and **KeyFlow** are approved for public summary display in `data/profile-config.json`. Their most recently observed summaries are saved in `data/private-projects.json`. The only published private fields are project name, bounded description, and latest default-branch commit date. Private code, files, commit messages, URLs, language statistics, reports, and release links are never published.

To keep private activity updating automatically, add an Actions repository secret **PROFILE_PRIVATE_READ_TOKEN** in this profile repository. Use a fine-grained GitHub token with **Contents: read-only** and metadata access to only the two approved private repositories. The workflow reads repository descriptions and commit dates, not private file contents. The ChatGPT connector's account access is separate from GitHub Actions credentials and is not inherited by workflow jobs.

Create the secret here:
https://github.com/MeazbahMehedi/MeazbahMehedi/settings/secrets/actions

Do not paste the token into chat or commit it into a file. No secrets or edits are required in any source repository. Without the secret, public discovery remains automatic, while private summaries retain their last observed activity. A warning in the workflow logs makes the missing credential visible.

Additional private projects require adding their names to the allowlist in this profile repository and granting the read token access. Unknown private projects are never made public automatically. Removing a name from the allowlist removes its summary at the next refresh.

## Featured projects and supporting sections

Four featured cards are selected independently using recent commits, documentation, releases, and stars. Private cards contain only the approved summary, without a repository link or inferred technologies. Research links and technology detection use public repositories only. Text is shortened at word or sentence boundaries, and technology rows show up to eight supported icons.

## Reliability

Expected empty-repository responses do not stop discovery. Unexpected public API failures stop publication and keep the last published profile intact. Private-read errors preserve the affected approved summary and log a warning. The workflow badge shows failures; the China-time timestamp records the last successful sync. Tests cover the seven-day boundary, reactivation, zero-size repositories, private metadata filtering, private-read failures, and China-time date rollover.
