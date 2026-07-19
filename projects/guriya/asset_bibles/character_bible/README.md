# Character Bible

The character bible stores one folder per character. Each character folder contains
validated metadata, prompt guidance, notes, and manually generated image reference
slots.

## Required Files

- `character.yaml`
- `prompt.md`
- `notes.md`

## Required Folders

- `references/`
- `poses/`
- `expressions/`
- `wardrobe/`
- `voice/`

## Required Reference Images

`references/` must contain:

- `front.png`
- `back.png`
- `left.png`
- `right.png`
- `three_quarter.png`
- `full_body.png`
- `closeup.png`

`expressions/` must contain:

- `neutral.png`
- `happy.png`
- `sad.png`
- `crying.png`
- `angry.png`
- `thinking.png`
- `worried.png`
- `dua.png`
- `smile.png`

`poses/` must contain:

- `standing.png`
- `walking.png`
- `sitting.png`
- `running.png`
- `working.png`
- `holding_child.png`
- `sewing.png`
- `cooking.png`

`wardrobe/` must contain:

- `default.png`
- `dress_01.png`
- `dress_02.png`
- `winter.png`
- `wedding.png`
- `sleep.png`

Do not invent character appearances in metadata. Use approved visual references as the
source of truth.
