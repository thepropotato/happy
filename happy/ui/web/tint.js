// THE ONE COLOUR HAPPY WEARS, CHOSEN IN THE SETTINGS. EVERYTHING ELSE THAT WAS
// HIS COLOUR IS WORKED OUT FROM IT: THE LIGHTS ON THE PANEL, THE LIPS, THE ROOM.

const Tint = (() => {
  function parts(hex) {
    const value = parseInt(String(hex).replace('#', ''), 16)

    return [(value >> 16) & 255, (value >> 8) & 255, value & 255]
  }

  function blend(a, b, t) {
    return a.map((each, i) => Math.round(each + (b[i] - each) * t))
  }

  function hexed(c) {
    return `#${c.map((each) => each.toString(16).padStart(2, '0')).join('')}`
  }

  const WHITE = [255, 255, 255]
  const BLACK = [0, 0, 0]

  return {
    apply(hex) {
      const base = parts(hex)
      const light = (t) => hexed(blend(base, WHITE, t))
      const dark = (t) => hexed(blend(base, BLACK, t))
      const root = document.documentElement.style
      const glow = blend(base, WHITE, 0.2)

      root.setProperty('--glow', hexed(glow))
      root.setProperty('--glow-soft', `rgba(${glow.join(', ')}, 0.5)`)
      root.setProperty('--state', hexed(base))
      root.setProperty('--state-soft', `rgba(${base.join(', ')}, 0.5)`)
      root.setProperty('--accent', base.join(', '))
      root.setProperty('--asked', light(0.72))

      if (typeof SKIN !== 'undefined') {
        SKIN.lip = [light(0.25), dark(0.2)]
        SKIN.rim = light(0.7)
        SKIN.deep = dark(0.82)
      }

      if (typeof MOODS !== 'undefined') {
        MOODS.loading.colours = [dark(0.3), dark(0.55)]
        MOODS.idle.colours = [light(0.2), dark(0.1)]
        MOODS.idle.room = [hexed(base), dark(0.35)]
        MOODS.listening.colours = [light(0.4), light(0.05)]
        MOODS.hearing.colours = [light(0.3), dark(0.1)]
        MOODS.thinking.colours = [light(0.2), dark(0.2)]
        MOODS.thinking.room = [light(0.15), dark(0.3)]
        MOODS.speaking.colours = [light(0.4), light(0.2)]
      }

      if (typeof Aurora !== 'undefined' && typeof mood !== 'undefined') Aurora.mood(mood)
    },
  }
})()
