const MARKS = {
  brain:
    '<rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6"/>' +
    '<path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
  ears: '<rect x="9" y="2" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0"/><path d="M12 18v4"/>',
  voice: '<path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/>',
  eyes: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
  mcps: '<path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 0 1 0 10h-2"/><path d="M8 12h8"/>',
  memory: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  allowing:
    '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>' +
    '<path d="M12 15v2"/>',
  // ONE WAVE, NOT THREE: THE OTHER TWO ARE A SMUDGE AT THE SIZE THIS IS DRAWN AT.
  hear: '<path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/>',
}

// BUILT AS TEXT BECAUSE AN SVG PATH IS NOT WORTH TWELVE createElementNS CALLS.
function glyph(key) {
  return (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"' +
    ` stroke-linecap="round" stroke-linejoin="round">${MARKS[key]}</svg>`
  )
}

function marking(key, label) {
  const held = element('div', 'mark')

  if (!MARKS[key]) {
    held.textContent = (label || key || '?').slice(0, 1).toUpperCase()
    return held
  }

  held.innerHTML = glyph(key)

  return held
}
