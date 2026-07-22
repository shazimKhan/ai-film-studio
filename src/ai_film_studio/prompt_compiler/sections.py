"""Production prompt section builder."""

from __future__ import annotations

from collections.abc import Iterable
from typing import ClassVar

from ai_film_studio.prompt_compiler.models import (
    PromptSection,
    ResolvedCharacterReference,
    ResolvedSceneContext,
)


class PromptSectionBuilder:
    """Builds engine-neutral cinematic prompt sections in canonical order."""

    SECTION_TITLES: ClassVar[tuple[str, ...]] = (
        "PROJECT",
        "DIRECTOR INTENT",
        "ACTION",
        "CHARACTER IDENTITY LOCK",
        "WORLD AND PERIOD",
        "WARDROBE AND HAIR",
        "CAMERA",
        "LIGHTING",
        "MOTION",
        "CONTINUITY",
        "AUDIO",
        "NEGATIVE CONSTRAINTS",
        "OUTPUT QUALITY",
    )

    def build(self, context: ResolvedSceneContext) -> tuple[PromptSection, ...]:
        """Build all sections for a resolved scene context."""
        return (
            PromptSection(title="PROJECT", content=self._project(context)),
            PromptSection(title="DIRECTOR INTENT", content=self._director_intent(context)),
            PromptSection(title="ACTION", content=context.scene.action),
            PromptSection(
                title="CHARACTER IDENTITY LOCK",
                content=self._character_identity(context.characters),
            ),
            PromptSection(title="WORLD AND PERIOD", content=self._world(context)),
            PromptSection(
                title="WARDROBE AND HAIR",
                content=self._wardrobe_and_hair(context.characters),
            ),
            PromptSection(title="CAMERA", content=self._camera(context)),
            PromptSection(title="LIGHTING", content=self._lighting(context)),
            PromptSection(title="MOTION", content=self._motion(context)),
            PromptSection(title="CONTINUITY", content=self._continuity(context)),
            PromptSection(title="AUDIO", content=self._audio(context)),
            PromptSection(title="NEGATIVE CONSTRAINTS", content=self._negative(context)),
            PromptSection(title="OUTPUT QUALITY", content=self._output_quality(context)),
        )

    @staticmethod
    def render(sections: Iterable[PromptSection]) -> str:
        """Render sections as engine-neutral text."""
        return "\n\n".join(f"{section.title}\n{section.content}" for section in sections)

    @staticmethod
    def _project(context: ResolvedSceneContext) -> str:
        scene = context.scene
        return _lines(
            (
                f"Project: {scene.project}",
                f"Episode: {scene.episode}",
                f"Scene: {scene.scene}",
                f"Clip: {scene.clip}",
                f"Title: {scene.title}",
                f"Duration: {scene.duration:g} seconds",
            ),
        )

    @staticmethod
    def _director_intent(context: ResolvedSceneContext) -> str:
        scene = context.scene
        world = context.world.asset
        return (
            f"Create a grounded cinematic clip centered on {scene.emotion}. "
            f"The shot must feel specific to {world.name}, {world.period}, with restrained "
            "performances, exact continuity, and no anachronistic details."
        )

    @staticmethod
    def _character_identity(characters: tuple[ResolvedCharacterReference, ...]) -> str:
        entries: list[str] = []
        seen_identity_ids: set[str] = set()
        seen_state_ids: set[tuple[str, str]] = set()
        for character in characters:
            if (
                character.identity is not None
                and (character.identity.identity_locked or character.identity.continuity_prompt)
                and character.identity.identity_id not in seen_identity_ids
            ):
                seen_identity_ids.add(character.identity.identity_id)
                entries.append(_identity_continuity_block(character))

            if character.identity is not None and character.state is not None:
                state_key = (character.identity.identity_id, character.state.state_id)
                if state_key not in seen_state_ids:
                    seen_state_ids.add(state_key)
                    entries.append(_state_continuity_block(character))

            asset = character.asset
            reference = character.reference
            constraints = _sentence_list(asset.performance_constraints)
            role = f" Role in clip: {reference.role}." if reference.role else ""
            notes = f" Scene notes: {_sentence_list(reference.notes)}" if reference.notes else ""
            entries.append(
                (
                    "- "
                    f"{asset.name} ({asset.id}), age {asset.age}: "
                    f"{_ensure_period(asset.appearance)} "
                    f"Personality/performance: {_ensure_period(asset.personality)}"
                    f"{role}{notes} "
                    "Identity constraints: "
                    f"{constraints or 'maintain the same face, body, and age.'}"
                ).strip()
            )
        return "\n\n".join(entries)

    @staticmethod
    def _world(context: ResolvedSceneContext) -> str:
        world = context.world.asset
        return _lines(
            (
                f"World: {world.name}",
                f"Period: {world.period}",
                f"Location: {world.location}",
                f"Description: {world.description}",
                f"Atmosphere: {world.atmosphere}",
                f"Textures: {_sentence_list(world.textures)}",
                f"Visual rules: {_sentence_list(world.visual_rules)}",
            ),
        )

    @staticmethod
    def _wardrobe_and_hair(characters: tuple[ResolvedCharacterReference, ...]) -> str:
        entries: list[str] = []
        for character in characters:
            asset = character.asset
            reference = character.reference
            wardrobe = reference.wardrobe or asset.wardrobe
            hair = reference.hair or asset.hair
            entries.append(
                f"{asset.name}: wardrobe: {_trim_terminal_punctuation(wardrobe)}; "
                f"hair: {_trim_terminal_punctuation(hair)}."
            )
        return _bullet_lines(entries)

    @staticmethod
    def _camera(context: ResolvedSceneContext) -> str:
        camera = context.scene.camera
        return _lines(
            (
                f"Shot size: {camera.shot_size}",
                f"Angle: {camera.angle}",
                f"Lens: {camera.lens}",
                f"Movement: {camera.movement}",
                f"Framing: {camera.framing}",
                f"Focus: {camera.focus}",
            ),
        )

    @staticmethod
    def _lighting(context: ResolvedSceneContext) -> str:
        lighting = context.scene.lighting
        return _lines(
            (
                f"Quality: {lighting.quality}",
                f"Source: {lighting.source}",
                f"Color temperature: {lighting.color_temperature}",
                f"Contrast: {lighting.contrast}",
                f"Mood: {lighting.mood}",
            ),
        )

    @staticmethod
    def _motion(context: ResolvedSceneContext) -> str:
        motion = context.scene.motion
        return _lines(
            (
                f"Subject motion: {motion.subject}",
                f"Environmental motion: {motion.environment}",
                f"Camera motion: {motion.camera}",
                f"Pace: {motion.pace}",
            ),
        )

    @staticmethod
    def _continuity(context: ResolvedSceneContext) -> str:
        continuity = context.scene.continuity
        return _lines(
            (
                f"Previous clip: {continuity.previous_clip}",
                f"Visual state: {continuity.visual_state}",
                f"Prop state: {continuity.prop_state}",
                f"Emotional state: {continuity.emotional_state}",
            ),
        )

    @staticmethod
    def _audio(context: ResolvedSceneContext) -> str:
        if context.scene.audio:
            return context.scene.audio
        return (
            f"Use diegetic ambience from the location only: {context.world.asset.soundscape}. "
            f"Let the sound support {context.scene.emotion}; avoid music unless explicitly "
            "directed."
        )

    @staticmethod
    def _negative(context: ResolvedSceneContext) -> str:
        negative_constraints: list[str] = []
        seen_constraints: set[str] = set()
        for character in context.characters:
            identity = character.identity
            if (
                identity is not None
                and identity.negative_continuity_prompt
                and identity.negative_continuity_prompt not in seen_constraints
            ):
                seen_constraints.add(identity.negative_continuity_prompt)
                negative_constraints.append(identity.negative_continuity_prompt)

            state = character.state
            if state is None or not state.negative_continuity_prompt:
                continue
            if state.negative_continuity_prompt in seen_constraints:
                continue
            seen_constraints.add(state.negative_continuity_prompt)
            negative_constraints.append(state.negative_continuity_prompt)

        for negative_prompt in context.scene.negative_prompts:
            if negative_prompt in seen_constraints:
                continue
            seen_constraints.add(negative_prompt)
            negative_constraints.append(negative_prompt)
        return _bullet_lines(negative_constraints)

    @staticmethod
    def _output_quality(context: ResolvedSceneContext) -> str:
        scene = context.scene
        return (
            f"Generate a production-ready cinematic video prompt for a clip lasting "
            f"{scene.duration:g} seconds. Preserve anatomy, identity, geography, fabric "
            "behavior, historical period, camera continuity, and lighting continuity. Avoid "
            "captions, text overlays, watermarks, logos, modern UI artifacts, and unmotivated "
            "stylization."
        )


