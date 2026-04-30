import {
  type DifficultyKey,
  type LanguageKey,
  difficultySettings,
  isAlphabeticWord,
  isWordForLanguage,
  normalizeCasefold,
} from './hangperson'
import { publicPath } from './publicPath'

export class ScoreWordSourceError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ScoreWordSourceError'
  }
}

export const difficultyTsvPaths: Record<LanguageKey, string> = {
  e: publicPath('data/difficulty/en_difficulty.tsv'),
  f: publicPath('data/difficulty/fr_difficulty.tsv'),
  r: publicPath('data/difficulty/ru_difficulty.tsv'),
  el: publicPath('data/difficulty/el_difficulty.tsv'),
}

const validBands = new Set(['easy', 'medium', 'hard'])

type TsvRow = Record<string, string>

function parseTsv(text: string): { fieldNames: string[]; rows: TsvRow[] } {
  const lines = text.split(/\r?\n/).filter((line) => line.length > 0)
  if (lines.length === 0) {
    throw new ScoreWordSourceError('Score TSV has no header')
  }

  const fieldNames = lines[0].split('\t')
  const rows = lines.slice(1).map((line) => {
    const values = line.split('\t')
    return Object.fromEntries(fieldNames.map((field, index) => [field, values[index] ?? '']))
  })

  return { fieldNames, rows }
}

export function loadBandWordsFromTsvText(
  text: string,
  languageKey: LanguageKey,
  band: string,
  sourceName = 'score TSV',
): string[] {
  if (!validBands.has(band)) {
    throw new ScoreWordSourceError(`Unsupported difficulty band: ${band}`)
  }

  const { fieldNames, rows } = parseTsv(text)
  const columns = new Set(fieldNames)
  if (!columns.has('word') || !columns.has('band')) {
    throw new ScoreWordSourceError(
      `Score TSV must include 'word' and 'band' columns: ${sourceName}`,
    )
  }

  const seen = new Set<string>()
  const words: string[] = []

  rows.forEach((row) => {
    const rawBand = String(row.band ?? '').trim().toLocaleLowerCase()
    if (rawBand !== band) {
      return
    }

    const word = normalizeCasefold(String(row.word ?? '').trim())
    if (word.length < 6) {
      return
    }
    if (!isAlphabeticWord(word)) {
      return
    }
    if (word !== word.toLocaleLowerCase()) {
      return
    }
    if (!isWordForLanguage(word, languageKey)) {
      return
    }
    if (seen.has(word)) {
      return
    }

    seen.add(word)
    words.push(word)
  })

  if (words.length === 0) {
    throw new ScoreWordSourceError(`No valid words found for score band '${band}' in ${sourceName}`)
  }

  return words
}

export async function fetchText(path: string): Promise<string> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new ScoreWordSourceError(`Score TSV not found: ${path}`)
  }
  return response.text()
}

export async function loadScoredWordsForDifficulty(
  languageKey: LanguageKey,
  difficultyKey: DifficultyKey,
): Promise<string[]> {
  const path = difficultyTsvPaths[languageKey]
  if (!path) {
    throw new ScoreWordSourceError(`No score TSV mapping configured for language key: ${languageKey}`)
  }

  const band = difficultySettings[difficultyKey]?.band
  if (!band) {
    throw new ScoreWordSourceError(`Unsupported difficulty key for score loading: ${difficultyKey}`)
  }

  const text = await fetchText(path)
  return loadBandWordsFromTsvText(text, languageKey, band, path)
}
