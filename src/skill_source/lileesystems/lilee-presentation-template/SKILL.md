---
name: lilee-presentation-template
description: "Use when creating English-language LILEE Systems technical presentations that must follow the company PPTX template, preserve brand consistency, and maximize information density without sacrificing scanability. This skill defines LILEE-specific presentation rules only; generic PPTX creation, editing, extraction, and file handling remain the responsibility of the existing pptx skill."
license: Proprietary. LICENSE.txt has complete terms
---

# LILEE Presentation Template

## Overview

This skill is the LILEE Systems presentation overlay. It does **not** replace the `pptx` skill. It defines how company presentations should look and read when the output must follow the LILEE PPTX template.

Use this skill together with `pptx` whenever the work involves a LILEE presentation. The `pptx` skill handles PowerPoint mechanics. This skill handles company-specific brand, density, language, and communication standards.

The default use case is **technical and solution explanation decks**, not sales storytelling. The goal is to communicate the most useful technical information in the fewest slides possible, while keeping each slide easy to scan.

## When to Use

Use this skill when:
- the output is a LILEE Systems presentation
- the deck should match the company PPTX template
- the deck is primarily for technical explanation, architecture, design review, root cause review, status communication, or solution discussion
- the content should be written in English

Do not use this skill by itself for generic `.pptx` operations. Load `pptx` for file handling and apply this skill as the company-template layer.

## Boundaries with `pptx`

**This skill owns:**
- company template compliance
- brand palette and visual consistency
- language expectations for slide content
- presentation density and scanability rules
- content-shaping rules for technical communication

**The `pptx` skill owns:**
- reading or extracting text from `.pptx` files
- editing `.pptx` files
- generating or exporting slide decks
- converting slides to images or PDF
- slide-level QA workflows for PowerPoint artifacts

Do not duplicate generic PPTX instructions here. Reuse the `pptx` skill for those operations.

## Core Communication Standard

All presentation content should be written in **English**.

These decks are optimized for technical comprehension, not marketing tone. Prefer precise wording, concrete labels, and explicit structure. Avoid slogan-like language, emotional framing, and decorative narrative filler.

The presentation should adapt its form to the material. Do **not** force a fixed slide pattern. Choose the structure that expresses the source content most clearly.

For **PO requirement review** decks, default to an information-surface style rather than a presenter-narrative style. Start from the core rule, formula, model, or artifact being reviewed, then show the contribution terms, boundaries, and explicit confirmation points. Do not add a "Goal" section unless the user explicitly asks for it.

## Information Density Standard

LILEE presentation style is intentionally **high information density**.

The goal is to transmit the most useful information with the fewest slides practical. Do not split content into many slides just to make the deck feel lighter. If multiple related ideas can be understood on one slide through clear structure, keep them together.

High density does **not** mean visual clutter. A dense slide must still be easy to scan. Readers should be able to identify the slide's sections, locate key evidence, and understand the main takeaway quickly.

Prefer:
- fewer slides with more structured content
- tables, grids, comparison layouts, grouped callouts, and annotated diagrams when they compress information well
- combining evidence, explanation, and takeaway on the same slide when that improves comprehension
- for rule-review slides, one dense page with the formula first, then contribution terms, concrete values, and only the minimum necessary supporting sections

Avoid:
- decorative transition slides
- single-sentence slides that waste space
- oversized hero statements
- excessive whitespace that lowers information throughput
- large blocks of unstructured paragraph text
- adding more pages when the meeting only needs one review surface

If a slide becomes hard to scan within a few seconds, split or restructure it.

## Visual Aid Standard

Use diagrams, charts, and other visual aids when they improve technical comprehension.

Visuals are support material, not decoration. They should compress complexity, clarify relationships, or make comparisons easier. A good visual reduces the reader's effort to understand the system.

Do not enlarge visuals at the expense of useful content. If a diagram can be paired with concise annotations, evidence, or conclusions on the same slide, prefer that over spreading the explanation across multiple slides.

If a visual does not improve understanding, replace it with a clearer structure such as a table, grouped text, or a more explicit comparison.

For formula-heavy review slides, prefer visuals that directly explain the model:
- score composition diagrams
- time-axis graphics for threshold-based urgency models
- compact comparison tables with real weights or coefficient values

Do not add visual sections that restate the obvious. If the formula is already visible, a secondary "contribution map" is usually redundant unless it reveals a relationship the formula does not.

## PO Functional-Design / System-Operation Review Decks

