import type { FirstRunCopy } from './types_first_run'

export const esFirstRun: FirstRunCopy = {
  beats: {
    name: 'Nombre',
    theme: 'Color de acento',
    layout: 'Diseño',
    connectors: 'Apps',
    plugins: 'Plugins',
    tour: 'Recorrido',
    build: 'Primera tarea'
  },
  namePlaceholder: 'Tu nombre',
  useName: name => `Usar «${name}»`,
  install: 'Instalar',
  installed: 'Instalado',
  loading: 'Cargando…',
  noPlugins: 'No hay plugins para mostrar ahora mismo.',
  noneChosen: 'Ninguno',
  answeredInChat: 'Respondido en el chat',
  noAnswer: 'Sin respuesta',
  skippedAll: 'Configuración omitida',
  skip: 'Omitir configuración',
  skipTip: 'Termina la configuración guiada. Puedes seguir chateando aquí.',
  localModel: {
    title: 'Este ordenador puede ejecutar un modelo localmente',
    text: (model, size) =>
      `${model} (${size}) encaja con tu hardware. Funciona gratis y tus chats se quedan en este ordenador.`,
    setUp: 'Configurarlo',
    notNow: 'Ahora no'
  },
  rerun: {
    title: 'Repetir la configuración inicial',
    description: 'Abre un nuevo chat de configuración que recorre los primeros pasos con tu modelo actual.',
    action: 'Repetir',
    failed: 'No se pudo iniciar la configuración inicial'
  }
}
