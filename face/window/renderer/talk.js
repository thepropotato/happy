// WHAT WAS SAID, AS IT IS SAID. THE PIECES LAND ONE AT A TIME AND THE LINE THEY
// ARE LANDING IN STAYS OPEN UNTIL THE WHOLE ANSWER IS THERE.

const Talk = (() => {
  let stream = null
  let live = null

  function clock(seconds) {
    if (seconds === null || seconds === undefined) return null
    return seconds < 1 ? `${Math.round(seconds * 1000)}ms` : `${seconds.toFixed(2)}s`
  }

  function pinned() {
    return stream.scrollHeight - stream.scrollTop - stream.clientHeight < 60
  }

  function settle(was) {
    if (was) stream.scrollTop = stream.scrollHeight
  }

  function make(who, text) {
    const line = element('div', `line ${who}`)
    const words = element('div', 'words', text)

    line.append(element('div', 'who', who), words)

    return { line, words }
  }

  function add(who, text) {
    const was = pinned()
    const built = make(who, text)

    stream.append(built.line)
    settle(was)

    return built
  }

  function bare() {
    const empty = stream.querySelector('.empty')
    if (empty) empty.remove()
  }

  return {
    start(node) {
      stream = node
    },

    quiet(words) {
      stream.innerHTML = ''
      live = null

      stream.append(element('div', 'empty', words))
    },

    history(messages) {
      const said = messages.filter((each) => each.who === 'you' || each.who === 'happy')

      if (!said.length) return

      stream.innerHTML = ''
      live = null

      for (const each of said) stream.append(make(each.who, each.text).line)

      stream.scrollTop = stream.scrollHeight
    },

    message(word) {
      bare()

      if (word.who === 'happy' && live) {
        live.words.textContent = word.text
        live = null
        return
      }

      add(word.who, word.text)
    },

    piece(text) {
      bare()

      const was = pinned()

      if (!live) live = add('happy', '')

      live.words.textContent += text
      settle(was)
    },

    // ONE FAINT NUMBER, WHICH BECOMES THE WHOLE ACCOUNT WHEN IT IS POINTED AT.
    // NOBODY OPENS THE PANEL TO READ TIMINGS, AND EVERYBODY WHO OPENS IT SAW THEM.
    spent(word) {
      const parts = []

      if (word.heard != null) parts.push(`heard <b>${clock(word.heard)}</b>`)
      if (word.thought != null) parts.push(`thought <b>${clock(word.thought)}</b>`)
      if (word.first != null) parts.push(`first word <b>${clock(word.first)}</b>`)
      parts.push(`total <b>${clock(word.total)}</b>`)

      const tools = word.tools.map((each) => `${each.name} ${clock(each.seconds)}`).join(' · ')

      const line = element('div', 'spent')

      line.innerHTML =
        `<span class="all">${clock(word.total)}</span>` +
        `<span class="parts">${parts.join(' · ')}${tools ? `<br />${tools}` : ''}</span>`

      const was = pinned()
      stream.append(line)
      settle(was)

      live = null
    },

    aside(text, sort) {
      bare()

      const line = element('div', 'spent', sort === 'trouble' ? `— ${text}` : text)

      const was = pinned()
      stream.append(line)
      settle(was)
    },
  }
})()
