import type { FirstRunCopy } from './types_first_run'

export const zhHantFirstRun: FirstRunCopy = {
  beats: {
    name: '名字',
    theme: '強調色',
    layout: '版面配置',
    connectors: '應用程式',
    plugins: '外掛',
    tour: '導覽',
    build: '第一個任務'
  },
  namePlaceholder: '你的名字',
  useName: name => `使用「${name}」`,
  install: '安裝',
  installed: '已安裝',
  loading: '正在載入…',
  noPlugins: '目前沒有可顯示的外掛。',
  noneChosen: '無',
  answeredInChat: '已在對話中回答',
  noAnswer: '未回答',
  skippedAll: '已略過設定',
  skip: '略過設定',
  skipTip: '結束引導設定。你可以繼續在這裡對話。',
  localModel: {
    title: '這部電腦可以在本機執行模型',
    text: (model, size) => `${model}（${size}）適合你的硬體。它免費執行，你的對話會留在這部電腦上。`,
    setUp: '設定',
    notNow: '暫時不要'
  },
  rerun: {
    title: '重新執行新手引導',
    description: '開啟新的設定對話，用你目前的模型走一遍首次執行的步驟。',
    action: '重新執行',
    failed: '無法啟動新手引導'
  }
}
