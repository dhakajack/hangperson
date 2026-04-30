import { describe, expect, it } from 'vitest'
import { ScoreWordSourceError, loadBandWordsFromTsvText } from './scoredWords'

describe('loadBandWordsFromTsvText', () => {
  it('validates required columns', () => {
    const tsv = 'word\tscore\nplanet\t1.0\n'

    expect(() => loadBandWordsFromTsvText(tsv, 'e', 'easy')).toThrow(ScoreWordSourceError)
  })

  it('filters, dedupes, and returns matching band words', () => {
    const tsv = [
      'word\tband\tscore',
      'planet\teasy\t0.1',
      'planet\teasy\t0.2',
      'forest\teasy\t0.3',
      'Forest\teasy\t0.4',
      'number7\teasy\t0.5',
      'mountain\tmedium\t0.6',
    ].join('\n')

    expect(loadBandWordsFromTsvText(tsv, 'e', 'easy')).toEqual(['planet', 'forest'])
  })

  it('raises for an empty band', () => {
    const tsv = 'word\tband\nplanet\teasy\n'

    expect(() => loadBandWordsFromTsvText(tsv, 'e', 'hard')).toThrow(ScoreWordSourceError)
  })

  it('supports Greek and canonicalizes final sigma', () => {
    const tsv = ['word\tband', 'αγαπη\teasy', 'κοσμος\teasy'].join('\n')

    expect(loadBandWordsFromTsvText(tsv, 'el', 'easy')).toEqual(['κοσμοσ'])
  })
})
