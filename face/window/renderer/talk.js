// WHAT WAS SAID, AS IT IS SAID, IN THE ORDER IT HAPPENED.
//
// AN EXCHANGE IS THE BLOCK, NOT A LINE: WHAT WAS ASKED, WHAT WAS REACHED FOR,
// AND WHAT CAME BACK, KEPT TOGETHER.

const ONE_LINE = 56

const TICK_MS = 100

// WHICH STATES EARN A LINE AT THE FOOT OF THE EXCHANGE. NOT speaking: THOSE
// WORDS ARE ALREADY ARRIVING.
const BUSY = { hearing: true, thinking: true, listening: true }

const Talk = (() => {
  let stream = null
  let turn = null // THE EXCHANGE EVERYTHING IS LANDING IN.
  let prose = null // THE ANSWER BLOCK STILL BEING FILLED IN.
  let status = null // THE ONE LINE SAYING WHAT IS HAPPENING RIGHT NOW.
  let mood = null // THE LAST THING WE WERE TOLD HE WAS DOING.

  const running = new Map() // id → A CALL THAT HAS STARTED AND NOT FINISHED.
  let ticking = null

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

  function cut(text, most) {
    const said = String(text).replace(/\s+/g, ' ').trim()

    return said.length > most ? `${said.slice(0, most - 1)}…` : said
  }

  // ── THE EXCHANGE ──

  // NOTHING IS BUILT WITH IT: EVERY PART OF A TURN IS OPTIONAL.
  function begun() {
    const box = element('div', 'turn')

    stream.append(box)

    turn = box
    prose = null

    return box
  }

  function within() {
    return turn || begun()
  }

  // EVERYTHING ARRIVES THROUGH HERE, SO THE ORDER ON SCREEN IS WHAT HAPPENED.
  function land(node, keep) {
    const was = pinned()

    within().append(node)

    // ANYTHING THAT IS NOT MORE OF THE ANSWER CLOSES THE ANSWER.
    if (!keep) prose = null

    bump()
    settle(was)

    return node
  }

  // THE LIVE LINE IS A FOOTER, NOT AN EVENT: IT GOES BACK TO THE BOTTOM.
  function bump() {
    if (status && status.parentElement) status.parentElement.append(status)
  }

  // A RUNNING CALL ALREADY HAS ITS OWN PULSING DOT AND CLOCK, SO THE LIVE LINE
  // STANDS DOWN WHILE ONE RUNS AND COMES BACK WHEN THE LAST ONE FINISHES.
  function revise() {
    if (!turn || !mood || !BUSY[mood.state] || running.size) {
      if (status) status.remove()

      status = null

      return
    }

    if (!status) {
      status = element('div', 'doing')
      status.append(element('span', 'beat'), element('span', 'word', ''))
    }

    status.querySelector('.word').textContent = mood.word || mood.state

    const was = pinned()

    turn.append(status)
    settle(was)
  }

  // ── WHAT WAS SAID ──

  function make(who, text) {
    const line = element('div', `line ${who}`)

    line.append(element('div', 'words', text))

    return { line, words: line.firstChild }
  }

  function add(who, text) {
    const built = make(who, text)

    land(built.line, who === 'happy')

    if (who === 'happy') prose = built

    return built
  }

  // ── ONE CALL ──

  // A TOOL NAME ALONE IS "search" FOUR TIMES IN A ROW.
  function gist(args) {
    if (args === undefined || args === null) return ''
    if (typeof args !== 'object') return cut(args, ONE_LINE)

    // ONLY PLAIN VALUES SPEAK FOR THE CALL; A NESTED OBJECT IS NOT A PHRASE.
    const plain = Object.values(args).filter(
      (each) => each !== null && each !== '' && typeof each !== 'object',
    )

    if (plain.length) return cut(plain.join(' · '), ONE_LINE)

    const held = Object.keys(args).length

    return held ? `${held} ${held === 1 ? 'field' : 'fields'}` : ''
  }

  // AN "ASKED {}" TELLS A READER LESS THAN NOTHING, SO IT DOES NOT EARN THE ROOM.
  function worth(args) {
    if (args === undefined || args === null) return false
    if (typeof args === 'object') return Object.keys(args).length > 0

    return String(args).trim() !== ''
  }

  function body(value) {
    if (typeof value === 'string') return value

    const whole = JSON.stringify(value, null, 2) || String(value)

    return whole.length <= ONE_LINE ? JSON.stringify(value) : whole
  }

  // A TOOL THAT RETURNED NOTHING, OR NOTHING BUT WHITESPACE, HAS NO OUTPUT TO OPEN.
  function returned(each) {
    if (each.result === undefined || each.result === null) return null

    const said = typeof each.result === 'string' ? each.result : body(each.result)

    return String(said).trim() ? String(said) : null
  }

  // WHAT IS UNDER THE FOLD. null MEANS THE ROW HAS NOTHING TO OPEN.
  function detail(each) {
    const pairs = []
    const said = returned(each)

    if (worth(each.args)) pairs.push(['Arguments', body(each.args)])
    if (said) pairs.push([each.failed ? 'Error' : 'Result', said])

    if (!pairs.length) return null

    const box = element('div', 'inside')

    for (const [label, text] of pairs) {
      const pair = element('div', 'pair')

      pair.append(element('div', 'label', label), element('pre', 'said', text))
      box.append(pair)
    }

    return box
  }

  // ONE CALL AS ONE LINE, THE SAME LINE LIVE OR READ BACK NEXT WEEK. WHY COMES
  // BEFORE THE ARGUMENTS: IT IS THE SAME THING IN A SENTENCE A PERSON READS.
  function call(each, live) {
    const row = element('div', live ? 'call running' : 'call')
    const face = element('button', 'face')

    if (each.id) row.dataset.id = each.id
    if (each.failed) row.classList.add('failed')

    face.append(element('span', 'dot'), element('span', 'what', each.name || 'a tool'))

    // THE REASON ONLY ARRIVES WITH THE FINISHED CALL. UNTIL THEN THE ARGUMENTS
    // ARE THE ONLY THING THAT SAYS WHICH CALL THIS IS.
    const summary = each.why || gist(each.args)

    if (summary) face.append(element('span', 'why', summary))

    face.append(element('span', 'took', live ? '' : clock(each.seconds) || ''))

    const inside = detail(each)

    if (!inside) {
      face.classList.add('shut')
      row.append(face)

      return row
    }

    face.append(element('span', 'go', '›'))

    face.onclick = () => row.classList.toggle('open')
    row.append(face, inside)

    return row
  }

  // ── CALLS THAT ARE STILL GOING ──

  function tick() {
    for (const [, held] of running) {
      const took = held.row.querySelector('.took')

      if (took) took.textContent = clock((performance.now() - held.started) / 1000)
    }
  }

  function watching() {
    if (ticking === null) ticking = setInterval(tick, TICK_MS)
  }

  function idle() {
    if (running.size || ticking === null) return

    clearInterval(ticking)
    ticking = null
  }

  // A CLOCK TICKING ON A ROW NO LONGER ON SCREEN IS A TIMER THAT NEVER STOPS.
  function forget() {
    running.clear()
    idle()
  }

  // ── READING A TURN BACK ──

  // THE CALLS CARRY HOW MUCH OF THE ANSWER HAD BEEN SAID WHEN EACH WAS REACHED
  // FOR, SO THE ANSWER IS CUT AT THOSE POINTS AND THE CALLS GO IN THE GAPS.
  function replay(each) {
    const box = begun()

    if (each.message) box.append(make('you', each.message).line)

    const reply = each.reply || ''
    let at = 0

    for (const one of each.tools || []) {
      const upto = Number.isFinite(one.after) ? Math.min(Math.max(one.after, at), reply.length) : at

      if (upto > at) box.append(make('happy', reply.slice(at, upto)).line)

      at = upto
      box.append(call(one))
    }

    if (at < reply.length) box.append(make('happy', reply.slice(at)).line)
  }

  function bare() {
    const empty = stream.querySelector('.empty')

    if (empty) empty.remove()
  }

  function wipe() {
    stream.innerHTML = ''

    turn = null
    prose = null
    status = null

    forget()
  }

  return {
    start(node) {
      stream = node
    },

    quiet(words) {
      wipe()
      stream.append(element('div', 'empty', words))
    },

    // ANY PART CAN BE MISSING: A CUT OFF TURN HAS NO ANSWER.
    history(rows) {
      const blocks = (rows || []).filter(
        (each) => each.message || each.reply || (each.tools || []).length,
      )

      if (!blocks.length) return

      wipe()

      for (const each of blocks) replay(each)

      turn = null // NOTHING FURTHER BELONGS TO AN EXCHANGE THAT IS ALREADY OVER.
      stream.scrollTop = stream.scrollHeight
    },

    message(word) {
      bare()

      if (word.who === 'you' || word.unprompted) begun()

      add(word.who, word.text)
    },

    piece(text) {
      bare()

      if (!prose) {
        // THE PIECE AFTER A TOOL CALL LEADS WITH THE SPACE THAT CLOSED THE LAST.
        const opening = text.replace(/^\s+/, '')

        if (opening) add('happy', opening)

        return
      }

      const was = pinned()

      prose.words.textContent += text
      settle(was)
    },

    began(word) {
      bare()

      const row = call(word, true)

      land(row)

      if (!word.id) return

      running.set(word.id, { row, started: performance.now() })
      watching()
      revise()
    },

    step(word) {
      bare()

      const held = word.id ? running.get(word.id) : null

      if (!held) {
        land(call(word))

        return
      }

      running.delete(word.id)
      idle()

      // REBUILT RATHER THAN PATCHED: FINISHING BRINGS THE REASON, THE OUTPUT AND
      // THE FOLD ITSELF. IT TAKES THE OLD ROW'S PLACE, AND ITS OPEN STATE WITH IT.
      const was = pinned()
      const fresh = call(word)

      if (held.row.classList.contains('open')) fresh.classList.add('open')

      held.row.replaceWith(fresh)

      settle(was)
      revise()
    },

    doing(state, word) {
      mood = { state, word }
      revise()
    },

    // THE PIECES ALREADY CARRIED EVERY WORD; ONLY THE LIVE LINE COMES DOWN.
    done() {
      mood = null

      revise()

      prose = null

      for (const [, held] of running) held.row.classList.remove('running')

      forget()
    },

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

      land(line)
    },

    aside(text, sort) {
      bare()
      land(element('div', sort === 'trouble' ? 'aside trouble' : 'aside', text))
    },
  }
})()
