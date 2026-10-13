import type { FirstRunCopy } from './types_first_run'

export const deFirstRun: FirstRunCopy = {
  beats: {
    name: 'Name',
    theme: 'Akzentfarbe',
    layout: 'Layout',
    connectors: 'Apps',
    plugins: 'Plugins',
    tour: 'Tour',
    build: 'Erste Aufgabe'
  },
  namePlaceholder: 'Dein Name',
  useName: name => `„${name}“ verwenden`,
  install: 'Installieren',
  installed: 'Installiert',
  loading: 'Wird geladen…',
  noPlugins: 'Gerade keine Plugins verfügbar.',
  noneChosen: 'Keine',
  answeredInChat: 'Im Chat beantwortet',
  noAnswer: 'Keine Antwort',
  skippedAll: 'Einrichtung übersprungen',
  skip: 'Einrichtung überspringen',
  skipTip: 'Beendet die geführte Einrichtung. Du kannst hier weiterchatten.',
  localModel: {
    title: 'Dieser Computer kann ein Modell lokal ausführen',
    text: (model, size) =>
      `${model} (${size}) passt zu deiner Hardware. Es läuft kostenlos, und deine Chats bleiben auf diesem Computer.`,
    setUp: 'Einrichten',
    notNow: 'Nicht jetzt'
  },
  rerun: {
    title: 'Onboarding erneut starten',
    description: 'Öffnet einen neuen Einrichtungs-Chat, der die ersten Schritte mit deinem aktuellen Modell durchgeht.',
    action: 'Erneut starten',
    failed: 'Onboarding konnte nicht gestartet werden'
  }
}
