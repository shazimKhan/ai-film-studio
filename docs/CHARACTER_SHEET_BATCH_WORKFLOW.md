# Character Sheet Batch Workflow

Yeh workflow batch mein character references prepare karne ke liye hai. AIFS image
generate nahi karta; aap Gemini, Flow, Veo, Kling, Photoshop, ya kisi aur tool se
final HD images banate hain aur repo mein place karte hain.

## Golden Rule

Master sheet identity review ke liye hai. Cropped previews final production refs nahi
hain. Compiler default mode mein sirf approved HD production references use karega.

## Folder

Har character ke final HD refs yahan save karein:

```bash
projects/guriya/characters/guriya/references/production/
```

Required filenames:

```text
front.png
left_profile.png
three_quarter_left.png
three_quarter_right.png
full_body_front.png
full_body_back.png
seated_front.png
```

## Batch Generation

Image tool mein har angle separately generate karein. Ek combined sheet se crop karke
final production ref na banayein. Har output clean, full-resolution, aur identity
consistent hona chahiye.

Minimum sizes:

```text
Portrait: 1024x1024
Full-body/seated: 1024x1536
```

No upscaling. Agar image chhoti hai to dobara native HD generate karein.

## Register Commands

Har file save karne ke baad register karein:

```bash
aifs register-production-reference --project guriya --character guriya --type front --path projects/guriya/characters/guriya/references/production/front.png
aifs register-production-reference --project guriya --character guriya --type left_profile --path projects/guriya/characters/guriya/references/production/left_profile.png
aifs register-production-reference --project guriya --character guriya --type three_quarter_left --path projects/guriya/characters/guriya/references/production/three_quarter_left.png
aifs register-production-reference --project guriya --character guriya --type three_quarter_right --path projects/guriya/characters/guriya/references/production/three_quarter_right.png
aifs register-production-reference --project guriya --character guriya --type full_body_front --path projects/guriya/characters/guriya/references/production/full_body_front.png
aifs register-production-reference --project guriya --character guriya --type full_body_back --path projects/guriya/characters/guriya/references/production/full_body_back.png
aifs register-production-reference --project guriya --character guriya --type seated_front --path projects/guriya/characters/guriya/references/production/seated_front.png
```

Generated variants ke liye:

```bash
aifs register-production-reference --project guriya --character guriya --type front --path projects/guriya/characters/guriya/references/production/front.png --source-type generated_variant
```

## Validate

```bash
aifs list-production-references --project guriya --character guriya
aifs validate-production-references --project guriya --character guriya
```

Validation yeh check karti hai:

- file exists
- image readable hai
- minimum dimensions pass hain
- duplicate path nahi hai
- `source_type` production-selectable hai
- `production_selectable: true`
- approval status visible hai

## Approve

Sirf validated HD references approve karein:

```bash
aifs approve-reference --project guriya --character guriya --reference front
aifs approve-reference --project guriya --character guriya --reference left_profile
aifs approve-reference --project guriya --character guriya --reference three_quarter_left
aifs approve-reference --project guriya --character guriya --reference three_quarter_right
aifs approve-reference --project guriya --character guriya --reference full_body_front
aifs approve-reference --project guriya --character guriya --reference full_body_back
aifs approve-reference --project guriya --character guriya --reference seated_front
```

Final readiness:

```bash
aifs validate-production-references --project guriya --character guriya
```

Jab saari required refs valid aur approved hon, production readiness true hogi.

## Selector Test

```bash
aifs select-references projects/guriya/tests/reference_selection/close_up_front.yaml --engine gemini
aifs select-references projects/guriya/tests/reference_selection/profile_left.yaml --engine gemini
aifs select-references projects/guriya/tests/reference_selection/full_body_standing.yaml --engine gemini
```

Debug previews ke liye:

```bash
aifs select-references projects/guriya/tests/reference_selection/close_up_front.yaml --engine gemini --allow-preview-references
```

`--allow-preview-references` production default nahi hai. Yeh sirf troubleshooting ke
liye hai.
