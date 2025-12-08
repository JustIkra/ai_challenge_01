# План имплементации: Настройка температуры ИИ

## Обзор

Добавление контрола температуры в настройки чата для управления креативностью ответов Gemini AI.

**Затрагиваемые компоненты:**
- Backend: модель, схемы, сервис, миграция
- Frontend: типы, компонент настроек
- Gemini Client: логирование

**Принятые решения:**
| # | Вопрос | Решение |
|---|--------|---------|
| Q1 | Диапазон | 0.1–1.5 в UI |
| Q2 | Дефолт существующих | UPDATE до 0.7 в миграции |
| Q3 | При создании | Только через настройки |
| Q4 | В списке чатов | Не показывать |
| Q5 | Обработка NULL | Явная проверка на None |
| Q6 | Тесты | Backend CRUD + GeminiRequest |
| Q7 | Округление float | На фронте перед отправкой |
| Q8 | Кнопка сброса | Нет (MVP) |
| Q9 | Ошибки валидации | Оставить как есть (MVP) |
| Q10 | Логирование | Добавить в gemini-client |

---

## Шаг 1: Backend - Миграция БД

**Файл:** `backend/alembic/versions/003_add_temperature.py`

**Действие:** Создать миграцию с UPDATE для существующих записей

```python
"""Add temperature to chats

Revision ID: 003
Revises: 002
Create Date: 2025-12-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add column with server default
    op.add_column('chats', sa.Column('temperature', sa.Float(), nullable=True, server_default='0.7'))

    # Update existing records to have explicit value (Q2)
    op.execute("UPDATE chats SET temperature = 0.7 WHERE temperature IS NULL")


def downgrade() -> None:
    op.drop_column('chats', 'temperature')
```

**Проверка:** `docker-compose exec backend alembic upgrade head`

---

## Шаг 2: Backend - Модель Chat

**Файл:** `backend/app/models/chat.py`

**Действие:** Добавить поле temperature

```python
from sqlalchemy import Float  # добавить в импорты

# После system_prompt (строка ~27):
temperature: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.7)
```

---

## Шаг 3: Backend - Схемы Pydantic

**Файл:** `backend/app/schemas/chat.py`

**Действие:** Добавить temperature в три схемы с валидацией 0.1-1.5 (Q1)

### ChatCreate (строка ~13)
```python
class ChatCreate(BaseModel):
    """Schema for creating a new chat."""
    user_id: uuid.UUID = Field(..., description="User ID")
    title: str | None = Field(None, max_length=255, description="Optional chat title")
    system_prompt: str | None = Field(None, description="System instruction for AI")
    temperature: float | None = Field(None, ge=0.1, le=1.5, description="AI temperature (0.1-1.5)")
```

### ChatUpdate (строка ~20)
```python
class ChatUpdate(BaseModel):
    """Schema for updating a chat."""
    title: str | None = Field(None, max_length=255)
    system_prompt: str | None = Field(None)
    temperature: float | None = Field(None, ge=0.1, le=1.5)
```

### ChatResponse (строка ~26)
```python
class ChatResponse(BaseModel):
    """Schema for chat response."""
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    system_prompt: str | None
    temperature: float | None  # добавить
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

## Шаг 4: Backend - Сервис ChatService

**Файл:** `backend/app/services/chat.py`

### 4.1 Метод create_chat (строка ~39)
```python
chat = Chat(
    user_id=user_id,
    title=chat_data.title,
    system_prompt=chat_data.system_prompt,
    temperature=chat_data.temperature  # добавить
)
```

### 4.2 Метод send_message_to_gemini (строка ~246)

**Изменить:** Использовать явную проверку на None (Q5)

```python
# Перед return GeminiRequestMessage (строка ~246):
# Определить температуру с fallback на дефолт
temperature = chat.temperature if chat.temperature is not None else 0.7

return GeminiRequestMessage(
    request_id=request_id,
    prompt=prompt,
    model=settings.GEMINI_MODEL_TEXT,
    parameters=GenerationParameters(temperature=temperature),  # передать temperature
    system_instruction=chat.system_prompt
)
```

---

## Шаг 5: Frontend - Типы

**Файл:** `frontend/src/types/chat.ts`

### Chat (строка ~1)
```typescript
export interface Chat {
  id: string
  user_id: string
  title: string | null
  system_prompt: string | null
  temperature: number | null  // добавить
  created_at: string
}
```

### ChatUpdate (строка ~31)
```typescript
export interface ChatUpdate {
  title?: string | null
  system_prompt?: string | null
  temperature?: number | null  // добавить
}
```

---

## Шаг 6: Frontend - Компонент настроек

**Файл:** `frontend/src/components/chat/ChatSettingsModal.vue`

### 6.1 Template - добавить слайдер (после System Prompt, строка ~39, перед Buttons)

```vue
<!-- Temperature -->
<div class="mb-6">
  <label class="block text-sm font-medium text-gray-300 mb-2">
    Temperature: {{ displayTemperature }}
  </label>
  <input
    v-model.number="formData.temperature"
    type="range"
    min="0.1"
    max="1.5"
    step="0.1"
    class="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
  />
  <div class="flex justify-between text-xs text-gray-500 mt-1">
    <span>0.1 (precise)</span>
    <span>1.5 (creative)</span>
  </div>
  <p class="mt-2 text-xs text-gray-400">
    Lower values produce more focused and deterministic responses.
    Higher values produce more creative and varied responses.
  </p>
</div>
```

### 6.2 Script - computed для отображения (после isSaving)

```typescript
import { ref, watch, computed } from 'vue'  // добавить computed

