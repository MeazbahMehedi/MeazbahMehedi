# Automatic profile updates

The profile refreshes hourly at minute 23 using public GitHub data. Run **Refresh profile animations** manually from the Actions tab for an earlier refresh.

## Four current projects
The four nonempty, original public repositories with the most recent default-branch commit dates are selected. New projects enter automatically when their commit dates place them in the newest four. Forks, archived repositories, and the profile repository are excluded. Add the repository topic `profile-hidden` to exclude a project.

Status is **Working on** while the most recent default-branch commit is less than 20 days old. At exactly 20 full days (480 hours) without a commit, status becomes **Finished**. A new default-branch commit automatically restores **Working on**. This is an inactivity rule, not verified completion; no topics, releases or manual updates are required. Repository description edits and tag-only pushes do not reset the timer.

Descriptions come from each repository's GitHub description. Keep those descriptions up to date to improve the cards. Actual default-branch commit dates select projects; descriptions summarize the project rather than guessing what individual commits achieved.

## Languages and tools
Language icons are ranked by GitHub code bytes across owned public repositories. Supported framework badges come from root dependency manifests. Docker and GitHub Actions are detected from configuration. Unsupported languages and tools do not get invented icons. Local-only work and unrecorded editor usage cannot be detected.

## Reliability
All API reads and section checks finish before generated text is saved. A failed sync stops publishing, preserves the last published sections, and makes the workflow status badge show the failure. Existing artwork generation renders cards from the synced data. Generated README changes are committed with assets.

The mindset image has dark, light and static variants. The original quotation remains readable below it.

## Featured projects
Current work remains the newest four repositories. Featured cards are selected independently using a deterministic score: activity up to 30 points (60-day exponential decay), a root README 20, a description 10, a stable release 20, and stars up to 20 (logarithmic). Ties use commit date then repository name. Forks, archived repositories, hidden repositories, and the profile are excluded. This is a portfolio heuristic, not a code-quality assessment.

## Readability and research
Text is shortened at sentence or word boundaries with an ellipsis. Each card includes its latest commit age and stars. Technology rows show up to eight supported icons; framework order uses the number of repositories declaring each dependency.

Research candidates are identified from repository names, descriptions and topics. Up to four recent candidates are checked for reports or papers in PDF format, result summaries and data, and stable releases. Only files actually returned by GitHub are linked; large truncated trees are skipped. Paths link to GitHub's file viewer.

The profile shows the latest successful sync time in UTC and a workflow status badge. The 20-day Finished rule remains based only on the default-branch commit date.
