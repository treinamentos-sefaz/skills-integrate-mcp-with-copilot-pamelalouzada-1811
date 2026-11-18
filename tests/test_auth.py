import copy
import stat
import tempfile
import unittest
from http.cookies import SimpleCookie
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, Request, Response

from src import app as app_module
from src.app import TeacherLogin, login_teacher, signup_for_activity, unregister_from_activity
from src.auth import (
    SESSION_COOKIE_NAME,
    _teacher_sessions,
    hash_password,
    load_teacher_hashes,
    require_teacher,
    save_teacher_hashes,
    verify_password,
)


def make_request(cookie: str | None = None) -> Request:
    headers = []
    if cookie:
        headers.append((b"cookie", f"{SESSION_COOKIE_NAME}={cookie}".encode("ascii")))
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": headers,
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
        "scheme": "http",
    }
    return Request(scope)


class TeacherAuthTests(unittest.TestCase):
    def setUp(self):
        self.activities = copy.deepcopy(app_module.activities)
        _teacher_sessions.clear()

    def tearDown(self):
        app_module.activities.clear()
        app_module.activities.update(self.activities)
        _teacher_sessions.clear()

    def test_password_hash_verifies_without_storing_plaintext(self):
        password = "correct horse battery staple"
        encoded_hash = hash_password(password)

        self.assertNotIn(password, encoded_hash)
        self.assertTrue(verify_password(password, encoded_hash))
        self.assertFalse(verify_password("wrong password", encoded_hash))
        self.assertFalse(verify_password(password, "invalid-hash"))

    def test_teacher_hashes_round_trip_to_private_json_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "teachers.json"
            teacher_hashes = {"teacher": hash_password("teacher-password")}

            save_teacher_hashes(teacher_hashes, path)

            self.assertEqual(load_teacher_hashes(path), teacher_hashes)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_invalid_teacher_password_is_rejected(self):
        with patch(
            "src.app.load_teacher_hashes",
            return_value={"teacher": hash_password("correct-password")},
        ):
            with self.assertRaises(HTTPException) as login_error:
                login_teacher(
                    TeacherLogin(username="teacher", password="wrong-password"),
                    Response(),
                )

        self.assertEqual(login_error.exception.status_code, 401)

    def test_anonymous_users_cannot_change_registrations(self):
        with self.assertRaises(HTTPException) as signup_error:
            signup_for_activity("Chess Club", "new@mergington.edu", make_request())
        self.assertEqual(signup_error.exception.status_code, 401)

        with self.assertRaises(HTTPException) as unregister_error:
            unregister_from_activity(
                "Chess Club", "michael@mergington.edu", make_request()
            )
        self.assertEqual(unregister_error.exception.status_code, 401)

    def test_teacher_login_allows_registration_changes(self):
        password = "teacher-password"
        with patch(
            "src.app.load_teacher_hashes",
            return_value={"teacher": hash_password(password)},
        ):
            response = Response()
            login_teacher(
                TeacherLogin(username="teacher", password=password), response
            )

        cookie = SimpleCookie()
        cookie.load(response.headers["set-cookie"])
        session_token = cookie[SESSION_COOKIE_NAME].value
        request = make_request(session_token)

        self.assertEqual(require_teacher(request), "teacher")
        signup_for_activity("Chess Club", "new@mergington.edu", request)
        self.assertIn(
            "new@mergington.edu",
            app_module.activities["Chess Club"]["participants"],
        )
        unregister_from_activity(
            "Chess Club", "new@mergington.edu", request
        )
        self.assertNotIn(
            "new@mergington.edu",
            app_module.activities["Chess Club"]["participants"],
        )


if __name__ == "__main__":
    unittest.main()
