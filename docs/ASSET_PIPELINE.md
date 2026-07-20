# Asset Pipeline

AI Film Studio does not generate production asset images inside this repository.
Character, environment, wardrobe, expression, pose, and prop references are manually
generated or approved outside the framework, then stored in the project asset bible.

## How To Generate Images

Use the approved creative workflow for the production: Gemini, Flow, Veo, Kling, or
another image/video tool. Generate image references outside the repository, review
them manually, and only save approved production references into the asset folders.

Do not commit experimental generations, temporary variations, or unapproved identity
tests as final references.

## Where To Place Images

Character assets live in:

```text
projects/guriya/characters/<character_id>/
```

Environment assets live in:

```text
projects/guriya/environment/<environment_id>/
```

Prop assets live in:

```text
projects/guriya/props/<prop_id>/
```

Each image must be saved into the correct subfolder using the required filename. The
repository contains `.gitkeep` files in empty reference folders so the folders are
tracked without pretending image references exist.

## Naming Convention

Use lowercase snake case for asset ids and folder names:

```text
mother
sister_01
old_sewing_machine
village_bicycle
```

Character production references for compiler/default selector use:

```text
references/production/front.png
references/production/left_profile.png
references/production/three_quarter_left.png
references/production/three_quarter_right.png
references/production/full_body_front.png
references/production/full_body_back.png
references/production/seated_front.png
```

`references/master/master_sheet.png` identity review ke liye hai. Split crops
`references/views/` mein aa sakte hain, lekin woh `cropped_preview` hain aur default
compiler/selector unhein production references ke taur par use nahi karta.

Character expressions:

```text
expressions/neutral.png
expressions/happy.png
expressions/sad.png
expressions/crying.png
expressions/angry.png
expressions/thinking.png
expressions/worried.png
expressions/dua.png
expressions/smile.png
```

Character poses:

```text
poses/standing.png
poses/walking.png
poses/sitting.png
poses/running.png
poses/working.png
poses/holding_child.png
poses/sewing.png
poses/cooking.png
```

Character wardrobe:

```text
wardrobe/default.png
wardrobe/dress_01.png
wardrobe/dress_02.png
wardrobe/winter.png
wardrobe/wedding.png
wardrobe/sleep.png
```

Environment references:

```text
references/front_day.png
references/front_evening.png
references/front_night.png
references/back_day.png
references/back_evening.png
references/back_night.png
```

Environment angles:

```text
angles/front.png
angles/back.png
angles/left.png
angles/right.png
angles/top.png
angles/drone.png
angles/inside_to_outside.png
angles/outside_to_inside.png
```

Environment lighting:

```text
lighting/morning.png
lighting/afternoon.png
lighting/golden_hour.png
lighting/evening.png
lighting/night.png
lighting/rain.png
```

Props should place approved images in:

```text
references/
```

## Validation

Run validation from the repository root:

```bash
aifs validate-assets
```

To print more than the first 50 issues:

```bash
aifs validate-assets --max-issues 200
```

The validator checks:

- missing YAML files
- missing `prompt.md`
- missing `notes.md` for characters
- missing required folders
- missing reference images
- duplicate asset ids
- broken path fields inside asset YAML

Validation writes:

```text
projects/guriya/asset_index.json
```

If images are still awaiting approval, validation will report missing-image issues.
That is expected until the real image files are placed in the asset bible.

## Compilation

Prompt compilation should reference approved assets by stable id and path. The prompt
compiler must not generate missing image references or invent appearances. Asset
bible references are production inputs used by future compiler and QA stages.

Reference sheets can be split into reviewable cropped previews, but final
generation manifests should use separately generated approved HD production
references. See `docs/REFERENCE_SHEET_WORKFLOW.md` and
`docs/CHARACTER_SHEET_BATCH_WORKFLOW.md`.

## Best Practices

- Keep `reference_status: awaiting_reference` until approved images are present.
- Do not replace approved references silently.
- Keep character identity images separate from expression, pose, wardrobe, and voice notes.
- Use one stable folder per character, environment, or prop.
- Keep prompt templates generic and reusable.
- Do not store tool-specific temporary outputs as production references.
- Run `aifs validate-assets` before compiling production prompts.
