from graphrag_kb_server.service.validations import (
    check_password,
    generate_hash,
    validate_email,
)


def test_validate_email_success():
    email = "john.doe@gmail.com"
    assert validate_email(email) is True


def test_validate_email_fail():
    email = "john.doe@gmailcom"
    assert validate_email(email) is False


def test_generate_hash():
    password_plain = "password"
    password_hash = generate_hash(password_plain)
    assert password_hash is not None
    assert password_hash != password_plain


def test_check_password():
    password_plain = "password"
    password_hash = generate_hash(password_plain)
    assert check_password(password_plain, password_hash) is True
