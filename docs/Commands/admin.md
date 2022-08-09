### Admin / Bot Configuration

???+ tldr "Admin chat commands"
    | Command | Arguments | Description |
    |---------|-----------|-------------|
    | `;sync` | "guild" (required) | Syncs the bot's slash commands to your guild |

???+ tldr "/set commands"
    `/set` is a group command that can be used to set a number of bot channel and settings.  
    You can also `/unset` any `channel` or `role`. You cannot unset the bot prefix.  
    Example usage:  
        `/set channel lfg #gaming-room`  
        `/unset role dj`  
    
    | Subcommand | Arguments | Description |
    | :--- | :--- |:--- |
    | `prefix` | `new_prefix` | Set's the bot prefix for your guild. Does not affect slash commands | 
    | `mod_roles` | `mod_roles`: Role IDs or mentions | Sets the mod roles for your guild | 
    | `member_role` | `mod_roles`: Role IDs or mentions | Sets the DJ role for your guild (for music commands) |
    | `member_role` | `mod_roles`: Role IDs or mentions | Sets the member roles for your guild |
    | `channel` | - `target`: Which database entry to update.<br>&emsp;Options: `logs`, `bot`, `videos`*<br>- `new_channel`: Channel to set as database entry | 

    Note\*: If you set a `videos` channel, all messages containing videos will be moved to this channel.<br>You can allow videos in a channel by using `/allowvideos`, or allow videos in all channels again by using `/unset channel videos`
