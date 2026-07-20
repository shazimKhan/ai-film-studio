# Guriya Project

This folder contains the first production planning structure for `guriya`.

The project is set in Taxila, Punjab, Pakistan, in 1988. The structure is designed
for later AI Director, Story Engine, Scene Compiler, Prompt Compiler, QA, and
Exporter stages.

## Folder Map

- `01_story/`: episode story outline and narrative spine.
- `02_characters/`: production prompt packs for principal recurring characters.
- `03_locations/`: reusable location prompt packs and continuity rules.
- `04_scenes/`: scene-level episode structure.
- `05_shots/`: shot-level metadata and batch files.
- `06_image_prompts/`: generated image prompt outputs.
- `07_video_prompts/`: generated video motion prompt outputs.
- `08_generated_images/`: manually generated or tool-generated image outputs.
- `09_generated_videos/`: rendered video outputs.
- `10_voiceover/`: narration and dialogue, separated from video prompts.
- `11_music_sfx/`: music and sound cue metadata.
- `12_editing/`: edit plan and timeline notes.
- `qa/`: shot and episode quality checks.
- `exports/`: final exported artifacts.

## Production Rules

- One shot contains one main action, one emotion, and one camera instruction.
- Shot durations stay between 4 and 8 seconds.
- Video prompts focus on motion; keyframe images define appearance.
- Dialogue and narration are never embedded inside video prompts.
- Guriya identity consistency is locked through the character master prompt and
  approved production references.
