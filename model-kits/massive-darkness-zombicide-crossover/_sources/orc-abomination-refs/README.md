# Orc Abomination (Zombicide: Green Horde) — references & generated proxy

Identified from the uploaded grey render as the **Orc Abomination** from *Zombicide: Green Horde* (CMON).

## Other angles found online

| File | Source | View |
| --- | --- | --- |
| `abom-1.jpg` … `abom-4.jpg`, `abom-family.jpg` | [Azazel's Bitz Box paint log](https://azazelx.com/2020/06/07/zombicide-black-plague-green-horde-orc-abomination-contrast-paint-experiment-20/) | Front / side / rear painted |
| `orcs-lineup.png` | [Kickstarter — Green Horde](https://www.kickstarter.com/projects/cmon/zombicide-green-horde) | Official concept lineup (Abomination on the right) |
| `orc-minis-render.png` | Kickstarter | Unpainted plastic group shot (Abomination bottom-right) |
| `generated-preview-views.png` | This repo | Preview of generated STL proxy |

Key sculpt cues matched across angles:
- raised oversized claw arm + reaching lower arm
- horned / masked small head between shoulders
- bone spikes along spine and elbows
- spiked pauldron / metal bands
- skull trophies on belt
- tattered loincloth, lunging pose, round base

## Generated STL

- Path: `green-horde/orc-abomination/04-orc-abomination-proxy-generated.stl`
- Generator: `scripts/generate_orc_abomination_proxy.py`
- Scale: ~58 mm tall, ~36 mm footprint (print-ready watertight mesh)
- Nature: **original silhouette proxy** rebuilt from references (CSG + voxel remesh). **Not** a photogrammetry scan and **not** a 1:1 CMON lookalike.

Regenerate:

```bash
python3 scripts/generate_orc_abomination_proxy.py
```

## Lookalike status

Same conclusion as [`LOOKALIKE-RESEARCH.md`](LOOKALIKE-RESEARCH.md): no free public STL recreates the retail Green Horde Orc Abomination sculpt. Closest prior stand-ins remain MZ4250 / Schlossbauer flesh-golem / zombie-ogre proxies in this folder. Paid “based on original” Green Horde KS exclusives exist (e.g. ciccioneroladro) but do not cover this retail Abomination.
