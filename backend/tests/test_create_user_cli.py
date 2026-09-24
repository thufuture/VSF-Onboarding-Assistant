from src.cli.create_user import validate


def test_accepts_real_email_and_strong_password() -> None:
    assert validate("thu@example.com", "a-long-password-1") is None


def test_rejects_dev_domain() -> None:
    assert validate("x@vsf-demo.example", "a-long-password-1") is not None


def test_rejects_short_password() -> None:
    assert validate("thu@example.com", "short") is not None


def test_rejects_malformed_email() -> None:
    assert validate("not-an-email", "a-long-password-1") is not None
