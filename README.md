# AI Film Studio

Production-grade AI Filmmaking Framework.

AI Film Studio is being built as a reusable AI filmmaking operating system. The
current milestone provides a working local Prompt Compiler v1: it reads a
validated scene blueprint, resolves reusable project assets, builds structured
cinematic prompt sections, formats them through an engine adapter, and writes a
versioned prompt file.

## V3 Architecture

AI Film Studio now separates production work into three layers:

- `engine/`: reusable engine responsibility map. Current Python implementation lives
  under `src/ai_film_studio`.
- `shared/`: reusable schemas, templates, prompt blocks, validators, and shared asset
  library metadata.
- `projects/`: isolated production projects such as `guriya` and `insan`.

The engine must not contain project-specific story content. A project owns its own
research, assets, episodes, scenes, shots, prompts, generated media, QA, and exports.

## Projects

`projects/guriya` is a fictional Pakistani drama project. It does not require Islamic
source validation.

`projects/insan` is a research-first Islamic history project. It requires approved
source records before factual outlines, narration, scenes, shots, or prompts can
enter production.

Create a small new project scaffold with:

```bash
aifs create-project --project-id example_project --project-name "Example Project" --genre documentary
```

Validate a project with:

```bash
aifs validate-project projects/guriya
aifs validate-project projects/insan
```

Insan is expected to fail production readiness until approved source records are
added to `projects/insan/01_research/source_registry.yaml`.

## Shared Assets

Shared reusable metadata belongs under `shared/asset_library`. Project-local assets
belong under `projects/<project_id>`. Shared assets must remain story-neutral and
project configs decide which shared libraries are allowed.

## Source Validation

Islamic-history projects use a source hierarchy:

1. Qur'an
2. Authentic Hadith
3. Reliable Tafsir
4. Established Seerah sources
5. Carefully evaluated classical histories
6. Scholarly interpretation
7. Modern academic references for geography, archaeology, chronology, and material culture

No source is marked verified or approved without review. Weak or disputed material
must be labeled and cannot be presented as certainty.

## Engine Adapters

Engine adapters isolate provider-specific formatting. The V3 adapter roadmap supports
Flow, Gemini, Veo, Kling, Runway, Hailuo, Seedance, and future engines without
tightly coupling the core engine to any provider.

## Installation

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Tests

```bash
pytest
ruff check .
mypy src
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

## Identity Locks

Project-local characters can define strict approved identity references in:

```text
projects/<project_id>/05_characters/<character_id>/identity.yaml
```

Validate one locked identity with:

```bash
aifs validate-identity --project insan --character storyteller
```

The current approved Storyteller identity reference is:

```text
projects/insan/12_generated_images/episode_01/assets/storyteller_master.png
```

Prompt compilation injects a mandatory character identity continuity block and carries
the reference image forward in engine-neutral `reference_assets` metadata. The core
compiler does not copy image files or call external engines.

## Production Character References

Character images manually generate hoti hain. Aap Gemini, Flow, Veo, Kling,
Photoshop, ya kisi bhi image tool se final HD angle banate hain, phir usay project
folder mein store karte hain.

Important rule:

- `master_sheet.png` sirf identity review ke liye hai.
- Split crops sirf preview/debug ke liye hain.
- Compiler default mode mein sirf approved HD production references use karta hai.
- HD production references yahan rakhni hain:

```text
projects/guriya/characters/guriya/references/production/
```

Required production references:

```text
front
left_profile
three_quarter_left
three_quarter_right
full_body_front
full_body_back
seated_front
```

Master sheet preview dekhne ke liye:

```bash
aifs preview-reference-sheet projects/guriya/characters/guriya/references/master/master_sheet.png --layout guriya_master_v1 --overrides projects/guriya/characters/guriya/references/crop_overrides.yaml
```

Master sheet split karna sirf review crops banata hai:

```bash
aifs split-reference-sheet projects/guriya/characters/guriya/references/master/master_sheet.png --project guriya --character guriya --layout guriya_master_v1
```

Equivalent module entry point:

```bash
python -m ai_film_studio.cli split-reference-sheet projects/guriya/characters/guriya/references/master/master_sheet.png --project guriya --character guriya --layout guriya_master_v1
```

Cropped previews yahan likhe jate hain:

```text
projects/guriya/characters/guriya/references/views/
```

Yeh crops production references nahi hain. Existing cropped metadata migrate karne
ke liye:

```bash
aifs migrate-cropped-references --project guriya --character guriya
```

Har final angle ko separately HD mein generate karein, phir register karein:

```bash
aifs register-production-reference --project guriya --character guriya --type front --path projects/guriya/characters/guriya/references/production/front.png
```

Validate aur readiness check:

```bash
aifs list-production-references --project guriya --character guriya
aifs validate-production-references --project guriya --character guriya
```

Valid HD image approve karne ke baad selector usay default mode mein use kar sakta hai:

```bash
aifs approve-reference --project guriya --character guriya --reference front
```

Debug mode mein cropped previews allow karne ke liye explicit flag chahiye:

```bash
aifs select-references projects/guriya/tests/reference_selection/close_up_front.yaml --engine gemini --allow-preview-references
```

Crop preview image yahan likhi jati hai:

```text
projects/guriya/characters/guriya/references/master/master_sheet_preview.png
```

The reference manifest is written to:

```text
projects/guriya/characters/guriya/references/reference_sheet_manifest.json
```

See `docs/REFERENCE_SHEET_WORKFLOW.md` for the Roman Urdu workflow and exact
Guriya commands. See `docs/CHARACTER_SHEET_BATCH_WORKFLOW.md` for batch HD
reference generation workflow.

## Current Limitations

- Local prompt compilation only.
- No Gemini API calls yet.
- Gemini support currently means prompt formatting through `GeminiAdapter`.
- Guriya is demo project data, not compiler logic.
- Prompt Compiler v1 resolves character and world assets from local YAML files.
- Asset reference images are manually generated and may be awaiting approval.
- Reference sheet splitting is deterministic local asset management only; the combined
  master sheet and cropped previews are not production generation references.
- No automatic upscaling or image generation is performed.

## Features

- AI Director
- Prompt Compiler
- Scene Compiler
- Identity Engine
- QA Engine
- Multi-engine support
