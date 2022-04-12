
#### General Commands

???+ tldr "Slash Commands"
    | Command | Arguments | Description |
    | :--- | :--- | :--- |
    | `avatar` | `None` | Get a user's Discord avatar |
    | `banner` | `None` | Get a user's Discord banner |
    | `ping` | `None` | Returns "Pong!" and the ping latency. |

???+ tldr "Chat Commands"

#### Moderation

???+ tldr "Slash Commands (mod only)"
    | Command | Arguments | Description |
    | :--- | :--- | :--- |
    | `purge` | `num`: Number of message to delete | Deletes the specified number of message from the current channel. |

???+ tldr "Chat Commands (mod only)"
    | Command | Arguments | Description |
    | :---| :--- | :--- |
    | Reaction: `:mag:` | When a mod reacts to a message with `:mag:` the messages is flagged and a log is sent to the logs channel |
    | `moveto` | `channel`: Destination channel<br>`message id`: Message to be moved | Move a message to a specific channel |

#### Admin / Bot Configuration

???+ tldr "Admin Commands - Setting up the bot"
    | Command | Arguments | Description |
    |---------|-----------|-------------|
    | `setprefix` | New prefix | Sets the bot prefix for your guild (default: `;`) |
    | `setmodroles` | Role ID's or mentions | Sets the mod roles for your guild |
    | `setlogschannel` | Channel ID or link | Sets the logs channel for your guild |
    | `sync` | "guild" (required) | Syncs the bot's slash commands to your guild |