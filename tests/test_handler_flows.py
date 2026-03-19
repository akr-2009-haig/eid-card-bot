"""Comprehensive handler-flow tests verifying every bot button and message handler.

Each test exercises a specific callback or message handler in isolation, using
lightweight fakes instead of a live Telegram connection.  The goal is to confirm
that every piece of interactive logic reachable through the bot's keyboards
actually functions correctly before the project is handed over.
"""

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from database import db
from handlers import admin as admin_handlers
from handlers import ads as ads_handler
from handlers import forcesub as forcesub_handler_module
from handlers import forcesub_admin as forcesub_admin_handlers
from handlers import start as start_handler_module
from handlers import texts_buttons
from handlers import user as user_handler_module
from utils import rate_limit


# ---------------------------------------------------------------------------
# Shared fake helpers
# ---------------------------------------------------------------------------

class FakeApp:
    """Minimal Pyrogram Client stand-in that collects registered handlers."""

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


class FakeWaitMessage:
    """Returned by FakeMessage.reply() so handlers can call .delete()/.edit_text()."""

    def __init__(self):
        self.edited_text = None
        self.edited_reply_markup = None
        self.deleted = False

    async def edit_text(self, text, reply_markup=None):
        self.edited_text = text
        self.edited_reply_markup = reply_markup

    async def delete(self):
        self.deleted = True


