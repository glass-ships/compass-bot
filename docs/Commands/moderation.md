???+ tldr "Chat commands (mod only)"
    | Command | Arguments | Description |
    | :--- | :--- | :--- |
    | `;modroles` |  | Get a list of the guild's mod roles. |
    | `;send` | `message`, `channel` (optional) | Send a `message` to a `channel`<br>Example usage: `;send "Some kinda message" #some-channel |
    | `;sendembed` | `channel`, `embed fields` | Send an `embed` to a `channel`. WIP |

???+ tldr "Slash Commands (mod only)"
    | Command | Arguments | Description |
    | :--- | :--- | :--- |
    | `purge` | `num`: Number of message to delete | Deletes the specified number of message from the current channel |
    | `moveto` | - `channel`: Destination channel<br>- `message id`: Message to be moved | Move a message to a specific channel |

???+ tldr "Mod reactions"
    | Reaction | Description |
    | :---| :--- |
    | 🔍`:mag:` | When a mod reacts to a message with 🔍(`:mag:`) the messages is flagged and a log is sent to the logs channel<br>**Note:** requires that a logs channel be set |
