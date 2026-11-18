import pytest
import requests
import responses
from responses import matchers

BASE_URL = "https://cloud-api.yandex.net/v1/disk/resources"
HEADERS = {"Authorization": "OAuth test_token"}


class TestCreateFolderUnit:
    """Unit-тесты эндпоинта создания папки с мокированием HTTP."""

    @responses.activate
    def test_create_folder_success(self):
        """Успешный запрос возвращает 201 и Link."""
        responses.put(
            BASE_URL,
            json={
                "href": "https://cloud-api.yandex.net/v1/disk/resources?path=disk%3A%2Ftest",
                "method": "GET",
                "templated": False,
            },
            status=201,
            match=[
                matchers.query_param_matcher({"path": "/test"}),
                matchers.header_matcher({"Authorization": "OAuth test_token"}),
            ],
        )

        resp = requests.put(BASE_URL, headers=HEADERS, params={"path": "/test"})

        assert resp.status_code == 201
        assert "href" in resp.json()
        assert resp.json()["method"] == "GET"

    @responses.activate
    def test_create_folder_conflict(self):
        """Конфликт имени возвращает 409."""
        responses.put(
            BASE_URL,
            json={"error": "DiskResourceAlreadyExistsError", "message": "Resource already exists"},
            status=409,
        )

        resp = requests.put(BASE_URL, headers=HEADERS, params={"path": "/existing"})

        assert resp.status_code == 409
        assert "error" in resp.json()

    @responses.activate
    def test_create_folder_unauthorized(self):
        """Невалидный токен возвращает 401."""
        responses.put(BASE_URL, json={"error": "UnauthorizedError"}, status=401)

        resp = requests.put(
            BASE_URL,
            headers={"Authorization": "OAuth bad_token"},
            params={"path": "/test"},
        )

        assert resp.status_code == 401

    @responses.activate
    def test_create_folder_missing_path(self):
        """Отсутствие path возвращает 400."""
        responses.put(BASE_URL, json={"error": "FieldValidationError"}, status=400)

        resp = requests.put(BASE_URL, headers=HEADERS)

        assert resp.status_code == 400

    @responses.activate
    def test_create_folder_forbidden_no_space(self):
        """Недостаточно места (403)."""
        responses.put(
            BASE_URL,
            json={"error": "ForbiddenError", "message": "Disk is full"},
            status=403,
        )

        resp = requests.put(BASE_URL, headers=HEADERS, params={"path": "/big_folder"})

        assert resp.status_code == 403

    def test_create_folder_without_mock_raises_connection_error(self):
        """Если мок не зарегистрирован, responses выбрасывает ConnectionError."""
        with responses.RequestsMock(assert_all_requests_are_fired=False):
            with pytest.raises(requests.exceptions.ConnectionError):
                requests.put(BASE_URL, headers=HEADERS, params={"path": "/test"})
