# Environment Bible

The environment bible stores reusable locations for production continuity. Every
environment is a manually referenced asset with metadata, prompt guidance, lighting
slots, and camera angle slots.

## Required Files

- `environment.yaml`
- `prompt.md`

## Required Folders

- `references/`
- `lighting/`
- `angles/`

## House Reference Image Standard

`references/` must support:

- `front_day.png`
- `front_evening.png`
- `front_night.png`
- `back_day.png`
- `back_evening.png`
- `back_night.png`

## Camera Angles

`angles/` must support:

- `front.png`
- `back.png`
- `left.png`
- `right.png`
- `top.png`
- `drone.png`
- `inside_to_outside.png`
- `outside_to_inside.png`

## Lighting

`lighting/` must support:

- `morning.png`
- `afternoon.png`
- `golden_hour.png`
- `evening.png`
- `night.png`
- `rain.png`

Do not invent environment appearance in metadata. Approved visual references are the
source of truth.
