export type LanguageKey = 'e' | 'f' | 'r' | 'el'
export type DifficultyKey = '1' | '2' | '3'
export type GuessOutcome = 'repeat' | 'correct' | 'incorrect'

export type DifficultySettings = {
  minLength: number
  maxLength: number | null
  maxErrors: number
  band: 'easy' | 'medium' | 'hard'
}

export const languageSettings: Record<LanguageKey, { name: string; assetCode: string }> = {
  e: { name: 'English', assetCode: 'en' },
  f: { name: 'Français', assetCode: 'fr' },
  r: { name: 'Русский', assetCode: 'ru' },
  el: { name: 'Ελληνικά', assetCode: 'el' },
}

export const languageAliases: Record<string, LanguageKey> = {
  e: 'e',
  english: 'e',
  en: 'e',
  f: 'f',
  fr: 'f',
  francais: 'f',
  français: 'f',
  french: 'f',
  r: 'r',
  р: 'r',
  p: 'r',
  ru: 'r',
  russian: 'r',
  русский: 'r',
  g: 'el',
  el: 'el',
  greek: 'el',
  ελληνικα: 'el',
  ελληνικά: 'el',
}

export const difficultySettings: Record<DifficultyKey, DifficultySettings> = {
  '1': { minLength: 6, maxLength: 7, maxErrors: 10, band: 'easy' },
  '2': { minLength: 8, maxLength: 9, maxErrors: 8, band: 'medium' },
  '3': { minLength: 10, maxLength: null, maxErrors: 6, band: 'hard' },
}

export const difficultyAliases: Record<string, DifficultyKey> = {
  '1': '1',
  easy: '1',
  e: '1',
  '2': '2',
  medium: '2',
  m: '2',
  '3': '3',
  hard: '3',
  h: '3',
}

const latinLetterPattern = /^\p{Script=Latin}$/u
const cyrillicLetterPattern = /^\p{Script=Cyrillic}$/u
const greekLetterPattern = /^\p{Script=Greek}$/u
const alphabeticWordPattern = /^\p{L}+$/u

export function normalizeCasefold(value: string): string {
  return value.normalize('NFC').toLocaleLowerCase().replaceAll('ς', 'σ').normalize('NFC')
}

export function normalizeGuessForLanguage(guess: string, languageKey: LanguageKey): string {
  void languageKey
  return normalizeCasefold(guess)
}

export function formatLetterForDisplay(letter: string): string {
  return letter.normalize('NFC').toLocaleUpperCase().normalize('NFC')
}

export function isAlphabeticWord(value: string): boolean {
  return alphabeticWordPattern.test(value)
}

export function isLetterForLanguage(letter: string, languageKey: LanguageKey): boolean {
  if ([...letter].length !== 1 || !isAlphabeticWord(letter)) {
    return false
  }

  if (languageKey === 'e' || languageKey === 'f') {
    return latinLetterPattern.test(letter)
  }
  if (languageKey === 'r') {
    return cyrillicLetterPattern.test(letter)
  }
  return greekLetterPattern.test(letter)
}

export function isWordForLanguage(word: string, languageKey: LanguageKey): boolean {
  return [...word].every((letter) => isLetterForLanguage(letter, languageKey))
}

export function resolveLanguageChoice(choice: string): LanguageKey | undefined {
  return languageAliases[normalizeCasefold(choice.trim())]
}

export function resolveDifficultyChoice(choice: string): DifficultyKey | undefined {
  return difficultyAliases[normalizeCasefold(choice.trim())]
}

export function chooseWord(words: readonly string[], random = Math.random): string {
  if (words.length === 0) {
    throw new Error('No valid words were found. Add lowercase words of length >= 6.')
  }
  return words[Math.floor(random() * words.length)]
}

export function formatProgress(progress: readonly string[]): string {
  return progress.join(' ')
}

export class HangpersonGame {
  readonly word: string
  readonly maxErrors: number
  readonly guessedNone: string
  progress: string[]
  guessedLetters: Set<string>
  errors: number

  constructor({
    word,
    maxErrors,
    guessedNone = '(none)',
  }: {
    word: string
    maxErrors: number
    guessedNone?: string
  }) {
    this.word = word
    this.maxErrors = maxErrors
    this.guessedNone = guessedNone
    this.progress = [...word].map(() => '-')
    this.guessedLetters = new Set()
    this.errors = 0
  }

  get guessesRemaining(): number {
    return this.maxErrors - this.errors
  }

  get guessedDisplay(): string {
    const guessed = [...this.guessedLetters].map(formatLetterForDisplay).sort().join(', ')
    return guessed || this.guessedNone
  }

  wordContainsGuess(guess: string): boolean {
    const canonicalGuess = normalizeCasefold(guess)
    return [...this.word].some((letter) => normalizeCasefold(letter) === canonicalGuess)
  }

  applyGuess(guess: string): GuessOutcome {
    const canonicalGuess = normalizeCasefold(guess)
    if (this.guessedLetters.has(canonicalGuess)) {
      return 'repeat'
    }

    this.guessedLetters.add(canonicalGuess)

    if (this.wordContainsGuess(canonicalGuess)) {
      [...this.word].forEach((letter, index) => {
        if (normalizeCasefold(letter) === canonicalGuess) {
          this.progress[index] = formatLetterForDisplay(letter)
        }
      })
      return 'correct'
    }

    this.errors += 1
    return 'incorrect'
  }

  isWon(): boolean {
    return !this.progress.includes('-')
  }

  isLost(): boolean {
    return this.errors >= this.maxErrors
  }

  incorrectGuessSlots(emptyLabel = ''): string[] {
    const incorrectLetters = [...this.guessedLetters]
      .filter((letter) => !this.wordContainsGuess(letter))
      .map(formatLetterForDisplay)
      .sort()
    const remainingSlots = Math.max(this.maxErrors - incorrectLetters.length, 0)
    return [...incorrectLetters, ...Array.from({ length: remainingSlots }, () => emptyLabel)]
  }
}
