# Accessibility Checklist

Use this checklist when creating or reviewing UI components to ensure WCAG AA compliance.

## Color Contrast

- [ ] All body text (14px+) has ≥4.5:1 contrast ratio against its background
- [ ] All large text (18px+ or 14px+ bold) has ≥3:1 contrast ratio
- [ ] Interactive elements (buttons, links) have sufficient contrast in all states (default, hover, focus, active)
- [ ] Status colors (success, warning, danger, info) are paired with icons or text labels, not color alone
- [ ] Form validation errors are indicated by text/icon, not just red border color

### AI-Life Approved Text/Background Pairings

✅ **Pass WCAG AA:**
- `text-fg-0` (zinc-50) on `bg-bg-0` (zinc-950): **18.5:1** (AAA)
- `text-fg-1` (zinc-300) on `bg-bg-0`: **10.2:1** (AAA)
- `text-fg-2` (zinc-400) on `bg-bg-0`: **7.2:1** (AA large)
- `text-accent` (violet-500) on `bg-bg-0`: **5.8:1** (AA large)
- `text-success` on `bg-bg-0`: **6.1:1** (AA)
- `text-warning` on `bg-bg-0`: **7.4:1** (AA)
- `text-danger` on `bg-bg-0`: **4.8:1** (AA large)

❌ **Do NOT use:**
- `text-fg-3` (zinc-600) on `bg-bg-0`: **2.6:1** (fails AA) — disabled/hint text only
- `text-fg-2` on `bg-bg-2` or lighter: may fail AA for small text
- Any custom colors without checking contrast first

### Contrast Checking Tools
- **Browser DevTools:** Inspect element → Accessibility pane shows contrast ratio
- **Online:** https://webaim.org/resources/contrastchecker/
- **macOS:** Digital Color Meter (built-in) + manual calculation
- **VS Code Extension:** "axe Accessibility Linter" (real-time checks)

## Keyboard Navigation

- [ ] All interactive elements are keyboard accessible (no mouse-only interactions)
- [ ] Tab order is logical and follows visual layout
- [ ] Focus indicator is visible on all interactive elements (2px outline or border change minimum)
- [ ] `Tab` moves forward through interactive elements
- [ ] `Shift+Tab` moves backward
- [ ] `Enter` or `Space` activates buttons and toggles
- [ ] `Escape` closes modals, dialogs, dropdowns
- [ ] Custom components (e.g., tabs, accordions) support arrow key navigation where appropriate

### Focus State Patterns

**Buttons:**
```tsx
className="... focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-bg-0 outline-none"
```

**Inputs:**
```tsx
className="... border border-border-1 focus:border-border-focus outline-none"
```

**Icon buttons:**
```tsx
className="... focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-bg-0 rounded-lg outline-none"
```

**Links:**
```tsx
className="... underline-offset-4 hover:underline focus:underline focus:outline-none"
```

## Semantic HTML

- [ ] Use semantic elements (`<button>`, `<a>`, `<input>`, `<select>`, `<nav>`, `<main>`, `<article>`, `<section>`, `<header>`, `<footer>`)
- [ ] Buttons trigger actions: use `<button>` or `<button type="submit">`
- [ ] Links navigate: use `<a href="...">`, never `<div onclick="...">`
- [ ] Never use `<div>` or `<span>` with `onClick` for interactive elements (fails keyboard nav)
- [ ] Form controls are wrapped in `<form>` where appropriate
- [ ] Heading hierarchy is logical (`<h1>` → `<h2>` → `<h3>`, no skipping levels)

## ARIA Labels & Roles

- [ ] All icon-only buttons have `aria-label` describing their action
- [ ] Form inputs have associated `<label>` elements (via `htmlFor`/`id` pairing) or `aria-label`
- [ ] Loading states use `aria-busy="true"` on the loading container
- [ ] Dynamic content updates use `aria-live="polite"` or `role="status"` for non-critical updates, `aria-live="assertive"` for critical alerts
- [ ] Modals have `role="dialog"`, `aria-modal="true"`, and `aria-labelledby` pointing to the title
- [ ] Tab panels have `role="tabpanel"`, `aria-labelledby` pointing to the tab
- [ ] Custom components have appropriate ARIA roles (`role="button"`, `role="menu"`, etc.) only if not using semantic HTML

