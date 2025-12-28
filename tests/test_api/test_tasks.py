import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestTasksAPI:
    """Тесты для API задач"""

    async def test_health_check(self, client: AsyncClient):
        """Тест health check endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data

    async def test_create_task(self, client: AsyncClient, sample_task_data):
        """Тест создания задачи"""
        response = await client.post("/api/v1/tasks", json=sample_task_data)

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert data["title"] == sample_task_data["title"]
        assert data["description"] == sample_task_data["description"]
        assert data["priority"] == sample_task_data["priority"]
        assert data["status"] == "PENDING"  # После создания статус PENDING
        assert data["created_at"] is not None
        assert data["started_at"] is None
        assert data["completed_at"] is None

    async def test_create_task_minimal(self, client: AsyncClient):
        """Тест создания задачи с минимальными данными"""
        response = await client.post(
            "/api/v1/tasks",
            json={"title": "Minimal Task", "priority": "LOW"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minimal Task"
        assert data["description"] is None
        assert data["priority"] == "LOW"

    async def test_create_task_validation_error(self, client: AsyncClient):
        """Тест валидации при создании задачи"""
        # Без обязательных полей
        response = await client.post("/api/v1/tasks", json={})
        assert response.status_code == 422

        # Неправильный приоритет
        response = await client.post(
            "/api/v1/tasks",
            json={"title": "Test", "priority": "INVALID"}
        )
        assert response.status_code == 422

    async def test_get_task(self, client: AsyncClient, sample_task_data):
        """Тест получения задачи по ID"""
        # Создаем задачу
        create_response = await client.post("/api/v1/tasks", json=sample_task_data)
        task_id = create_response.json()["id"]

        # Получаем задачу
        response = await client.get(f"/api/v1/tasks/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["title"] == sample_task_data["title"]

    async def test_get_task_not_found(self, client: AsyncClient):
        """Тест получения несуществующей задачи"""
        response = await client.get("/api/v1/tasks/99999")
        assert response.status_code == 404

    async def test_get_task_status(self, client: AsyncClient, sample_task_data):
        """Тест получения статуса задачи"""
        # Создаем задачу
        create_response = await client.post("/api/v1/tasks", json=sample_task_data)
        task_id = create_response.json()["id"]

        # Получаем статус
        response = await client.get(f"/api/v1/tasks/{task_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["status"] == "PENDING"
        assert "created_at" in data

    async def test_list_tasks_empty(self, client: AsyncClient):
        """Тест получения пустого списка задач"""
        response = await client.get("/api/v1/tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 10

    async def test_list_tasks(self, client: AsyncClient):
        """Тест получения списка задач"""
        # Создаем несколько задач
        await client.post("/api/v1/tasks", json={"title": "Task 1", "priority": "HIGH"})
        await client.post("/api/v1/tasks", json={"title": "Task 2", "priority": "MEDIUM"})
        await client.post("/api/v1/tasks", json={"title": "Task 3", "priority": "LOW"})

        # Получаем список
        response = await client.get("/api/v1/tasks")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3

    async def test_list_tasks_with_pagination(self, client: AsyncClient):
        """Тест пагинации списка задач"""
        # Создание 5 задач
        for i in range(5):
            await client.post("/api/v1/tasks", json={"title": f"Task {i}", "priority": "MEDIUM"})

        # Получаем первую страницу (2 элемента)
        response = await client.get("/api/v1/tasks?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1

        # Получаем вторую страницу
        response = await client.get("/api/v1/tasks?page=2&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["page"] == 2

    async def test_list_tasks_filter_by_priority(self, client: AsyncClient):
        """Тест фильтрации по приоритету"""
        # Создаем задачи с разными приоритетами
        await client.post("/api/v1/tasks", json={"title": "High 1", "priority": "HIGH"})
        await client.post("/api/v1/tasks", json={"title": "High 2", "priority": "HIGH"})
        await client.post("/api/v1/tasks", json={"title": "Low", "priority": "LOW"})

        # Фильтруем по HIGH
        response = await client.get("/api/v1/tasks?priority=HIGH")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        assert all(item["priority"] == "HIGH" for item in data["items"])

    async def test_list_tasks_filter_by_status(self, client: AsyncClient):
        """Тест фильтрации по статусу"""
        # Создаем задачи
        await client.post("/api/v1/tasks", json={"title": "Task 1", "priority": "HIGH"})
        await client.post("/api/v1/tasks", json={"title": "Task 2", "priority": "LOW"})

        # Все задачи должны быть в статусе PENDING
        response = await client.get("/api/v1/tasks?status=PENDING")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(item["status"] == "PENDING" for item in data["items"])

    async def test_cancel_task(self, client: AsyncClient, sample_task_data):
        """Тест отмены задачи"""
        # Создаем задачу
        create_response = await client.post("/api/v1/tasks", json=sample_task_data)
        task_id = create_response.json()["id"]

        # Отменяем задачу
        response = await client.delete(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 204

        # Проверка, что статус изменился на CANCELLED
        get_response = await client.get(f"/api/v1/tasks/{task_id}")
        assert get_response.json()["status"] == "CANCELLED"

    async def test_cancel_task_not_found(self, client: AsyncClient):
        """Тест отмены несуществующей задачи"""
        response = await client.delete("/api/v1/tasks/99999")
        assert response.status_code == 404

    async def test_task_published_to_queue(self, client: AsyncClient, mock_queue_service, sample_task_data):
        """Тест, что задача публикуется в очередь"""
        # Создаем задачу
        response = await client.post("/api/v1/tasks", json=sample_task_data)
        task_id = response.json()["id"]

        # Проверяем что задача была опубликована
        assert len(mock_queue_service.published_tasks) == 1
        published = mock_queue_service.published_tasks[0]
        assert published["task_id"] == task_id
        assert published["priority"] == "HIGH"
