export function shuffle(items) {
  const shuffled = [...items];

  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [shuffled[index], shuffled[randomIndex]] = [
      shuffled[randomIndex],
      shuffled[index],
    ];
  }

  return shuffled;
}

export function createGame(roster, questionCount = 10, answerCount = 4) {
  return shuffle(roster)
    .slice(0, questionCount)
    .map((player) => {
      const distractors = shuffle(
        roster.filter((candidate) => candidate.player !== player.player),
      ).slice(0, answerCount - 1);

      return {
        player,
        answers: shuffle([player, ...distractors]),
      };
    });
}
