// MAKING ONE ELEMENT, WHICH IS MOST OF WHAT DRAWING ANYTHING HERE AMOUNTS TO.

function element(kind, className, text) {
  const made = document.createElement(kind)

  if (className) made.className = className
  if (text !== undefined) made.textContent = text

  return made
}
