// AN ANSWER ARRIVES AS MARKDOWN, SO **THIS** IS BOLD RATHER THAN FOUR STARS READ
// OFF THE SCREEN. THE RAW TEXT IS KEPT ON THE NODE AND THE WHOLE BLOCK IS DRAWN
// AGAIN FROM IT, BECAUSE A HALF WRITTEN FENCE ONLY CLOSES ONCE THE REST LANDS.

const Prose = (() => {
  // WHAT AN ANSWER IS ALLOWED TO BE. NOTHING HERE FETCHES, RUNS OR TAKES A TYPED
  // CHARACTER, SO A MODEL THAT WRITES A TAG CANNOT REACH PAST ITS OWN BUBBLE.
  const CLEAN = {
    ALLOWED_TAGS: [
      'p', 'br', 'hr', 'strong', 'em', 'del', 'code', 'pre', 'blockquote',
      'ul', 'ol', 'li', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'table', 'thead', 'tbody', 'tr', 'th', 'td', 'img',
    ],
    ALLOWED_ATTR: ['href', 'title', 'alt', 'src', 'start'],
    ALLOWED_URI_REGEXP: /^(https?|mailto):/i,
  }

  let ready = false

  function set() {
    if (ready) return

    // A SINGLE NEWLINE IS A NEW LINE: THIS IS A CHAT, NOT A TYPESET DOCUMENT.
    marked.setOptions({ gfm: true, breaks: true })

    ready = true
  }

  // MARKDOWN IS A BLOCK LANGUAGE, SO A LEADING INDENT THE STREAM HAPPENED TO CARRY
  // WOULD TURN AN ORDINARY SENTENCE INTO A CODE BLOCK.
  function level(text) {
    return String(text || '').replace(/^[ \t]+(?=\S)/gm, (run) => (run.length >= 4 ? '' : run))
  }

  function drawn(text) {
    set()

    return DOMPurify.sanitize(marked.parse(level(text)), CLEAN)
  }

  return {
    // MARKDOWN OFF WHERE IT IS NOT WANTED: WHAT A PERSON SAID IS WHAT THEY SAID.
    plain(node, text) {
      node.textContent = text
      node.raw = text
    },

    write(node, text) {
      node.raw = text
      node.innerHTML = drawn(text)
    },

    grow(node, more) {
      this.write(node, (node.raw || '') + more)
    },

    // A GUARD TOOK THAT ROUND BACK AFTER IT WAS DRAWN, SO ITS WORDS COME OFF AGAIN.
    shrink(node, many) {
      const had = node.raw || ''

      this.write(node, many < had.length ? had.slice(0, -many) : '')
    },

    // AN ADDRESS BELONGS IN THEIR BROWSER. FOLLOWED IN HERE IT WOULD REPLACE THE
    // PANEL WITH A WEB PAGE AND THERE IS NO WAY BACK FROM THAT.
    away(root) {
      root.addEventListener('click', (event) => {
        const link = event.target.closest('a[href]')

        if (!link) return

        event.preventDefault()
        window.happy.open(link.href)
      })
    },
  }
})()
