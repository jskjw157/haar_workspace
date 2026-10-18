---
name: HAAR Workspace
description: A bright, soft fashion and jewelry work studio with honest draft and connection states.
colors:
  "bg": "#faf7f5"
  "surface": "#fffdfb"
  "rail": "#f0e6e5"
  "text": "#382b35"
  "secondary": "#67525e"
  "muted": "#715e69"
  "line": "#e6dadd"
  "line-strong": "#9c8390"
  "hover": "#f4ecee"
  "primary": "#78455c"
  "primary-hover": "#63374b"
  "primary-active": "#532d3f"
  "primary-soft": "#f0e1e7"
  "error": "#a43f3b"
  "error-soft": "#fbece8"
  "warning": "#865b21"
  "warning-soft": "#faf0df"
  "success": "#466b56"
  "success-soft": "#e9f0e8"
  "on-primary": "#fffdfb"
  "rail-hover": "#e8d9df"
  "rail-count": "#916579"
  "studio-rose": "#f2e5e7"
  "studio-sage": "#e9eee7"
  "studio-cream": "#f4eee3"
  "studio-lilac": "#ece7f0"
  "avatar": "#eee4e8"
  "track": "#e8dbe1"
  "neutral-dot": "#88737f"
  "warning-line": "#c1a370"
  "error-line": "#c28d80"
  "inset": "#f6efed"
  "toast": "#47313e"
  "scrim": "#382b3570"
  "shadow": "#382b3525"
typography:
  headline:
    fontFamily: "-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR',sans-serif"
    fontSize: "2rem"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "-.025em"
  title:
    fontFamily: "-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR',sans-serif"
    fontSize: "16px"
    fontWeight: 650
    lineHeight: 1.5
    letterSpacing: "-.025em"
  body:
    fontFamily: "-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR',sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.8
    letterSpacing: "-.015em"
  label:
    fontFamily: "-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR',sans-serif"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "-.015em"
  field:
    fontFamily: "-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR',sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "-.015em"
rounded:
  "sm": "6px"
  "md": "8px"
  "lg": "12px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "24px"
  "6": "32px"
  "7": "40px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
    padding: "9px 15px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-primary-active:
    backgroundColor: "{colors.primary-active}"
  button-new-task:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
    padding: "9px 15px"
    height: "44px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.secondary}"
    rounded: "{rounded.md}"
    padding: "9px 15px"
  button-text:
    textColor: "{colors.secondary}"
  field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "10px 12px"
  nav-item:
    textColor: "{colors.secondary}"
    rounded: "{rounded.sm}"
    padding: "11px 12px"
  nav-item-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
  filter-active:
    textColor: "{colors.primary}"
    padding: "8px 12px"
  focus-row:
    backgroundColor: "{colors.surface}"
    padding: "19px 20px"
  agent-card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    padding: "22px"
  menu-banner:
    backgroundColor: "{colors.studio-rose}"
    rounded: "{rounded.lg}"
    width: "100%"
    height: "clamp(240px,26vw,340px)"
---

# Design System: HAAR Workspace

## Overview

**Creative North Star: "The soft work studio"**

The soft work studio brings HAAR’s fashion and jewelry context into operational work: warm porcelain surrounds a light rose sidebar, warm white surfaces hold dense records, and mulberry marks the next action and current selection. Supporting rose, cream, sage and lilac grounds give the four menu illustrations a coherent home.

Native Korean interface typography, fine warm rules and restrained curves keep priorities, evidence and next actions legible. Decorative generated illustrations orient the workspace without replacing labels or suggesting real products, running agents or completed external actions. Connection and draft states remain explicit.

**Key Characteristics:**

- Bright porcelain, rose and warm white surfaces throughout the interface.
- Mulberry actions, selection, hover and visible keyboard focus.
- Large full-width menu imagery alongside preserved small paper studies.
- Dense ranked work rows, native Korean type and responsive reflow.

## Colors

The palette is warm, bright and softly rose-toned, with readable plum text and a single mulberry action family. Frontmatter records the exact shared CSS values; synthesized sidecar tonal ramps are preview metadata, not extra application colors.

### Primary

