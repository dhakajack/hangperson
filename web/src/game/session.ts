import {
  type DifficultyKey,
  type GuessOutcome,
  type LanguageKey,
  HangpersonGame,
  chooseWord,
  difficultySettings,
  formatLetterForDisplay,
  isAlphabeticWord,
  isLetterForLanguage,
  normalizeGuessForLanguage,
} from './hangperson'

export type UiMode = 'setup' | 'active_round' | 'round_complete'
export type MessageKind = 'info' | 'success' | 'error'
export type RoundResult = 'won' | 'lost'

export type UiLocale = {
  difficulty_names: Record<DifficultyKey, string>
  guessed_none: string
  [key: string]: string | Record<string, string>
}

export type SessionMessage = {
  kind: MessageKind
  text: string
}

export type SessionState = {
  uiMode: UiMode
  pendingLanguageKey: LanguageKey
  pendingDifficultyKey: DifficultyKey
  languageKey: LanguageKey | null
  difficultyKey: DifficultyKey | null
  locale: UiLocale
  words: string[]
  game: HangpersonGame | null
  maxErrors: number
  sessionRoundsPlayed: number
  sessionRoundsWon: number
  message: SessionMessage | null
  loading: boolean
  error: string | null
  scriptWarningShown: boolean
  settingsLockHintShown: boolean
  resetConfirmOpen: boolean
  roundResult: RoundResult | null
  roundSummary: string
  lastGuessOutcome: GuessOutcome | null
}

export type SessionAction =
  | { type: 'cycle_language'; locale: UiLocale }
  | { type: 'cycle_difficulty' }
  | { type: 'start_session'; locale: UiLocale; words: string[] }
  | { type: 'start_next_round' }
  | { type: 'submit_guess'; guess: string }
  | { type: 'request_reset' }
  | { type: 'confirm_reset' }
  | { type: 'cancel_reset' }
  | { type: 'end_session' }

const languageCycle: LanguageKey[] = ['e', 'f', 'r', 'el']
const difficultyCycle: DifficultyKey[] = ['1', '2', '3']

export const defaultLocale: UiLocale = {
  guessed_none: '(none)',
  difficulty_names: {
    '1': 'Easy',
    '2': 'Medium',
    '3': 'Hard',
  },
  letter_invalid: 'Please enter letters only.',
  letter_wrong_script: 'Please use letters from the selected language alphabet.',
  repeat_guess: "You already guessed '{letter}'. Try a new letter.",
  correct: 'Correct!',
  incorrect: 'Incorrect.',
  win_short: 'You win!',
  loss_summary: 'Game over. You used {max_errors} incorrect guesses.',
  loss_word: 'The word was {word}.',
  no_words_error: 'Could not start game: no words match your selected language and difficulty.',
  start_error: 'Could not start game: {error}',
  setup_hint: 'Click language and difficulty badges, then press Start.',
  settings_locked_hint: 'To change language or difficulty, start a new game.',
  session_kept_current: 'Kept current session (new game setup was cancelled).',
  session_stats_format: 'Won {won}/{played} rounds ({pct}%).',
  start_button: 'Start',
  new_game_button: 'New Game',
  replay_prompt_label: 'Replay?',
  play_again_yes_button: 'Yes',
  play_again_no_button: 'No',
  restart_confirm_title: 'Reset Game?',
  restart_confirm_body:
    'Current round and session score will be reset. Press Cancel to keep playing, or OK to return to setup.',
  restart_confirm_ok_button: 'OK',
  restart_confirm_cancel_button: 'Cancel',
  language_click_hint: 'Click to change language.',
  difficulty_click_hint: 'Click to change difficulty.',
  guess_prompt_label: 'Your Guess',
  keyboard_input_hint: 'Type a letter, then press Enter.',
  score_tooltip: 'Score: won / rounds played',
  incorrect_guesses_tooltip: 'Incorrect letters',
  target_word_tooltip: 'Guess this word',
}

function cycleChoice<T>(options: readonly T[], current: T): T {
  const index = options.indexOf(current)
  if (index < 0) {
    return options[0]
  }
  return options[(index + 1) % options.length]
}

function copyGame(game: HangpersonGame): HangpersonGame {
  const copy = new HangpersonGame({
    word: game.word,
    maxErrors: game.maxErrors,
    guessedNone: game.guessedNone,
  })
  copy.progress = [...game.progress]
  copy.guessedLetters = new Set(game.guessedLetters)
  copy.errors = game.errors
  return copy
}

function wordForDisplay(word: string): string {
  return [...word].map(formatLetterForDisplay).join('')
}