### Common ARIA Patterns

**Icon button:**
```tsx
<button aria-label="Refresh transit data">
  <RefreshIcon />
</button>
```

**Loading container:**
```tsx
<div aria-busy="true" role="status" aria-live="polite">
  <Spinner />
  <span className="sr-only">Loading transit data...</span>
</div>
```

**Form input:**
```tsx
<label htmlFor="email">Email</label>
<input
  id="email"
  type="email"
  aria-describedby="email-help"
  aria-invalid={hasError}
/>
<p id="email-help">We'll never share your email.</p>
{hasError && <p id="email-error" role="alert">Please enter a valid email.</p>}
```

**Modal:**
```tsx
<div role="dialog" aria-modal="true" aria-labelledby="modal-title">
  <h2 id="modal-title">Confirm Action</h2>
  {/* ... */}
</div>
```

**Status update (live region):**
```tsx
<div aria-live="polite" aria-atomic="true" className="sr-only">
  {statusMessage}
</div>
```

## Screen Reader Support

- [ ] All content is accessible to screen readers (VoiceOver on macOS: `Cmd+F5`)
- [ ] Decorative images have `alt=""` (empty string)
- [ ] Meaningful images have descriptive `alt` text
- [ ] Icon-only buttons have `aria-label` or visible text (use `.sr-only` for visually hidden text)
- [ ] Form errors are announced (use `role="alert"` or `aria-live="assertive"`)
- [ ] Loading states are announced (use `aria-live="polite"` + `.sr-only` text)
- [ ] Dynamic content changes are announced appropriately

### Screen-Reader-Only Text

Use Tailwind's `sr-only` class for text that should be read by screen readers but not visible:

```tsx
<button>
  <TrashIcon />
  <span className="sr-only">Delete item</span>
</button>
```

**Tailwind `sr-only` definition:**
```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
```

## Forms

- [ ] All form controls have associated labels
- [ ] Required fields are marked with `required` attribute and visual indicator (asterisk, "Required" text)
- [ ] Form validation errors are visible, specific, and announced to screen readers
- [ ] Error messages appear near the invalid field
- [ ] Successful form submission is confirmed (toast, success message, redirect)
- [ ] Forms can be submitted via `Enter` key (use `<form onSubmit={...}>`)
- [ ] Multi-step forms indicate progress (step 1 of 3, progress bar, etc.)

### Form Validation Pattern

```tsx
const [errors, setErrors] = useState<Record<string, string>>({});

<div className="space-y-2">
  <label htmlFor="email" className="block text-sm font-medium text-fg-0">
    Email <span className="text-danger">*</span>
  </label>
  <input
    id="email"
    type="email"
    required
    aria-invalid={!!errors.email}
    aria-describedby={errors.email ? "email-error" : "email-help"}
    className={`w-full px-4 py-3 bg-bg-1 rounded-lg text-fg-0 outline-none transition-colors ${
      errors.email
        ? "border-2 border-danger focus:border-danger"
        : "border border-border-1 focus:border-border-focus"
    }`}
  />
  {errors.email ? (
    <p id="email-error" role="alert" className="text-xs text-danger flex items-center gap-1">
      <AlertIcon className="w-3 h-3" />
      {errors.email}
    </p>
  ) : (
    <p id="email-help" className="text-xs text-fg-2">
      We'll never share your email.
    </p>
  )}
</div>
```

## Responsive Design

- [ ] Layout works on mobile (320px+), tablet (768px+), and desktop (1024px+)
- [ ] Text is readable without horizontal scrolling
- [ ] Interactive elements are at least 44×44px (Apple HIG) or 48×48px (Material Design) on mobile
- [ ] Touch targets don't overlap on mobile
- [ ] Pinch-to-zoom is not disabled (`<meta name="viewport" content="width=device-width, initial-scale=1">`)

### Mobile-First Breakpoints (Tailwind)

