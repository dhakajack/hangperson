import { type DifficultyKey, type LanguageKey, languageSettings } from './hangperson'
import { publicPath } from './publicPath'

export type CharacterLayerKey =
  | 'silhouette'
  | 'head'
  | 'left_eye'
  | 'right_eye'
  | 'nose'
  | 'mouth'
  | 'shirt'
  | 'left_arm'
  | 'right_arm'
  | 'left_leg'
  | 'right_leg'
  | 'dead'

type CharacterLayerState = {
  uiMode: 'setup' | 'active_round' | 'round_complete'
  game: { errors: number; isLost: () => boolean } | null
  difficultyKey: DifficultyKey | null
  pendingDifficultyKey?: DifficultyKey
}

export const revealGroupsByDifficulty: Record<DifficultyKey, CharacterLayerKey[][]> = {
  '1': [
    ['head'],
    ['left_eye'],
    ['right_eye'],
    ['nose'],
    ['mouth'],
    ['shirt'],
    ['left_arm'],
    ['right_arm'],
    ['left_leg'],
    ['right_leg'],
  ],
  '2': [
    ['head'],
    ['left_eye', 'right_eye'],
    ['nose', 'mouth'],
    ['shirt'],
    ['left_arm'],
    ['right_arm'],
    ['left_leg'],
    ['right_leg'],
  ],
  '3': [
    ['head'],
    ['left_eye', 'right_eye'],
    ['nose', 'mouth'],
    ['shirt'],
    ['left_arm', 'right_arm'],
    ['left_leg', 'right_leg'],
  ],
}

export function revealedPartsForErrors(
  errors: number,
  difficultyKey: DifficultyKey,
): CharacterLayerKey[] {
  if (errors <= 0) {
    return []
  }
  return revealGroupsByDifficulty[difficultyKey].slice(0, errors).flat()
}

export function currentCharacterLayerKeys(state: CharacterLayerState): CharacterLayerKey[] {
  if (state.uiMode === 'setup') {
    return ['silhouette']
  }
  if (!state.game) {
    return []
  }

  const difficultyKey = state.difficultyKey ?? state.pendingDifficultyKey ?? '2'
  const layers: CharacterLayerKey[] = [
    'silhouette',
    ...revealedPartsForErrors(state.game.errors, difficultyKey),
  ]
  if (state.game.isLost()) {
    layers.push('dead')
  }
  return layers
}

export function languageBadgePath(languageKey: LanguageKey): string {
  return publicPath(`assets/images/language/lang_${languageSettings[languageKey].assetCode}.png`)
}

export function difficultyIconPath(difficultyKey: DifficultyKey): string {
  const names: Record<DifficultyKey, string> = {
    '1': 'easy',
    '2': 'medium',
    '3': 'hard',
  }
  return publicPath(`assets/images/difficulty/difficulty_${names[difficultyKey]}.png`)
}

export function characterLayerPath(
  languageKey: LanguageKey,
  layerKey: CharacterLayerKey,
): string {
  const code = languageSettings[languageKey].assetCode
  return publicPath(`assets/images/people/${code}/${layerKey}_${code}.png`)
}

export const startButtonPath = publicPath('assets/images/buttons/start_rocket.png')
export const restartButtonPath = publicPath('assets/images/buttons/restart_arrow.png')
export const trophyPath = publicPath('assets/images/decoration/trophy.png')
