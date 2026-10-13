import type { FirstRunCopy } from './types_first_run'

export const ruFirstRun: FirstRunCopy = {
  beats: {
    name: 'Имя',
    theme: 'Акцентный цвет',
    layout: 'Макет',
    connectors: 'Приложения',
    plugins: 'Плагины',
    tour: 'Обзор',
    build: 'Первая задача'
  },
  namePlaceholder: 'Ваше имя',
  useName: name => `Использовать «${name}»`,
  install: 'Установить',
  installed: 'Установлено',
  loading: 'Загрузка…',
  noPlugins: 'Сейчас нет плагинов для показа.',
  noneChosen: 'Нет',
  answeredInChat: 'Ответ дан в чате',
  noAnswer: 'Нет ответа',
  skippedAll: 'Настройка пропущена',
  skip: 'Пропустить настройку',
  skipTip: 'Завершить пошаговую настройку. Можно продолжить общение здесь.',
  localModel: {
    title: 'Этот компьютер может запускать модель локально',
    text: (model, size) =>
      `${model} (${size}) подходит для вашего оборудования. Она работает бесплатно, а ваши чаты остаются на этом компьютере.`,
    setUp: 'Настроить',
    notNow: 'Не сейчас'
  },
  rerun: {
    title: 'Пройти знакомство заново',
    description: 'Открывает новый чат настройки, который проводит по первым шагам с вашей текущей моделью.',
    action: 'Запустить снова',
    failed: 'Не удалось начать знакомство'
  }
}
