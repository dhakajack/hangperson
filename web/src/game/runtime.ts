import { type DifficultyKey, type LanguageKey, languageSettings } from './hangperson'
import { publicPath } from './publicPath'
import { loadScoredWordsForDifficulty } from './scoredWords'
import type { UiLocale } from './session'

export const localePaths: Record<LanguageKey, string> = {
  e: publicPath('data/locales/en.json'),
  f: publicPath('data/locales/fr.json'),
  r: publicPath('data/locales/ru.json'),
  el: publicPath('data/locales/el.json'),
}

export async function loadLocale(languageKey: LanguageKey): Promise<UiLocale> {
  const response = await fetch(localePaths[languageKey])
  if (!response.ok) {
    throw new Error(`Locale not found for ${languageSettings[languageKey].name}`)
  }

  const data = await response.json()
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error(`Invalid locale data for ${languageSettings[languageKey].name}`)
  }
  return data as UiLocale
}

export async function loadWordsForRound(
  languageKey: LanguageKey,
  difficultyKey: DifficultyKey,
): Promise<string[]> {
  return loadScoredWordsForDifficulty(languageKey, difficultyKey)
}
