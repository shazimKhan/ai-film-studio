# AI Film Studio

Production-grade AI Filmmaking Framework.

AI Film Studio is being built as a reusable AI filmmaking operating system. The
current milestone provides a working local Prompt Compiler v1: it reads a
validated scene blueprint, resolves reusable project assets, builds structured
cinematic prompt sections, formats them through an engine adapter, and writes a
versioned prompt file.

## Installation

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Example Command

From the repository root:

```bash
aifs compile projects/guriya/episode_01/scene_02/clip_001.yaml --engine gemini
```

Equivalent module entry point:

```bash
python -m ai_film_studio.cli compile projects/guriya/episode_01/scene_02/clip_001.yaml --engine gemini
```

The command prints the generated output path.

## Scene YAML Format

Scene blueprints are YAML files with validated required fields:

```yaml
project: guriya
episode: episode_01
scene: scene_02
clip: clip_001
title: "Courtyard Before Dusk"
duration: 8
action: "What happens in the clip."
emotion: "The intended emotional state."
characters:
  - id: guriya
    module: ../../characters/guriya.yaml
world:
  id: taxila_1988
  module: ../../worlds/taxila_1988.yaml
camera:
  shot_size: "medium close-up"
  angle: "child-height perspective"
  lens: "35mm"
  movement: "slow push-in"
  framing: "doorway frame within frame"
  focus: "eyes sharp, background soft"
lighting:
  quality: "soft natural light"
  source: "late-afternoon sun"
  color_temperature: "warm amber"
  contrast: "gentle"
  mood: "tense and intimate"
motion:
  subject: "subtle body movement"
  environment: "dust motes drift"
  camera: "controlled push-in"
  pace: "restrained"
continuity:
  previous_clip: "What came before."
  visual_state: "Current visual continuity."
  prop_state: "Important prop continuity."
  emotional_state: "Current emotional continuity."
negative prompts:
  - "modern objects"
  - "text overlays"
```

Reusable character and world modules can be YAML or Markdown, but Prompt
Compiler v1 expects referenced character and world identity assets to be YAML
mappings. Example assets live at:

- `projects/guriya/characters/guriya.yaml`
- `projects/guriya/worlds/taxila_1988.yaml`

## Generated Output

For the included Guriya example, Gemini prompts are written to:

```text
output/guriya/episode_01/scene_02/clip_001/gemini_prompt_v1.txt
```

Existing prompts are not overwritten. Re-running the same command creates the
next available version, such as `gemini_prompt_v2.txt`.

## Asset Bible Validation

Production image references are generated manually outside this repository and stored
under the project asset bible folders. Validate the asset structure and generate the
asset index with:

```bash
aifs validate-assets
```

This writes:

```text
projects/guriya/asset_index.json
```

See `docs/ASSET_PIPELINE.md` for naming conventions, validation rules, and best
practices.

## Current Limitations

- Local prompt compilation only.
- No Gemini API calls yet.
- Gemini support currently means prompt formatting through `GeminiAdapter`.
- Guriya is demo project data, not compiler logic.
- Prompt Compiler v1 resolves character and world assets from local YAML files.
- Asset reference images are manually generated and may be awaiting approval.

## Features

- AI Director
- Prompt Compiler
- Scene Compiler
- Identity Engine
- QA Engine
- Multi-engine support
