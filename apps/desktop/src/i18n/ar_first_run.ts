import type { FirstRunCopy } from './types_first_run'

export const arFirstRun: FirstRunCopy = {
  beats: {
    name: 'الاسم',
    theme: 'لون التمييز',
    layout: 'التخطيط',
    connectors: 'التطبيقات',
    plugins: 'الإضافات',
    tour: 'الجولة',
    build: 'المهمة الأولى'
  },
  namePlaceholder: 'اسمك',
  useName: name => `استخدام «${name}»`,
  install: 'تثبيت',
  installed: 'مثبّت',
  loading: 'جارٍ التحميل…',
  noPlugins: 'لا توجد إضافات لعرضها الآن.',
  noneChosen: 'لا شيء',
  answeredInChat: 'تمت الإجابة في المحادثة',
  noAnswer: 'لا توجد إجابة',
  skippedAll: 'تم تخطي الإعداد',
  skip: 'تخطي الإعداد',
  skipTip: 'إنهاء الإعداد الموجَّه. يمكنك متابعة المحادثة هنا.',
  localModel: {
    title: 'يمكن لهذا الكمبيوتر تشغيل نموذج محليًا',
    text: (model, size) => `${model} (${size}) يناسب أجهزتك. يعمل مجانًا، وتبقى محادثاتك على هذا الكمبيوتر.`,
    setUp: 'إعداده',
    notNow: 'ليس الآن'
  },
  rerun: {
    title: 'تشغيل الإعداد الأولي مرة أخرى',
    description: 'يفتح محادثة إعداد جديدة تمر بخطوات التشغيل الأول باستخدام نموذجك الحالي.',
    action: 'تشغيل مرة أخرى',
    failed: 'تعذّر بدء الإعداد الأولي'
  }
}
