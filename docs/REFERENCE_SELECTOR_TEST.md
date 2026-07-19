# Reference Selector Test Workflow

Yeh workflow Guriya ke already split reference images ko validate, approve, select,
aur generation manifest mein compile karta hai. Is milestone mein koi Gemini API call
nahi hoti; sirf local paths, scores, aur manifest output generate hota hai.

## 1. Guriya References Validate Karein

```bash
aifs validate-references --project guriya --character guriya
```

Expected: har mapped image `Valid: yes` ho. Invalid ya missing image approve nahi
karni.

## 2. References List Karein

```bash
aifs list-references --project guriya --character guriya
```

Is se status dikhega: `approved`, `pending_review`, ya `rejected`.

## 3. Requested References Approve Karein

Sirf woh references approve karein jo exist karti hain aur validation pass karti hain:

```bash
aifs approve-reference --project guriya --character guriya --reference front
aifs approve-reference --project guriya --character guriya --reference left_profile
aifs approve-reference --project guriya --character guriya --reference three_quarter_left
aifs approve-reference --project guriya --character guriya --reference three_quarter_right
aifs approve-reference --project guriya --character guriya --reference full_body_front
aifs approve-reference --project guriya --character guriya --reference full_body_back
aifs approve-reference --project guriya --character guriya --reference seated_front
```

`full_body_back_left` is test mein intentionally approve nahi hota, taake selector
default behavior verify ho: unapproved references automatically select nahi hoti.

## 4. Close-up Front Scene Select Karein

```bash
aifs select-references projects/guriya/tests/reference_selection/close_up_front.yaml --engine gemini
```

Expected first selected reference:

```text
references/views/front_v2.png
```

Manifest:

```text
output/guriya/reference_selection/close_up_front/generation_manifest.json
```

## 5. Profile-left Scene Select Karein

```bash
aifs select-references projects/guriya/tests/reference_selection/profile_left.yaml --engine gemini
```

Expected first selected reference:

```text
references/views/left_profile_v2.png
```

Manifest:

```text
output/guriya/reference_selection/profile_left/generation_manifest.json
```

## 6. Full-body Standing Scene Select Karein

```bash
aifs select-references projects/guriya/tests/reference_selection/full_body_standing.yaml --engine gemini
```

Expected first selected reference:

```text
references/views/full_body_front_v2.png
```

Manifest:

```text
output/guriya/reference_selection/full_body_standing/generation_manifest.json
```

## 7. Weak Fallbacks

Default mode weak fallbacks disable rakhta hai. Is ka matlab: full-body shot ke liye
portrait reference use nahi hogi agar exact full-body reference missing ho.

Explicit weak fallback test ke liye:

```bash
aifs select-references projects/guriya/tests/reference_selection/full_body_standing.yaml --engine gemini --allow-weak-fallbacks
```

Weak fallback sirf debugging ya recovery ke liye use karein; production mein approved
exact references prefer karein.

## 8. Verification

Automated verification:

```bash
pytest
ruff check .
mypy src
```

Selector checks:

- close-up front ka first reference `front`
- profile-left ka first reference `left_profile`
- full-body standing ka first reference `full_body_front`
- rejected references select nahi hoti
- unapproved references default mode mein select nahi hoti
- engine reference limit respect hota hai