When the audience is a PO reviewing how a system operates, prefer **diagram-first slides** over text-first slides. The reader should be able to understand the main behavior by looking at the drawing plus a small amount of annotation.

Default form for this class of deck:
- one light boundary / reading-guide slide at most
- then scenario-driven operational slides
- each main slide embeds the minimum architecture, data-flow, ownership, and schema concepts needed to understand that scenario
- avoid standalone "theory" slides for architecture, writer model, or schema if those concepts can be attached directly to the operational diagrams

Do **not** over-simplify away the concepts the PO still needs to review. If the source material defines them, preserve at least the following at presentation level:
- where the golden copy / operational truth lives
- who is the operational writer vs who forwards vs who persists history
- the authoritative data flow through the main systems
- the minimum schema / object identity concepts needed to understand the behavior

If the source material already contains sequence diagrams, use that as the semantic source and derive a **simplified presentation sequence** from it rather than inventing a new flow shape from scratch. Keep the presentation version one abstraction level above detailed design:
- keep the major actors / systems
- keep the key state writes and operational effects
- keep the important branches
- drop message-by-message noise, DTO detail, and implementation chatter

For PO readability:
- use simplified sequence diagrams for nominal shared flows and happy paths when ordering and handoff are the main story
- use compare views for side-by-side behavior differences
- use branch diagrams for validation / exception splits
- use fan-out maps for visibility / logging / subscriber surfaces
- do not force every page into the same diagram type

When a subsystem decomposition makes the review harder to scan, collapse it to the product-relevant boundary the user asked for. Example: if splitting one subsystem into internal components distracts from the review, keep a single subsystem block and explain ownership via notes instead.

See also `references/po-functional-review-decks.md` for a compact checklist distilled from a system-operation review session.

## Template and Brand Rules

Reuse the bundled LILEE PPTX template asset as the default visual system and the source of truth for layout compliance. The allowed layouts are the layouts already present in that template. Do not invent new layouts or create new page structures outside that template language.

When the source material does not map cleanly to a single template layout, adapt the content within the closest existing template layout instead of designing a new one from scratch.

Observed palette from the template:
- LILEE Black `#000000`
- LILEE Dark Blue `#003059`
- LILEE Mid Gray `#646569`
- LILEE Mid Blue `#004F8A`
- LILEE Gray `#4E5654`
- LILEE Orange `#FF8300`
- LILEE Yellow `#FFB700`
- LILEE Blue `#009BDE`
- Gradient treatment: `#FFB700` to `#FF8300`

Use the template's 16:9 slide structure and existing layout language where possible. Keep colors, emphasis treatments, and composition aligned with the company template rather than default generic presentation styling.

## Content-Selection Rules

Choose the presentation form that best fits the source material.

Do not hard-code preferred slide archetypes. The correct structure depends on what the material is trying to explain. Use the simplest form that makes the content understandable, technically accurate, and fast to scan.

When choosing a form, optimize for:
- technical clarity
- compression of related information
- side-by-side comparison when comparison matters
- direct visibility of the conclusion, issue, or decision
- compatibility with the company template

For rule-definition slides, prefer this order unless the user overrides it:
1. formula or scoring model first
2. each contribution term with concrete values or categories
3. eligibility / gating rules
4. tie-breaker and override rules
5. compact scenarios only if they materially help review

Avoid opening with narrative framing when the user is reviewing a rule set definition. In that case, the artifact itself should lead the slide.

## Writing Rules

Prefer concise, explicit English.

Good slide writing in this template usually has these properties:
- titles state the subject directly
- section headers reveal the structure of the slide
- labels are concrete and technically specific
- callouts explain why the reader should care
- wording is neutral, factual, and low-drama

Avoid:
- marketing adjectives
- vague claims without evidence
- long prose paragraphs when a structured layout would be clearer
- rhetorical filler meant to create excitement rather than understanding

## QA Checklist

Before finalizing a LILEE presentation, verify:
- all slide content is in English
- the deck still uses the LILEE template's visual language
- the slide count is not artificially inflated
- dense slides remain easy to scan
- visuals improve understanding rather than consume space
- important conclusions, issues, or decisions are easy to locate
- layout choice matches the actual source material instead of a forced pattern
- the deck reads like a technical explanation, not a sales pitch

## Reference Artifact

Bundled template asset:
- `assets/LILEE_Presentation_Template_2026.pptx`

Use this bundled template asset as the source of truth for visual style and layout compliance when generating future LILEE Systems presentations.
