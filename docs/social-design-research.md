# Social design research: what top finance accounts do, and what we took from it

Written 2026-09-20 for the Debt Direct Solutions Instagram and Facebook feeds. This is the
reasoning behind design system v2 ("Ledger") in `agent/src/social/html/theme.css`.

## Who we looked at

| Account | Followers (approx.) | What their best posts have in common |
|---|---|---|
| Vivian Tu, @your.richbff | 4M | A person on camera, one idea per post, a hook line in the first second, saves-first educational carousels. Design is secondary to the face. |
| Humphrey Yang, @humphreytalks | 3M+ | Same: creator-led, whiteboard-style math, calm delivery. Numbers are shown being computed. |
| Freedom Debt Relief, @freedomdebtrelief | 33K | "From stress to stability" tone. Influencer payoff stories, employee voices, soft premium palette. Brand posts alone underperform the human ones. |
| National Debt Relief, @nationaldebtrelief | scaled through paid social | User-generated how-to videos and number breakdowns, then paid amplification. Organic feed reads corporate. |
| Accredited Debt Relief, Debt Freedom USA | small | Template-looking posts, high hashtag counts, stock imagery. Low engagement: the look we are moving away from. |

Instagram itself does not expose per-post engagement for accounts we do not manage, so
"highest engagement" is read from what these accounts pin, repeat, and put paid spend behind,
plus the 2026 platform research summarized below.

## What the 2026 research says drives engagement

- Carousels average about 10% engagement vs 7% for single images and 6% for Reels, and earn
  about 22% more saves than a single photo. Saves and DM shares outweigh likes in ranking.
- Slide 1 is the audition: bold type, high contrast, one headline with a curiosity gap.
  Text-led covers outperform photo-led covers for educational content.
- One number per slide with one contextual sentence beats a dense slide. 6 to 10 slides,
  completion rate is the gate.
- Human faces and employee voices outperform brand accounts. This is the one lever we
  cannot render; it needs Brendon on camera or in a photo. Everything else is design.
- Trust for a financial brand comes from looking established and consistent: the same type,
  the same palette, the same layout grid on every post, real contact details, and no claims
  that read like a pitch.

## What "premium" looks like in 2026, concretely

Pulled from the fintech and luxury-brand design trend write-ups for 2026:

1. **Editorial serif headlines, quiet sans body.** Playfair Display or a sharp serif for the
   line that matters, a clean sans (Inter, DM Sans, Poppins) for everything else. The serif
   carries authority; the sans keeps it modern. The named "editorial/premium" pairing in
   the font-trend reports is exactly Playfair + a geometric sans.
2. **Restrained, grown-up palette.** Navy, deep green, or slate as the base. Gold as a small
   accent, roughly 10% of the surface, and a *muted warm* gold rather than a bright yellow
   (bright yellow-heavy gold reads cheap on screens). Harsh neon blocks are out.
3. **Texture over flat.** Fine paper grain, soft glows, hairline rules, thin frames. Depth
   without drop shadows and rounded pills.
4. **Seamless, consistent grid.** Every slide shares the same margins, header, and footer so
   the swipe feels like turning pages of one document.
5. **Real photography only when it is real.** Stock that looks like stock, and any AI imagery,
   undercuts trust and Meta reduces reach on undisclosed AI content.
6. **True credibility cues.** Website, what the offer actually is (a free review), what it is
   not (no obligation). No badges, awards, or "trusted by" claims we cannot back.

## What we changed (v1 → v2)

| Element | v1 | v2 "Ledger" |
|---|---|---|
| Headlines | Poppins bold, 92px | Playfair Display, 96px, highlighted words in italic gold |
| Kicker | Yellow pill, rounded | Small caps in gold with a short rule, hairline under the header |
| Palette | Navy, bright blue, yellow blocks | Navy, slate, paper, white; the logo's yellow used only as gold accents and the emphasis bar |
| Background | Big blue circles | Soft glows, paper grain, a 1px inset frame |
| Stat slide | Yellow card, big sans number | Serif numeral between two hairlines, small-caps label |
| Lists | Yellow check circles | Hairline dividers, serif italic numerals or thin gold checks |
| Myth vs fact | Rounded cards | Bordered two-column plate, fact column in navy (gold on dark themes) |
| Footer band | Logo, follow, dots | Logo, follow, `debtdirectsolutions.com`, thin gold progress ticks |
| Cover extras | "swipe →" in yellow | Small-caps SWIPE, an italic "4 ideas, 6 slides" serial line |
| CTA slide | White with yellow pill | Paper texture, serif headline, follow line, a trust strip: Free review · No obligation · site |
| Themes | navy, cream, sky, white | navy, paper, slate, white (old names still map) |

Theme aliases: `cream` → `paper`, `sky` → `slate`. Existing queue specs render unchanged.

## Looks (added 2026-09-24)

Five complete looks, each a font pairing, palette and shape language, picked per post by a seed
of the post's date so the grid does not read as one template. All share the logo, footer text and
layout grid. Fonts are open-license from the Google Fonts repo, stored in `agent/assets/fonts/`.

| Look | Fonts | Palette | Shapes |
|---|---|---|---|
| ledger | Playfair Display + Poppins | navy, paper, gold | glows, grain, hairline frame |
| studio | DM Serif Display + Inter | deep green, mint | rings, rounded cards |
| grotesk | Space Grotesk | charcoal, the logo's lemon and blue | hard corners, diagonal stripes, a blue square |
| warm | Fraunces + Outfit | plum, terracotta, sand | arches, blobs |
| notebook | Lora + Inter | slate blue, ice, gold | ruled lines, margin rule |

Within each look the per-post variants still apply (cover alignment, glow corner, frame, kicker
style, footer style, highlight style, white/paper body mix, accent slide, serif body, big index).
Pin any of it with `spec.variant`, for example `{"look": "warm", "cover_align": "center"}`.

## What still needs a human

- **A face.** The single biggest gap between us and the accounts that perform. A short
  phone video (even a still photo) of Brendon per week would beat any template.
- **Own photos.** `site/social/photos/own/` is empty. Real desk, real office, real hands
  on a statement. Until then one-pagers render on the navy/paper themes without photos.
- **Licensed music** for Reels in `agent/assets/audio/`.

## Sources

- Font trends 2026 (Simplified), editorial/premium pairing named as Playfair + sans.
- Instagram carousel trends 2026 (Scrolo, whaaat.ai, Slidy Creator, Krumzi, TrueFuture Media).
- Financial brand visual identity guides 2026 (WOLF Financial, Metabrand, Splash Creative,
  Intelnest, Hyper Creative, Athub on gold ratios).
- Freedom Debt Relief and National Debt Relief public Instagram profiles; Level Agency case
  study on National Debt Relief's paid social.
- Top finance influencers 2026 (HireInfluence).
