### Admin / Bot Configuration

???+ tldr "/set commands"
    `/set` is a group command that can be used to set a number of bot channel and settings.  
    Example usage: `/set channel videos #videos-and-clips`  

    | Sub-command | Arguments | Description |
    | :--- | :--- |:--- |
    | `prefix` | `new_prefix` | Set's the bot prefix for your guild. Does not affect slash commands | 
    | `channel` | - `target`: Which database entry to update. Options: `logs`, `bot`, `videos`<br>- `new_channel`: Channel to set as database entry | 
    | `modroles` | `mod_roles`: Role IDs or mentions | Sets the mod roles for your guild

???+ tldr "Admin chat commands"
    | Command | Arguments | Description |
    |---------|-----------|-------------|
    | `sync` | "guild" (required) | Syncs the bot's slash commands to your guild |
    