# Endpoint for images

## Classes

`https://cdn.wynncraft.com/nextgen/classes/icons/{class name}.svg` (item representation)
`https://cdn.wynncraft.com/nextgen/classes/icons/artboards/{class_name}.webp` (badge icon)

- archer (hunter)
- warrior (knight)
- assassin (ninja)
- mage (dark wizard)
- shaman (skyseer)

## Professions and other levels

`https://cdn.wynncraft.com/nextgen/classes/professions/{profession}.webp` (profession icon)
`https://cdn.wynncraft.com/nextgen/skill/{skill}_book.svg` (skill book)

I will need a way to convert SVG into PNG.
One solution is to use custom emojis.
I think there could be default values but I will put an option to create the emojis on a specified server.
This will maybe be done in the future.

# Time (e.g. join)

2022-11-23T16:49:54.563Z

## Format

It's the ISO 8601 format, available in python using the format `"%Y-%m-%dT%H:%M:%S.%fZ"` (in python use `datetime.strptime`).

# Player representation

The generator used by the official Wynncraft website is available here:
`https://visage.surgeplay.com/bust/{UUID}`

## Embed format

This are the structure of the embeds I'm looking for.
(use a website like `discohook` to render the message)

### Large embed

```json
{
  "content": null,
  "embeds": [
    {
      "title": "ascpial",
      "description": "**First joined** <t:1669218594:D>\n\n**Total levels** 141\n**Total playtime** 20 hours\n**Total mobs killed**  3,079 mobs\n\n**Guild** No guild\n\n**Characters**",
      "color": 12233344,
      "fields": [
        {
          "name": ":dagger: Assassin",
          "value": "Combat: 38\nTotal: 103"
        },
        {
          "name": ":axe: Warrior",
          "value": "Combat: 15\nTotal: 38"
        }
      ],
      "footer": {
        "text": "Last seen"
      },
      "timestamp": "2022-11-29T00:32:00.000Z",
      "thumbnail": {
        "url": "https://visage.surgeplay.com/bust/3f6ddb7c-f214-48a9-9f4a-eb22b9cf53f0"
      }
    }
  ],
  "attachments": []
}
```

## Small embed

```json
{
  "content": null,
  "embeds": [
    {
      "title": "ascpial",
      "description": "**Total levels** 141\n**Total playtime** 20 hours\n\n**Guild** No guild",
      "color": 12233344,
      "footer": {
        "text": "Last seen"
      },
      "timestamp": "2022-11-29T00:32:00.000Z",
      "thumbnail": {
        "url": "https://visage.surgeplay.com/bust/3f6ddb7c-f214-48a9-9f4a-eb22b9cf53f0"
      }
    }
  ],
  "attachments": []
}
```