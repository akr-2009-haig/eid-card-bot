import importlib
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from database import db
from handlers import admin as admin_handlers
from handlers import templates as template_handlers
from handlers import texts_buttons
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


class FakeApp:
    def __init__(self):
        self.message_handlers = []
        self.callback_handlers = []

    def on_message(self, *args, **kwargs):
        def decorator(func):
            self.message_handlers.append(func)
            return func

        return decorator

    def on_callback_query(self, *args, **kwargs):
        def decorator(func):
            self.callback_handlers.append(func)
            return func

        return decorator


class FakeCallbackMessage:
    def __init__(self):
        self.edited_text = None
        self.reply_markup = None
        self.chat = SimpleNamespace(id=999)

    async def edit_text(self, text, reply_markup=None):
        self.edited_text = text
        self.reply_markup = reply_markup


class FakeCallback:
    def __init__(self, user_id: int, data: str):
        self.from_user = SimpleNamespace(id=user_id)
        self.data = data
        self.message = FakeCallbackMessage()
        self.answer_calls = []

    async def answer(self, text=None, show_alert=False):
        self.answer_calls.append((text, show_alert))


class FakeReplyMessage:
    def __init__(self, user_id: int, text: str):
        self.from_user = SimpleNamespace(id=user_id)
        self.text = text
        self.reply_calls = []

    async def reply(self, text, reply_markup=None, quote=False):
        self.reply_calls.append(
            {"text": text, "reply_markup": reply_markup, "quote": quote}
        )


class FakeTemplateMessage:
    def __init__(self, user_id: int, message_id: int = 50, photo=None, document=None):
        self.from_user = SimpleNamespace(id=user_id)
        self.id = message_id
        self.photo = photo
        self.document = document
        self.reply_calls = []

    async def reply(self, text, reply_markup=None, quote=False):
        self.reply_calls.append(
            {"text": text, "reply_markup": reply_markup, "quote": quote}
        )


class FakeTemplateClient:
    def __init__(self, download_path: str = ""):
        self.download_path = download_path
        self.sent_photos = []
        self.sent_documents = []

    async def download_media(self, media, file_name=None):
        return self.download_path

    async def send_photo(self, chat_id, photo, caption=None):
        self.sent_photos.append({"chat_id": chat_id, "photo": photo, "caption": caption})

    async def send_document(self, chat_id, document, caption=None):
        self.sent_documents.append({"chat_id": chat_id, "document": document, "caption": caption})


class AdminHandlerFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DATABASE_PATH
        db.DATABASE_PATH = os.path.join(self.temp_dir.name, "test.db")
        db.init_db()
        texts_buttons._admin_text_state.clear()
        texts_buttons._waiting_button_input.clear()
        texts_buttons._button_input_data.clear()
        template_handlers._waiting_template_upload.clear()

    async def asyncTearDown(self):
        texts_buttons._admin_text_state.clear()
        texts_buttons._waiting_button_input.clear()
        texts_buttons._button_input_data.clear()
        template_handlers._waiting_template_upload.clear()
        db.DATABASE_PATH = self.original_db_path
        self.temp_dir.cleanup()

    async def test_admin_edit_text_callback_updates_text_via_texts_buttons_state(self):
        app = FakeApp()
        admin_handlers.register_admin_handler(app)
        texts_buttons.register_texts_buttons_handlers(app)

        admin_edit_text_cb = next(
            handler for handler in app.callback_handlers if handler.__name__ == "admin_edit_text_cb"
        )
        handle_admin_text_input = next(
            handler for handler in app.message_handlers if handler.__name__ == "handle_admin_text_input"
        )

        callback = FakeCallback(user_id=1, data="admin_edit_start")
        message = FakeReplyMessage(user_id=1, text="رسالة بداية جديدة")

        with patch.object(admin_handlers, "is_admin", return_value=True), patch.object(
            texts_buttons, "is_admin", return_value=True
        ):
            await admin_edit_text_cb(None, callback)
            await handle_admin_text_input(None, message)

        self.assertIn("✏️ أرسل رسالة البداية الجديدة", callback.message.edited_text)
        self.assertEqual(db.get_text("start_message"), "رسالة بداية جديدة")
        self.assertEqual(message.reply_calls[-1]["text"], "✅ تم تحديث النص بنجاح")

    async def test_admin_add_button_flow_saves_button_and_confirms(self):
        app = FakeApp()
        texts_buttons.register_texts_buttons_handlers(app)

        admin_add_button_cb = next(
            handler for handler in app.callback_handlers if handler.__name__ == "admin_add_button_cb"
        )
        handle_admin_text_input = next(
            handler for handler in app.message_handlers if handler.__name__ == "handle_admin_text_input"
        )

        callback = FakeCallback(user_id=1, data="admin_add_button")
        message = FakeReplyMessage(user_id=1, text="قناة البوت\nhttps://t.me/mychannel")

        with patch.object(texts_buttons, "is_admin", return_value=True):
            await admin_add_button_cb(None, callback)
            await handle_admin_text_input(None, message)

        buttons = db.get_buttons()
        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0]["label"], "قناة البوت")
        self.assertEqual(buttons[0]["url"], "https://t.me/mychannel")
        self.assertIn("✅ تم إضافة الزر بنجاح", message.reply_calls[-1]["text"])

    async def test_admin_add_template_flow_reports_storage_and_ocr_details(self):
        app = FakeApp()
        template_handlers.register_template_handlers(app)

        admin_add_template_cb = next(
            handler for handler in app.callback_handlers if handler.__name__ == "admin_add_template"
        )
        receive_template_photo = next(
            handler for handler in app.message_handlers if handler.__name__ == "receive_template_photo"
        )

        callback = FakeCallback(user_id=1, data="admin_add_template")
        message = FakeTemplateMessage(
            user_id=1,
            photo=SimpleNamespace(file_id="photo-file-id"),
        )
        client = FakeTemplateClient(download_path=os.path.join(self.temp_dir.name, "template_upload.jpg"))
        saved_path = os.path.join(self.temp_dir.name, "template_saved.png")
        with open(client.download_path, "wb") as downloaded_file:
            downloaded_file.write(b"downloaded")

        with patch.object(template_handlers, "is_admin", return_value=True), patch.object(
            template_handlers, "save_template_file", return_value=saved_path
        ), patch.object(
            template_handlers,
            "register_template",
            return_value=(
                7,
                {
                    "placeholder_x": 520,
                    "placeholder_y": 760,
                    "placeholder_w": 120,
                    "placeholder_h": 40,
                    "font_size": 60,
                    "placeholder_text": "[الاسم]",
                },
            ),
        ), patch.object(template_handlers.os, "remove") as remove_mock:
            await admin_add_template_cb(None, callback)
            await receive_template_photo(client, message)

        self.assertIn("PNG أو JPG أو JPEG", callback.message.edited_text)
        self.assertIn("data/templates/template_saved.png", message.reply_calls[-1]["text"])
        self.assertIn("🔎 OCR: تم اكتشاف موضع الاسم تلقائيًا", message.reply_calls[-1]["text"])
        self.assertIn("X=520 | Y=760", message.reply_calls[-1]["text"])
        remove_mock.assert_called_once_with(client.download_path)

    async def test_admin_view_templates_lists_random_selection_and_metadata(self):
        app = FakeApp()
        template_handlers.register_template_handlers(app)
        admin_view_templates = next(
            handler for handler in app.callback_handlers if handler.__name__ == "admin_view_templates"
        )

        template_path = os.path.join(self.temp_dir.name, "template1.jpg")
        with open(template_path, "wb") as template_file:
            template_file.write(b"template")
        db.add_template(
            "file-id",
            template_path,
            original_filename="eid_template_gold.jpg",
            placeholder_x=540,
            placeholder_y=820,
            placeholder_w=110,
            placeholder_h=44,
            font_size=60,
            placeholder_text="[الاسم]",
        )

        callback = FakeCallback(user_id=1, data="admin_view_templates")
        client = FakeTemplateClient()

        with patch.object(template_handlers, "is_admin", return_value=True):
            await admin_view_templates(client, callback)

        self.assertIn("عدد القوالب: 1", callback.message.edited_text)
        self.assertIn("اختيار قالب عشوائي", callback.message.edited_text)
        self.assertEqual(len(client.sent_photos), 1)
        self.assertIn("eid_template_gold.jpg", client.sent_photos[0]["caption"])
        self.assertIn("🔎 OCR: تم اكتشاف موضع الاسم تلقائيًا", client.sent_photos[0]["caption"])
        self.assertIn("data/templates/template1.jpg", client.sent_photos[0]["caption"])

    async def test_admin_delete_template_flow_removes_file_and_confirms_database_update(self):
        app = FakeApp()
        template_handlers.register_template_handlers(app)
        admin_confirm_delete_template = next(
            handler for handler in app.callback_handlers if handler.__name__ == "admin_confirm_delete_template"
        )

        template_path = os.path.join(self.temp_dir.name, "delete_me.png")
        with open(template_path, "wb") as template_file:
            template_file.write(b"template")
        template_id = db.add_template(
            "file-id",
            template_path,
            original_filename="eid_template_gold.png",
        )
        callback = FakeCallback(user_id=1, data=f"admin_del_tpl_{template_id}")

        with patch.object(template_handlers, "is_admin", return_value=True):
            await admin_confirm_delete_template(None, callback)

        self.assertIsNone(db.get_template(template_id))
        self.assertFalse(os.path.exists(template_path))
        self.assertIn("eid_template_gold.png", callback.message.edited_text)
        self.assertIn("تم تحديث قاعدة البيانات", callback.message.edited_text)


if __name__ == "__main__":
    unittest.main()
