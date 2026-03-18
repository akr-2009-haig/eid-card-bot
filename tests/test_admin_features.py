import importlib
import os
import tempfile
import unittest
from types import SimpleNamespace

from database import db
from main import validate_runtime_config
from utils.helpers import get_full_name
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

    def test_add_user_updates_missing_profile_fields(self):
        db.add_user(1001, "", "")
        db.add_user(1001, "eid_user", "محمد أحمد")
        user = db.get_user(1001)
        self.assertEqual(user["username"], "eid_user")
        self.assertEqual(user["full_name"], "محمد أحمد")

    def test_add_user_preserves_existing_profile_fields_when_new_values_are_blank(self):
        db.add_user(1002, "eid_user", "محمد أحمد")
        db.add_user(1002, "", "")
        user = db.get_user(1002)
        self.assertEqual(user["username"], "eid_user")
        self.assertEqual(user["full_name"], "محمد أحمد")


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


class RuntimeConfigTests(unittest.TestCase):
    def test_config_reads_all_environment_variables_and_applies_type_conversions(self):
        original_values = {
            key: os.environ.get(key)
            for key in (
                "BOT_TOKEN",
                "API_ID",
                "API_HASH",
                "ADMIN_IDS",
                "STORAGE_DIR",
                "DATABASE_PATH",
                "TEMPLATES_DIR",
                "FONTS_DIR",
                "GENERATED_DIR",
                "LOG_FILE",
                "FONT_PATH",
            )
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            env_updates = {
                "BOT_TOKEN": "999999:XYZ",
                "API_ID": "67890",
                "API_HASH": "render-hash",
                "ADMIN_IDS": "1, 2,invalid,3",
                "STORAGE_DIR": temp_dir,
                "DATABASE_PATH": os.path.join(temp_dir, "custom", "bot.db"),
                "TEMPLATES_DIR": os.path.join(temp_dir, "templates"),
                "FONTS_DIR": os.path.join(temp_dir, "fonts"),
                "GENERATED_DIR": os.path.join(temp_dir, "generated"),
                "LOG_FILE": os.path.join(temp_dir, "logs", "bot.log"),
                "FONT_PATH": os.path.join(temp_dir, "fonts", "arabic.ttf"),
            }
            os.environ.update(env_updates)

            try:
                import config
                reloaded_config = importlib.reload(config)
                self.assertEqual(reloaded_config.BOT_TOKEN, "999999:XYZ")
                self.assertEqual(reloaded_config.API_ID, 67890)
                self.assertEqual(reloaded_config.API_HASH, "render-hash")
                self.assertEqual(reloaded_config.ADMIN_IDS, [1, 2, 3])
                self.assertEqual(reloaded_config.DATABASE_PATH, env_updates["DATABASE_PATH"])
                self.assertEqual(reloaded_config.TEMPLATES_DIR, env_updates["TEMPLATES_DIR"])
                self.assertEqual(reloaded_config.FONTS_DIR, env_updates["FONTS_DIR"])
                self.assertEqual(reloaded_config.GENERATED_DIR, env_updates["GENERATED_DIR"])
                self.assertEqual(reloaded_config.LOG_FILE, env_updates["LOG_FILE"])
                self.assertEqual(reloaded_config.FONT_PATH, env_updates["FONT_PATH"])
            finally:
                for key, value in original_values.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
                import config
                importlib.reload(config)

    def test_get_full_name_joins_first_and_last_name(self):
        user = SimpleNamespace(first_name="محمد", last_name="أحمد")
        self.assertEqual(get_full_name(user), "محمد أحمد")

    def test_get_full_name_handles_missing_last_name(self):
        user = SimpleNamespace(first_name="محمد", last_name=None)
        self.assertEqual(get_full_name(user), "محمد")

    def test_validate_runtime_config_detects_placeholders(self):
        missing = validate_runtime_config("YOUR_BOT_TOKEN_HERE", 0, "")
        self.assertEqual(missing, ["BOT_TOKEN", "API_ID", "API_HASH"])

    def test_validate_runtime_config_accepts_complete_values(self):
        missing = validate_runtime_config("123456:ABC", 12345, "hash")
        self.assertEqual(missing, [])

    def test_config_admin_ids_falls_back_when_environment_value_has_no_valid_ids(self):
        original_admin_ids = os.environ.get("ADMIN_IDS")

        try:
            for value in (" , invalid , ", "   "):
                with self.subTest(admin_ids=value):
                    os.environ["ADMIN_IDS"] = value
                    import config
                    reloaded_config = importlib.reload(config)
                    self.assertEqual(reloaded_config.ADMIN_IDS, reloaded_config.DEFAULT_ADMIN_IDS)
        finally:
            if original_admin_ids is None:
                os.environ.pop("ADMIN_IDS", None)
            else:
                os.environ["ADMIN_IDS"] = original_admin_ids
            import config
            importlib.reload(config)


if __name__ == "__main__":
    unittest.main()
