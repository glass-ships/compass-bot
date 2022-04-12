
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
    | Reaction: `:mag:` | When a mod reacts to a message with :mag: the messages is flagged and a log is sent to the logs channel |
    | `moveto` | `channel`: Destination channel<br>`message id`: Message to be moved | Move a message to a specific channel |

#### Admin / Bot Configuration

???+ tldr "Bot Configuration (admin only)"
    | Command | Arguments | Description |
    |---------|-----------|-------------|
    | `set_prefix` | New prefix | Sets the bot prefix for your guild (default: `;`) |
    | `set_mod_roles` | Role ID's or mentions | Sets the mod roles for your guild |
    | `set_logs_channel` | Channel ID or link | Sets the logs channel for your guild |
    | `sync` | None, "all", or Guild IDs | Syncs the bot's slash commands globally, or to a list of guilds</br>(ex. `;sync` `;sync all` or `;sync 987654321123456789`) |