```tsx
// Mobile (default): < 768px
<div className="p-4 text-sm">

// Tablet: >= 768px
<div className="p-4 md:p-6 text-sm md:text-base">

// Desktop: >= 1024px
<div className="p-4 md:p-6 lg:p-8 text-sm md:text-base lg:text-lg">
```

## Motion & Animation

- [ ] Animations can be disabled for users who prefer reduced motion (use `prefers-reduced-motion` media query)
- [ ] Animations are subtle and purposeful (150-300ms max)
- [ ] No auto-playing videos or carousels without pause/stop controls
- [ ] No flashing content (seizure risk if flashing >3 times per second)

### Reduced Motion Pattern

```tsx
// In globals.css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

Or conditionally in components:
```tsx
<div className="transition-transform duration-300 motion-reduce:transition-none">
  {/* ... */}
</div>
```

## Testing Checklist

### Automated Testing
- [ ] Run axe DevTools (browser extension) on the page
- [ ] Check Chrome DevTools Lighthouse accessibility score (aim for 90+)
- [ ] Use VS Code "axe Accessibility Linter" extension during development

### Manual Testing
- [ ] Navigate the entire page using only the keyboard (`Tab`, `Shift+Tab`, `Enter`, `Space`, `Escape`)
- [ ] Test with VoiceOver (macOS: `Cmd+F5`) or NVDA (Windows, free)
- [ ] Zoom to 200% and verify layout doesn't break
- [ ] Test on mobile device (real device, not just browser DevTools)
- [ ] Test with slow/no network (loading states, error states)
- [ ] Test in different color modes (though AI-Life is dark-only, verify it doesn't accidentally respect system light mode)

### Screen Reader Testing Workflow (macOS VoiceOver)

1. `Cmd+F5` to enable VoiceOver
2. `VO` = `Ctrl+Option` (VoiceOver modifier keys)
3. `VO+A` to read the entire page
4. `VO+Right Arrow` / `VO+Left Arrow` to navigate element by element
5. `VO+Cmd+H` to jump between headings
6. `VO+Cmd+L` to jump between links
7. `VO+Cmd+J` to jump between form controls
8. `Tab` to move through interactive elements (buttons, links, inputs)
9. `VO+Space` to activate buttons/links
10. `Cmd+F5` to disable VoiceOver

Verify:
- All content is announced in a logical order
- All buttons/links announce their purpose
- All form inputs announce their labels
- All images announce their alt text (or are skipped if decorative)
- Loading/error/success states are announced

## Common Pitfalls

❌ **Don't:**
- Use `<div onClick={...}>` or `<span onClick={...}>` for buttons (not keyboard accessible)
- Set `outline: none` without a replacement focus style
- Use `tabindex` > 0 (disrupts natural tab order)
- Use color alone to convey meaning (e.g., red border for error without text)
- Hide focus indicators (users need to know where they are)
- Use `pointer-events: none` on interactive elements (breaks focus)
- Auto-play videos without controls
- Disable zoom (`maximum-scale=1` in viewport meta tag)

✅ **Do:**
- Use semantic HTML (`<button>`, `<a>`, `<input>`)
- Provide text alternatives for images, icons, and charts
- Ensure 4.5:1 contrast for body text, 3:1 for large text
- Support keyboard navigation for all interactions
- Test with real assistive technology (VoiceOver, NVDA)
- Label form inputs properly
- Announce dynamic content changes
- Respect user preferences (reduced motion, high contrast, zoom)

## Resources

- **WCAG 2.1 Guidelines:** https://www.w3.org/WAI/WCAG21/quickref/
- **WebAIM:** https://webaim.org/ (contrast checker, tutorials, guides)
- **A11y Project Checklist:** https://www.a11yproject.com/checklist/
- **Apple HIG Accessibility:** https://developer.apple.com/design/human-interface-guidelines/accessibility
- **MDN Accessibility:** https://developer.mozilla.org/en-US/docs/Web/Accessibility
- **axe DevTools:** https://www.deque.com/axe/devtools/ (browser extension)
- **VoiceOver User Guide:** https://support.apple.com/guide/voiceover/welcome/mac