- **Mulberry / Deep Mulberry / Pressed Mulberry** (`primary`, `primary-hover`, `primary-active`): primary actions, active desktop navigation, links, filter selection and keyboard focus.
- **Rose Selection / Warm On-Action** (`primary-soft`, `on-primary`): selected pins, mobile selection and text on mulberry.

### Secondary

- **Studio Rose / Cream / Sage / Lilac** (`studio-rose`, `studio-cream`, `studio-sage`, `studio-lilac`): the today, all-items, review and AI-workspace banner grounds respectively. Sage also grounds agent-card avatars.

### Neutral

- **Porcelain / Warm White / Rose Rail** (`bg`, `surface`, `rail`): page canvas, grouped content and the desktop sidebar.
- **Plum Ink / Supporting Plum / Muted Plum** (`text`, `secondary`, `muted`): reading hierarchy, including placeholders and metadata.
- **Warm Rule / Field Rule / Rose Hover** (`line`, `line-strong`, `hover`): subtle separation, meaningful field boundaries and interactive feedback.
- **Rail Hover / Count Rose / Avatar / Track / Neutral Dot / Inset** (`rail-hover`, `rail-count`, `avatar`, `track`, `neutral-dot`, `inset`): component support tones.
- **Toast / Scrim / Shadow** (`toast`, `scrim`, `shadow`): transient and modal layers.

Error and warning pairs indicate blocked, overdue or uncertain-save states; success pairs indicate reviewed or archived states. The corresponding line tokens support warning and error banners. These meanings remain distinct from the decorative menu colors.

**The Mulberry Action Rule.** Use mulberry for actions, selection and focus; keep warning, error and success colors tied to their stated meanings.

**The Instant Selection Rule.** Navigation selection changes without a color transition, preserving readable foreground and background pairs throughout the menu switch.

## Typography

**Interface Font:** the native sans-serif stack in the frontmatter, with named Korean fallbacks. No downloadable font or separate display face is used.

The final page heading uses the headline role (650, 2rem, 1.25), becoming (25px) on mobile. Section headings use title (650, 16px), becoming (15px) on mobile. Introductory copy uses body (13px, 1.8), becoming (12px) on mobile. Label describes dense metadata (11px). Task titles use (15px, 600), record titles (13px, 550), and next actions (12px). Counts and dates use tabular numerals.

Form fields use the field role on desktop and become (16px) on mobile for comfortable entry. Supporting explanations use line heights (1.7–1.8); form notes cap at (75ch). Native interface text carries the hierarchy; the Latin HAAR wordmark remains a restrained brand detail.

## Layout

Desktop has a fixed light sidebar (216px), a warm white top bar (64px), and main content capped at (1536px) with padding (36px 40px 22px). The work/support grid uses a supporting column (264px) and gap (32px). Four summary columns precede the work area. Shared spacing follows the frontmatter scale; component-local measurements remain local.

Each of the four menu views places its title, description and visible new-task CTA above a separate full-width banner. The banner is (100%) of the content width and (clamp(240px,26vw,340px)) high on desktop; at the mobile breakpoint it is (210px) high. The source scenes are (720 × 480), rendered with contain, centered positioning and a (1.08) scale within the clipped banner. No text overlaps the detailed image. The new-task CTA has a minimum height (44px) at every width. At narrow widths the introduction stacks while preserving this order.

The focus group is one bordered numbered list. Desktop work rows align a pin, flexible title, status (94px), AI (85px) and deadline (61px), separated by (12px). Titles can shrink and wrap.

At (1200px) and below the sidebar narrows to (196px) and content tightens. At (1000px) and below support moves beneath work in two columns. At (760px) and below navigation becomes four bottom tabs, top bar becomes (54px), content padding becomes (26px 20px 20px), work metadata stacks, and fields and mobile controls use minimum targets (44px). Bottom navigation and toasts account for safe-area insets. At (350px) and below the introduction and form grid stack. At (1600px) and above content padding and the support column widen.

## Elevation & Depth

Working surfaces are flat, distinguished by warm tonal layers and fine borders. Shadow is reserved for a toast and the modal editor; the backdrop uses the scrim token. There are no floating card shadows.

### Shadow Vocabulary

- **Toast:** `0 5px 16px var(--color-shadow)` for transient feedback.
- **Dialog:** `0 20px 70px var(--color-shadow)` for the modal editor.

