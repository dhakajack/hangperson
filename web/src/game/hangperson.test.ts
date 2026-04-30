import { describe, expect, it } from 'vitest'
import {
  HangpersonGame,
  formatLetterForDisplay,
  isLetterForLanguage,
  normalizeGuessForLanguage,
  resolveLanguageChoice,
} from './hangperson'

describe('HangpersonGame', () => {
  it('tracks correct, incorrect, and repeat guesses', () => {
    const game = new HangpersonGame({ word: 'planet', maxErrors: 3 })

    expect(game.guessesRemaining).toBe(3)
    expect(game.guessedDisplay).toBe('(none)')

    expect(game.applyGuess('p')).toBe('correct')
    expect(game.progress).toEqual(['P', '-', '-', '-', '-', '-'])
    expect(game.errors).toBe(0)

    expect(game.applyGuess('x')).toBe('incorrect')
    expect(game.errors).toBe(1)
    expect(game.guessesRemaining).toBe(2)

    expect(game.applyGuess('x')).toBe('repeat')
    expect(game.errors).toBe(1)
  })

  it('reports win and loss states', () => {
    const winGame = new HangpersonGame({ word: 'aba', maxErrors: 3 })
    winGame.applyGuess('a')
    winGame.applyGuess('b')
    expect(winGame.isWon()).toBe(true)
    expect(winGame.isLost()).toBe(false)

    const lossGame = new HangpersonGame({ word: 'planet', maxErrors: 2 })
    lossGame.applyGuess('x')
    lossGame.applyGuess('y')
    expect(lossGame.isLost()).toBe(true)
    expect(lossGame.isWon()).toBe(false)
  })

  it('accepts language aliases including Cyrillic Russian and Greek', () => {
    expect(resolveLanguageChoice('r')).toBe('r')
    expect(resolveLanguageChoice('R')).toBe('r')
    expect(resolveLanguageChoice('р')).toBe('r')
    expect(resolveLanguageChoice('Р')).toBe('r')
    expect(resolveLanguageChoice('p')).toBe('r')
    expect(resolveLanguageChoice('P')).toBe('r')
    expect(resolveLanguageChoice('g')).toBe('el')
    expect(resolveLanguageChoice('el')).toBe('el')
    expect(resolveLanguageChoice('Ελληνικά')).toBe('el')
  })

  it('validates letters against the selected script', () => {
    expect(isLetterForLanguage('e', 'e')).toBe(true)
    expect(isLetterForLanguage('é', 'f')).toBe(true)
    expect(isLetterForLanguage('д', 'r')).toBe(true)
    expect(isLetterForLanguage('α', 'el')).toBe(true)

    expect(isLetterForLanguage('д', 'e')).toBe(false)
    expect(isLetterForLanguage('e', 'r')).toBe(false)
    expect(isLetterForLanguage('e', 'el')).toBe(false)
    expect(isLetterForLanguage('7', 'e')).toBe(false)
  })

  it('treats Greek sigma variants as a single guess', () => {
    const game = new HangpersonGame({ word: 'κόσμος', maxErrors: 5 })

    const guess1 = normalizeGuessForLanguage('ς', 'el')
    expect(guess1).toBe('σ')
    expect(normalizeGuessForLanguage('Σ', 'el')).toBe('σ')
    expect(game.applyGuess(guess1)).toBe('correct')
    expect(game.progress).toEqual(['-', '-', 'Σ', '-', '-', 'Σ'])

    const guess2 = normalizeGuessForLanguage('σ', 'el')
    expect(guess2).toBe('σ')
    expect(game.applyGuess(guess2)).toBe('repeat')
  })

  it('preserves accented Latin display and keeps French accents distinct', () => {
    const game = new HangpersonGame({ word: 'rivière', maxErrors: 5 })

    expect(game.applyGuess('e')).toBe('correct')
    expect(game.progress).toEqual(['-', '-', '-', '-', '-', '-', 'E'])

    expect(game.applyGuess('è')).toBe('correct')
    expect(game.progress).toEqual(['-', '-', '-', '-', 'È', '-', 'E'])

    expect(game.applyGuess('é')).toBe('incorrect')
    expect(game.guessedDisplay).toBe('E, È, É')
  })

  it('formats display letters with visible diacritics', () => {
    expect(formatLetterForDisplay('e')).toBe('E')
    expect(formatLetterForDisplay('é')).toBe('É')
    expect(formatLetterForDisplay('e\u0301')).toBe('É')
    expect(formatLetterForDisplay('ç')).toBe('Ç')
    expect(formatLetterForDisplay('σ')).toBe('Σ')
  })

  it('matches decomposed accented guesses against composed word letters', () => {
    const game = new HangpersonGame({ word: 'caféine', maxErrors: 5 })
    const guess = normalizeGuessForLanguage('e\u0301', 'f')

    expect(guess).toBe('é')
    expect(game.applyGuess(guess)).toBe('correct')
    expect(game.progress).toEqual(['-', '-', '-', 'É', '-', '-', '-'])
  })

  it('uses accented word letters when showing French progress', () => {
    const game = new HangpersonGame({ word: 'espérer', maxErrors: 10 })
    ;['e', 'é', 's', 'p', 'r'].forEach((raw) => {
      game.applyGuess(normalizeGuessForLanguage(raw, 'f'))
    })

    expect(game.progress).toEqual(['E', 'S', 'P', 'É', 'R', 'E', 'R'])
  })

  it('formats incorrect guess slots without counting correct sigma or losing accents', () => {
    const greekGame = new HangpersonGame({ word: 'κόσμος', maxErrors: 5 })
    greekGame.applyGuess('σ')
    expect(greekGame.incorrectGuessSlots()).toEqual(['', '', '', '', ''])

    const frenchGame = new HangpersonGame({ word: 'rivière', maxErrors: 5 })
    frenchGame.applyGuess('e')
    frenchGame.applyGuess('é')
    expect(frenchGame.incorrectGuessSlots()).toEqual(['É', '', '', '', ''])
  })
})
