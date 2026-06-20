# Как убрать .env из git и запушить без блокировки

GitHub заблокировал пуш, потому что обнаружил твой OpenAI-ключ внутри
коммита `.env`. Просто изменить файл и закоммитить заново НЕ поможет —
ключ уже есть в истории. Нужно убрать его из истории целиком.

## Шаг 0 — обязательно: перевыпусти ключ OpenAI

Ключ уже "засвечен" (был в переписке, теперь в git-истории) — его нужно
ротировать в любом случае, независимо от шагов ниже:

1. https://platform.openai.com/api-keys
2. Найди ключ, который Екатерина присылала в чате (тот самый, что попал
   в коммит `.env` и был заблокирован GitHub Push Protection)
3. Нажми Revoke (отозвать)
4. Создай новый ключ, сохрани его себе отдельно (НЕ в git)

Токен Telegram-бота тоже стоит перевыпустить на всякий случай:
@BotFather -> /mybots -> выбрать бота -> Bot Settings -> Revoke Token

## Шаг 1 — добавь .gitignore (уже сделано в новом архиве)

В проект уже добавлен `.gitignore`, который исключает `.env` из будущих
коммитов. Проверь, что он у тебя есть:

```powershell
cat .gitignore
```

Должна быть строка `.env`.

## Шаг 2 — убери .env из ИСТОРИИ git (не только из текущего коммита)

Самый простой способ для небольшого репозитория — переписать историю
через `git filter-repo` (рекомендуемый Git'ом инструмент) или, если его
нет, через `git filter-branch`.

### Вариант А (проще, если репозиторий ещё небольшой и недавно создан):

Если у тебя только локальный коммит и ты ОДИН работаешь с этим репо,
проще всего удалить .git историю и начать заново:

```powershell
cd C:\Users\user\Downloads\psy-bot\psy-bot
Remove-Item -Recurse -Force .git
git init
git add .
git commit -m "Initial commit (без секретов)"
git branch -M main
git remote add origin https://github.com/nurzhan2/Psy_bot.git
git push -u origin main --force
```

⚠️ `--force` перезапишет историю на GitHub. Это нормально, если ты ещё
не давал доступ другим людям к этому репозиторию и не клонировал его
больше нигде.

### Вариант Б (если нужно сохранить историю коммитов):

Используй `git filter-repo` (нужно установить отдельно: `pip install git-filter-repo`):

```powershell
pip install git-filter-repo
cd C:\Users\user\Downloads\psy-bot\psy-bot
git filter-repo --path .env --invert-paths
git remote add origin https://github.com/nurzhan2/Psy_bot.git
git push origin main --force
```

## Шаг 3 — создай .env заново локально (НЕ коммить)

```powershell
copy .env.example .env
notepad .env
```

Впиши туда НОВЫЕ ключи (после ротации из Шага 0).

## Шаг 4 — сделай репозиторий приватным (рекомендуется)

Раз в нём будет крутиться терапевтический бот с потенциально
чувствительной логикой — на GitHub: Settings -> Danger Zone ->
Change repository visibility -> Private.

## Дальше

```powershell
git add .
git status   # убедись, что .env НЕ в списке файлов на коммит
git commit -m "Добавлен .gitignore, секреты убраны из истории"
git push origin main
```

Если пуш снова заблокирован — значит где-то ещё остался секрет в
истории; проверь вывод ошибки, там будет указан конкретный коммит и файл.
