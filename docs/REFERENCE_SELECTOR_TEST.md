# Reference Selector Test Workflow

Yeh workflow Guriya ke reference selector ko local mode mein test karta hai. Is
milestone mein koi Gemini API call nahi hoti; sirf local paths, scores, exclusions,
aur generation manifest banta hai.

## 1. Cropped Metadata Migrate Karein

Purani split crops agar `views` mein hain to unhein `legacy_crops` mein migrate karein:

```bash
aifs migrate-cropped-references --project guriya --character guriya
```

Migration files delete nahi karti. Crops ka source type `cropped_preview` hota hai aur
`production_selectable: false` rehta hai.

## 2. Production References Validate Karein

```bash
aifs list-production-references --project guriya --character guriya
aifs validate-production-references --project guriya --character guriya
```

Expected: required HD production images exist, readable hon, minimum dimensions pass
karein, aur approved hon. Missing ya low-res image production-ready nahi hoti.

## 3. HD References Register Karein

Example front reference:

```bash
aifs register-production-reference --project guriya --character guriya --type front --path projects/guriya/characters/guriya/references/production/front.png
```

Baaki required refs:

```text
left_profile
three_quarter_left
three_quarter_right
full_body_front
full_body_back
seated_front
```

Har angle ko separate HD file ke taur par generate karein. Master sheet crop ko final
production reference na banayein.

## 4. HD References Approve Karein

Sirf woh references approve karein jo validation pass karti hain:

```bash
aifs approve-reference --project guriya --character guriya --reference front
aifs approve-reference --project guriya --character guriya --reference left_profile
aifs approve-reference --project guriya --character guriya --reference three_quarter_left
aifs approve-reference --project guriya --character guriya --reference three_quarter_right
aifs approve-reference --project guriya --character guriya --reference full_body_front
aifs approve-reference --project guriya --character guriya --reference full_body_back
aifs approve-reference --project guriya --character guriya --reference seated_front
```

## 5. Close-up Front Scene Select Karein

```bash
aifs select-references projects/guriya/tests/reference_selection/close_up_front.yaml --engine gemini
```

Expected first selected production reference:

```text
references/production/front.png
```

Manifest:

```text
output/guriya/reference_selection/close_up_front/generation_manifest.json
```

## 6. Profile-left Scene Select Karein

```bash
aifs select-references projects/guriya/tests/reference_selection/profile_left.yaml --engine gemini
```

Expected first selected production reference:

```text
references/production/left_profile.png
```

Manifest:

```text
output/guriya/reference_selection/profile_left/generation_manifest.json
```

## 7. Full-body Standing Scene Select Karein

```bash
aifs select-references projects/guriya/tests/reference_selection/full_body_standing.yaml --engine gemini
```

Expected first selected production reference:

```text
references/production/full_body_front.png
```

Manifest:

```text
output/guriya/reference_selection/full_body_standing/generation_manifest.json
```

## 8. Debug Preview Mode

Cropped previews default mode mein select nahi hotay. Debug ke liye explicit flag:

```bash
aifs select-references projects/guriya/tests/reference_selection/close_up_front.yaml --engine gemini --allow-preview-references
```

Weak fallback debug:

```bash
aifs select-references projects/guriya/tests/reference_selection/full_body_standing.yaml --engine gemini --allow-weak-fallbacks
```

Production mein weak fallback aur preview references avoid karein jab tak explicit
review reason na ho.

## 9. Verification

Automated verification:

```bash
pytest
ruff check .
mypy src
```

Selector checks:

- close-up front ka first production ref `front`
- profile-left ka first production ref `left_profile`
- full-body standing ka first production ref `full_body_front`
- rejected references select nahi hoti
- unapproved references default mode mein select nahi hoti
- cropped previews default mode mein select nahi hoti
- master sheet default mode mein select nahi hoti
- engine reference limit respect hota hai
