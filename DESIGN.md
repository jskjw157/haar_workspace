---
name: HAAR Workspace
description: A quiet operational console for visible work and honest connection states.
colors:
  bg: "#f5f6f8"
  surface: "#ffffff"
  rail: "#181b22"
  text: "#1b202b"
  secondary: "#505a6c"
  muted: "#647084"
  line: "#e1e5ec"
  line-strong: "#c8ced8"
  hover: "#f1f4f9"
  primary: "#2855d9"
  primary-hover: "#1c43b9"
  primary-soft: "#edf2ff"
  error: "#b23d32"
  error-soft: "#fff0ed"
  warning: "#956114"
  warning-soft: "#fff5e1"
  success: "#267349"
  success-soft: "#eaf6ee"
typography:
  headline:
    fontFamily: "-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR',sans-serif"
    fontSize: "2rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-.035em"
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
    lineHeight: 1.5
    letterSpacing: "-.015em"
  label:
    fontFamily: "-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR',sans-serif"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "-.015em"
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
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
    textColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    padding: "9px 15px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.secondary}"
    rounded: "{rounded.sm}"
    padding: "9px 15px"
  button-text:
    textColor: "{colors.secondary}"
  field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "10px 12px"
  nav-item:
    rounded: "{rounded.sm}"
    padding: "11px 12px"
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
---

# Design System: HAAR Workspace

## Overview

**Creative North Star: "The quiet work console"**

The quiet work console makes operational reading immediate: a dark navigation rail frames a cool neutral canvas, while white grouped surfaces and fine rules organize dense information. Blue identifies actions and selection; text hierarchy and alignment carry the rest.

The component system uses native interface typography, restrained curves and flat surfaces. Connection and draft labels remain explicit, so a polished presentation never implies an AI adapter is running or a draft has been dispatched.

**Key Characteristics:**

- Dark rail with cool neutral content.
- One blue action accent with semantic status colors.
- Ranked focus rows and aligned work metadata.
- Flat surfaces, visible focus and responsive reflow.

## Colors

Action blue sits against cool whites and dark ink. The frontmatter preserves the exact shared CSS values. Sidecar tonal ramps are synthesized preview metadata, not additional colors used by the application.

### Primary

- **Action Blue** (`primary`): primary buttons, active filters, selected focus pins, links and the review progress bar.
- **Pressed / Hover Blue** (`primary-hover`): primary-button hover.
- **Selection Mist** (`primary-soft`): selected controls and mobile navigation.

### Neutral

- **Cool Canvas / White Surface** (`bg`, `surface`): page ground and grouped content.
- **Graphite Rail / Ink** (`rail`, `text`): desktop navigation and primary reading.
- **Slate / Muted Slate** (`secondary`, `muted`): supporting copy and metadata, with their hierarchy preserved.
- **Fine Rule / Field Rule / Hover Wash** (`line`, `line-strong`, `hover`): row separation, input boundaries and interaction feedback.

Error and warning pairs identify blocked work, overdue dates and uncertain saving. Success pairs identify reviewed or archived states; these are semantic colors, not additional decorative accents. Rail-specific text and selected-navigation tones remain component-local CSS values.

**The Action Blue Rule.** Use blue for actions, selection and review emphasis; reserve warning, error and success colors for their stated status.

## Typography

**Interface Font:** the native sans-serif stack in the frontmatter. No downloadable font or separate display family is used. The stack adapts to the host platform; Korean fallbacks are named, not fetched.

The hierarchy is compact and task-oriented. The page heading uses the headline role; section headings use title. Introductory copy uses body, and dense metadata uses label. Individual task titles are (15px, 600), row titles (13px, 550), and next actions (12px). These are implemented component roles, not an invented proportional scale.

The page heading becomes (27px) on mobile, section headings (15px), and form fields (16px) to retain comfortable mobile entry. Counts and dates use tabular numerals. Default interface tracking is slightly tight; labels retain sentence case. Supporting text commonly uses (11–12px), and explanatory paragraphs use line heights of (1.7–1.8). Form notes cap at (75ch).

## Layout

Desktop uses a fixed rail (216px), a white top bar (64px) and a content area capped at (1536px), with page padding (36px 40px 22px). The primary grid places work beside a supporting column (264px), separated by (32px). A four-column summary precedes the work area. The spacing primitives are the actual shared CSS scale; component-local measurements remain local.