**The Flat Work Rule.** Keep working surfaces flat; reserve shadows for dialogs and transient notifications.

## Shapes

Gently curved controls and fields use the shared small radius; primary and secondary buttons use the medium radius. Focus groups, agent cards, dialogs and menu banners use the large radius. Avatars and nested evidence surfaces use the medium radius; compact tags retain local (3–4px) corners. Fine one-pixel borders separate records and group related content. Status dots stay small and circular; they never resemble an active heartbeat.

## Components

### Buttons

Mulberry primary actions use warm on-action text, medium corners and padding (9px 15px); hover and pressed states use the corresponding deeper tokens. The header new-task action is at least (44px) high at all widths; other desktop primary and secondary actions are at least (40px), rising to (44px) on mobile. Secondary actions use warm white, a field-rule border and supporting plum. Text actions use supporting plum and become mulberry on hover. Disabled controls use muted text, hover wash and a fine rule.

Buttons, links and expandable summaries have a (3px) mulberry focus outline offset by (3px). Non-navigation controls transition background, color and border color over (160ms ease-out) only under `prefers-reduced-motion: no-preference`.

### Chips and status labels

Filters are text tabs with an active mulberry underline (2px). Hover uses the warm hover wash. Labels retain explicit status text beside a dot; review is warning, blocked is error, and archived is success. Neutral tags use the hover wash; content-confirmed tags use success colors. Styling never implies that an execution adapter is connected.

### Cards / Containers

Focus lists group numbered rows within a large-radius warm white container. Row hover uses the shared hover wash. Agent cards use warm white, fine borders, large corners and padding (22px), becoming (20px) on mobile. Evidence and handoff blocks use the inset tone and medium corners. Summary and support panels use spacing and rules instead of floating-card elevation.

### Inputs / Fields

Warm white fields have a one-pixel field-rule border, small corners, padding (10px 12px), and a minimum height (42px) on desktop. Mobile fields use padding (10px), font size (16px) and minimum height (44px). Placeholders use muted plum at full opacity. Focus uses a (2px) mulberry outline offset by (1px), with the border transparent. Carets use mulberry.

### Navigation

The bright rose sidebar uses supporting plum idle labels, warm rail-hover feedback, and a solid mulberry active item with warm on-action text. Active counts use count rose. Selection is immediate (`transition: none`), avoiding transient low-contrast color interpolation. Navigation targets are at least (44px) high on desktop. Mobile tabs use warm white, muted idle labels, and rose-selection/mulberry active pairing; each item is at least (52px) high. The active menu is also exposed by `aria-current`.

### Ranked focus and work rows

Stable ordinals, priority bars, task titles and next actions organize the focus group. Pins retain a real pressed state; priority and stage retain text labels. The slim linear progress track describes manual result-link review, never AI execution. Current records are pre-Paperclip intake drafts, manual artifact reviews and handoff notes; the disconnected labels must remain visible.

### Menu banners and small paper studies

The existing four-menu switch updates the view title, description, banner source and matching background together. Real generated assets are `app/static/banners/today.webp`, `all.webp`, `review.webp` and `agents.webp`: planning, organized work/materials, draft inspection and disconnected execution workstations. These are decorative (`alt=""`, hidden from assistive technology), not product photographs or execution evidence. Preserve the existing focus, review, connection and empty-state illustrations under `app/static/illustrations/`; small studies stay with section orientation and empty states rather than individual data rows. No autoplay or decorative live-state animation is introduced.

## Do's and Don'ts

### Do:

- **Do** keep priority, title, status, assigned AI and deadline easy to scan.
- **Do** preserve explicit draft, sample and disconnected labels.
- **Do** place each menu’s full-width banner below its title and new-task action; keep the action at least 44px high.
- **Do** use the native Korean font stack, inline stroke SVG controls and visible keyboard focus.
- **Do** reflow work rows into stacked metadata and move navigation to the bottom on mobile.

### Don't:

- **Don't** restore the dark navigation rail or blue admin palette.
- **Don't** imply running AI, automatic dispatch, external publishing or external approval through styling or illustrations.
- **Don't** place text over the detailed banner image or turn decorative artwork into product evidence.
- **Don't** add external fonts, remote UI dependencies or autoplay motion.
