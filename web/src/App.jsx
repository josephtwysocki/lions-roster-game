import { useEffect, useRef, useState } from "react";
import Papa from "papaparse";
import { createGame } from "./game";

const QUESTION_COUNT = 10;
const NEXT_QUESTION_DELAY = 1000;

function App() {
  const [screen, setScreen] = useState("start");
  const [roster, setRoster] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const advanceTimer = useRef(null);

  useEffect(() => {
    Papa.parse("/data/active_roster.csv", {
      download: true,
      header: true,
      skipEmptyLines: true,
      complete: ({ data, errors }) => {
        if (errors.length > 0 && data.length === 0) {
          setError("The roster could not be loaded. Please try again later.");
          setIsLoading(false);
          return;
        }

        const validPlayers = data
          .map((row) => ({
            ...row,
            player: row.player?.trim(),
            headshot_file: row.headshot_file?.trim(),
          }))
          .filter((row) => row.player && row.headshot_file);

        const uniquePlayers = Array.from(
          new Map(validPlayers.map((player) => [player.player, player])).values(),
        );

        if (uniquePlayers.length < QUESTION_COUNT) {
          setError("There are not enough valid players to start a game.");
        } else {
          setRoster(uniquePlayers);
        }

        setIsLoading(false);
      },
      error: () => {
        setError("The roster could not be loaded. Please try again later.");
        setIsLoading(false);
      },
    });

    return () => window.clearTimeout(advanceTimer.current);
  }, []);

  function startGame() {
    setQuestions(createGame(roster));
    setQuestionIndex(0);
    setScore(0);
    setSelectedAnswer(null);
    setError("");
    setScreen("quiz");
  }

  function answerQuestion(playerName) {
    if (selectedAnswer !== null) return;

    const isCorrect = playerName === questions[questionIndex].player.player;
    setSelectedAnswer(playerName);

    if (isCorrect) setScore((currentScore) => currentScore + 1);

    advanceTimer.current = window.setTimeout(() => {
      if (questionIndex === QUESTION_COUNT - 1) {
        setScreen("results");
      } else {
        setQuestionIndex((currentIndex) => currentIndex + 1);
        setSelectedAnswer(null);
      }
    }, NEXT_QUESTION_DELAY);
  }

  function handleImageError() {
    window.clearTimeout(advanceTimer.current);
    setError("This player’s headshot could not be loaded. Please start a new game.");
  }

  if (isLoading) {
    return <main className="app-shell status-screen">Loading roster…</main>;
  }

  if (screen === "start") {
    return (
      <main className="app-shell start-screen">
        <section className="card start-card">
          <p className="eyebrow">Detroit football</p>
          <h1>Lions Roster Game</h1>
          <p className="intro">How well do you know the Lions roster?</p>
          {error && <p className="error-message" role="alert">{error}</p>}
          <button className="primary-button" onClick={startGame} disabled={Boolean(error)}>
            Start Game
          </button>
          <p className="game-note">10 players · 4 choices · 1 final score</p>
        </section>
      </main>
    );
  }

  if (screen === "results") {
    const percentage = Math.round((score / QUESTION_COUNT) * 100);

    return (
      <main className="app-shell results-screen">
        <section className="card results-card">
          <p className="eyebrow">Game over</p>
          <h1>Your Score</h1>
          <p className="final-score">
            <strong>{score}</strong>
            <span>/ {QUESTION_COUNT}</span>
          </p>
          <p className="percentage">{percentage}%</p>
          <button className="primary-button" onClick={startGame}>Play Again</button>
        </section>
      </main>
    );
  }

  const question = questions[questionIndex];
  const correctName = question.player.player;

  return (
    <main className="app-shell quiz-screen">
      <section className="quiz-card">
        <header className="quiz-header">
          <p>Question {questionIndex + 1} of {QUESTION_COUNT}</p>
          <p>Score: {score}</p>
        </header>
        <div className="progress-track" aria-hidden="true">
          <div
            className="progress-fill"
            style={{ width: `${((questionIndex + 1) / QUESTION_COUNT) * 100}%` }}
          />
        </div>

        {error ? (
          <div className="image-error" role="alert">
            <p>{error}</p>
            <button className="primary-button" onClick={startGame}>Start New Game</button>
          </div>
        ) : (
          <>
            <div className="headshot-frame">
              <img
                key={question.player.headshot_file}
                src={`/headshots/${question.player.headshot_file}`}
                alt="Detroit Lions player to identify"
                onError={handleImageError}
              />
            </div>
            <h1 className="question-prompt">Who is this player?</h1>
            <div className="answers">
              {question.answers.map((answer) => {
                const wasSelected = selectedAnswer === answer.player;
                const isCorrect = answer.player === correctName;
                let stateClass = "";

                if (selectedAnswer !== null && isCorrect) stateClass = " correct";
                if (selectedAnswer !== null && wasSelected && !isCorrect) stateClass = " incorrect";

                return (
                  <button
                    className={`answer-button${stateClass}`}
                    disabled={selectedAnswer !== null}
                    key={answer.player}
                    onClick={() => answerQuestion(answer.player)}
                  >
                    <span>{answer.player}</span>
                    {selectedAnswer !== null && isCorrect && <span aria-hidden="true">✓</span>}
                    {selectedAnswer !== null && wasSelected && !isCorrect && <span aria-hidden="true">×</span>}
                  </button>
                );
              })}
            </div>
          </>
        )}
      </section>
    </main>
  );
}

export default App;