The focus group is a single bordered list with numbered rows rather than separate floating cards. Work rows align a pin, flexible title, state (94px), AI (85px) and deadline (61px), with gaps (12px). The title column can shrink and wrap.

At (1200px) and below the rail narrows to (196px) and the content tightens. At (1000px) and below the support column moves beneath the work in two columns. At (760px) and below navigation becomes four bottom tabs, the top bar is (54px), content padding is (26px 20px 20px), and work rows stack status, AI and deadline below their title. The final mobile rules give controls minimum targets of (44px). Bottom navigation and toasts account for safe-area insets. At (350px) and below the introduction and form grid stack. At (1600px) and above content padding widens and the support column becomes (290px).

## Elevation & Depth

Borders, white surfaces and the darker rail establish depth without shadows on work panels. Toasts use (`0 5px 16px #18203325`); dialogs use (`0 20px 70px #18203330`) with a translucent backdrop (`#18203370`). These exact overlay values also live in the sidecar.

**The Flat Work Rule.** Keep working surfaces flat; reserve shadows for dialogs and transient notifications.

## Shapes

Controls and fields use the small radius, avatars and inset result blocks use the medium radius, and focus groups, agent cards and dialogs use the large radius. Fine (1px) borders define containers and fields. Status indicators are small circles; priority uses three rising bars plus a text label. Filter controls use an underline rather than pill silhouettes. The small outlined sample label is reserved for actual sample records.

## Components

### Buttons

Compact, direct controls. Primary buttons use Action Blue, white text and the small radius, with the exact padding in the frontmatter. Hover darkens the fill; active uses the component-local pressed blue (`#16389e`). Secondary buttons use white, a strong border and slate text; hover uses the neutral wash. Text buttons pair a label with an optional inline SVG. Disabled buttons use muted text and the hover wash. Keyboard focus is a blue (3px) outline offset (3px).

State transitions are (160ms ease-out) for background, color and border color, only when reduced motion is not requested. There is no entrance animation.

### Chips

Filters are flat text tabs with a (2px) bottom border. Selection uses blue text and underline with stronger weight; hover darkens text. Tags are quieter compact status or sample annotations, not repeated decoration.

### Cards / Containers

Focus groups and agent cards use white surfaces, fine borders and the large radius. Focus rows have internal separators and the padding in the frontmatter; agent cards use their own recorded padding. Supporting panels use bottom rules instead of enclosing cards. Result and handoff blocks use a subtle neutral inset with medium corners. Cards do not lift on hover.

### Inputs / Fields

White fields use a strong neutral border, small corners and the recorded padding, with a minimum height (42px). Focus replaces the visible border with a blue (2px) outline offset (1px). Placeholder text uses muted slate. Mobile fields are at least (44px) high. Error and uncertain-save banners use semantic soft backgrounds, a border and explanatory text; they remain separate from field styling.

### Navigation

The dark desktop rail uses icon-and-label rows. Hover lightens the row; selection uses a muted blue rail fill with pale text. Counts are compact and subordinate. On mobile, the rail becomes white bottom navigation with blue-soft selection and no counts. Icons use the shipped inline SVG vocabulary: no icon font or Unicode pictogram substitution.

### Ranked Focus and Work Rows

Focus rows lead with a stable ordinal, priority bars and a readable task title, followed by the next action and metadata. A selectable pin remains a real button with a pressed state. The work list repeats the same task language in aligned columns, then reflows on mobile. Priority and stage retain text labels in addition to their visual marks. Review progress is a slim linear track whose copy identifies manual result review, not AI execution.

## Do's and Don'ts

### Do:

- **Do** keep priority, title, status, assigned AI and deadline easy to scan.
- **Do** preserve explicit draft, sample and disconnected labels.
- **Do** use the existing inline stroke SVGs and visible keyboard focus.
- **Do** reflow rows into stacked metadata and move navigation to the bottom on mobile.

### Don't:

- **Don't** imply running AI, dispatch or external approval through status styling.
- **Don't** add decorative hero treatments, repeated badges or a circular progress display to this console.
- **Don't** add external fonts, imagery or a second decorative action accent.
