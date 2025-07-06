### Moderation Commands

Compass has a few commands that can be used to moderate your server.  
These commands are only available to users with roles set via the `/ set mod_roles` command.

???+ tldr "Chat commands (mod only)"
    | Command | Arguments | Description |
    | :--- | :--- | :--- |
    | `;sendembed` | `channel`, `embed fields` | Send an `embed` to a `channel` |
    | `;lastmessage` | `user` (id or mention) | Get the last message from a user (if you have `/set track_activity` to true) |

    `;sendembed` supported fields:
    
    - title
    - description
    - image (url)
    - footer
    - footer image

    Example of `;sendembed`:  
        
        ;sendembed #bot-testing --title Example Title --description Example description for an embed --image https://media.discordapp.net/attachments/954197737140793365/954270177208467467/unknown.png --footer peekabo --footer-image https://glass-ships.gitlab.io/compass-bot/images/compassBkgd.png

???+ tldr "Slash Commands (mod only)"
    | Command | Arguments | Description |
    | :--- | :--- | :--- |
    | `send` | `message`, `channel` (optional) | Send a `message` to a `channel`<br>Example usage: `;send "Some kinda message" #some-channel |
    | `dm` | `user`, `message` | Send a `message` to a `user` |
    | `moveto` | - `channel`: Destination channel<br>- `message id`: Message to be moved | Move a message to a specific channel (also available as a right-click menu command) |
    | `purge` | `number` | Deletes the specified number of message from the current channel |
    | `giverole` | `user`, `role`, `duration` (in seconds) | Give a `role` to a `user`, optionally for a `duration` |
    | `removerole` | `user`, `role`, `duration` (in seconds) | Remove a `role` from a `user`, optionally for a `duration` |
    | `getmodroles` |  | Get a list of the guild's mod roles. |
    | `checkroles` | | Check for any users missing one of your server's required roles (if set) |
    | `checkinactive` | `number of days` | Check for inactive users (haven't sent a message in the last `number of days`), if you have `/set track_activity` to true |


???+ tldr "Mod reactions"
    | Reaction | Description |
    | :---| :--- |
    | 🔍`:mag:` | When a mod reacts to a message with 🔍(`:mag:`) the messages is flagged and a log is sent to the logs channel<br>**Note:** requires that a logs channel be set |
