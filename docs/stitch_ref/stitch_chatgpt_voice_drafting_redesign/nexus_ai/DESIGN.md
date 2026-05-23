---
name: Nexus AI
colors:
  surface: '#0f1512'
  surface-dim: '#0f1512'
  surface-bright: '#343b37'
  surface-container-lowest: '#0a0f0d'
  surface-container-low: '#171d1a'
  surface-container: '#1b211e'
  surface-container-high: '#252b28'
  surface-container-highest: '#303633'
  on-surface: '#dee4df'
  on-surface-variant: '#bccac2'
  inverse-surface: '#dee4df'
  inverse-on-surface: '#2c322e'
  outline: '#86948d'
  outline-variant: '#3d4a44'
  surface-tint: '#61dbb4'
  primary: '#61dbb4'
  on-primary: '#00382a'
  primary-container: '#12a480'
  on-primary-container: '#003024'
  inverse-primary: '#006c52'
  secondary: '#b9c7e0'
  on-secondary: '#233144'
  secondary-container: '#3c4a5e'
  on-secondary-container: '#abb9d2'
  tertiary: '#95d3ba'
  on-tertiary: '#003829'
  tertiary-container: '#5f9d85'
  on-tertiary-container: '#003023'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#7ff8cf'
  primary-fixed-dim: '#61dbb4'
  on-primary-fixed: '#002117'
  on-primary-fixed-variant: '#00513d'
  secondary-fixed: '#d5e3fd'
  secondary-fixed-dim: '#b9c7e0'
  on-secondary-fixed: '#0d1c2f'
  on-secondary-fixed-variant: '#3a485c'
  tertiary-fixed: '#b0f0d6'
  tertiary-fixed-dim: '#95d3ba'
  on-tertiary-fixed: '#002117'
  on-tertiary-fixed-variant: '#0b513d'
  background: '#0f1512'
  on-background: '#dee4df'
  surface-variant: '#303633'
  surface-card: '#161D1A'
  surface-glass: rgba(22, 29, 26, 0.6)
  text-primary: '#F8FAFC'
  text-secondary: '#94A3B8'
  market-up: '#10A37F'
  market-down: '#EF4444'
  market-neutral: '#64748B'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  mono-stats:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 32px
  unit-xs: 4px
  unit-sm: 8px
  unit-md: 16px
  unit-lg: 24px
  unit-xl: 40px
---

## Brand & Style

The design system is engineered for **Nexus AI**, an institutional-grade investment platform that bridges the gap between complex quantitative finance and retail accessibility. The brand personality is **Intelligent, Sophisticated, and Vigilant**. It must evoke a sense of deep-tech reliability—as if the user is stepping into a high-end quant fund's private terminal.

The chosen style is a fusion of **Modern Corporate** and **Glassmorphism**. 
- **Minimalism** ensures that data-heavy screens remain legible and decision-focused.
- **Translucent Layers** (Glassmorphism) are used to signify the "AI Layer"—a digital lens that clarifies complex market data.
- **High-Trust Visuals** are achieved through a restrained color palette, precise typography, and intentional use of whitespace, moving away from "gamified" fintech toward a serious wealth management experience.

## Colors

The system utilizes a **True Dark Mode** default to provide a focused, low-strain environment for monitoring financial markets.

- **Primary (Emerald):** Reserved strictly for "Growth," "Confirmation," and "Primary Action" signals. It represents the "vibrant intelligence" of the AI.
- **Secondary (Slate):** Used for structural elements, inactive states, and secondary information architecture to maintain a professional, calm atmosphere.
- **Neutral (Deep Charcoal):** The canvas. This specific shade provides better depth for glassmorphism effects than pure black.
- **Functional Colors:** A high-contrast red is introduced solely for risk alerts and downward market movements, ensuring immediate cognitive recognition of portfolio threats.

## Typography

The typography system relies on **Inter** for its exceptional legibility in data-dense environments. For numerical financial data and ticker symbols, **Geist** (a technical, developer-friendly mono font) should be used as a secondary family to ensure vertical alignment of digits in tables and portfolio lists.

- **Scale:** High contrast between display sizes and body text helps users scan complex dashboards.
- **Weight:** Medium weights (500) are preferred for labels to maintain readability against dark backgrounds.
- **Hierarchy:** "Display" and "Headline" styles are reserved for portfolio totals and AI-generated insight headers.

## Layout & Spacing

This design system employs a **12-column Fixed Grid** for desktop to ensure data visualizations maintain consistent aspect ratios, transitioning to a **Fluid Grid** for mobile devices.

- **Rhythm:** An 8px linear scale governs all padding and margins.
- **Dashboard Layout:** A "Modular Bento" approach is used, where content is grouped into logical blocks. On desktop, the primary AI insight panel should span 4 columns, while the portfolio visualization spans 8. 
- **Mobile Reflow:** For mobile, all 12-column components stack vertically. Sidebars collapse into a bottom-anchored navigation bar and a floating "Ask AI" action button.

## Elevation & Depth

Hierarchy is established through **Tonal Layers** and **Backdrop Blurs** rather than traditional shadows.

- **Level 0 (Base):** Deep Charcoal (#0F1512).
- **Level 1 (Cards):** Surface-card (#161D1A) with a subtle 1px border (#334155).
- **Level 2 (Overlays/Modals):** Surface-glass with a 20px backdrop blur and a slight top-down gradient border to simulate light catching the edge of a glass pane.
- **Shadows:** Only used for high-level floating elements (like the Chat AI bubble). Use a soft, ultra-diffused shadow with a 0% spread and 20% opacity.

## Shapes

The shape language is **Refined and Modern**. 
- **Standard UI Elements:** (Inputs, Small Buttons) use a 0.5rem (8px) radius.
- **Container Elements:** (Cards, Modals, Large Buttons) use `rounded-lg` (16px) to create a approachable, professional feel.
- **AI Components:** Chat bubbles and "Ask AI" triggers may use `rounded-xl` (24px) to distinguish AI-generated content from structural system data.

## Components

- **Buttons:** Primary buttons use the Emerald gradient (Primary to Tertiary) with white text. Secondary buttons are "Ghost" style with Slate borders.
- **AI Rationale Cards:** Feature a subtle left-accent border in Emerald to signify the "Reasoning" layer. These cards use the Glassmorphism style to feel "layered" over the raw data.
- **Input Fields:** Dark-filled with a subtle Slate border that glows Emerald on focus. Errors are displayed with high-contrast red text and borders.
- **Chips/Badges:** Small, low-saturation backgrounds (e.g., 10% opacity Emerald) with high-saturation text for status indicators like "Bullish" or "Rebalance Recommended."
- **Data Tables:** Row-based with no vertical lines. Hover states use a 5% opacity Emerald highlight.
- **Chat Interface:** A floating, compact window in the bottom-right. Message bubbles from the AI utilize the Glassmorphic level 2 styling to differentiate from user messages.