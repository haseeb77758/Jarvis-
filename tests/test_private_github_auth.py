"""No-network security regressions for private GitHub Jarvis update access."""
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request
from unittest.mock import Mock, patch
import io
import json
import tempfile
import unittest

from tools import update_windows as u


class GitHubAuthTests(unittest.TestCase):
    def test_non_logged_in_user_gets_actionable_error_not_generic_internet_error(self):
        with patch.object(u, "github_cli", return_value=None):
            with self.assertRaisesRegex(u.GitHubAuthenticationRequired, "PRIVATE GITHUB ACCESS"):
                u.github_auth_token()

    def test_login_token_is_only_in_memory(self):
        completed = Mock(returncode=0, stdout="ghp_fake_testing_only_abcdefghijk\\n")
        with patch.object(u, "github_cli", return_value="C:/Test/gh.exe"), \
             patch.object(u.subprocess, "run", return_value=completed) as run:
            token = u.github_auth_token()
        self.assertTrue(token.startswith("ghp_"))
        self.assertEqual(run.call_args.args[0][:3], ["C:/Test/gh.exe", "auth", "token"])
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(run.call_args.kwargs["stderr"], u.subprocess.DEVNULL)

    def test_request_requires_api_github_host(self):
        with self.assertRaisesRegex(u.UpdateError, "official GitHub"):
            u._request("https://example.com/untrusted", 100, 1)

    def test_private_repo_404_has_auth_message(self):
        fake_http_error = HTTPError(u.LATEST_URL, 404, "Not Found", {}, None)
        transport = Mock()
        transport.open.side_effect = fake_http_error
        with patch.object(u, "github_auth_token", return_value="dummy_valid_test_token"), \
             patch.object(u, "build_opener", return_value=transport):
            with self.assertRaisesRegex(u.GitHubAuthenticationRequired, "HTTP 404"):
                u.latest_commit()

    def test_remote_archives_use_approved_sha_authenticated_api(self):
        sha = "a"*40
        fake = Mock()
        fake.return_value = b"not-a-zip"
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            python = root / ".venv" / "Scripts" / "python.exe"
            python.parent.mkdir(parents=True)
            python.write_bytes(b"fake")
            with patch.object(u, "_request", fake):
                with self.assertRaises(u.UpdateError):
                    u.install_update(root, sha)
            self.assertEqual(
                fake.call_args.args[0],
                "https://api.github.com/repos/haseeb77758/Jarvis-/zipball/" + sha
            )

    def test_cross_host_redirect_drops_authorization(self):
        redirect = u.SafeGitHubRedirect()
        request = Request(
            "https://api.github.com/repos/haseeb77758/Jarvis-/zipball/" + "a"*40,
            headers={"Authorization": "Bearer TEST_ONLY"}
        )
        moved = redirect.redirect_request(
            request, None, 302, "Found", {},
            "https://codeload.github.com/haseeb77758/Jarvis-/legacy.zip/" + "a"*40
        )
        self.assertFalse(moved.has_header("Authorization"))
        with self.assertRaisesRegex(u.UpdateError, "untrusted host"):
            redirect.redirect_request(
                request, None, 302, "Found", {},
                "https://malicious.example/file.zip"
            )


if __name__ == "__main__":
    unittest.main()
