import copy
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src import auth
from src.manage_teachers import main as assign_teacher
from src.app import activities, app


class AdminTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = auth.password_record("a-long-test-password")

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "teachers.json"
        self.path.write_text(json.dumps({"teacher": self.record}))
        self.environment = patch.dict(os.environ, {"TEACHERS_FILE": str(self.path)})
        self.environment.start()
        self.original = copy.deepcopy(activities)
        auth.sessions.clear()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        activities.clear()
        activities.update(self.original)
        auth.sessions.clear()
        self.environment.stop()
        self.directory.cleanup()

    def login(self):
        response = self.client.post("/auth/login", json={
            "username": "teacher", "password": "a-long-test-password",
        })
        self.assertEqual(response.status_code, 200)
        return response.json()["access_token"]

    def test_public_view_and_blocked_mutations(self):
        self.assertEqual(self.client.get("/activities").status_code, 200)
        self.assertIn("participants", self.client.get("/activities").json()["Chess Club"])
        for method, action, email in (
            ("POST", "signup", "new@mergington.edu"),
            ("DELETE", "unregister", "michael@mergington.edu"),
        ):
            for headers in ({}, {"Authorization": "Bearer invalid"}):
                response = self.client.request(
                    method, f"/activities/Chess Club/{action}",
                    params={"email": email}, headers=headers,
                )
                self.assertEqual(response.status_code, 401)
        self.assertEqual(activities, self.original)

    def test_teacher_mutations_preserve_validation(self):
        headers = {"Authorization": f"Bearer {self.login()}"}
        url = "/activities/Chess Club"
        params = {"email": "new@mergington.edu"}
        self.assertEqual(self.client.post(f"{url}/signup", params=params, headers=headers).status_code, 200)
        self.assertIn(params["email"], activities["Chess Club"]["participants"])
        self.assertEqual(self.client.post(f"{url}/signup", params=params, headers=headers).status_code, 400)
        self.assertEqual(self.client.delete(f"{url}/unregister", params=params, headers=headers).status_code, 200)
        self.assertEqual(self.client.delete(f"{url}/unregister", params=params, headers=headers).status_code, 400)
        self.assertEqual(self.client.post("/activities/Missing/signup", params=params, headers=headers).status_code, 404)

    def test_wrong_credentials(self):
        for username, password in (("teacher", "wrong"), ("unknown", "a-long-test-password")):
            response = self.client.post("/auth/login", json={"username": username, "password": password})
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], "Invalid username or password")
        self.assertEqual(auth.sessions, {})

    def test_logout_and_expiry_revoke_access(self):
        token = self.login()
        headers = {"Authorization": f"Bearer {token}"}
        self.assertEqual(self.client.post("/auth/logout", headers=headers).status_code, 200)
        self.assertNotIn(token, auth.sessions)
        self.assertEqual(self.client.post("/activities/Chess Club/signup", params={"email": "x"}, headers=headers).status_code, 401)
        token = self.login()
        auth.sessions[token] = ("teacher", time.monotonic() - 1)
        self.assertEqual(self.client.delete(
            "/activities/Chess Club/unregister", params={"email": "michael@mergington.edu"},
            headers={"Authorization": f"Bearer {token}"},
        ).status_code, 401)
        self.assertNotIn(token, auth.sessions)

    def test_missing_and_invalid_credentials_file(self):
        for content in ("not json", "[]", '{"teacher": {}}'):
            self.path.write_text(content)
            with self.assertLogs("src.auth", level="ERROR"):
                self.assertEqual(self.client.post("/auth/login", json={
                    "username": "teacher", "password": "test",
                }).status_code, 503)
        self.path.unlink()
        with self.assertLogs("src.auth", level="ERROR"):
            self.assertEqual(self.client.post("/auth/login", json={
                "username": "teacher", "password": "test",
            }).status_code, 503)

    def test_assign_teacher_stores_only_hash_and_preserves_others(self):
        password = "new-teacher-password"
        with patch("sys.argv", ["manage_teachers", "new-teacher"]), \
                patch("getpass.getpass", side_effect=[password, password]), \
                patch("builtins.print"):
            assign_teacher()
        self.assertNotIn(password, self.path.read_text())
        self.assertEqual(json.loads(self.path.read_text())["teacher"], self.record)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertTrue(auth.authenticate("new-teacher", password))
        with patch("sys.argv", ["manage_teachers", "new-teacher"]), \
                patch("getpass.getpass", side_effect=["replacement-password"] * 2), \
                patch("builtins.print"):
            assign_teacher()
        self.assertFalse(auth.authenticate("new-teacher", password))
        self.assertTrue(auth.authenticate("new-teacher", "replacement-password"))


if __name__ == "__main__":
    unittest.main()