export function t(locale: UiLocale, key: string, fallback = ''): string {
  const value = locale[key]
  return typeof value === 'string' ? value : fallback
}

export function formatTemplate(template: string, values: Record<string, string | number>): string {
  return template.replaceAll(/\{([^}]+)\}/g, (_, key: string) => String(values[key] ?? `{${key}}`))
}

export function nextLanguageKey(current: LanguageKey): LanguageKey {
  return cycleChoice(languageCycle, current)
}

export function nextDifficultyKey(current: DifficultyKey): DifficultyKey {
  return cycleChoice(difficultyCycle, current)
}

export function createInitialSessionState(locale: UiLocale = defaultLocale): SessionState {
  return {
    uiMode: 'setup',
    pendingLanguageKey: 'e',
    pendingDifficultyKey: '2',
    languageKey: null,
    difficultyKey: null,
    locale,
    words: [],
    game: null,
    maxErrors: difficultySettings['2'].maxErrors,
    sessionRoundsPlayed: 0,
    sessionRoundsWon: 0,
    message: {
      kind: 'info',
      text: t(locale, 'setup_hint', ''),
    },
    loading: false,
    error: null,
    scriptWarningShown: false,
    settingsLockHintShown: false,
    resetConfirmOpen: false,
    roundResult: null,
    roundSummary: '',
    lastGuessOutcome: null,
  }
}

export function setSessionLoading(state: SessionState, loading: boolean): SessionState {
  return { ...state, loading, error: null }
}

export function setSessionError(state: SessionState, error: string): SessionState {
  return {
    ...state,
    loading: false,
    error,
    message: { kind: 'error', text: error },
  }
}

export function setPendingLanguage(
  state: SessionState,
  languageKey: LanguageKey,
  locale: UiLocale,
): SessionState {
  if (state.uiMode !== 'setup') {
    return showLockedSettingsHint(state)
  }
  return {
    ...state,
    pendingLanguageKey: languageKey,
    locale,
    message: {
      kind: 'info',
      text: t(locale, 'setup_hint', ''),
    },
    loading: false,
    error: null,
  }
}

export function cyclePendingLanguage(state: SessionState, locale: UiLocale): SessionState {
  return setPendingLanguage(state, nextLanguageKey(state.pendingLanguageKey), locale)
}

export function cyclePendingDifficulty(state: SessionState): SessionState {
  if (state.uiMode !== 'setup') {
    return showLockedSettingsHint(state)
  }

  const pendingDifficultyKey = nextDifficultyKey(state.pendingDifficultyKey)
  return {
    ...state,
    pendingDifficultyKey,
    maxErrors: difficultySettings[pendingDifficultyKey].maxErrors,
    error: null,
  }
}

export function showLockedSettingsHint(state: SessionState): SessionState {
  if (state.settingsLockHintShown) {
    return state
  }
  return {
    ...state,
    settingsLockHintShown: true,
    message: {
      kind: 'info',
      text: t(state.locale, 'settings_locked_hint', 'To change language or difficulty, start a new game.'),
    },
  }
}

export function startSession(
  state: SessionState,
  {
    locale,
    words,
    languageKey = state.pendingLanguageKey,
    difficultyKey = state.pendingDifficultyKey,
    random = Math.random,
  }: {
    locale: UiLocale
    words: string[]
    languageKey?: LanguageKey
    difficultyKey?: DifficultyKey
    random?: () => number
  },
): SessionState {
  if (words.length === 0) {
    return setSessionError(
      { ...state, locale },
      t(locale, 'no_words_error', 'Could not start game: no words match your selected language and difficulty.'),
    )
  }

  const maxErrors = difficultySettings[difficultyKey].maxErrors
  const game = new HangpersonGame({
    word: chooseWord(words, random),
    maxErrors,
    guessedNone: t(locale, 'guessed_none', '(none)'),
  })

  return {
    ...state,
    uiMode: 'active_round',
    pendingLanguageKey: languageKey,
    pendingDifficultyKey: difficultyKey,
    languageKey,
    difficultyKey,
    locale,
    words,
    game,
    maxErrors,
    sessionRoundsPlayed: 0,
    sessionRoundsWon: 0,
    message: null,
    loading: false,
    error: null,
    scriptWarningShown: false,
    settingsLockHintShown: false,
    resetConfirmOpen: false,
    roundResult: null,
    roundSummary: '',
    lastGuessOutcome: null,
  }
}

