### Commands / Listeners

#### General

- `avatar` (alias `av`): Returns the Discord avatar URL for the mentioned user (or command issuer, if no user is mentioned)

- `ping`: For testing purposes (and fun). Checks that bot is connected and listening. 

- `purge` (alias `p`): **Mod-only**. Deletes the specified number of message from the current channel.

- `:mag: react`: When a mod reacts to a message with :mag: the messages is flagged and a log is sent to the logs channel

#### Tesseract

- `streamschedule` (alias `ss`): **Mod-only**. Interactive command, creates and sends an embed with a weekly Twitch stream schedule 
    - Simply respond to the bot's prompts (being sure to use the proper date time format)
    - The bot will preview the embed and request confirmation before sending 
    - Example usage: 
    <p align="center">
        <img src="docs/img/ss_example.gif" width="50%"/>
    </p>
