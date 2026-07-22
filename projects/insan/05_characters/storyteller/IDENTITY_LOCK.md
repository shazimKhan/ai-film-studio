# Storyteller Identity Lock

The approved Storyteller master reference is:

```text
projects/insan/12_generated_images/episode_01/assets/storyteller_master.png
```

This file is the canonical `v1` identity reference for `insan_storyteller_v1`.
Do not copy it into `assets/generated/` and do not replace it silently.

## Validation

Run from the repository root:

```bash
aifs validate-identity --project insan --character storyteller
```

The validation must pass before Storyteller shots use the strict identity lock.

## Usage

Any compiled generation request that references the locked Storyteller identity
must include:

```yaml
reference_assets:
  - character_id: storyteller
    identity_id: insan_storyteller_v1
    path: projects/insan/12_generated_images/episode_01/assets/storyteller_master.png
    required: true
    identity_lock: strict
```
