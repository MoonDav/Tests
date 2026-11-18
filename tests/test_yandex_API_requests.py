# Требуется переменная окружения YANDEX_DISK_TOKEN с действующим OAuth-токеном.

import os
import uuid
import pytest
import requests

BASE_URL = "https://cloud-api.yandex.net/v1/disk/resources"
TOKEN = os.getenv("YANDEX_DISK_TOKEN")
HEADERS = {"Authorization": f"OAuth {TOKEN}"}


@pytest.fixture
def folder_path():
    """Уникальный путь для папки, чтобы тесты не конфликтовали."""
    path = f"/test_folder_{uuid.uuid4().hex[:8]}"
    yield path
    # Очистка после теста (необязательно, но полезно)
    requests.delete(BASE_URL, headers=HEADERS, params={"path": path, "permanently": True})


class TestCreateFolder:
    """Тесты создания папки на Яндекс.Диске."""

    def test_create_folder_returns_201(self, folder_path):
        """Успешное создание возвращает 201 Created."""
        response = requests.put(BASE_URL, headers=HEADERS, params={"path": folder_path})
        assert response.status_code == 201, response.text

    def test_folder_appears_in_listing(self, folder_path):
        """Созданная папка появляется в списке файлов."""
        # Создаём
        create_resp = requests.put(BASE_URL, headers=HEADERS, params={"path": folder_path})
        assert create_resp.status_code == 201

        # Проверяем наличие в корне
        list_resp = requests.get(
            BASE_URL,
            headers=HEADERS,
            params={"path": "/", "limit": 100},
        )
        assert list_resp.status_code == 200
        items = list_resp.json()["_embedded"]["items"]
        names = [item["name"] for item in items]
        assert folder_path.lstrip("/") in names

    def test_create_duplicate_folder_returns_409(self, folder_path):
        """Повторное создание папки с тем же именем — конфликт (409)."""
        requests.put(BASE_URL, headers=HEADERS, params={"path": folder_path})
        response = requests.put(BASE_URL, headers=HEADERS, params={"path": folder_path})
        assert response.status_code == 409

    def test_create_folder_unauthorized(self, folder_path):
        """Без токена — 401 Unauthorized."""
        response = requests.put(
            BASE_URL,
            headers={"Authorization": "OAuth invalid_token_12345"},
            params={"path": folder_path},
        )
        assert response.status_code == 401

    def test_create_folder_missing_path(self):
        """Без параметра path — 400 Bad Request."""
        response = requests.put(BASE_URL, headers=HEADERS)
        assert response.status_code == 400

    @pytest.mark.parametrize("invalid_path,expected_status", [
        ("", 400),
        ("/a" * 20000, 414),          # слишком длинный путь
        ("/folder_with_invalid_chars<*>|", 201),
    ])
    def test_create_folder_invalid_path(self, invalid_path, expected_status):
        """Некорректные пути возвращают 400."""
        response = requests.put(BASE_URL, headers=HEADERS, params={"path": invalid_path})
        assert response.status_code == expected_status