class FakeMessage:
    """Generic fake incoming message (from_user, text, reply())."""

    def __init__(self, user_id, username="", first_name="User", last_name=None, text=""):
        self.from_user = SimpleNamespace(
            id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        self.text = text
        self.reply_calls = []
        self._wait_message = FakeWaitMessage()

    async def reply(self, text, reply_markup=None, quote=False):
        self.reply_calls.append({"text": text, "reply_markup": reply_markup})
        return self._wait_message

    async def copy(self, chat_id):
        pass


class FakeCallbackMessage:
    """Fake message object attached to a CallbackQuery."""

    def __init__(self):
        self.edited_text = None
        self.reply_markup = None
        self.chat = SimpleNamespace(id=999)
        self.reply_calls = []

    async def edit_text(self, text, reply_markup=None):
        self.edited_text = text
        self.reply_markup = reply_markup

    async def edit_reply_markup(self, reply_markup=None):
        self.reply_markup = reply_markup

    async def reply(self, text, reply_markup=None, quote=False):
        self.reply_calls.append({"text": text, "reply_markup": reply_markup})
        return FakeWaitMessage()


class FakeCallback:
    """Fake CallbackQuery."""

    def __init__(self, user_id: int, data: str):
        # Include username / first_name / last_name because several handlers call
        # add_user(user.id, user.username or "", get_full_name(user)).
        self.from_user = SimpleNamespace(
            id=user_id,
            username="",
            first_name="User",
            last_name=None,
        )
        self.data = data
        self.message = FakeCallbackMessage()
        self.answer_calls = []

    async def answer(self, text=None, show_alert=False):
        self.answer_calls.append((text, show_alert))


class FakeUserClient:
    """Minimal Pyrogram Client with send_photo support for card-generation tests."""

    def __init__(self):
        self.sent_photos = []

    async def send_photo(self, chat_id, photo, caption=None, reply_markup=None):
        self.sent_photos.append({"chat_id": chat_id, "photo": photo, "caption": caption})

    async def download_media(self, media, file_name=None):
        return file_name or ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_handler(app: FakeApp, name: str, kind: str = "callback"):
    collection = app.callback_handlers if kind == "callback" else app.message_handlers
    return next(h for h in collection if h.__name__ == name)


# ---------------------------------------------------------------------------
# User start / navigation flow
# ---------------------------------------------------------------------------

class TestUserStartAndNavigation(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DATABASE_PATH
        db.DATABASE_PATH = os.path.join(self.temp_dir.name, "test.db")
        db.init_db()

    async def asyncTearDown(self):
        db.DATABASE_PATH = self.original_db_path
        self.temp_dir.cleanup()

    async def test_start_no_channels_shows_main_menu(self):
        app = FakeApp()
        start_handler_module.register_start_handler(app)
        handler = _get_handler(app, "start_handler", kind="message")

        msg = FakeMessage(user_id=101, username="u1", first_name="Ali")
        await handler(None, msg)

        self.assertEqual(len(msg.reply_calls), 1)
        self.assertIn("أهلاً", msg.reply_calls[0]["text"])
        self.assertIsNotNone(msg.reply_calls[0]["reply_markup"])

    async def test_start_with_channels_not_subscribed_shows_forcesub(self):
        db.add_channel(
            "@testchan", "Test Channel", "channel",
            channel_link="https://t.me/testchan", chat_id="-100123",
        )
        app = FakeApp()
        start_handler_module.register_start_handler(app)
        handler = _get_handler(app, "start_handler", kind="message")

        msg = FakeMessage(user_id=102)
        with patch.object(
            start_handler_module, "check_subscription",
            return_value=(False, [db.get_channels()[0]]),
        ):
            await handler(None, msg)

        self.assertEqual(len(msg.reply_calls), 1)
        self.assertIn("اشتراك", msg.reply_calls[0]["text"])

    async def test_start_with_channels_subscribed_shows_main_menu(self):
        db.add_channel(
            "@testchan", "Test Channel", "channel",
            channel_link="https://t.me/testchan", chat_id="-100123",
        )
        app = FakeApp()
        start_handler_module.register_start_handler(app)
        handler = _get_handler(app, "start_handler", kind="message")

        msg = FakeMessage(user_id=103)
        with patch.object(start_handler_module, "check_subscription", return_value=(True, [])):
            await handler(None, msg)

        self.assertEqual(len(msg.reply_calls), 1)
        self.assertIn("أهلاً", msg.reply_calls[0]["text"])

    async def test_how_to_use_shows_instructions_and_back_button(self):
        app = FakeApp()
        start_handler_module.register_start_handler(app)
        handler = _get_handler(app, "how_to_use_callback")

        cb = FakeCallback(user_id=104, data="how_to_use")
        await handler(None, cb)

        self.assertIn("طريقة الاستخدام", cb.message.edited_text)
        self.assertIsNotNone(cb.message.reply_markup)
        self.assertEqual(len(cb.answer_calls), 1)

    async def test_back_home_no_channels_shows_main_menu(self):
        app = FakeApp()
        start_handler_module.register_start_handler(app)
        handler = _get_handler(app, "back_home_callback")

        cb = FakeCallback(user_id=105, data="back_home")
        await handler(None, cb)

        self.assertIn("أهلاً", cb.message.edited_text)
        self.assertEqual(len(cb.answer_calls), 1)

    async def test_back_home_not_subscribed_shows_forcesub(self):
        db.add_channel(
            "@testchan", "Test Channel", "channel",
            channel_link="https://t.me/testchan", chat_id="-100123",
        )
        app = FakeApp()
        start_handler_module.register_start_handler(app)
        handler = _get_handler(app, "back_home_callback")

        cb = FakeCallback(user_id=106, data="back_home")
        with patch.object(
            start_handler_module, "check_subscription",
            return_value=(False, [db.get_channels()[0]]),
        ):
            await handler(None, cb)

        self.assertIn("اشتراك", cb.message.edited_text)
        self.assertEqual(len(cb.answer_calls), 1)

    async def test_back_home_subscribed_shows_main_menu(self):
        db.add_channel(
            "@testchan", "Test Channel", "channel",
            channel_link="https://t.me/testchan", chat_id="-100123",
        )
        app = FakeApp()
        start_handler_module.register_start_handler(app)
        handler = _get_handler(app, "back_home_callback")

        cb = FakeCallback(user_id=107, data="back_home")
        with patch.object(start_handler_module, "check_subscription", return_value=(True, [])):
            await handler(None, cb)

        self.assertIn("أهلاً", cb.message.edited_text)


# ---------------------------------------------------------------------------
# Design-card and name-input flow
# ---------------------------------------------------------------------------

class TestDesignCardFlow(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DATABASE_PATH
        db.DATABASE_PATH = os.path.join(self.temp_dir.name, "test.db")
        db.init_db()
        user_handler_module._waiting_for_name.clear()
        rate_limit._last_request.clear()

    async def asyncTearDown(self):
        user_handler_module._waiting_for_name.clear()
        rate_limit._last_request.clear()
        db.DATABASE_PATH = self.original_db_path
        self.temp_dir.cleanup()

    async def test_design_card_no_templates_shows_alert(self):
        app = FakeApp()
        user_handler_module.register_user_handlers(app)
        handler = _get_handler(app, "design_card_callback")

        cb = FakeCallback(user_id=201, data="design_card")
        await handler(None, cb)

        self.assertEqual(len(cb.answer_calls), 1)
        answer_text, show_alert = cb.answer_calls[0]
        self.assertIn("لا توجد قوالب", answer_text)
        self.assertTrue(show_alert)

    async def test_design_card_not_subscribed_shows_forcesub(self):
        db.add_channel(
            "@testchan", "Test Channel", "channel",
            channel_link="https://t.me/testchan", chat_id="-100123",
        )
        db.add_template("fid", "some/path.jpg")
        app = FakeApp()
        user_handler_module.register_user_handlers(app)
        handler = _get_handler(app, "design_card_callback")

        cb = FakeCallback(user_id=202, data="design_card")
        with patch.object(
            user_handler_module, "check_subscription",
            return_value=(False, [db.get_channels()[0]]),
        ):
            await handler(None, cb)

        self.assertIn("اشتراك", cb.message.edited_text)
        self.assertEqual(len(cb.answer_calls), 1)

    async def test_design_card_rate_limited_shows_alert(self):
        db.add_template("fid", "some/path.jpg")
        app = FakeApp()
        user_handler_module.register_user_handlers(app)
        handler = _get_handler(app, "design_card_callback")

        # First click – passes rate limit, enters waiting state
        cb1 = FakeCallback(user_id=203, data="design_card")
        await handler(None, cb1)
        user_handler_module._waiting_for_name.discard(203)

        # Second click immediately – should be rate-limited
        cb2 = FakeCallback(user_id=203, data="design_card")
        await handler(None, cb2)

        self.assertEqual(len(cb2.answer_calls), 1)
        answer_text, show_alert = cb2.answer_calls[0]
        self.assertIn("انتظار", answer_text)
        self.assertTrue(show_alert)

    async def test_design_card_success_enters_waiting_for_name(self):
        db.add_template("fid", "some/path.jpg")
        app = FakeApp()
        user_handler_module.register_user_handlers(app)
        handler = _get_handler(app, "design_card_callback")

        cb = FakeCallback(user_id=204, data="design_card")
        await handler(None, cb)

        self.assertIn(204, user_handler_module._waiting_for_name)
        self.assertIn("اسمك", cb.message.edited_text)

    async def test_handle_name_input_not_in_waiting_state_is_ignored(self):
        app = FakeApp()
        user_handler_module.register_user_handlers(app)
        handler = _get_handler(app, "handle_name_input", kind="message")

        msg = FakeMessage(user_id=205, text="محمد")
        await handler(None, msg)

        self.assertEqual(len(msg.reply_calls), 0)

    async def test_handle_name_input_empty_name_is_rejected(self):
        user_handler_module._waiting_for_name.add(206)
        app = FakeApp()
        user_handler_module.register_user_handlers(app)
        handler = _get_handler(app, "handle_name_input", kind="message")

        msg = FakeMessage(user_id=206, text="   ")
        await handler(None, msg)

        # Still waiting – invalid name should not remove from set
        self.assertIn(206, user_handler_module._waiting_for_name)
        self.assertEqual(len(msg.reply_calls), 1)
        self.assertIn("غير صالح", msg.reply_calls[0]["text"])

    async def test_handle_name_input_too_long_name_is_rejected(self):
        user_handler_module._waiting_for_name.add(207)
        app = FakeApp()
        user_handler_module.register_user_handlers(app)
        handler = _get_handler(app, "handle_name_input", kind="message")

        msg = FakeMessage(user_id=207, text="أ" * 51)
        await handler(None, msg)

        self.assertIn(207, user_handler_module._waiting_for_name)
        self.assertEqual(len(msg.reply_calls), 1)
        self.assertIn("غير صالح", msg.reply_calls[0]["text"])

    async def test_handle_name_input_valid_name_generates_and_sends_card(self):
        user_handler_module._waiting_for_name.add(208)

        template_file = os.path.join(self.temp_dir.name, "template.jpg")
        with open(template_file, "wb") as fh:
            fh.write(b"fake_image")
        tpl_id = db.add_template("fid", template_file)

        card_file = os.path.join(self.temp_dir.name, "card.png")
        with open(card_file, "wb") as fh:
            fh.write(b"fake_card")

        app = FakeApp()
        user_handler_module.register_user_handlers(app)
        handler = _get_handler(app, "handle_name_input", kind="message")

        msg = FakeMessage(user_id=208, text="محمد")
        client = FakeUserClient()

        with patch.object(user_handler_module, "generate_card", return_value=card_file), \
             patch.object(user_handler_module, "pick_random_template",
                          return_value=db.get_template(tpl_id)), \
             patch.object(user_handler_module.os, "remove"):
            await handler(client, msg)

        self.assertNotIn(208, user_handler_module._waiting_for_name)
        self.assertEqual(len(client.sent_photos), 1)
        self.assertEqual(client.sent_photos[0]["chat_id"], 208)
        self.assertTrue(msg._wait_message.deleted)

    async def test_handle_name_input_card_error_shows_error_message(self):
        user_handler_module._waiting_for_name.add(209)

        template_file = os.path.join(self.temp_dir.name, "template.jpg")
        with open(template_file, "wb") as fh:
            fh.write(b"fake_image")
        tpl_id = db.add_template("fid", template_file)

        app = FakeApp()
        user_handler_module.register_user_handlers(app)
        handler = _get_handler(app, "handle_name_input", kind="message")

        msg = FakeMessage(user_id=209, text="محمد")
        client = FakeUserClient()

        with patch.object(user_handler_module, "generate_card",
                          side_effect=Exception("test error")), \
             patch.object(user_handler_module, "pick_random_template",
                          return_value=db.get_template(tpl_id)):
            await handler(client, msg)

        self.assertNotIn(209, user_handler_module._waiting_for_name)
        self.assertIn("حدث خطأ", msg._wait_message.edited_text)


# ---------------------------------------------------------------------------
# Force-sub check flow
# ---------------------------------------------------------------------------

class TestCheckSubFlow(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DATABASE_PATH
        db.DATABASE_PATH = os.path.join(self.temp_dir.name, "test.db")
        db.init_db()

    async def asyncTearDown(self):
        db.DATABASE_PATH = self.original_db_path
        self.temp_dir.cleanup()

    async def test_check_sub_no_channels_shows_main_menu(self):
        app = FakeApp()
        forcesub_handler_module.register_forcesub_handler(app)
        handler = _get_handler(app, "check_sub_callback")

        cb = FakeCallback(user_id=301, data="check_sub")
        await handler(None, cb)

        self.assertIn("أهلاً", cb.message.edited_text)
        answer_text, _ = cb.answer_calls[0]
        self.assertIn("تم التحقق", answer_text)

    async def test_check_sub_subscribed_shows_main_menu(self):
        db.add_channel(
            "@testchan", "Test Channel", "channel",
            channel_link="https://t.me/testchan", chat_id="-100123",
        )
        app = FakeApp()
        forcesub_handler_module.register_forcesub_handler(app)
        handler = _get_handler(app, "check_sub_callback")

        cb = FakeCallback(user_id=302, data="check_sub")
        with patch.object(forcesub_handler_module, "check_subscription", return_value=(True, [])):
            await handler(None, cb)

        self.assertIn("أهلاً", cb.message.edited_text)
        answer_text, _ = cb.answer_calls[0]
        self.assertIn("تم التحقق", answer_text)

    async def test_check_sub_still_not_subscribed_shows_error(self):
        db.add_channel(
            "@testchan", "Test Channel", "channel",
            channel_link="https://t.me/testchan", chat_id="-100123",
        )
        channel = db.get_channels()[0]
        app = FakeApp()
        forcesub_handler_module.register_forcesub_handler(app)
        handler = _get_handler(app, "check_sub_callback")

        cb = FakeCallback(user_id=303, data="check_sub")
        with patch.object(
            forcesub_handler_module, "check_subscription",
            return_value=(False, [channel]),
        ):
            await handler(None, cb)

        answer_text, show_alert = cb.answer_calls[0]
        self.assertIn("يجب الاشتراك", answer_text)
        self.assertTrue(show_alert)
        # Keyboard should be refreshed to show missing channels
        self.assertIsNotNone(cb.message.reply_markup)


# ---------------------------------------------------------------------------
# Admin main panel
# ---------------------------------------------------------------------------

class TestAdminMainPanel(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DATABASE_PATH
        db.DATABASE_PATH = os.path.join(self.temp_dir.name, "test.db")
        db.init_db()

    async def asyncTearDown(self):
        db.DATABASE_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def _make_app(self):
        app = FakeApp()
        admin_handlers.register_admin_handler(app)
        return app

    async def test_admin_command_non_admin_denied(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_command", kind="message")

        msg = FakeMessage(user_id=401)
        with patch.object(admin_handlers, "is_admin", return_value=False):
            await handler(None, msg)

        self.assertEqual(len(msg.reply_calls), 1)
        self.assertIn("هذا الأمر للأدمن فقط", msg.reply_calls[0]["text"])

    async def test_admin_command_admin_sees_panel(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_command", kind="message")

        msg = FakeMessage(user_id=402)
        with patch.object(admin_handlers, "is_admin", return_value=True):
            await handler(None, msg)

        self.assertEqual(len(msg.reply_calls), 1)
        self.assertIn("لوحة تحكم", msg.reply_calls[0]["text"])
        self.assertIsNotNone(msg.reply_calls[0]["reply_markup"])

    async def test_admin_back_non_admin_denied(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_back")

        cb = FakeCallback(user_id=403, data="admin_back")
        with patch.object(admin_handlers, "is_admin", return_value=False):
            await handler(None, cb)

        answer_text, show_alert = cb.answer_calls[0]
        self.assertEqual(answer_text, "⛔ ممنوع")
        self.assertTrue(show_alert)

    async def test_admin_back_shows_main_panel(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_back")

        cb = FakeCallback(user_id=404, data="admin_back")
        with patch.object(admin_handlers, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("لوحة تحكم", cb.message.edited_text)
        self.assertIsNotNone(cb.message.reply_markup)

    async def test_admin_stats_shows_counts(self):
        db.add_user(2001, "u", "User")
        db.add_channel("@c", "Chan", "channel")
        db.add_template("fid", "path.jpg")

        app = self._make_app()
        handler = _get_handler(app, "admin_stats")

        cb = FakeCallback(user_id=405, data="admin_stats")
        with patch.object(admin_handlers, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("إحصائيات", cb.message.edited_text)
        self.assertIn("عدد المستخدمين: 1", cb.message.edited_text)
        self.assertIn("عدد القوالب: 1", cb.message.edited_text)
        self.assertIn("عدد قنوات الاشتراك: 1", cb.message.edited_text)

    async def test_admin_templates_menu(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_templates_menu")

        cb = FakeCallback(user_id=406, data="admin_templates")
        with patch.object(admin_handlers, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("قوالب", cb.message.edited_text)
        self.assertIsNotNone(cb.message.reply_markup)

    async def test_admin_forcesub_menu(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_forcesub_menu")

        cb = FakeCallback(user_id=407, data="admin_forcesub")
        with patch.object(admin_handlers, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("الاشتراك الإجباري", cb.message.edited_text)
        self.assertIsNotNone(cb.message.reply_markup)

    async def test_admin_texts_menu(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_texts_menu")

        cb = FakeCallback(user_id=408, data="admin_texts")
        with patch.object(admin_handlers, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("النصوص والأزرار", cb.message.edited_text)
        self.assertIsNotNone(cb.message.reply_markup)

    async def test_admin_buttons_menu(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_buttons_menu")

        cb = FakeCallback(user_id=409, data="admin_buttons")
        with patch.object(admin_handlers, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("الأزرار", cb.message.edited_text)
        self.assertIsNotNone(cb.message.reply_markup)

    async def test_admin_ads_menu(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_ads_menu")

        cb = FakeCallback(user_id=410, data="admin_ads")
        with patch.object(admin_handlers, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("الإعلانات", cb.message.edited_text)
        self.assertIsNotNone(cb.message.reply_markup)

    async def test_admin_edit_text_all_keys_are_handled(self):
        """Every admin_edit_* callback_data value must map to a valid text key."""
        app = self._make_app()
        texts_buttons.register_texts_buttons_handlers(app)

        admin_edit_h = _get_handler(app, "admin_edit_text_cb")
        handle_text_h = _get_handler(app, "handle_admin_text_input", kind="message")

        keys = [
            ("admin_edit_start", "start_message"),
            ("admin_edit_ask_name", "ask_name_message"),
            ("admin_edit_designing", "designing_message"),
            ("admin_edit_card_ready", "card_ready_message"),
            ("admin_edit_forcesub_msg", "forcesub_message"),
        ]
        for callback_data, db_key in keys:
            with self.subTest(callback_data=callback_data):
                texts_buttons._admin_text_state.clear()
                cb = FakeCallback(user_id=1, data=callback_data)
                msg = FakeMessage(user_id=1, text="نص جديد")
                with patch.object(admin_handlers, "is_admin", return_value=True), \
                        patch.object(texts_buttons, "is_admin", return_value=True):
                    await admin_edit_h(None, cb)
                    await handle_text_h(None, msg)
                self.assertEqual(db.get_text(db_key), "نص جديد")
                self.assertIn("✅ تم تحديث النص بنجاح", msg.reply_calls[-1]["text"])


# ---------------------------------------------------------------------------
# Force-sub admin management
# ---------------------------------------------------------------------------

class TestForceSubAdminFlow(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DATABASE_PATH
        db.DATABASE_PATH = os.path.join(self.temp_dir.name, "test.db")
        db.init_db()
        forcesub_admin_handlers._waiting_channel_input.clear()

    async def asyncTearDown(self):
        forcesub_admin_handlers._waiting_channel_input.clear()
        db.DATABASE_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def _make_app(self):
        app = FakeApp()
        forcesub_admin_handlers.register_forcesub_admin_handlers(app)
        return app

    async def test_admin_view_channels_empty(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_view_channels_cb")

        cb = FakeCallback(user_id=501, data="admin_view_channels")
        with patch.object(forcesub_admin_handlers, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("لا توجد قنوات", cb.message.edited_text)

    async def test_admin_view_channels_with_channels_shows_list(self):
        db.add_channel(
            "@testchan", "Test Channel", "channel",
            channel_link="https://t.me/testchan", chat_id="-100123",
        )
        app = self._make_app()
        handler = _get_handler(app, "admin_view_channels_cb")

        cb = FakeCallback(user_id=502, data="admin_view_channels")
        with patch.object(forcesub_admin_handlers, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("القنوات والقروبات الحالية", cb.message.edited_text)
        self.assertIn("Test Channel", cb.message.edited_text)

    async def test_admin_add_channel_enters_waiting_state(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_add_channel_cb")

        cb = FakeCallback(user_id=503, data="admin_add_channel")
        with patch.object(forcesub_admin_handlers, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn(503, forcesub_admin_handlers._waiting_channel_input)
        self.assertIn("أرسل رابط القناة", cb.message.edited_text)

    async def test_admin_delete_channel_no_channels_shows_warning(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_delete_channel_cb")

        cb = FakeCallback(user_id=504, data="admin_delete_channel")
        with patch.object(forcesub_admin_handlers, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("لا توجد قنوات", cb.message.edited_text)

    async def test_admin_delete_channel_shows_selection_keyboard(self):
        db.add_channel(
            "@testchan", "Test Channel", "channel",
            channel_link="https://t.me/testchan", chat_id="-100123",
        )
        app = self._make_app()
        handler = _get_handler(app, "admin_delete_channel_cb")

        cb = FakeCallback(user_id=505, data="admin_delete_channel")
        with patch.object(forcesub_admin_handlers, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("اختر القناة", cb.message.edited_text)
        self.assertIsNotNone(cb.message.reply_markup)

    async def test_admin_del_ch_deletes_channel_and_confirms(self):
        db.add_channel(
            "@testchan", "Test Channel", "channel",
            channel_link="https://t.me/testchan", chat_id="-100123",
        )
        ch_id = db.get_channels()[0]["id"]
        app = self._make_app()
        handler = _get_handler(app, "admin_confirm_delete_channel")

        cb = FakeCallback(user_id=506, data=f"admin_del_ch_{ch_id}")
        with patch.object(forcesub_admin_handlers, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertEqual(len(db.get_channels()), 0)
        self.assertIn("تم حذف القناة", cb.message.edited_text)

    async def test_admin_non_admin_callbacks_denied(self):
        app = self._make_app()
        for cb_name, data in [
            ("admin_add_channel_cb", "admin_add_channel"),
            ("admin_view_channels_cb", "admin_view_channels"),
            ("admin_delete_channel_cb", "admin_delete_channel"),
        ]:
            with self.subTest(cb_name=cb_name):
                handler = _get_handler(app, cb_name)
                cb = FakeCallback(user_id=999, data=data)
                with patch.object(forcesub_admin_handlers, "is_admin", return_value=False):
                    await handler(None, cb)
                answer_text, show_alert = cb.answer_calls[0]
                self.assertEqual(answer_text, "⛔ ممنوع")
                self.assertTrue(show_alert)


# ---------------------------------------------------------------------------
# Texts / Buttons admin flow
# ---------------------------------------------------------------------------

class TestTextsButtonsAdminFlow(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DATABASE_PATH
        db.DATABASE_PATH = os.path.join(self.temp_dir.name, "test.db")
        db.init_db()
        texts_buttons._admin_text_state.clear()
        texts_buttons._waiting_button_input.clear()
        texts_buttons._button_input_data.clear()

    async def asyncTearDown(self):
        texts_buttons._admin_text_state.clear()
        texts_buttons._waiting_button_input.clear()
        texts_buttons._button_input_data.clear()
        db.DATABASE_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def _make_app(self):
        app = FakeApp()
        texts_buttons.register_texts_buttons_handlers(app)
        return app

    async def test_admin_view_buttons_empty(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_view_buttons")

        cb = FakeCallback(user_id=601, data="admin_view_buttons")
        with patch.object(texts_buttons, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("لا توجد أزرار", cb.message.edited_text)

    async def test_admin_view_buttons_shows_existing_buttons(self):
        db.add_button("قناتي", "https://t.me/mychan")
        app = self._make_app()
        handler = _get_handler(app, "admin_view_buttons")

        cb = FakeCallback(user_id=602, data="admin_view_buttons")
        with patch.object(texts_buttons, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("الأزرار الحالية", cb.message.edited_text)
        self.assertIn("قناتي", cb.message.edited_text)
        self.assertIn("https://t.me/mychan", cb.message.edited_text)

    async def test_admin_add_button_wrong_format_rejected(self):
        texts_buttons._waiting_button_input.add(603)
        texts_buttons._button_input_data[603] = {"step": "combined"}
        app = self._make_app()
        handler = _get_handler(app, "handle_admin_text_input", kind="message")

        msg = FakeMessage(user_id=603, text="only one line")
        with patch.object(texts_buttons, "is_admin", return_value=True):
            await handler(None, msg)

        self.assertEqual(len(db.get_buttons()), 0)
        self.assertIn(603, texts_buttons._waiting_button_input)
        self.assertIn("الصيغة غير صحيحة", msg.reply_calls[-1]["text"])

    async def test_admin_add_button_invalid_url_rejected(self):
        texts_buttons._waiting_button_input.add(604)
        texts_buttons._button_input_data[604] = {"step": "combined"}
        app = self._make_app()
        handler = _get_handler(app, "handle_admin_text_input", kind="message")

        msg = FakeMessage(user_id=604, text="زر تجريبي\nftp://bad-scheme")
        with patch.object(texts_buttons, "is_admin", return_value=True):
            await handler(None, msg)

        self.assertEqual(len(db.get_buttons()), 0)
        self.assertIn(604, texts_buttons._waiting_button_input)
        self.assertIn("الرابط غير صالح", msg.reply_calls[-1]["text"])

    async def test_admin_add_button_valid_tg_url_accepted(self):
        texts_buttons._waiting_button_input.add(605)
        texts_buttons._button_input_data[605] = {"step": "combined"}
        app = self._make_app()
        handler = _get_handler(app, "handle_admin_text_input", kind="message")

        msg = FakeMessage(user_id=605, text="شارك\ntg://resolve?domain=testbot")
        with patch.object(texts_buttons, "is_admin", return_value=True):
            await handler(None, msg)

        buttons = db.get_buttons()
        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0]["label"], "شارك")
        self.assertEqual(buttons[0]["url"], "tg://resolve?domain=testbot")

    async def test_admin_delete_button_empty(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_delete_button_cb")

        cb = FakeCallback(user_id=606, data="admin_delete_button")
        with patch.object(texts_buttons, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("لا توجد أزرار", cb.message.edited_text)

    async def test_admin_delete_button_shows_keyboard(self):
        db.add_button("قناتي", "https://t.me/mychan")
        app = self._make_app()
        handler = _get_handler(app, "admin_delete_button_cb")

        cb = FakeCallback(user_id=607, data="admin_delete_button")
        with patch.object(texts_buttons, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertIn("اختر الزر", cb.message.edited_text)
        self.assertIsNotNone(cb.message.reply_markup)

    async def test_admin_del_btn_deletes_button_and_confirms(self):
        db.add_button("قناتي", "https://t.me/mychan")
        btn_id = db.get_buttons()[0]["id"]
        app = self._make_app()
        handler = _get_handler(app, "admin_confirm_delete_button")

        cb = FakeCallback(user_id=608, data=f"admin_del_btn_{btn_id}")
        with patch.object(texts_buttons, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertEqual(len(db.get_buttons()), 0)
        self.assertIn("تم حذف الزر", cb.message.edited_text)


# ---------------------------------------------------------------------------
# Ads / Broadcast admin flow
# ---------------------------------------------------------------------------

class TestAdsAdminFlow(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DATABASE_PATH
        db.DATABASE_PATH = os.path.join(self.temp_dir.name, "test.db")
        db.init_db()
        ads_handler._waiting_broadcast.clear()

    async def asyncTearDown(self):
        ads_handler._waiting_broadcast.clear()
        db.DATABASE_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def _make_app(self):
        app = FakeApp()
        ads_handler.register_ads_handlers(app)
        return app

    async def test_admin_broadcast_users_enters_waiting(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_broadcast_users_cb")

        cb = FakeCallback(user_id=701, data="admin_broadcast_users")
        with patch.object(ads_handler, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertEqual(ads_handler._waiting_broadcast.get(701), "users")
        self.assertIn("أرسل الرسالة", cb.message.edited_text)

    async def test_admin_broadcast_channels_enters_waiting(self):
        app = self._make_app()
        handler = _get_handler(app, "admin_broadcast_channels_cb")

        cb = FakeCallback(user_id=702, data="admin_broadcast_channels")
        with patch.object(ads_handler, "is_admin", return_value=True):
            await handler(None, cb)

        self.assertEqual(ads_handler._waiting_broadcast.get(702), "channels")
        self.assertIn("أرسل الرسالة", cb.message.edited_text)

    async def test_handle_broadcast_not_in_waiting_is_ignored(self):
        app = self._make_app()
        handler = _get_handler(app, "handle_broadcast_message", kind="message")

        msg = FakeMessage(user_id=703)
        with patch.object(ads_handler, "is_admin", return_value=True):
            await handler(None, msg)

        self.assertEqual(len(msg.reply_calls), 0)

    async def test_handle_broadcast_to_users_sends_and_reports(self):
        db.add_user(9001, "u1", "User 1")
        db.add_user(9002, "u2", "User 2")
        ads_handler._waiting_broadcast[704] = "users"

        app = self._make_app()
        handler = _get_handler(app, "handle_broadcast_message", kind="message")

        msg = FakeMessage(user_id=704)
        with patch.object(ads_handler, "is_admin", return_value=True), \
             patch.object(ads_handler, "broadcast_to_users",
                          return_value=(2, 0)) as mock_bcast:
            await handler(None, msg)

        mock_bcast.assert_called_once()
        self.assertIn("تم إرسال الإعلان بنجاح", msg._wait_message.edited_text)
        self.assertIn("تم الإرسال: 2", msg._wait_message.edited_text)
        self.assertIn("فشل: 0", msg._wait_message.edited_text)

    async def test_handle_broadcast_to_channels_no_channels_shows_warning(self):
        ads_handler._waiting_broadcast[705] = "channels"
        app = self._make_app()
        handler = _get_handler(app, "handle_broadcast_message", kind="message")

        msg = FakeMessage(user_id=705)
        with patch.object(ads_handler, "is_admin", return_value=True):
            await handler(None, msg)

        self.assertIn("لا توجد قنوات", msg._wait_message.edited_text)

    async def test_handle_broadcast_to_channels_sends_and_reports(self):
        db.add_channel(
            "@chan1", "Channel 1", "channel",
            channel_link="https://t.me/chan1", chat_id="-100001",
        )
        ads_handler._waiting_broadcast[706] = "channels"
        app = self._make_app()
        handler = _get_handler(app, "handle_broadcast_message", kind="message")

        msg = FakeMessage(user_id=706)
        with patch.object(ads_handler, "is_admin", return_value=True), \
             patch.object(ads_handler, "broadcast_to_channels",
                          return_value=(1, 0)) as mock_bcast:
            await handler(None, msg)

        mock_bcast.assert_called_once()
        self.assertIn("تم إرسال الإعلان بنجاح", msg._wait_message.edited_text)
        self.assertIn("تم الإرسال: 1", msg._wait_message.edited_text)

    async def test_handle_broadcast_non_admin_ignored(self):
        ads_handler._waiting_broadcast[707] = "users"
        app = self._make_app()
        handler = _get_handler(app, "handle_broadcast_message", kind="message")

        msg = FakeMessage(user_id=707)
        with patch.object(ads_handler, "is_admin", return_value=False):
            await handler(None, msg)

        # Non-admin: handler returns early without replying
        self.assertEqual(len(msg.reply_calls), 0)
        # The state must have been left untouched
        self.assertIn(707, ads_handler._waiting_broadcast)


if __name__ == "__main__":
    unittest.main()
