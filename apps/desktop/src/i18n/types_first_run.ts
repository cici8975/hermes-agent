/** First-run onboarding: the setup_beat cards and their receipts, Skip setup, the local-model offer
 *  at the end, and the Settings row that runs it again. */
export interface FirstRunCopy {
  /** Receipt labels, one per beat. */
  beats: {
    name: string
    theme: string
    layout: string
    connectors: string
    plugins: string
    tour: string
    build: string
  }
  namePlaceholder: string
  /** The OS account's full name, offered as a row on the name card. */
  useName: (name: string) => string
  install: string
  installed: string
  loading: string
  noPlugins: string
  /** A receipt for a card that settled with nothing chosen (no apps connected, no plugin installed). */
  noneChosen: string
  answeredInChat: string
  noAnswer: string
  skippedAll: string
  skip: string
  skipTip: string
  localModel: {
    title: string
    text: (model: string, size: string) => string
    setUp: string
    notNow: string
  }
  rerun: {
    title: string
    description: string
    action: string
    failed: string
  }
}