def _lines(lines: Iterable[str]) -> str:
    return "\n".join(line for line in lines if line)


def _bullet_lines(lines: Iterable[str]) -> str:
    return "\n".join(f"- {line}" for line in lines if line)


def _sentence_list(values: Iterable[str]) -> str:
    return " ".join(value.rstrip(".") + "." for value in values if value)


def _ensure_period(value: str) -> str:
    stripped = value.strip()
    if stripped.endswith((".", "!", "?")):
        return stripped
    return f"{stripped}."


def _trim_terminal_punctuation(value: str) -> str:
    return value.strip().rstrip(".!?")


def _identity_continuity_block(character: ResolvedCharacterReference) -> str:
    identity = character.identity
    if identity is None:
        return ""

    immutable = _sentence_list(identity.immutable_attributes)
    mutable = _sentence_list(identity.mutable_attributes)
    lines = [
        "CHARACTER IDENTITY CONTINUITY — MANDATORY",
        f"Character: {character.asset.name} ({identity.character_id})",
        f"Identity ID: {identity.identity_id}",
        f"Lock level: {identity.lock_level}",
        "This identity continuity guidance overrides wardrobe, pose, styling, and shot-level "
        "variation if any later instruction conflicts with identity continuity.",
        identity.continuity_prompt or "",
    ]
    if identity.reference_image is not None:
        lines.append(f"Reference image: {identity.reference_image.path}")
    if immutable:
        lines.append(f"Immutable attributes: {immutable}")
    if mutable:
        lines.append(f"Mutable attributes may vary only when the shot requires them: {mutable}")
    return _lines(lines)


def _state_continuity_block(character: ResolvedCharacterReference) -> str:
    identity = character.identity
    state = character.state
    if identity is None or state is None:
        return ""

    immutable = _sentence_list(state.immutable_attributes)
    mutable = _sentence_list(state.mutable_attributes)
    lines = [
        "CHARACTER STATE CONTINUITY — MANDATORY",
        f"Character: {character.asset.name} ({identity.character_id})",
        f"Identity ID: {identity.identity_id}",
        f"State ID: {state.state_id}",
        f"State status: {state.status}",
        f"State lock level: {state.lock_level}",
        state.continuity_prompt or "",
    ]
    if state.reference_image is not None:
        lines.append(f"Reference image: {state.reference_image.path}")
    prompt_path = state.master_prompt_path or state.prompt_ref
    if prompt_path:
        lines.append(f"Master prompt: {prompt_path}")
    if immutable:
        lines.append(f"State immutable attributes: {immutable}")
    if mutable:
        lines.append(f"State mutable attributes may vary only when required: {mutable}")
    return _lines(lines)
