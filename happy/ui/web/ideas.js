// A FEW THINGS TO ASK, FOR SOMEBODY WHO HAS JUST MET HIM. EACH ONE WORKS WITH NOTHING CONNECTED.

const IDEAS = [
  {
    words: 'Play some lo-fi on YouTube',
    icon: '<path d="M8 5.5v13l10.5-6.5z" />',
  },
  {
    words: "What's the weather tomorrow?",
    icon: '<path d="M7 18a4.5 4.5 0 1 1 .9-8.9A6 6 0 0 1 19 11a3.5 3.5 0 0 1-.5 7z" />',
  },
  {
    words: 'Remind me in 10 minutes to stretch',
    icon: '<circle cx="12" cy="13" r="7" /><path d="M12 9.5V13l2.5 1.5M5 4 3 6M19 4l2 2" />',
  },
  {
    words: "What's on my screen?",
    icon: '<rect x="3" y="4.5" width="18" height="12" rx="2" /><path d="M8.5 20h7M12 16.5V20" />',
  },
]

const Ideas = (() => {
  function chip(idea, asking) {
    const button = element('button', 'idea')

    button.type = 'button'
    button.innerHTML =
      `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" ` +
      `stroke-linecap="round" stroke-linejoin="round">${idea.icon}</svg>`
    button.append(element('span', '', idea.words))
    button.onclick = () => asking(idea.words)

    return button
  }

  return {
    start(holder, asking) {
      for (const idea of IDEAS) holder.append(chip(idea, asking))
    },
  }
})()
