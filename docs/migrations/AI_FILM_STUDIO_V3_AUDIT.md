# AI Film Studio V3 Audit

## Current Architecture Summary

AI Film Studio currently has a working Python package under `src/ai_film_studio`
with reusable services for CLI commands, prompt compilation, engine adapters,
module loading, asset bible validation, reference sheet splitting, reference
selection, and shared validation primitives.

The active production data is under `projects/guriya`. Guriya now contains a
numbered production planning structure (`01_story` through `12_editing`) plus older
asset bible folders (`characters`, `environment`, `props`, `asset_bibles`,
`worlds`, and prompt compiler demo files).

The repository also contains early top-level placeholders: `core/`, `engines/`,
`modules/`, `templates/`, `assets/`, and `output/`. These are not currently the
main implementation path; the real Python implementation lives in `src/ai_film_studio`.

## Current Directory Snapshot

```text
AGENTS.md
README.md
assets/
core/
docs/
engines/
modules/
output/
projects/guriya/
pyproject.toml
requirements.txt
src/ai_film_studio/
templates/
tests/
```

## Reusable Components

- `src/ai_film_studio/cli`: Typer command surface.
- `src/ai_film_studio/builder`: runtime composition and dependency wiring.
- `src/ai_film_studio/module_loader`: YAML, Markdown, and Python object loading.
- `src/ai_film_studio/engine_adapters`: provider-neutral adapter contracts and
  Gemini formatting adapter.
- `src/ai_film_studio/prompt_compiler`: local structured prompt compiler.
- `src/ai_film_studio/asset_bible`: project asset scanning, validation, and indexing.
- `src/ai_film_studio/reference_sheets`: reference sheet splitting, approval,
  inventory validation, production reference readiness, and selection.
- `src/ai_film_studio/validator`: generic validation result contracts.
- `tests/unit`: pytest coverage for core reusable behavior.

## Project-Specific Components

- `projects/guriya/01_story` through `projects/guriya/12_editing`.
- `projects/guriya/characters`, `environment`, `props`, `worlds`, and `asset_bibles`.
- `projects/guriya/episode_01/scene_02/clip_001.yaml`.
- `projects/guriya/tests/reference_selection`.
- `templates/reference_sheet_layouts/guriya_master_v1.yaml` is Guriya-specific and
  should move or receive a shared template wrapper later.
- `output/guriya` contains generated artifacts and should remain outside core logic.

## Duplicated Structures

- `projects/guriya/02_characters` and `projects/guriya/characters` both describe
  characters at different maturity levels. The first is production planning; the
  second is asset-bible/reference management.
- `projects/guriya/03_locations` and `projects/guriya/environment` similarly split
  production planning from asset reference management.
- Top-level `templates/` overlaps with the requested `shared/templates/`.
- Top-level `assets/` overlaps with the requested `shared/asset_library/`.

## Missing Components

- Project-agnostic `shared/` layer.
- Explicit `engine/` responsibility documentation.
- Islamic research/source validation project foundation.
- Reusable project schema and source record schema.
- Project-level validation command for source requirements, depiction policy, and
  adapter checks.
- Migration manifest.
- Dedicated architecture/workflow/policy docs for V3.

## Incorrectly Placed Or Ambiguous Files

- `templates/reference_sheet_layouts/guriya_master_v1.yaml` is project-specific but
  lives in top-level templates.
- `assets/character_library` is a shared library candidate but currently outside the
  requested `shared/asset_library`.
- Top-level `core/`, `engines/`, and `modules/` are placeholders and may confuse
  readers because implementation lives under `src/ai_film_studio`.

## Files That Should Move Later

- `templates/reference_sheet_layouts/guriya_master_v1.yaml` should move to
  `projects/guriya/templates/reference_sheet_layouts/` or be replaced by a shared
  generic layout template plus Guriya configuration.
- Shared, non-project-specific character-library material under `assets/` should move
  to `shared/asset_library/characters/` after a dedicated asset-library migration.
- Generic prompt template material under `projects/guriya/asset_bibles/prompt_templates`
  should be evaluated for migration to `shared/prompt_blocks` or `shared/templates`.

## Files That Should Remain Inside Guriya

- Story, scene, shot, voiceover, music/SFX, editing, QA, and export planning files.
- Guriya character/location/prop/world assets.
- Guriya generated output manifests and prompts.
- Guriya-specific prompt and reference sheet metadata.

## Files That Require Compatibility Wrappers

- CLI commands that default to `projects/guriya` should keep working while accepting
  any project path.
- Prompt compiler examples should keep resolving older `projects/guriya/characters`
  and `projects/guriya/worlds` paths.
- Reference-sheet layout lookup should support legacy top-level `templates/`.

## Migration Risks

- Moving Guriya asset files could break existing tests and prompt compilation paths.
- Moving top-level templates too early could break reference sheet tests.
- Adding Insan historical content without verified sources could create false
  religious claims.
- Treating all source types equally would be unsafe for Islamic-history production.
- Direct depiction rules for Prophets and revered personalities need strict defaults.

## Proposed Target Architecture

```text
engine/          # responsibility docs and future engine module map
shared/          # reusable templates, schemas, asset libraries, prompt blocks
projects/        # isolated production projects
docs/            # architecture, workflows, migrations, policies
src/             # current Python implementation package
tests/           # reusable behavior tests
config/          # future runtime configuration
scripts/         # future operational scripts
```

## Assumptions

- V3 migration should be additive in this phase.
- Existing Python package remains under `src/ai_film_studio` for now.
- `engine/` is scaffolded as responsibility documentation, not a duplicate Python
  implementation.
- Insan gets research/governance scaffolding only; no episode story is written yet.
- No source is marked verified without real review.

## Recommended Migration Order

1. Add audit and migration manifest.
2. Add shared schemas/templates and project validation.
3. Scaffold `engine/` responsibilities without duplicating implementation.
4. Keep Guriya stable and document compatibility boundaries.
5. Create Insan governance/research/project foundation.
6. Add source validation and depiction-policy checks.
7. Update README and V3 docs.
8. Run tests and use future phases for any file moves.
