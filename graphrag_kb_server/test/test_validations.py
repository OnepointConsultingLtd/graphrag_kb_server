from graphrag_kb_server.service.validations import validate_email


def test_validate_email_success():
    email = "john.doe@gmail.com"
    assert validate_email(email) is True


def test_validate_email_fail():
    email = "john.doe@gmailcom"
    assert validate_email(email) is False
