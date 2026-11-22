# Automatic profile updates

The profile refreshes hourly at minute 23 using public GitHub data. Run **Refresh profile animations** manually from the Actions tab for an earlier refresh.

## Four current projects
The four most recently pushed, nonempty, original public repositories are selected. Forks, archived repositories, and the profile repository are excluded. Add the repository topic `profile-hidden` to exclude a project.

Status is **Working on** by default. A published stable release is shown as **Released** until a newer default-branch commit appears. Add the topic `profile-completed` to explicitly mark a project **Completed**. No completion claims are inferred from inactivity.

Descriptions come from each repository's GitHub description. Keep those descriptions up to date to improve the cards. Recent pushes select projects; descriptions summarize the project rather than guessing what individual commits achieved.

## Languages and tools
Language icons are ranked by GitHub code bytes across owned public repositories. Supported framework badges come from root dependency manifests. Docker and GitHub Actions are detected from configuration. Unsupported languages and tools do not get invented icons. Local-only work and unrecorded editor usage cannot be detected.

## Reliability
All API reads and section checks finish before generated text is saved. A failed sync preserves existing sections and project data; the workflow logs a warning and continues refreshing graphs. Existing artwork generation renders cards from the synced data. Generated README changes are committed with assets.

The mindset image has dark, light and static variants. The original quotation remains readable below it.
