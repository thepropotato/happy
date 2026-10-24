// IT HEARS THE SAME LINES THE PANEL DOES, AND KEEPS ONLY WHAT MOVES THE MOUTH.
const WORKING = { hearing: true, thinking: true, speaking: true }
let mood = 'loading'
let troubled = false

Smile.start(document.getElementById('face'))

window.happy.hears((word) => {
  if (word.is === 'state') {
    if (word.state === 'idle' && WORKING[mood]) {
      Smile.react(troubled ? 'sorry' : 'pleased')
      troubled = false
    }
    mood = word.state
    Smile.mood(word.state)
  }
  if (word.is === 'tint') Tint.apply(word.colour)
  if (word.is === 'hover') document.body.classList.toggle('hover', word.on)
  if (word.is === 'level') Smile.level(word.level)
  if (word.is === 'hush') Smile.hush()
  if (word.is === 'step' && word.failed) troubled = true
  if (word.is === 'trouble') troubled = true
})
    
