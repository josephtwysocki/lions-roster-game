import assert from "node:assert/strict";
import test from "node:test";
import { createGame, shuffle } from "../src/game.js";

const roster = Array.from({ length: 20 }, (_, index) => ({
  player: `Player ${index + 1}`,
  headshot_file: `player_${index + 1}.jpg`,
}));

test("shuffle does not mutate its input", () => {
  const names = roster.map((player) => player.player);
  shuffle(roster);
  assert.deepEqual(roster.map((player) => player.player), names);
});

test("a game has 10 unique questions with four valid unique answers", () => {
  for (let run = 0; run < 100; run += 1) {
    const game = createGame(roster);
    assert.equal(game.length, 10);
    assert.equal(new Set(game.map(({ player }) => player.player)).size, 10);

    for (const question of game) {
      const answerNames = question.answers.map((answer) => answer.player);
      assert.equal(answerNames.length, 4);
      assert.equal(new Set(answerNames).size, 4);
      assert.equal(
        answerNames.filter((name) => name === question.player.player).length,
        1,
      );
    }
  }
});
