# Reference Sheet Workflow

Yeh workflow manual character reference sheets ko production assets mein convert karta hai.
System koi image generate nahi karta, OCR nahi karta, face recognition nahi karta, aur
character ko automatically identify nahi karta. Aap Gemini, Flow, Veo, Kling, Photoshop,
ya kisi bhi tool se image bana kar repo mein rakhte hain; AIFS sirf deterministic layout
ke mutabiq us sheet ko crop karta hai.

## Guriya Master Sheet

Guriya ke liye source sheet yahan rakhein:

```bash
projects/guriya/characters/guriya/references/master/master_sheet.png
```

Stable preserved master filename yeh hai:

```bash
projects/guriya/characters/guriya/references/master/master_sheet.png
```

Original source delete ya mutate nahi hota.

## Preview Pehle Dekhein

Pehle crop boxes preview karna behtar hai:

```bash
aifs preview-reference-sheet projects/guriya/characters/guriya/references/master/master_sheet.png --layout guriya_master_v1 --overrides projects/guriya/characters/guriya/references/crop_overrides.yaml
```

Equivalent module command:

```bash
python -m ai_film_studio.cli preview-reference-sheet projects/guriya/characters/guriya/references/master/master_sheet.png --layout guriya_master_v1 --overrides projects/guriya/characters/guriya/references/crop_overrides.yaml
```

Preview output:

```bash
projects/guriya/characters/guriya/references/master/master_sheet_preview.png
```

Preview sirf rectangles aur labels banata hai. Crop files, manifest, aur
`character.yaml` update nahi hotay.

## Sheet Split Karna

Jab preview theek ho, split run karein:

```bash
aifs split-reference-sheet projects/guriya/characters/guriya/references/master/master_sheet.png --project guriya --character guriya --layout guriya_master_v1
```

Equivalent module command:

```bash
python -m ai_film_studio.cli split-reference-sheet projects/guriya/characters/guriya/references/master/master_sheet.png --project guriya --character guriya --layout guriya_master_v1
```

Default output PNG hota hai. Options:

```bash
--output-format png
--output-format jpg
--output-format webp
--padding 0.01
--min-width 128
--min-height 128
--overwrite
--dry-run
```

Without `--overwrite`, existing files silently replace nahi hoti. System versioned
filenames banata hai, jaise `front_v2.png`.

## Expected Crops

`guriya_master_v1` layout 4 columns x 2 rows hai:

```text
front.png
left_profile.png
three_quarter_left.png
three_quarter_right.png
full_body_front.png
full_body_back_left.png
full_body_back.png
seated_front.png
```

Crop outputs:

```bash
projects/guriya/characters/guriya/references/views/
```

Manifest:

```bash
projects/guriya/characters/guriya/references/reference_sheet_manifest.json
```

Manifest repo-relative paths, normalized crops, pixel crops, dimensions, tags,
review status, aur SHA-256 checksums store karta hai.

## Manual Crop Overrides

Agar grid crop thora off ho, override file update karein:

```bash
projects/guriya/characters/guriya/references/crop_overrides.yaml
```

Format:

```yaml
panels:
  front:
    x: 0.02
    y: 0.01
    width: 0.22
    height: 0.48
```

Values normalized hain: `0.0` se `1.0` tak. Override panel crop layout grid se
priority leta hai. Invalid ya out-of-bounds crop reject hota hai.

## Review Approval

Split ke baad references auto-approve nahi hotay. Har crop `pending_review` hota hai.

Approve:

```bash
aifs approve-reference --project guriya --character guriya --reference front
```

Reject:

```bash
aifs reject-reference --project guriya --character guriya --reference front --reason "Face crop is soft"
```

Rejected references automatic selector mein include nahi hotay.

## Smart Selection

`ReferenceSelector` generic hai. Woh character asset metadata, shot type, camera
angle, framing, action, pose, approved-only preference, aur engine reference limit
leta hai. Guriya-specific rules selector ke andar hardcoded nahi hain.

Examples:

```text
close_up + front -> front, three_quarter_left
profile_left -> left_profile, three_quarter_left
full_body + standing -> full_body_front
back_view -> full_body_back, full_body_back_left
seated -> seated_front
```

Default behavior approved references choose karta hai. Prompt compilation ke future
milestone mein selected reference paths/manifest use honge; koi upload ya cloud API
call is milestone mein nahi hoti.

## Best Practices

- Master sheet ko direct video prompt ke liye ideal input mat samjhein; sheet ko split
  karke clean individual references use karein.
- Manual image generation ke baad naming convention follow karein.
- Preview check kiye baghair approval na dein.
- Crop files ko manually overwrite karne ke bajaye `--overwrite` explicit use karein.
- `reference_sheet_manifest.json` ko production audit trail samjhein.
