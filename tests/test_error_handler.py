import pytest
import requests_mock
from src.utils.error_handler import (
    send_critical_alert, 
    alert_on_failure, 
    should_send_critical_alert,
    APIAuthenticationError
)

def test_send_critical_alert_success():
    with requests_mock.Mocker() as m:
        m.post("https://api.telegram.org/bot/sendMessage", status_code=200)
        # This shouldn't raise any exception
        send_critical_alert("Test Error", "Test Message")

def test_alert_on_failure_decorator():
    @alert_on_failure("Critical Failure")
    def failing_function():
        raise ValueError("Boom")

    with requests_mock.Mocker() as m:
        m.post("https://api.telegram.org/bot/sendMessage", status_code=200)
        with pytest.raises(ValueError, match="Boom"):
            failing_function()

def test_should_send_critical_alert():
    assert should_send_critical_alert("Auth", Exception("Authentication failed")) is True
    assert should_send_critical_alert("Data", Exception("Some minor error")) is False
    assert should_send_critical_alert("Auth", Exception("API key is expired")) is True
