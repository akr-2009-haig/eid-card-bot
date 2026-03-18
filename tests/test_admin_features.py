import os
import tempfile
import unittest

from database import db
from utils.telegram_links import normalize_channel_input, resolve_channel_link, resolve_channel_target


class AdminFeatureStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DATABASE_PATH
        db.DATABASE_PATH = os.path.join(self.temp_dir.name, "test.db")
        db.init_db()

    def tearDown(self):
        db.DATABASE_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_init_db_supports_extended_channel_fields(self):
        db.add_channel(
            "@channelname",
            "My Channel",
            "channel",
            channel_link="https://t.me/channelname",
            chat_id="-10012345",
        )
        channels = db.get_channels()
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]["channel_link"], "https://t.me/channelname")
        self.assertEqual(channels[0]["chat_id"], "-10012345")

    def test_init_db_supports_template_placeholder_metadata(self):
        template_id = db.add_template(
            "file-id",
            "data/templates/template.png",
            original_filename="template.png",
            placeholder_x=520,
            placeholder_y=760,
            placeholder_w=120,
            placeholder_h=40,
            font_size=60,
            placeholder_text="[الاسم]",
        )
        template = db.get_template(template_id)
        self.assertEqual(template["original_filename"], "template.png")
        self.assertEqual(template["placeholder_x"], 520)
        self.assertEqual(template["placeholder_text"], "[الاسم]")


class TelegramLinkParsingTests(unittest.TestCase):
    def test_normalize_public_username(self):
        parsed = normalize_channel_input("@channelname")
        self.assertEqual(parsed["lookup_value"], "@channelname")
        self.assertEqual(parsed["channel_link"], "https://t.me/channelname")

    def test_normalize_private_invite_link(self):
        parsed = normalize_channel_input("https://t.me/+AbCdEfGh")
        self.assertEqual(parsed["lookup_value"], "https://t.me/+AbCdEfGh")
        self.assertEqual(parsed["channel_link"], "https://t.me/+AbCdEfGh")

    def test_resolve_channel_helpers(self):
        channel = {
            "channel_username": "@channelname",
            "channel_link": "https://t.me/channelname",
            "chat_id": "-100222",
        }
        self.assertEqual(resolve_channel_link(channel), "https://t.me/channelname")
        self.assertEqual(resolve_channel_target(channel), -100222)


if __name__ == "__main__":
    unittest.main()
