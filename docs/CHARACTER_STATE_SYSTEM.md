# Character State System

AI Film Studio models evolving characters as:

```text
Character
↓
Identity
↓
State
↓
Prompt
↓
Reference Image
↓
Compiled Prompt
```

## Character

A character is the stable production entity, such as `storyteller` or `iblis`.
Character assets live under:

```text
projects/<project_id>/05_characters/<character_id>/
```

Legacy one-state character assets remain valid. Multi-state characters add a
canonical character folder and state folders.

## Identity

`identity.yaml` defines the continuing identity family:

```text
projects/<project_id>/05_characters/<character_id>/identity.yaml
```

It can define `default_state`, `state_aliases`, immutable identity rules,
continuity prompts, and optional identity reference image metadata.

## State

Each visual state lives in:

```text
projects/<project_id>/05_characters/<character_id>/states/<state_id>/state.yaml
```

A state can own:

- master prompt path
- reference image path
- immutable state attributes
- continuity prompt
- negative continuity prompt
- optional identity lock settings

If a scene references a character without a state, the compiler resolves the
identity `default_state`. If a state is explicitly provided, that state is used.

## Prompt Compiler

Scene YAML can use:

```yaml
characters:
  - id: iblis
    state: pre_rebellion
    module: ../../05_characters/iblis/asset.yaml
```

When `state` is omitted, the compiler uses `default_state`.

Compiled prompts automatically include:

- character identity continuity
- character state continuity
- configured reference image path
- negative identity and state continuity constraints
- engine-neutral `reference_assets` metadata

## Backward Compatibility

Existing single-identity characters keep working. Existing assets such as
`iblis_pre_rebellion` can remain as legacy aliases while new production files
resolve the canonical character `iblis` plus state `pre_rebellion`.
