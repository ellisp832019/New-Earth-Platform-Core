# NEDS — New Earth Design System Contract

Platform Core records which NEDS version each UI project targets.

The design system should eventually expose machine-readable tokens for:

- colour;
- typography;
- spacing;
- radius;
- elevation;
- motion;
- component versions;
- accessibility requirements;
- application shell patterns;
- status language.

Platform Core v0.1 governs metadata only. It does not implement the Flutter package, component library, or source scanner.

Current project contracts declare:

- design system;
- design-system version;
- application shell;
- product personality;
- accessibility requirement.

Future NEDS metadata may include token versions, component versions, deprecated components, supported themes, and design compliance requirements.

NEOS can later use this metadata to detect:

- outdated NEDS versions;
- hard-coded colours;
- deprecated components;
- non-standard spacing;
- application shell drift;
- accessibility drift.

Those checks belong in NEOS because they require observed source-code inspection.
