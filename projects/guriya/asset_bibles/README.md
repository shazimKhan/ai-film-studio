# Guriya Asset Bibles

This folder contains the production asset bible system for the Guriya demo project.
It stores documentation, reusable prompt templates, and asset standards for manually
generated image references.

AI Film Studio does not generate character, environment, wardrobe, or prop images in
this repository. Approved references are generated outside the framework with tools
such as Gemini, Flow, Veo, Kling, or other image/video systems, then saved into the
asset folders using the required names.

## Bibles

- `character_bible/` defines identity, pose, expression, wardrobe, and voice standards.
- `environment_bible/` defines location reference, lighting, and camera angle standards.
- `prop_bible/` defines reusable object asset standards.
- `wardrobe_bible/` defines wardrobe continuity and naming standards.
- `prompt_templates/` contains reusable, project-neutral prompt templates.

## Status

All new assets start with `reference_status: awaiting_reference` until real approved
images are added.
