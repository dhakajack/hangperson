import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  characterLayerPath,
  currentCharacterLayerKeys,
  difficultyIconPath,
  languageBadgePath,
  restartButtonPath,
  startButtonPath,
  trophyPath,
} from './game/assets'
import { languageSettings } from './game/hangperson'
import { loadLocale, loadWordsForRound } from './game/runtime'
import {
  cancelReset,
  confirmReset,
  createInitialSessionState,
  cyclePendingDifficulty,
  endSession,
  formatSessionStats,
  formatTemplate,
  nextLanguageKey,
  requestReset,
  setPendingLanguage,
  setSessionError,
  setSessionLoading,
  showLockedSettingsHint,
  startNextRound,
  startSession,
  submitGuess,
  t,
} from './game/session'
import type { DifficultyKey, LanguageKey } from './game/hangperson'
import './App.css'

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function App() {
  const [state, setState] = useState(() => createInitialSessionState())
  const [guess, setGuess] = useState('')

  const displayLanguageKey = state.uiMode === 'setup' ? state.pendingLanguageKey : state.languageKey
  const displayDifficultyKey = state.uiMode === 'setup' ? state.pendingDifficultyKey : state.difficultyKey
  const languageKey: LanguageKey = displayLanguageKey ?? state.pendingLanguageKey
  const difficultyKey: DifficultyKey = displayDifficultyKey ?? state.pendingDifficultyKey
  const difficultyName = state.locale.difficulty_names[difficultyKey]
  const characterLayers = currentCharacterLayerKeys(state)
  const badGuessSlots =
    state.game?.incorrectGuessSlots('') ?? Array.from({ length: state.maxErrors }, () => '')
  const wordSlots = state.game?.progress ?? []
  const inputDisabled = state.uiMode !== 'active_round' || state.loading || state.resetConfirmOpen

  useEffect(() => {
    let canceled = false
    loadLocale('e')
      .then((locale) => {
        if (!canceled) {
          setState((current) =>
            current.uiMode === 'setup' && current.pendingLanguageKey === 'e'
              ? setPendingLanguage(current, 'e', locale)
              : current,
          )
        }
      })
      .catch((error: unknown) => {
        if (!canceled) {
          setState((current) => setSessionError(current, errorMessage(error)))
        }
      })
    return () => {
      canceled = true
    }
  }, [])

  async function handleCycleLanguage() {
    if (state.uiMode !== 'setup') {
      setState(showLockedSettingsHint)
      return
    }

    const nextLanguage = nextLanguageKey(state.pendingLanguageKey)
    setState((current) => setSessionLoading(current, true))
    try {
      const locale = await loadLocale(nextLanguage)
      setState((current) => setPendingLanguage(current, nextLanguage, locale))
    } catch (error: unknown) {
      setState((current) =>
        setSessionError(
          current,
          formatTemplate(t(current.locale, 'start_error', 'Could not start game: {error}'), {
            error: errorMessage(error),
          }),
        ),
      )
    }
  }

  function handleCycleDifficulty() {
    setState(cyclePendingDifficulty)
  }

  async function handleStartSession() {
    const language = state.pendingLanguageKey
    const difficulty = state.pendingDifficultyKey

    setState((current) => setSessionLoading(current, true))
    try {
      const [locale, words] = await Promise.all([
        loadLocale(language),
        loadWordsForRound(language, difficulty),
      ])
      setState((current) =>
        startSession(current, {
          locale,
          words,
          languageKey: language,
          difficultyKey: difficulty,
        }),
      )
      setGuess('')
    } catch (error: unknown) {
      setState((current) =>
        setSessionError(
          current,
          formatTemplate(t(current.locale, 'start_error', 'Could not start game: {error}'), {
            error: errorMessage(error),
          }),
        ),
      )
    }
  }

  function handleGuessSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setState((current) => submitGuess(current, guess))
    setGuess('')
  }

  function handleActionButton() {
    if (state.uiMode === 'setup') {
      void handleStartSession()
      return
    }
    setState(requestReset)
  }

  return (
    <main className="game-app">
      <section className="game-frame" aria-label="Hangperson">
        <aside className="status-panel">
          <div className="score-block" title={t(state.locale, 'score_tooltip', 'Score')}>
            <img src={trophyPath} alt="" className="score-trophy" />
            <div className="score-fraction" aria-label={formatSessionStats(state)}>
              <span>{state.sessionRoundsWon}</span>
              <span className="score-rule"></span>
              <span>{state.sessionRoundsPlayed}</span>
            </div>
          </div>

          <button
            type="button"
            className="badge-button"
            onClick={() => void handleCycleLanguage()}
            disabled={state.loading}
            aria-label={languageSettings[languageKey].name}
            title={t(state.locale, 'language_click_hint', 'Click to change language.')}
          >
            <img
              src={languageBadgePath(languageKey)}
              alt=""
              className="language-badge"
            />
          </button>

          <button
            type="button"
            className="badge-button difficulty-button"
            onClick={handleCycleDifficulty}
            disabled={state.loading}
            aria-label={difficultyName}
            title={t(state.locale, 'difficulty_click_hint', 'Click to change difficulty.')}
          >
            <img src={difficultyIconPath(difficultyKey)} alt="" className="difficulty-badge" />
          </button>

          <button
            type="button"
            className="action-button"
            onClick={handleActionButton}
            disabled={state.loading}
            aria-label={
              state.uiMode === 'setup'
                ? t(state.locale, 'start_button', 'Start')
                : t(state.locale, 'new_game_button', 'New Game')
            }
            title={
              state.uiMode === 'setup'
                ? t(state.locale, 'start_button', 'Start')
                : t(state.locale, 'new_game_button', 'New Game')
            }
          >
            <img
              src={state.uiMode === 'setup' ? startButtonPath : restartButtonPath}
              alt=""
              className="action-icon"
            />
          </button>
        </aside>

        <section className="play-panel">
          <div className="drawing-surface" aria-label={t(state.locale, 'drawing_area_title', 'Drawing')}>
            <div className="character-stack" aria-hidden="true">
              {characterLayers.map((layer) => (
                <img
                  key={layer}
                  src={characterLayerPath(languageKey, layer)}
                  alt=""
                  className="character-layer"
                  draggable="false"
                />
              ))}
            </div>
          </div>

          <div className="message-row" aria-live="polite">
            {state.loading && <span className="message info">Loading…</span>}
            {!state.loading && state.message && (
              <span className={`message ${state.message.kind}`}>{state.message.text}</span>
            )}
            {!state.loading && !state.message && <span className="message-placeholder"></span>}
          </div>

          <div className="word-area" title={t(state.locale, 'target_word_tooltip', 'Guess this word')}>
            {wordSlots.length > 0 ? (
              wordSlots.map((letter, index) => (
                <span className="word-slot" key={`${index}-${letter}`}>
                  {letter === '-' ? '' : letter}
                </span>
              ))
            ) : (
              <span className="setup-title">Hangperson</span>
            )}
          </div>

          <form className="guess-form" onSubmit={handleGuessSubmit}>
            <label htmlFor="guess-input">{t(state.locale, 'guess_prompt_label', 'Your Guess')}</label>
            <input
              id="guess-input"
              value={guess}
              onChange={(event) => setGuess(event.target.value)}
              disabled={inputDisabled}
              maxLength={8}
              autoComplete="off"
              inputMode="text"
              aria-label={t(state.locale, 'keyboard_input_hint', 'Type a letter, then press Enter.')}
            />
            <button type="submit" disabled={inputDisabled}>
              {t(state.locale, 'submit_button', 'Submit')}
            </button>
          </form>
        </section>

        <aside
          className="bad-guess-rail"
          title={t(state.locale, 'incorrect_guesses_tooltip', 'Incorrect letters')}
          aria-label={t(state.locale, 'incorrect_guesses_tooltip', 'Incorrect letters')}
        >
          {badGuessSlots.map((letter, index) => (
            <span className="bad-guess-slot" key={`${index}-${letter}`}>
              {letter}
            </span>
          ))}
        </aside>
      </section>

      {state.uiMode === 'round_complete' && (
        <div className="dialog-backdrop">
          <section className="dialog" role="dialog" aria-modal="true">
            {state.roundSummary && (
              <p className="dialog-summary">
                {state.roundSummary.split('\n').map((line) => (
                  <span key={line}>{line}</span>
                ))}
              </p>
            )}
            <p className="dialog-prompt">{t(state.locale, 'replay_prompt_label', 'Replay?')}</p>
            <div className="dialog-actions">
              <button type="button" onClick={() => setState(endSession)}>
                × {t(state.locale, 'play_again_no_button', 'No')}
              </button>
              <button type="button" className="primary" onClick={() => setState((current) => startNextRound(current))}>
                ✓ {t(state.locale, 'play_again_yes_button', 'Yes')}
              </button>
            </div>
          </section>
        </div>
      )}

      {state.resetConfirmOpen && (
        <div className="dialog-backdrop">
          <section className="dialog" role="dialog" aria-modal="true">
            <h2>{t(state.locale, 'restart_confirm_title', 'Reset Game?')}</h2>
            <p>{t(state.locale, 'restart_confirm_body', '')}</p>
            <div className="dialog-actions">
              <button type="button" onClick={() => setState(cancelReset)}>
                {t(state.locale, 'restart_confirm_cancel_button', 'Cancel')}
              </button>
              <button type="button" className="primary" onClick={() => setState(confirmReset)}>
                {t(state.locale, 'restart_confirm_ok_button', 'OK')}
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  )
}

export default App
