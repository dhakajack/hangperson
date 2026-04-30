import { describe, expect, it } from 'vitest'
import { currentCharacterLayerKeys } from './assets'
import {
  cancelReset,
  confirmReset,
  createInitialSessionState,
  cyclePendingDifficulty,
  cyclePendingLanguage,
  defaultLocale,
  requestReset,
  startNextRound,
  startSession,
  submitGuess,
} from './session'

const testLocale = defaultLocale

function activeState(word = 'planet') {
  return startSession(createInitialSessionState(testLocale), {
    locale: testLocale,
    words: [word],
    random: () => 0,
  })
}

describe('session state', () => {
  it('creates setup defaults and cycles pending settings', () => {
    let state = createInitialSessionState(testLocale)

    expect(state.uiMode).toBe('setup')
    expect(state.pendingLanguageKey).toBe('e')
    expect(state.pendingDifficultyKey).toBe('2')
    expect(state.maxErrors).toBe(8)

    state = cyclePendingLanguage(state, testLocale)
    expect(state.pendingLanguageKey).toBe('f')

    state = cyclePendingDifficulty(state)
    expect(state.pendingDifficultyKey).toBe('3')
    expect(state.maxErrors).toBe(6)
  })

  it('starts an active session with loaded words and difficulty settings', () => {
    const state = startSession(createInitialSessionState(testLocale), {
      locale: testLocale,
      words: ['planet', 'forest'],
      random: () => 0.9,
    })

    expect(state.uiMode).toBe('active_round')
    expect(state.words).toEqual(['planet', 'forest'])
    expect(state.game?.word).toBe('forest')
    expect(state.maxErrors).toBe(8)
    expect(state.sessionRoundsPlayed).toBe(0)
  })

  it('updates progress, bad guesses, messages, and score through a win', () => {
    let state = activeState('aba')

    state = submitGuess(state, 'a')
    expect(state.game?.progress).toEqual(['A', '-', 'A'])
    expect(state.message?.text).toBe('Correct!')

    state = submitGuess(state, 'x')
    expect(state.game?.errors).toBe(1)
    expect(state.game?.incorrectGuessSlots()[0]).toBe('X')
    expect(state.message?.text).toBe('Incorrect.')

    state = submitGuess(state, 'b')
    expect(state.uiMode).toBe('round_complete')
    expect(state.roundResult).toBe('won')
    expect(state.sessionRoundsPlayed).toBe(1)
    expect(state.sessionRoundsWon).toBe(1)
  })

  it('does not increment errors for repeat guesses', () => {
    let state = activeState()

    state = submitGuess(state, 'x')
    state = submitGuess(state, 'x')

    expect(state.game?.errors).toBe(1)
    expect(state.lastGuessOutcome).toBe('repeat')
    expect(state.message?.text).toBe("You already guessed 'X'. Try a new letter.")
  })

  it('warns once for wrong-script guesses while still processing them', () => {
    let state = activeState()

    state = submitGuess(state, 'д')
    expect(state.game?.errors).toBe(1)
    expect(state.scriptWarningShown).toBe(true)
    expect(state.message?.text).toBe('Please use letters from the selected language alphabet.')

    state = submitGuess(state, 'ж')
    expect(state.game?.errors).toBe(2)
    expect(state.message?.text).toBe('Incorrect.')
  })

  it('starts replay rounds without resetting score', () => {
    let state = startSession(createInitialSessionState(testLocale), {
      locale: testLocale,
      words: ['aba', 'planet'],
      random: () => 0,
    })
    state = submitGuess(state, 'a')
    state = submitGuess(state, 'b')

    const replay = startNextRound(state, () => 0.9)

    expect(replay.uiMode).toBe('active_round')
    expect(replay.game?.word).toBe('planet')
    expect(replay.sessionRoundsPlayed).toBe(1)
    expect(replay.sessionRoundsWon).toBe(1)
  })

  it('cancels or confirms reset from active play', () => {
    let state = activeState()

    state = requestReset(state)
    expect(state.resetConfirmOpen).toBe(true)

    state = cancelReset(state)
    expect(state.resetConfirmOpen).toBe(false)
    expect(state.uiMode).toBe('active_round')

    state = requestReset(state)
    state = confirmReset(state)
    expect(state.uiMode).toBe('setup')
    expect(state.game).toBeNull()
    expect(state.sessionRoundsPlayed).toBe(0)
  })

  it('matches wx character reveal groups by difficulty', () => {
    const easy = startSession(createInitialSessionState(testLocale), {
      locale: testLocale,
      words: ['planet'],
      difficultyKey: '1',
      random: () => 0,
    })
    easy.game!.errors = 2
    expect(currentCharacterLayerKeys(easy)).toEqual(['silhouette', 'head', 'left_eye'])

    const medium = startSession(createInitialSessionState(testLocale), {
      locale: testLocale,
      words: ['planet'],
      difficultyKey: '2',
      random: () => 0,
    })
    medium.game!.errors = 3
    expect(currentCharacterLayerKeys(medium)).toEqual([
      'silhouette',
      'head',
      'left_eye',
      'right_eye',
      'nose',
      'mouth',
    ])

    const hard = startSession(createInitialSessionState(testLocale), {
      locale: testLocale,
      words: ['planet'],
      difficultyKey: '3',
      random: () => 0,
    })
    hard.game!.errors = 5
    expect(currentCharacterLayerKeys(hard)).toEqual([
      'silhouette',
      'head',
      'left_eye',
      'right_eye',
      'nose',
      'mouth',
      'shirt',
      'left_arm',
      'right_arm',
    ])
  })
})
