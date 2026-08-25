"""
Unit tests fuer die Ableitung der Geraetekategorie aus dem User-Agent.

Der Zweck der Funktion ist Datensparsamkeit: aus bis zu 500 Zeichen Rohwert wird
ein Wort. Entsprechend pruefen diese Tests zwei Dinge -- dass die gaengigen
Geraeteklassen richtig einsortiert werden, und dass nichts anderes als die vier
erlaubten Werte herauskommen kann.
"""

import pytest

from utils.device_category import (
    CATEGORIES,
    DESKTOP,
    MOBILE,
    TABLET,
    UNKNOWN,
    derive_device_category,
)


# Echte User-Agent-Strings, gekuerzt wo es nichts zur Sache tut.
IOS_SAFARI = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)
IOS_CHROME = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/116.0.5845.177 Mobile/15E148 Safari/604.1"
)
ANDROID_PHONE = (
    "Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)
ANDROID_FIREFOX = "Mozilla/5.0 (Android 14; Mobile; rv:126.0) Gecko/126.0 Firefox/126.0"
IPAD = (
    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.5 Mobile/15E148 Safari/604.1"
)
ANDROID_TABLET = (
    "Mozilla/5.0 (Linux; Android 13; SM-X710) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
WINDOWS_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
MAC_SAFARI = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.4 Safari/605.1.15"
)
LINUX_FIREFOX = "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0"


class TestDeriveDeviceCategory:
    """Test suite fuer derive_device_category."""

    @pytest.mark.parametrize(
        "user_agent",
        [IOS_SAFARI, IOS_CHROME, ANDROID_PHONE, ANDROID_FIREFOX],
        ids=["ios-safari", "ios-chrome", "android-chrome", "android-firefox"],
    )
    def test_mobile_user_agents(self, user_agent):
        assert derive_device_category(user_agent) == MOBILE

    @pytest.mark.parametrize(
        "user_agent",
        [IPAD, ANDROID_TABLET],
        ids=["ipad", "android-tablet"],
    )
    def test_tablet_user_agents(self, user_agent):
        """iPad-Strings enthalten selbst 'Mobile' -- Tablet muss trotzdem gewinnen."""
        assert derive_device_category(user_agent) == TABLET

    @pytest.mark.parametrize(
        "user_agent",
        [WINDOWS_CHROME, MAC_SAFARI, LINUX_FIREFOX],
        ids=["windows-chrome", "mac-safari", "linux-firefox"],
    )
    def test_desktop_user_agents(self, user_agent):
        assert derive_device_category(user_agent) == DESKTOP

    def test_empty_string(self):
        assert derive_device_category("") == UNKNOWN

    def test_whitespace_only(self):
        assert derive_device_category("   \t\n ") == UNKNOWN

    def test_none(self):
        assert derive_device_category(None) == UNKNOWN

    @pytest.mark.parametrize(
        "value",
        [
            "asdfasdf",
            "curl/8.5.0",
            "\x00\x01\x02",
            "'; DROP TABLE usage_events; --",
            "\U0001f600\U0001f4a9",
            "a" * 5000,
        ],
        ids=["muell", "curl", "steuerzeichen", "sql", "emoji", "sehr-lang"],
    )
    def test_garbage_input(self, value):
        assert derive_device_category(value) == UNKNOWN

    @pytest.mark.parametrize(
        "value",
        [123, 4.2, True, [], {}, object()],
        ids=["int", "float", "bool", "liste", "dict", "objekt"],
    )
    def test_non_string_input_does_not_raise(self, value):
        """Der Wert kommt aus einem HTTP-Header; die Funktion darf nie werfen."""
        assert derive_device_category(value) == UNKNOWN

    def test_case_insensitive(self):
        assert derive_device_category(WINDOWS_CHROME.upper()) == DESKTOP
        assert derive_device_category(ANDROID_PHONE.lower()) == MOBILE

    @pytest.mark.parametrize(
        "user_agent",
        [
            IOS_SAFARI,
            IPAD,
            WINDOWS_CHROME,
            ANDROID_TABLET,
            "",
            None,
            "voelliger unfug",
        ],
        ids=["ios", "ipad", "windows", "android-tablet", "leer", "none", "unfug"],
    )
    def test_result_is_always_a_known_short_category(self, user_agent):
        """
        Nichts anderes als die vier Werte darf herauskommen, und alle passen in
        die Spalte usage_events.device_category (VARCHAR(20)).
        """
        result = derive_device_category(user_agent)
        assert result in CATEGORIES
        assert len(result) <= 20

    def test_raw_value_is_not_returned(self):
        """Der Rohwert darf die Funktion unter keinen Umstaenden verlassen."""
        marker = "SM-S911B"
        assert marker not in derive_device_category(ANDROID_PHONE)
