# AI Film Studio V3

AI Film Studio V3 separates the repository into three layers:

1. Core engine responsibilities
2. Shared asset, schema, template, prompt-block, and validator libraries
3. Individual production projects

The core engine must never contain project story content. Projects own their story,
research, assets, prompts, generated media, QA, and exports.

Current Python implementation remains in `src/ai_film_studio`; `engine/` documents
the target responsibility map for future extraction.
