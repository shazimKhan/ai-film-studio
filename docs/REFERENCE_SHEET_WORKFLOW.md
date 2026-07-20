# Reference Sheet Workflow

Yeh workflow character identity review ke liye hai. AIFS image generate nahi karta,
OCR nahi karta, face recognition nahi karta, aur character ko automatically identify
nahi karta. Aap manually image tools se references banate hain; AIFS un local files
ko validate, register, aur select karta hai.

## Core Rule

`master_sheet.png` production generation reference nahi hai. Yeh sirf identity review
aur crop preview ke liye use hota hai.

Split crops bhi production references nahi hain. Woh `cropped_preview` source type ke
saath `legacy_crops` mein preserve hotay hain aur default selector unhein ignore karta
hai. Crops sirf debug mode mein `--allow-preview-references` ke saath select ho sakte
hain.

Production ke liye har angle alag se HD image honi chahiye:

```text
projects/guriya/characters/guriya/references/production/
```

Production-selectable source types:

```text
native_high_resolution
generated_variant
```

## Master Sheet Preview

Guriya master sheet path:

```bash
projects/guriya/characters/guriya/references/master/master_sheet.png
```

Preview rectangles dekhne ke liye:

```bash
aifs preview-reference-sheet projects/guriya/characters/guriya/references/master/master_sheet.png --layout guriya_master_v1 --overrides projects/guriya/characters/guriya/references/crop_overrides.yaml
```

Preview output:

```bash
projects/guriya/characters/guriya/references/master/master_sheet_preview.png
```

Preview command crop files ya production refs nahi banata.

## Cropped Previews

Sheet split command:

```bash
aifs split-reference-sheet projects/guriya/characters/guriya/references/master/master_sheet.png --project guriya --character guriya --layout guriya_master_v1
```

Output crops:

```bash
projects/guriya/characters/guriya/references/views/
```

Manifest:

```bash
projects/guriya/characters/guriya/references/reference_sheet_manifest.json
```

Split ke baad `character.yaml` mein crops `reference_images.legacy_crops` ke andar
store hotay hain:

```yaml
source_type: cropped_preview
production_selectable: false
status: pending_review
approved: false
```

Existing purani `views` metadata migrate karne ke liye:

```bash
aifs migrate-cropped-references --project guriya --character guriya
```

Migration files delete nahi karti. Paths aur unknown YAML fields preserve rehte hain.

## HD Production References

Final generation ke liye yeh required HD references alag alag banani hain:

```text
front
left_profile
three_quarter_left
three_quarter_right
full_body_front
full_body_back
seated_front
```

Portrait references ki minimum size:

```text
1024x1024
```

Full-body aur seated references ki minimum size:

```text
1024x1536
```

No upscaling: agar image low-res hai to usay reject kiya jayega. Fresh HD image
generate karein.

Example save path:

```bash
projects/guriya/characters/guriya/references/production/front.png
```

Register command:

```bash
aifs register-production-reference --project guriya --character guriya --type front --path projects/guriya/characters/guriya/references/production/front.png
```

List production refs:

```bash
aifs list-production-references --project guriya --character guriya
```

Validate production refs:

```bash
aifs validate-production-references --project guriya --character guriya
```

Valid HD reference approve karne ke liye:

```bash
aifs approve-reference --project guriya --character guriya --reference front
```

Reject karne ke liye:

```bash
aifs reject-reference --project guriya --character guriya --reference front --reason "Face is inconsistent"
```

## Selector Behavior

Default selector order:

1. Approved `native_high_resolution`
2. Approved `generated_variant`
3. Cropped previews ignored
4. Master sheet ignored

Debug crop selection:

```bash
aifs select-references projects/guriya/tests/reference_selection/close_up_front.yaml --engine gemini --allow-preview-references
```

Without `--allow-preview-references`, cropped previews select nahi hotay, chahe woh
approved hon.

## Production Readiness

`production_ready` tabhi true maana jayega jab saari required HD production refs:

- exist karti hon
- readable image files hon
- minimum dimensions pass karti hon
- `source_type` native HD ya generated variant ho
- `production_selectable: true` ho
- `approved: true` aur `status: approved` ho

Cropped previews readiness ko true nahi bana sakte.

## Best Practices

- Master sheet ko identity comparison board samjhein, final generation ref nahi.
- Har camera angle ke liye clean HD native image separately generate karein.
- Production refs ko predictable names dein: `front.png`, `left_profile.png`, etc.
- Approval se pehle `validate-production-references` zaroor run karein.
- Crop previews ko sirf debugging aur visual review ke liye use karein.
- Project-specific data `projects/` ke andar rakhein; core compiler generic rahe.