// После isSaving ref:
const displayTemperature = computed(() => {
  return (formData.value.temperature ?? 0.7).toFixed(1)
})
```

### 6.3 Script - formData (строка ~79)

```typescript
const formData = ref<ChatUpdate>({
  title: '',
  system_prompt: '',
  temperature: 0.7  // добавить
})
```

### 6.4 Script - watch (строка ~86)

```typescript
watch(() => props.chat, (newChat) => {
  if (newChat) {
    formData.value = {
      title: newChat.title || '',
      system_prompt: newChat.system_prompt || '',
      temperature: newChat.temperature ?? 0.7  // добавить
    }
  }
}, { immediate: true })
```

### 6.5 Script - save функция с округлением (Q7)

```typescript
async function save() {
  if (!props.chat) return

  isSaving.value = true
  try {
    // Округлить temperature перед отправкой (Q7)
    const dataToSend: ChatUpdate = {
      ...formData.value,
      temperature: formData.value.temperature != null
        ? Math.round(formData.value.temperature * 10) / 10
        : null
    }

    const response = await chatApi.update(props.chat.id, dataToSend)
    emit('saved', response.data)
    close()
  } catch (error) {
    console.error('Failed to save chat settings:', error)
  } finally {
    isSaving.value = false
  }
}
```

---

## Шаг 7: Gemini Client - Логирование (Q10)

**Файл:** `gemini-client/src/main.py`

**Действие:** Добавить логирование temperature в методе process_request

### В методе process_request (после строки ~82, перед try)

```python
async def process_request(
    self,
    request: GeminiRequestMessage,
    message: AbstractIncomingMessage,
) -> None:
    start_time = time.time()
    request_id = str(request.request_id)

    # Log request parameters including temperature (Q10)
    logger.info(
        f"[{request_id}] Processing request: model={request.model}, "
        f"temperature={request.parameters.temperature}"
    )

    try:
        # ... остальной код
```

---

## Шаг 8: Тестирование (Q6)

### 8.1 Backend тесты

**Файл:** `backend/tests/test_chat_temperature.py` (новый или добавить в существующий)

```python
import pytest
from app.schemas.chat import ChatCreate, ChatUpdate, ChatResponse
from app.services.chat import ChatService

class TestChatTemperature:
    """Tests for chat temperature feature."""

    async def test_update_chat_temperature(self, db_session, test_chat):
        """Test updating chat temperature."""
        update_data = ChatUpdate(temperature=1.2)
        updated = await ChatService.update_chat(db_session, test_chat.id, update_data)

        assert updated is not None
        assert updated.temperature == 1.2

    async def test_temperature_in_gemini_request(self, db_session, test_chat):
        """Test temperature is passed to GeminiRequestMessage."""
        test_chat.temperature = 0.9

        request = await ChatService.send_message_to_gemini(
            db_session, test_chat, "Hello", uuid.uuid4()
        )

        assert request.parameters.temperature == 0.9

    async def test_temperature_default_fallback(self, db_session, test_chat):
        """Test fallback to 0.7 when temperature is None."""
        test_chat.temperature = None

        request = await ChatService.send_message_to_gemini(
            db_session, test_chat, "Hello", uuid.uuid4()
        )

        assert request.parameters.temperature == 0.7

    def test_temperature_validation_range(self):
        """Test temperature validation in schema."""
        # Valid
        ChatUpdate(temperature=0.1)
        ChatUpdate(temperature=1.5)

        # Invalid - should raise
        with pytest.raises(ValueError):
            ChatUpdate(temperature=0.0)
        with pytest.raises(ValueError):
            ChatUpdate(temperature=2.0)
```

### 8.2 Запуск тестов

```bash
# Backend
cd backend && pytest tests/ -v

# Frontend
cd frontend && npm run test
```

### 8.3 Ручная проверка

1. Открыть настройки существующего чата → temperature = 0.7
2. Изменить на 1.2, сохранить
3. Переоткрыть настройки → должно быть 1.2
4. Проверить в логах gemini-client: `temperature=1.2`
5. Проверить в БД: `SELECT temperature FROM chats WHERE id = '...'`

---

## Порядок выполнения

1. [ ] **Миграция БД** (Шаг 1) - создать файл
2. [ ] **Модель Chat** (Шаг 2) - добавить поле
3. [ ] **Схемы Pydantic** (Шаг 3) - обновить 3 схемы
4. [ ] **Сервис ChatService** (Шаг 4) - create_chat + send_message_to_gemini
5. [ ] **Типы Frontend** (Шаг 5) - Chat + ChatUpdate
6. [ ] **UI компонент** (Шаг 6) - слайдер + логика
7. [ ] **Gemini Client логирование** (Шаг 7)
8. [ ] **Запуск миграции**: `docker-compose exec backend alembic upgrade head`
9. [ ] **Перезапуск сервисов**: `docker-compose restart backend gemini-client`
10. [ ] **Тестирование** (Шаг 8)

---

## Файлы для изменения

| Компонент | Файл | Действие |
|-----------|------|----------|
| Backend | `alembic/versions/003_add_temperature.py` | Создать |
| Backend | `app/models/chat.py` | Изменить |
| Backend | `app/schemas/chat.py` | Изменить |
| Backend | `app/services/chat.py` | Изменить |
| Frontend | `src/types/chat.ts` | Изменить |
| Frontend | `src/components/chat/ChatSettingsModal.vue` | Изменить |
| Gemini | `src/main.py` | Изменить |
| Backend | `tests/test_chat_temperature.py` | Создать (опционально) |
