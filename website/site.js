// The page's one Happy: the app's own mouth and light, walked through everyday requests.
(() => {
  // A LINK HERE SHOWS THE "SUPPORT THE DEVELOPER" LINE IN THE FOOTER; EMPTY HIDES IT.
  const SUPPORT = ''

  const JOBS = [
    { label: 'Brightness', ask: 'set the brightness to 40.', steps: [['set_brightness', 'screen to 40%']], reply: 'Brightness set to 40%.',
      old: ['Open Settings', 'Go to Display', 'Find brightness', 'Grab the slider', 'Drag it to 40%', 'Close Settings'] },
    { label: 'Message', ask: 'tell Mom I’ll be late.', steps: [['whatsapp_send', 'to Mom on WhatsApp']], reply: 'Your message to Mom has been sent.',
      old: ['Find your phone', 'Unlock it', 'Open WhatsApp', 'Find Mom', 'Type the message', 'Send it'] },
    { label: 'PDF summary', ask: 'summarise the PDF in Chrome.', steps: [['read_tab', 'the PDF open in Chrome'], ['write_file', 'summary.txt on the Desktop']], reply: 'Saved the summary to your Desktop and opened it.',
      old: ['Read the whole PDF', 'Pick out what matters', 'Open a text editor', 'Write the summary', 'Save the file', 'Give it a name'] },
    { label: 'Price check', ask: 'find me the cheapest PS5.', steps: [['web_search', 'PS5 price on Amazon'], ['read_result', 'the Amazon listing'], ['web_search', 'PS5 price on Flipkart'], ['read_result', 'the Flipkart listing']], reply: 'Flipkart has it for ₹44,990, about ₹20,000 less than Amazon.',
      old: ['Open Amazon', 'Search for a PS5', 'Note the price', 'Open Flipkart', 'Search again', 'Compare the two'] },
    { label: 'Privacy', ask: 'open my privacy settings.', steps: [['open_app', 'Settings'], ['use_app', 'type privacy into Search']], reply: 'Privacy settings are open.',
      old: ['Open Settings', 'Scroll the sidebar', 'Look for Privacy', 'Open Privacy & Security', 'Find the setting', 'Change it'] },
  ]
  // MILLISECONDS PER CHARACTER: THE REQUEST AS IF SAID, THE REPLY A LITTLE QUICKER.
  const TYPE = 42
  const REPLY = 24
  const WORDS = { idle: 'Ready when you are', listening: 'Listening', hearing: 'Got it', thinking: 'On it', speaking: 'Here you go', pleased: 'Done' }

  const still = matchMedia('(prefers-reduced-motion: reduce)').matches
  const $ = (pick) => document.querySelector(pick)
  const $$ = (pick) => [...document.querySelectorAll(pick)]

  const typed = $('[data-typed]')
  const bubble = $('[data-said-bubble]')
  const clicks = $('[data-clicks]')
  const steps = $('[data-steps]')
  const reply = $('[data-reply]')
  const spoken = $('[data-reply-spoken]')
  const count = $('[data-count]')
  const spared = $('[data-spared]')
  const tabs = $('[data-tabs]')
  const pause = $('[data-pause]')
  const dot = $('[data-dot]')
  const stageStep = $('[data-stage-step]')

  const room = $('[data-room]')
  JOBS.forEach((job) => room.prepend(Object.assign(document.createElement('span'), { className: 'ask-room', textContent: job.ask })))

  if (SUPPORT) {
    $('[data-support-link]').href = SUPPORT
    $('[data-support]').hidden = false
  }

  // A WINDOWS VISITOR SEES THE WINDOWS DOWNLOAD FIRST, IN THE MAIN STYLE.
  const windows = /win/i.test(navigator.userAgentData?.platform || navigator.platform || navigator.userAgent)
  if (windows) {
    $$('[data-downloads]').forEach((group) => {
      const mac = group.querySelector('[data-os="mac"]')
      const win = group.querySelector('[data-os="windows"]')
      const [first, second] = [mac.className, win.className]
      mac.className = second
      win.className = first
      group.prepend(win)
    })
  }

  Aurora.start($('.aurora'))
  Smile.start(...$$('canvas.face'))

  let timers = []
  let auto = !still
  let current = 0

  function later(ms, fn) {
    timers.push(setTimeout(fn, ms))
  }

  function feel(mood) {
    Smile.mood(mood === 'pleased' ? 'idle' : mood)
    if (mood === 'pleased') Smile.react('pleased')
    Aurora.mood(mood === 'pleased' ? 'idle' : mood)
    $$('[data-word]').forEach((each) => { each.textContent = WORDS[mood] || '' })
    dot.style.background = (MOODS[mood] || MOODS.idle).room[0]
  }

  // A LOUDNESS CURVE FOR THE REPLY, SO THE MOUTH MOVES THE WAY IT DOES ON A REAL VOICE.
  function voice(seconds) {
    const values = []
    for (let i = 0; i < seconds * 25; i++) values.push(0.03 + 0.1 * Math.abs(Math.sin(i * 0.9) * Math.sin(i * 0.37 + 1)) + 0.02 * Math.random())
    Smile.envelope(values, seconds)
  }

  function row(step, busy) {
    const item = document.createElement('li')
    if (busy) item.className = 'busy'
    item.innerHTML = '<span class="mark"></span><span class="tool"></span><span class="why"></span>'
    item.querySelector('.mark').textContent = busy ? '…' : '✓'
    item.querySelector('.tool').textContent = step[0]
    item.querySelector('.why').textContent = step[1]
    return item
  }

  function say(job, upTo) {
    const words = job.ask.slice(0, upTo)
    bubble.textContent = upTo ? `“Hey Happy, ${words}${upTo >= job.ask.length ? '”' : ''}` : ''
  }

  function show(index) {
    const job = JOBS[index]
    current = index
    $$('[data-tabs] button').forEach((button, at) => button.setAttribute('aria-pressed', String(at === index)))
    clicks.className = 'clicks'
    clicks.replaceChildren(...job.old.map((text) => Object.assign(document.createElement('li'), { textContent: text })))
    steps.replaceChildren()
    reply.textContent = ''
    spoken.textContent = ''
    say(job, 0)
    spared.classList.remove('shown')
    count.textContent = `0 of ${job.old.length} done`
  }

  function finished(index) {
    const job = JOBS[index]
    show(index)
    clicks.querySelectorAll('li').forEach((item) => item.classList.add('done'))
    clicks.classList.add('folded')
    spared.classList.add('shown')
    count.textContent = 'none needed'
    spared.textContent = 'Six steps you get to skip.'
    say(job, job.ask.length)
    steps.replaceChildren(...job.steps.map((step) => row(step, false)))
    reply.textContent = spoken.textContent = job.reply
    feel('pleased')
  }

  // hero: WHETHER THE HEADLINE AND THE FACE'S STEP CHIP FOLLOW ALONG, WHICH THEY DO ONLY ON THE TOUR.
  function run(index, hero) {
    timers.forEach(clearTimeout)
    timers = []
    if (still) return finished(index)

    const job = JOBS[index]
    show(index)
    if (hero) {
      typed.textContent = ''
      stageStep.textContent = ''
    }
    feel('idle')

    // HAPPY STARTS AT ONCE; THE OLD WAY TICKS ALONG BESIDE HIM AND IS STILL MID-WAY WHEN HE FINISHES.
    let at = 200
    const done = 200 + 150 + job.ask.length * TYPE + 150 + 250 + 120 + job.steps.length * 380 + Math.max(job.reply.length * REPLY, (job.reply.length * 0.03 + 0.4) * 1000) + 150
    const reached = 3 + (index % 2)
    const tick = (done - 200) / reached
    job.old.slice(0, reached).forEach((_, k) => later(at + (k + 1) * tick - 60, () => {
      clicks.children[k].classList.add('done')
      count.textContent = `${k + 1} of ${job.old.length} done`
    }))
    later(at, () => feel('listening'))
    later(done, () => {
      clicks.classList.add('folded')
      spared.textContent = `Happy's done. You're on step ${reached + 1}.`
      spared.classList.add('shown')
      count.textContent = `${reached} of ${job.old.length} done`
    })
    at += 150
    for (let n = 1; n <= job.ask.length; n++) {
      later(at + n * TYPE, () => {
        say(job, n)
        if (hero) typed.textContent = job.ask.slice(0, n)
      })
    }
    at += job.ask.length * TYPE + 150
    later(at, () => feel('hearing'))
    at += 250
    later(at, () => feel('thinking'))
    job.steps.forEach((step, k) => later(at + 120 + k * 380, () => {
      steps.replaceChildren(...job.steps.slice(0, k + 1).map((each, j) => row(each, j === k)))
      if (hero) stageStep.textContent = `${step[0]}  …`
    }))
    at += 120 + job.steps.length * 380
    const talk = job.reply.length * 0.03 + 0.4
    later(at, () => {
      steps.replaceChildren(...job.steps.map((each) => row(each, false)))
      if (hero) stageStep.textContent = `${job.steps[job.steps.length - 1][0]}  ✓`
      spoken.textContent = job.reply
      feel('speaking')
      voice(talk)
    })
    for (let n = 1; n <= job.reply.length; n++) later(at + n * REPLY, () => { reply.textContent = job.reply.slice(0, n) })
    at += Math.max(job.reply.length * REPLY, talk * 1000) + 150
    later(at, () => feel('pleased'))
    at += 700
    later(at, () => {
      if (hero) stageStep.textContent = ''
      Smile.mood('idle')
      Aurora.mood('idle')
    })
    later(at + 700, () => { if (auto) next() })
  }

  // THE TOUR WAITS WHILE NOBODY CAN SEE IT: THE TAB IS HIDDEN, OR BOTH THE HERO AND THE DEMO ARE SCROLLED AWAY.
  const seen = new Set()
  let waiting = false
  function watching() {
    return !document.hidden && seen.size > 0
  }
  function next() {
    if (!auto) return
    if (watching()) return run((current + 1) % JOBS.length, true)
    waiting = true
  }
  function resume() {
    if (waiting && auto && watching()) {
      waiting = false
      run((current + 1) % JOBS.length, true)
    }
  }
  document.addEventListener('visibilitychange', resume)
  new IntersectionObserver((entries) => {
    entries.forEach((entry) => (entry.isIntersecting ? seen.add(entry.target) : seen.delete(entry.target)))
    resume()
  }).observe($('.hero'))
  ;[$('.demo')].forEach((each) => new IntersectionObserver((entries) => {
    entries.forEach((entry) => (entry.isIntersecting ? seen.add(entry.target) : seen.delete(entry.target)))
    resume()
  }).observe(each))

  function setAuto(on) {
    auto = on
    pause.textContent = on ? 'Pause' : 'Play'
    pause.setAttribute('aria-pressed', String(!on))
    pause.setAttribute('aria-label', on ? 'Pause the tour' : 'Play the tour')
  }

  JOBS.forEach((job, index) => {
    const button = document.createElement('button')
    button.type = 'button'
    button.textContent = job.label
    button.addEventListener('click', () => {
      setAuto(false)
      run(index, false)
    })
    tabs.append(button)
  })

  pause.addEventListener('click', () => {
    if (auto) return setAuto(false)
    setAuto(true)
    run((current + 1) % JOBS.length, true)
  })
  if (still) pause.hidden = true

  // HE LOOKS TOWARD THE POINTER, A LITTLE.
  const stage = $('[data-stage]')
  const face = $('.face-hero')
  const hero = $('.hero')
  if (!still) {
    hero.addEventListener('pointermove', (event) => {
      const box = stage.getBoundingClientRect()
      const x = Math.max(-1, Math.min(1, (event.clientX - (box.left + box.width / 2)) / (box.width * 0.9)))
      const y = Math.max(-1, Math.min(1, (event.clientY - (box.top + box.height / 2)) / (box.height * 0.9)))
      face.style.transform = `translate(${x * 14}px, ${y * 8}px) rotate(${x * 2.5}deg)`
    })
    hero.addEventListener('pointerleave', () => { face.style.transform = '' })
  }

  // THE MODELS: WHAT EACH ONE NEEDS, COSTS, AND WHERE YOUR WORDS GO.
  const BRAINS = [
    { need: 'Claude Code, signed in with a Pro or Max plan.', cost: 'Nothing extra. It uses the plan you already have.',
      where: 'To Anthropic, through your own Claude Code.', note: 'Your claude.ai connectors, like Gmail and Drive, come along.' },
    { need: 'A key from OpenAI, OpenRouter, Groq, Gemini, or any service that speaks the OpenAI format.', cost: 'Whatever that provider charges for what you use.',
      where: 'To the provider you chose, and nowhere else.', note: 'Paste the URL and key the provider documents. Happy trims the rest.' },
    { need: 'Ollama or LM Studio, running a model that can call tools.', cost: 'Nothing.',
      where: 'Nowhere. Your requests stay on your computer.', note: 'Happy picks the biggest local model that fits, and gives it small tools that do the heavy lifting in code.' },
  ]
  const brainButtons = $$('[data-brain]')
  const brainPanel = $('[data-brain-panel]')
  function brain(index) {
    const pick = BRAINS[index]
    brainButtons.forEach((button, at) => {
      button.setAttribute('aria-selected', String(at === index))
      button.tabIndex = at === index ? 0 : -1
    })
    brainPanel.setAttribute('aria-labelledby', brainButtons[index].id)
    $('[data-brain-need]').textContent = pick.need
    $('[data-brain-cost]').textContent = pick.cost
    $('[data-brain-where]').textContent = pick.where
    $('[data-brain-note]').textContent = pick.note
  }
  brainButtons.forEach((button, index) => {
    button.addEventListener('click', () => brain(index))
    button.addEventListener('keydown', (event) => {
      const step = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[event.key]
      if (!step) return
      event.preventDefault()
      const to = (index + step + BRAINS.length) % BRAINS.length
      brain(to)
      brainButtons[to].focus()
    })
  })
  brain(0)

  // A NAME TRIED HERE SHOWS UP WHEREVER THE PAGE SAYS "HAPPY" TO HIM, THE HEADLINE INCLUDED.
  const nameInput = $('[data-name-input]')
  nameInput.addEventListener('input', () => {
    const name = nameInput.value.trim().replace(/\s+/g, ' ') || 'Happy'
    $$('[data-name]').forEach((each) => { each.textContent = name })
  })

  const copy = $('[data-copy]')
  copy.addEventListener('click', async () => {
    const code = $('[data-code]')
    try {
      await navigator.clipboard.writeText(code.textContent)
      copy.textContent = 'Copied'
    } catch {
      getSelection().selectAllChildren(code)
      copy.textContent = 'Select and copy'
    }
    setTimeout(() => { copy.textContent = 'Copy' }, 1800)
  })

  // AN ANSWER GROWS OPEN AND SHRINKS SHUT, AND THE PLUS TURNS THE MOMENT IT IS CLICKED.
  $$('.faq-list details').forEach((item) => {
    const answer = item.querySelector('.answer')
    item.querySelector('summary').addEventListener('click', (event) => {
      event.preventDefault()
      if (item.dataset.moving) return
      const opening = !item.open
      item.classList.toggle('showing', opening)
      if (still) {
        item.open = opening
        return
      }
      item.dataset.moving = '1'
      if (opening) item.open = true
      const full = answer.scrollHeight
      const motion = answer.animate(
        { height: opening ? ['0px', `${full}px`] : [`${full}px`, '0px'], opacity: opening ? [0, 1] : [1, 0] },
        { duration: 340, easing: 'cubic-bezier(0.2, 0.7, 0.2, 1)' },
      )
      motion.onfinish = () => {
        if (!opening) item.open = false
        delete item.dataset.moving
      }
    })
  })

  run(0, true)
})()