export function startNextRound(
  state: SessionState,
  random: () => number = Math.random,
): SessionState {
  if (!state.languageKey || !state.difficultyKey || state.words.length === 0) {
    return state
  }

  const game = new HangpersonGame({
    word: chooseWord(state.words, random),
    maxErrors: state.maxErrors,
    guessedNone: t(state.locale, 'guessed_none', '(none)'),
  })

  return {
    ...state,
    uiMode: 'active_round',
    game,
    message: null,
    loading: false,
    error: null,
    scriptWarningShown: false,
    settingsLockHintShown: false,
    resetConfirmOpen: false,
    roundResult: null,
    roundSummary: '',
    lastGuessOutcome: null,
  }
}

export function submitGuess(state: SessionState, rawGuess: string): SessionState {
  if (state.uiMode !== 'active_round' || !state.game || !state.languageKey) {
    return state
  }

  const guess = normalizeGuessForLanguage(rawGuess.trim(), state.languageKey)
  if ([...guess].length !== 1 || !isAlphabeticWord(guess)) {
    return {
      ...state,
      message: {
        kind: 'error',
        text: t(state.locale, 'letter_invalid', 'Please enter letters only.'),
      },
      lastGuessOutcome: null,
    }
  }

  const wrongScript = !isLetterForLanguage(guess, state.languageKey)
  const shouldShowScriptWarning = wrongScript && !state.scriptWarningShown
  const game = copyGame(state.game)
  const outcome = game.applyGuess(guess)

  let nextState: SessionState = {
    ...state,
    game,
    scriptWarningShown: state.scriptWarningShown || wrongScript,
    message: null,
    lastGuessOutcome: outcome,
  }

  if (outcome === 'repeat') {
    return {
      ...nextState,
      message: {
        kind: 'info',
        text: formatTemplate(t(state.locale, 'repeat_guess', "You already guessed '{letter}'."), {
          letter: formatLetterForDisplay(guess),
        }),
      },
    }
  }

  if (game.isWon()) {
    nextState = {
      ...nextState,
      uiMode: 'round_complete',
      sessionRoundsPlayed: state.sessionRoundsPlayed + 1,
      sessionRoundsWon: state.sessionRoundsWon + 1,
      roundResult: 'won',
      roundSummary: t(state.locale, 'win_short', 'You win!'),
    }
    return nextState
  }

  if (game.isLost()) {
    const summary = [
      formatTemplate(t(state.locale, 'loss_summary', 'Game over. You used {max_errors} incorrect guesses.'), {
        max_errors: state.maxErrors,
      }),
      formatTemplate(t(state.locale, 'loss_word', 'The word was {word}.'), {
        word: wordForDisplay(game.word),
      }),
    ].join('\n')

    nextState = {
      ...nextState,
      uiMode: 'round_complete',
      sessionRoundsPlayed: state.sessionRoundsPlayed + 1,
      roundResult: 'lost',
      roundSummary: summary,
    }
    return nextState
  }

  if (shouldShowScriptWarning) {
    return {
      ...nextState,
      message: {
        kind: 'info',
        text: t(state.locale, 'letter_wrong_script', 'Please use letters from the selected language alphabet.'),
      },
    }
  }

  return {
    ...nextState,
    message: {
      kind: outcome === 'correct' ? 'success' : 'info',
      text:
        outcome === 'correct'
          ? t(state.locale, 'correct', 'Correct!')
          : t(state.locale, 'incorrect', 'Incorrect.'),
    },
  }
}

export function requestReset(state: SessionState): SessionState {
  if (state.uiMode === 'setup') {
    return state
  }
  return { ...state, resetConfirmOpen: true }
}

export function cancelReset(state: SessionState): SessionState {
  return {
    ...state,
    resetConfirmOpen: false,
    message: {
      kind: 'info',
      text: t(state.locale, 'session_kept_current', 'Kept current session.'),
    },
  }
}

export function endSession(state: SessionState): SessionState {
  return {
    ...createInitialSessionState(state.locale),
    pendingLanguageKey: state.languageKey ?? state.pendingLanguageKey,
    pendingDifficultyKey: state.difficultyKey ?? state.pendingDifficultyKey,
    maxErrors: difficultySettings[state.difficultyKey ?? state.pendingDifficultyKey].maxErrors,
  }
}

export function confirmReset(state: SessionState): SessionState {
  return endSession(state)
}

export function formatSessionStats(state: SessionState): string {
  const pct =
    state.sessionRoundsPlayed > 0
      ? Math.round((state.sessionRoundsWon * 100) / state.sessionRoundsPlayed)
      : 0
  return formatTemplate(t(state.locale, 'session_stats_format', 'Won {won}/{played} rounds ({pct}%).'), {
    won: state.sessionRoundsWon,
    played: state.sessionRoundsPlayed,
    pct,
  })
}
