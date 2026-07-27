# LaneGateway
LaneGateway это не "личный AI-ассистент" и не агентная платформа, а универсальный AI Gateway: единая точка входа для запросов, внутри которой принимаются решения о выборе модели, инструментов, памяти и бюджета.

Идея проекта: Каждая новая возможность подключается как модуль не требуя изменения ядра.

Нынешний этап разработки: Ядро
Полностью рабочий сервер (На уровне "Hello World"):

FastAPI
Конфиг
Логирование
Авторизация
Docker Compose
База данных (SQLite для старта)
Менеджер моделей

На данном этапе просто вызовы функций

Второй этап: Провадеры

Единый интерфейс
class Provider(ABC):
    async def chat(...) -> ChatResult
    async def embeddings(...) -> EmbeddingsResult
    async def vision(...) -> ChatResult   # или флаг поддержки + chat()

Каждый новый провайдер это отдельный файл/пакет:
providers/
  openrouter/
  openai/
  ollama/
  anthropic/
  gemini/

Первая реализация — только openrouter/

Третий этап: Роутеры

Request → Pre Rules → Router AI → Provider → LLM

Роутеры не в курсе про отдельные нейронки, они возвращают только потребности

need:
  - vision
  - large_context
  - code

Отдельный слой это "маппер потребностей" который решает, какой provider+model это покрывает:
{ "provider": "openrouter", "model": "anthropic/claude-sonnet", "tools": ["search"] }

На этом этапе появляется первый Event Bus — простой, свой, асинхронный, без внешних брокеров (RabbitMQ/Kafka не нужны):
event.emit(MessageReceived(...))
event.on(MessageReceived, callback)

Нужен, чтобы дальше клиенты (Telegram, Discord, WebSocket) могли подписываться на события, не трогая ядро.

Четвертый этап: Инструменты

Каждый инструмент — отдельный пакет:
tools/
  search/
  git/
  docker/
  ssh/
  browser/
  filesystem/

Правило: любой инструмент можно удалить, и проект продолжит работать.

Пятый этап: Движок пайплайнов

Вместо агентного фреймворка:
Начинаем с обычных функций: answer_question()
Добавляется шаг: search() → answer()
Добавляется память: memory() → search() → answer()
Когда видно повторяющийся паттерн — только тогда выделяется абстракция Пайплайнов

Принцип "никакой магии": каждый этап виден и разделён, никакого agent.run(), скрывающего происходящее:

Router → Memory → Search → Provider → Formatter

Пользователь сам собирает пайплайн декларативно:
pipeline:
  memory
  router
  search
  provider
  formatter
или
 pipeline:
  router
  browser
  browser
  provider

Открытый вопрос на будущее: строго линейный список шагов не поддерживает ветвление/повтор по условию ("искать, пока не найдётся релевантный результат, но не больше 3 раз") — решить, нужно ли это или оставить строго линейным.

Шестой этап: Память

Не история чата, грубо говоря знания

Project > Facts > Documents > Summaries

Поиск — через embeddings. Технически самая трудоёмкая часть, после стабилизации роутинга и pipeline.

Движок политик

Пользователь не программирует роутер — он пишет декларативные политики:

budget:
  daily: 1$
rules:
  - if: image
    use: claude
  - if: pdf
    use: claude
  - if: search
    tool: searxng
  - if: budget < 5$
    forbid: [claude]
  - if: night
    prefer: [deepseek]

Нужно сразу продумать приоритет между правилами (например, forbid всегда перекрывает prefer) — иначе при конфликте правил поведение непредсказуемо. Парсер/валидатор этого YAML — отдельная задача, не в рамках Этапа 3, а отдельный подэтап после базового rule-based роутера.

Менеджер бюджета

Прогноз стоимости заранее (до вызова модели), через estimate_cost() у провайдера

Если прогноз превышает остаток лимита — принудительное понижение уровня модели (это и есть одно из правил Движка политик: forbid/prefer).

Пример лимита: $1/день или $15/месяц (настраивается).

Пояснение роутинга

Поскольку каждый этап пайплайн виден отдельно (принцип "никакой магии"), это объяснение строится тривиально — просто лог каждого шага:

какие need определил Router
какой provider/model выбран и почему
сработал ли Движок политик (forbid/prefer) и по какому правилу
фактическая/прогнозная стоимость

Точки расширения (чтобы принцип "модуль без изменения ядра" реально работал)

Начиная с Этапа 1-2 явно зафиксировать реестры (registries):
ProviderRegistry — новый провайдер регистрируется, а не хардкодится
ToolRegistry — то же для инструментов
PipelineStepRegistry — то же для шагов pipeline

Без этих точек расширения принцип легко нарушить уже на 3-4 этапе.

Порядок запуска клиентов

Backend > CLI > Telegram > WebUI

CLI — для быстрого тестирования новых функций без поднятия интерфейса. WebUI — только когда ядро стабильно.

Примерная структура каталогов и файлов проекта:

LaneGateway/
├── app/
│   ├── main.py              # создание FastAPI-приложения, подключение api-роутов
│   ├── core/
│   │   ├── config.py        # настройки (Pydantic Settings, .env)
│   │   ├── logging.py       # настройка логирования
│   │   ├── security.py      # авторизация (API-key dependency)
│   │   └── db.py            # подключение к SQLite, сессии
│   │
│   ├── api/                 # HTTP-эндпоинты (FastAPI-роуты)
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── chat.py
│   │       └── health.py
│   │
│   ├── providers/
│   │   ├── base.py          # уже есть
│   │   ├── registry.py      # ProviderRegistry — новый провайдер регистрируется, не хардкодится
│   │   └── openrouter.py    # уже есть; openai/, ollama/, anthropic/, gemini/ — позже
│   │
│   ├── models_manager.py    # обёртка над ProviderRegistry: chat/vision/embeddings по имени модели
│   │
│   └── schemas/              # Pydantic-схемы запросов/ответов API (отдельно от dataclass-ов провайдера)
│       └── chat.py
│
├── tests/
│   ├── test_providers/
│   │   └── test_openrouter.py
│   └── test_api/
│
├── example_usage.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt (или pyproject.toml)
├── .env.example
├── .gitignore
├── LICENSE
└── README.md