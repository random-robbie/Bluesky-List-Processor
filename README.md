# Bluesky List Processor

This script processes Bluesky lists or feeds and allows you to perform bulk **block** or **mute** actions on users. It can operate in a "dry-run" mode to preview the actions without making any changes and saves the list of processed users to a JSON file for review.

## Features

- **Convert Bluesky feed/list URLs to AT URIs** automatically.
- Fetch unique users from a feed or list.
- Perform bulk **block** or **mute** actions on users.
- **Dry-run mode** to preview actions without applying them.
- Save processed users to a JSON file for auditing.

## Requirements

- Python 3.8 or higher
- A Bluesky account
- Environment variables for authentication:
  - `BSKY_USERNAME` (your Bluesky username)
  - `BSKY_PASSWORD` (your Bluesky password)

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/random-robbie/Bluesky-List-Processor.git
   cd bluesky-list-processor```

2. Run:

```
usage: bsky-blocker.py [-h] --action {block,mute} [--dry-run] [--output OUTPUT] [--limit LIMIT] list_url

Convert a Bluesky list or feed into a block or mute list

positional arguments:
  list_url              The URL or AT URI of the list (e.g., https://bsky.app/profile/user.bsky.social/feed/abc)

options:
  -h, --help            show this help message and exit
  --action {block,mute}
                        Whether to block or mute users
  --dry-run             Only print what would be done without actually blocking/muting
  --output OUTPUT       Output JSON file for the user list (default: users_to_process.json)
  --limit LIMIT         Number of posts to fetch from feed (default: 100)
```

3. In action:

```
python3 bsky-blocker.py https://bsky.app/profile/did:plc:jdkvwye2lf4mingzk7qdebzc/feed/furry-new --dry-run --action block
```
