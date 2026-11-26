import asyncio
import html
import random
import time
import datetime
import aiohttp
import re
import os
import dns.resolver

from pyrogram import Client, filters, idle, enums
from pyrogram.types import Message, CallbackQuery, ChatJoinRequest
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web
from bson.objectid import ObjectId

# ================= SAFE PVP FALLBACK =================
try:
    from pvp import MODES, Match
except ImportError:
    print("⚠️ WARNING: pvp.py not found! Using built-in fallback Match engine.")
    MODES = {
        "normal": {"rolls": 1, "low_wins": False},
        "crazy": {"rolls": 1, "low_wins": True},
        "double": {"rolls": 2, "low_wins": False},
        "double_crazy": {"rolls": 2, "low_wins": True},
        "triple": {"rolls": 3, "low_wins": False},
        "triple_crazy": {"rolls": 3, "low_wins": True},
    }

    class Match:
        def __init__(self, game: str, mode: str, target: int, stake: float, players: tuple[int, int]):
            self.game = game
            self.mode = mode
            self.target = int(target)
            self.stake = float(stake)
            self.players = players
            cfg = MODES.get(mode, MODES["normal"])
            self.rolls_needed = cfg["rolls"]
            self.low_wins = cfg["low_wins"]
            self.score = [0, 0]
            self.winner = None

        def play_round(self, mine: list[int], theirs: list[int]):
            s_mine = sum(mine)
            s_theirs = sum(theirs)
            if s_mine == s_theirs:
                return None
            if self.low_wins:
                round_win = 0 if s_mine < s_theirs else 1
            else:
                round_win = 0 if s_mine > s_theirs else 1
            self.score[round_win] += 1
            if self.score[0] >= self.target:
                self.winner = 0
            elif self.score[1] >= self.target:
                self.winner = 1
            return round_win

# ================= PYROGRAM ASYNCIO FIX =================
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# ================= PYDROID 3 / ANDROID DNS FIX =================
try:
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ["8.8.8.8", "8.8.4.4"]
except Exception:
    pass

# ================= CONFIGURATION =================
BOT_TOKEN = "9102679894:AAE3zU6FT7ZbvAMzvIGyXZdGpdUoa1letJQ"

HELPER_BOT_TOKEN_1 = "9018656267:AAGi8Jv4g11t_0qy6E1_paI_SMfWXmtwK90"
HELPER_BOT_TOKEN_2 = "9202520474:AAEjlEB_KW08g6Y04sKS8UarRDEd45FwW40"
HELPER_BOT_TOKEN_3 = "9061949019:AAGg0-gz0Y_Nh_HxAEqhSkBtdy38t_DASRg"
ACTIVE_HELPER_TOKENS = [
    t.strip()
    for t in [HELPER_BOT_TOKEN_1, HELPER_BOT_TOKEN_2, HELPER_BOT_TOKEN_3]
    if t and t.strip()
]

API_ID = 35831190
API_HASH = "f625657330797a7f149855cbdfcf9dae"
MONGO_URI = "mongodb+srv://Cricket_231:Rohit1616%40@zolmdho.mongodb.net/?appName=Cluster0"
OWNER_ID = 8686340235
TRACK_GROUP_ID = -1003946482336
REQUIRED_USERNAME_TAG = "@redcube"
FSUB_CHANNEL = "@redcube_en"
GROUP_INVITE_LINK = "https://t.me/+2PY5iAWv_lBhZGQ8"
WIN_LOG_CHANNEL_ID = -1003954075033
BANNED_PROMOS = ["@raika", "@dices", "@booplay", "@axoms", "casino"]
CASINO_NAME = "@Redcube"

BONUS_COOLDOWN_SECONDS = 4 * 3600  # 4 hours
BASE_BONUS_COINS = 1500
EXTRA_REF_COINS = 250

# ================= HTTP SESSION & GAME STATE =================
HTTP_SESSION: aiohttp.ClientSession | None = None
BOT_USERNAME: str = ""
BOT_ID: int = 0
_helper_rr_index: int = 0

matches: dict[str, dict] = {}
user_match: dict[int, str] = {}
msg_owner: dict[tuple[int, int], int] = {}
busy: set[int] = set()
user_last_dice_time = {}
user_names: dict[int, str] = {}
auth_groups_cache: set[int] = set()
bot_banned_cache: set[int] = set()
mines_sessions = {}
pending_join_requests: dict[int, dict] = {}
giveaway_wizard: dict[int, dict] = {}
giveaway_captcha_sessions: dict[tuple[int, str], dict] = {}

# ================= PREMIUM EMOJIS DATA =================
PREMIUM_EMOJIS = {
    "✅": "5123248930124989216", "❌": "5210952531676504517",
    "⚠️": "5420323339723881652", "💰": "5893473283696759404",
    "⛓️": "6021344879689341042", "📊": "5895444149699612825",
    "👥": "6021690418398239007", "🤖": "5258093637450866522",
    "💡": "6023897907034330805", "🎟": "6021617983774791539",
    "👨‍💻": "5444965061749644170", "🔐": "6019568309417023812",
    "🎉": "6023579259115674297", "⏱": "6034973034257848185",
    "🎁": "6023826881160157558", "🏆": "5893376775781617954",
    "📅": "6023880246128810031", "🛡": "6019328362479097179",
    "👑": "6021428854889913572", "📈": "5938539885907415367",
    "✏️": "5879841310902324730", "🏦": "5332455502917949981",
    "📍": "6023989024765516223", "🆕": "5886306834410640699",
    "👋": "5247133031235329609", "🌐": "6019205852831947754",
    "➡️": "5807462045288766810", "🇬🇧": "5395560546865013953",
    "🇷🇺": "5267224089382116952", "🇮🇳": "6129782715035163979",
    "💎": "5298988357538328017", "🏠": "5258503720928288433",
    "📢": "5938589252328624108", "🔙": "5255703720078879038",
    "💧": "5334757303667232230", "🌧": "5393512611968995988",
    "⛈": "5224257782013769471", "🌩": "5089144476023128742",
    "🌨": "5839380464116175529", "🌦": "5258362837411045098",
    "☔": "5348289410955754971", "🎮": "5258508428212445001",
    "🎲": "5960608239623082921", "👎": "5084577224980431440",
    "🤝": "5974565221182741203", "🪙": "4918300654197277832",
    "1️⃣": "5393089050884202480", "2️⃣": "5361902709232377443",
    "👤": "4913497231492908158", "🌊": "5262553290972875718",
    "💀": "5042209657527993345", "⭕️": "5435993158536143379",
    "💼": "5938492039971737551", "ℹ️": "6028435952299413210",
    "ℹ": "6028435952299413210", "⏳": "6113844439292054570",
    "💸": "5798678875823153004", "📥": "5879841310902324730",
    "📤": "5879841310902324730", "🔄": "6030657343744644592",
    "🔁": "6030657343744644592", "💬": "6034831751308644168",
    "🎰": "5258356394959957754", "💣": "5879841310902324730",
    "🔒": "5879841310902324730", "💲": "5879841310902324730",
    "⭐": "5879841310902324730", "🌀": "5879841310902324730",
    "🔴": "5879841310902324730", "⚫": "5879841310902324730",
    "🟢": "5879841310902324730", "⬆️": "5879841310902324730",
    "🖼": "5879841310902324730", "⚙️": "5879841310902324730"
}


def pe(emoji_char: str) -> str:
    eid = PREMIUM_EMOJIS.get(emoji_char)
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{emoji_char}</tg-emoji>'
    return emoji_char


def get_game_emo(game: str) -> str:
    mapping = {"dice": "🎲", "basket": "🏀", "bask": "🏀", "football": "⚽", "bowl": "🎳", "dart": "🎯", "slot": "🎰"}
    return mapping.get(game, "🎲")


def game_pe(game: str) -> str:
    return pe(get_game_emo(game))


def usd(amount: float) -> str:
    return f"{amount:,.2f}"


def get_mode_label(mode: str) -> str:
    labels = {"normal": "Normal", "crazy": "Crazy", "double": "Double", "double_crazy": "Double Crazy", "triple": "Triple", "triple_crazy": "Triple Crazy"}
    return labels.get(mode, "Normal")


def calc_mines_mult(mines, hits):
    if hits == 0:
        return 1.0
    mult = 0.96
    for i in range(hits):
        mult *= (25.0 - i) / (25.0 - mines - i)
    return round(mult, 2)


def calc_bonus_coins(ref_count: int) -> int:
    if ref_count <= 0:
        return BASE_BONUS_COINS
    return BASE_BONUS_COINS + (ref_count * EXTRA_REF_COINS)


def mention(uid: int, name: str = None) -> str:
    label = name or user_names.get(uid) or "Player"
    return f'<a href="tg://user?id={uid}">{html.escape(str(label))}</a>'


def _pick_helper_token() -> str | None:
    global _helper_rr_index
    if not ACTIVE_HELPER_TOKENS:
        return None
    tok = ACTIVE_HELPER_TOKENS[_helper_rr_index % len(ACTIVE_HELPER_TOKENS)]
    _helper_rr_index += 1
    return tok


# ================= HTTP REQUEST ENGINE =================
async def get_session() -> aiohttp.ClientSession:
    global HTTP_SESSION
    if HTTP_SESSION is None or HTTP_SESSION.closed:
        connector = aiohttp.TCPConnector(limit=500, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=10, connect=4)
        HTTP_SESSION = aiohttp.ClientSession(connector=connector, timeout=timeout)
    return HTTP_SESSION


api_semaphore = asyncio.Semaphore(50)


async def tg(method: str, use_helper: bool = False, helper_token: str | None = None, retries: int = 1, **params):
    async with api_semaphore:
        clean = {k: v for k, v in params.items() if v is not None}
        tok = BOT_TOKEN
        if helper_token:
            tok = helper_token
        elif use_helper and ACTIVE_HELPER_TOKENS:
            tok = _pick_helper_token() or BOT_TOKEN
        base = f"https://api.telegram.org/bot{tok}/"
        req_timeout = 6
        for attempt in range(retries + 1):
            try:
                s = await get_session()
                async with s.post(base + method, json=clean, timeout=req_timeout) as r:
                    res = await r.json()
                    if res.get("ok"):
                        return res["result"]
                    retry_after = res.get("parameters", {}).get("retry_after")
                    if retry_after and attempt < retries:
                        await asyncio.sleep(min(float(retry_after), 2.0))
                        continue
                    raise RuntimeError(res.get("description", str(res)))
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                if attempt < retries:
                    await asyncio.sleep(0.15)
                    continue
                raise RuntimeError(f"Network timeout on {method}: {e}")


# ================= BUTTON & KEYBOARD GENERATORS =================
def btn(text: str, data: str = None, style: str = None, url: str = None, icon: str = None) -> dict:
    b = {"text": str(text)}
    if url:
        b["url"] = str(url)
    else:
        b["callback_data"] = str(data) if data else "noop"
    if style:
        b["style"] = style
    if icon and icon in PREMIUM_EMOJIS:
        b["icon_custom_emoji_id"] = PREMIUM_EMOJIS[icon]
    return b


def kb(*rows) -> dict:
    board = []
    for row in rows:
        r = []
        for item in row:
            if isinstance(item, dict):
                r.append(item)
            elif len(item) >= 4:
                r.append(btn(item[0], item[1], style=item[2], icon=item[3]))
            elif len(item) == 3:
                r.append(btn(item[0], item[1], style=item[2]))
            elif len(item) == 2:
                r.append(btn(item[0], item[1]))
            elif len(item) == 1:
                r.append(btn(item[0], item[0]))
        if r:
            board.append(r)
    return {"inline_keyboard": board}


async def send_msg(chat_id: int, text: str, markup=None, parse_mode="HTML", reply_to: int = None, owner_id: int = None, disable_web_page_preview=True):
    try:
        res = await tg("sendMessage", chat_id=chat_id, text=text, reply_markup=markup, parse_mode=parse_mode, reply_to_message_id=reply_to, disable_web_page_preview=disable_web_page_preview)
        if owner_id and res and "message_id" in res:
            msg_owner[(chat_id, res["message_id"])] = owner_id
        return res
    except Exception as e:
        if reply_to is not None:
            try:
                res = await tg("sendMessage", chat_id=chat_id, text=text, reply_markup=markup, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
                if owner_id and res and "message_id" in res:
                    msg_owner[(chat_id, res["message_id"])] = owner_id
                return res
            except Exception as e2:
                print(f"[send_msg retry error] chat={chat_id}: {e2}")
                return None
        print(f"[send_msg error] chat={chat_id}: {e}")
        return None


async def send_photo_msg(chat_id: int, photo: str, caption: str = "", markup=None, parse_mode="HTML", reply_to: int = None):
    try:
        res = await tg("sendPhoto", chat_id=chat_id, photo=photo, caption=caption, reply_markup=markup, parse_mode=parse_mode, reply_to_message_id=reply_to)
        return res
    except Exception as e:
        print(f"[send_photo_msg error] chat={chat_id}: {e}")
        return await send_msg(chat_id, caption, markup=markup, parse_mode=parse_mode, reply_to=reply_to)


async def edit_msg(chat_id: int, message_id: int, text: str, markup=None, parse_mode="HTML", owner_id: int = None, disable_web_page_preview=True):
    try:
        res = await tg("editMessageText", chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
        if owner_id:
            msg_owner[(chat_id, message_id)] = owner_id
        return res
    except Exception as e:
        err_str = str(e).lower()
        if "message is not modified" in err_str or "message_not_modified" in err_str:
            return None
        return await send_msg(chat_id, text, markup=markup, parse_mode=parse_mode, owner_id=owner_id, disable_web_page_preview=disable_web_page_preview)


async def edit_giveaway_post(chat_id: int, message_id: int, text: str, markup=None, is_photo: bool = False):
    try:
        if is_photo:
            return await tg("editMessageCaption", retries=0, chat_id=chat_id, message_id=message_id, caption=text, reply_markup=markup, parse_mode="HTML")
        return await tg("editMessageText", retries=0, chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True)
    except Exception:
        return None


async def clear_buttons(chat_id: int, message_id: int):
    if not message_id:
        return
    try:
        await tg("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id, reply_markup=None, retries=0)
    except Exception:
        pass


async def del_msg(chat_id: int, message_id: int):
    try:
        await tg("deleteMessage", chat_id=chat_id, message_id=message_id, retries=0)
    except Exception:
        pass


async def answer_cb(cb_id: str, text: str = None, show_alert: bool = True):
    try:
        await tg("answerCallbackQuery", callback_query_id=cb_id, text=text, show_alert=show_alert, retries=0)
    except Exception:
        pass


# ================= INITIALIZATION =================
app = Client(
    "my_advanc97678e6d_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    sleep_threshold=30
)

client = AsyncIOMotorClient(MONGO_URI, maxPoolSize=500, minPoolSize=20, serverSelectionTimeoutMS=5000)
db = client["Advanced56BotDB"]
users_db = db["users"]
admins_db = db["admins"]
config_db = db["config"]
activity_db = db["activity"]
auth_groups_db = db["authorized_groups"]
rain_db = db["rain_events"]
games_db = db["games"]
giveaways_db = db["giveaways"]

user_states = {}
active_tickets = {}
pending_tickets = {}
user_langs = {}

admin_ticket_msgs = {}
admin_withdraw_msgs = {}

processed_msgs = {}
processed_cbs = {}
ldb_cache = {}
ADMIN_CACHE = {"data": [], "time": 0}
CONFIG_CACHE = {"data": None, "time": 0}

# ================= LANGUAGE DICTIONARY =================
TR = {
    "en": {
        "welcome_head": f"Welcome <b>{{name}}</b>! {pe('👋')}\n\n",
        "welcome": f"{pe('✅')} <b>Welcome to the Tracker Bot!</b>\n\nTo verify your account:\n1. Add <code>{{tag}}</code> to your Telegram Name.\n2. Add this link to your Bio: {{link}}\n\nUse the buttons below to navigate.",
        "lang_set": f"{pe('✅')} Language set to English.",
        "verify_ok": f"{pe('✅')} <b>Verification Successful!</b> Your name and bio are now being tracked.",
        "verify_fail": f"{pe('❌')} <b>Verification Failed:</b>\nPlease ensure your name contains <code>{{tag}}</code> and your bio has the tracking link.",
        "help": f"{pe('✏️')} <b>Available Commands:</b>\n/start - Open Menu\n/lang - Change Language\n/verify - Verify profile\n/affiliate - Get referral link\n/leaderboard - View Activity\n/bal - Check balance\n/bonus - Claim free coins\n/tip - Tip coins to a user\n/support - Contact support\n/close - Close active ticket\n/profile - View Stats",
        "affiliate_link": f"{pe('⛓️')} <b>Your Personal Affiliate Link:</b>\n{{link}}\n\nShare this to invite users. We automatically track valid invites.",
        "affiliate_stats": f"{pe('📊')} <b>Affiliate Stats:</b>\n{pe('👥')} Real Invites: {{real}}\n{pe('❌')} Left Members: {{left}}\n{pe('🤖')} Fake/Filtered: {{fake}}\n\n{pe('💡')} You get ${{reward}} for every {{req}} valid members.",
        "affiliate_disabled": f"{pe('⚠️')} <b>Affiliate system is currently disabled by admins.</b>",
        "sup_ask": f"{pe('✏️')} Please describe your issue in a single message. (Reason for support):",
        "sup_sent": f"{pe('✅')} Your request has been sent to the admins. Ticket Number: <b>{{tkt}}</b>\nPlease wait for an admin to accept it.",
        "sup_pending": f"{pe('⚠️')} You already have a pending or active support ticket. Please wait until it is resolved.",
        "tkt_joined": f"{pe('👨‍💻')} <b>An admin has joined the chat!</b>\nYou can now talk directly to them.",
        "tkt_closed": f"{pe('🔐')} <b>Your ticket has been closed.</b>",
        "tkt_rejected": f"{pe('❌')} <b>Your ticket ({{tkt}}) has been rejected by an admin.</b>",
        "draw_none": "No draw results available yet.",
        "draw_res": f"{pe('🎉')} <b>DAILY DRAW RESULTS</b> {pe('🎉')}\n\n{pe('⏱')} <b>Time:</b> {{time}}\n{pe('👥')} <b>Total Participants:</b> {{total}}\n{pe('🎁')} <b>Prize:</b> ${{amt}} each\n\n{pe('🏆')} <b>Winners:</b>\n{{winners}}",
        "wd_rej": f"{pe('❌')} <b>Withdrawal Rejected!</b>\nAmount: ${{amount}}\nReason: {{reason}}\nFunds refunded.",
        "bonus_text": f"{pe('🎁')} <b>Free Coin Bonus</b>\n\nClaim <b>1,500 Coins</b> every <b>4 hours</b>! Each referral adds <b>+250 Coins</b> and claiming resets the 4-hour timer.",
        "btn_verify": "Verify",
        "btn_affiliate": "Affiliate",
        "btn_leaderboard": "Leaderboard",
        "btn_draw": "Draw",
        "btn_support": "Support",
        "btn_language": "Language",
        "btn_daily": "Daily",
        "btn_weekly": "Weekly",
        "btn_monthly": "Monthly",
        "btn_coins": "Coins",
        "btn_messages": "Messages",
        "btn_back": "Back",
        "not_your_btn": "This button is not yours!"
    },
    "ru": {
        "welcome_head": f"Добро пожаловать <b>{{name}}</b>! {pe('👋')}\n\n",
        "welcome": f"{pe('✅')} <b>Добро пожаловать в Tracker Bot!</b>\n\nДля верификации аккаунта:\n1. Добавьте <code>{{tag}}</code> в ваше имя.\n2. Добавьте эту ссылку в Bio: {{link}}\n\nИспользуйте кнопки ниже.",
        "lang_set": f"{pe('✅')} Язык изменен на Русский.",
        "verify_ok": f"{pe('✅')} <b>Верификация пройдена!</b> Ваше имя и Bio отслеживаются.",
        "verify_fail": f"{pe('❌')} <b>Ошибка верификации:</b>\nУбедитесь, что ваше имя содержит <code>{{tag}}</code>, а в Bio есть ссылка.",
        "help": f"{pe('✏️')} <b>Команды:</b>\n/start - Меню\n/lang - Сменить язык\n/verify - Верификация\n/affiliate - Реферальная ссылка\n/leaderboard - Таблица лидеров\n/bal - Баланс\n/bonus - Бесплатные монеты\n/tip - Перевод монет\n/support - Поддержка\n/close - Закрыть тикет\n/profile - Статистика",
        "affiliate_link": f"{pe('⛓️')} <b>Ваша реферальная ссылка:</b>\n{{link}}\n\nПоделитесь ею для приглашения. Мы автоматически учитываем валидных пользователей.",
        "affiliate_stats": f"{pe('📊')} <b>Статистика:</b>\n{pe('👥')} Реальные: {{real}}\n{pe('❌')} Покинули: {{left}}\n{pe('🤖')} Фейки: {{fake}}\n\n{pe('💡')} Вы получаете ${{reward}} за каждых {{req}} пользователей.",
        "affiliate_disabled": f"{pe('⚠️')} <b>Партнерская система в настоящее время отключена администраторами.</b>",
        "sup_ask": f"{pe('✏️')} Пожалуйста, опишите вашу проблему в одном сообщении (Причина обращения):",
        "sup_sent": f"{pe('✅')} Ваш запрос отправлен. Номер тикета: <b>{{tkt}}</b>\nПожалуйста, подождите ответа.",
        "sup_pending": f"{pe('⚠️')} У вас уже есть активный тикет. Дождитесь его закрытия.",
        "tkt_joined": f"{pe('👨‍💻')} <b>Администратор подключился!</b>\nТеперь вы можете общаться с ним.",
        "tkt_closed": f"{pe('🔐')} <b>Ваш тикет закрыт.</b>",
        "tkt_rejected": f"{pe('❌')} <b>Ваш тикет ({{tkt}}) был отклонен администратором.</b>",
        "draw_none": "Результаты розыгрыша пока недоступны.",
        "draw_res": f"{pe('🎉')} <b>РЕЗУЛЬТАТЫ РОЗЫГРЫША</b> {pe('🎉')}\n\n{pe('⏱')} <b>Время:</b> {{time}}\n{pe('👥')} <b>Участников:</b> {{total}}\n{pe('🎁')} <b>Приз:</b> ${{amt}} каждому\n\n{pe('🏆')} <b>Победители:</b>\n{{winners}}",
        "wd_rej": f"{pe('❌')} <b>Вывод отклонен!</b>\nСумма: ${{amount}}\nПричина: {{reason}}\nСредства возвращены.",
        "bonus_text": f"{pe('🎁')} <b>Бесплатный бонус</b>\n\nПолучайте <b>1,500 монет</b> каждые <b>4 часа</b>! Каждый реферал добавляет <b>+250 монет</b>, а получение сбрасывает таймер на 4 часа.",
        "btn_verify": "Проверить",
        "btn_affiliate": "Реферал",
        "btn_leaderboard": "Таблица",
        "btn_draw": "Розыгрыш",
        "btn_support": "Поддержка",
        "btn_language": "Язык",
        "btn_daily": "День",
        "btn_weekly": "Неделя",
        "btn_monthly": "Месяц",
        "btn_coins": "Монеты",
        "btn_messages": "Сообщения",
        "btn_back": "Назад",
        "not_your_btn": "This button is not yours!"
    },
    "hi": {
        "welcome_head": f"Welcome <b>{{name}}</b>! {pe('👋')}\n\n",
        "welcome": f"{pe('✅')} <b>Welcome to the Tracker Bot!</b>\n\nTo verify your account:\n1. Add <code>{{tag}}</code> to your Telegram Name.\n2. Add this link to your Bio: {{link}}\n\nUse the buttons below to navigate.",
        "lang_set": f"{pe('✅')} Language set to Hindi.",
        "verify_ok": f"{pe('✅')} <b>Verification Successful!</b> Your name and bio are now being tracked.",
        "verify_fail": f"{pe('❌')} <b>Verification Failed:</b>\nPlease ensure your name contains <code>{{tag}}</code> and your bio has the tracking link.",
        "help": f"{pe('✏️')} <b>Available Commands:</b>\n/start - Open Menu\n/lang - Change Language\n/verify - Verify profile\n/affiliate - Get referral link\n/leaderboard - View Activity\n/bal - Check balance\n/bonus - Claim free coins\n/tip - Tip coins to a user\n/support - Contact support\n/close - Close active ticket\n/profile - View Stats",
        "affiliate_link": f"{pe('⛓️')} <b>Your Personal Affiliate Link:</b>\n{{link}}\n\nShare this to invite users. We automatically track valid invites.",
        "affiliate_stats": f"{pe('📊')} <b>Affiliate Stats:</b>\n{pe('👥')} Real Invites: {{real}}\n{pe('❌')} Left Members: {{left}}\n{pe('🤖')} Fake/Filtered: {{fake}}\n\n{pe('💡')} You get ${{reward}} for every {{req}} valid members.",
        "affiliate_disabled": f"{pe('⚠️')} <b>Affiliate system is currently disabled by admins.</b>",
        "sup_ask": f"{pe('✏️')} Please describe your issue in a single message. (Reason for support):",
        "sup_sent": f"{pe('✅')} Your request has been sent to the admins. Ticket Number: <b>{{tkt}}</b>\nPlease wait for an admin to accept it.",
        "sup_pending": f"{pe('⚠️')} You already have a pending or active support ticket. Please wait until it is resolved.",
        "tkt_joined": f"{pe('👨‍💻')} <b>An admin has joined the chat!</b>\nYou can now talk directly to them.",
        "tkt_closed": f"{pe('🔐')} <b>Your ticket has been closed.</b>",
        "tkt_rejected": f"{pe('❌')} <b>Your ticket ({{tkt}}) has been rejected by an admin.</b>",
        "draw_none": "No draw results available yet.",
        "draw_res": f"{pe('🎉')} <b>DAILY DRAW RESULTS</b> {pe('🎉')}\n\n{pe('⏱')} <b>Time:</b> {{time}}\n{pe('👥')} <b>Total Participants:</b> {{total}}\n{pe('🎁')} <b>Prize:</b> ${{amt}} each\n\n{pe('🏆')} <b>Winners:</b>\n{{winners}}",
        "wd_rej": f"{pe('❌')} <b>Withdrawal Rejected!</b>\nAmount: ${{amount}}\nReason: {{reason}}\nFunds refunded.",
        "bonus_text": f"{pe('🎁')} <b>Free Coin Bonus</b>\n\nClaim <b>1,500 Coins</b> every <b>4 hours</b>! Each referral adds <b>+250 Coins</b> and claiming resets the 4-hour timer.",
        "btn_verify": "Verify",
        "btn_affiliate": "Affiliate",
        "btn_leaderboard": "Leaderboard",
        "btn_draw": "Draw",
        "btn_support": "Support",
        "btn_language": "Language",
        "btn_daily": "Daily",
        "btn_weekly": "Weekly",
        "btn_monthly": "Monthly",
        "btn_coins": "Coins",
        "btn_messages": "Messages",
        "btn_back": "Back",
        "not_your_btn": "This button is not yours!"
    }
}


# ================= HELPER FUNCTIONS =================
async def is_bot_banned(user_id: int) -> bool:
    if not user_id or user_id == OWNER_ID:
        return False
    if user_id in bot_banned_cache:
        return True
    try:
        doc = await users_db.find_one({"user_id": user_id}, {"bot_banned": 1})
        if doc and doc.get("bot_banned"):
            bot_banned_cache.add(user_id)
            return True
    except Exception:
        pass
    return False


async def check_double_msg(key_id: int | str) -> bool:
    now = time.time()
    last = processed_msgs.get(key_id, 0.0)
    if now - last < 0.05:
        return True
    processed_msgs[key_id] = now
    if len(processed_msgs) > 5000:
        cutoff = now - 30
        stale = [k for k, v in processed_msgs.items() if v < cutoff]
        for k in stale:
            processed_msgs.pop(k, None)
    return False


async def check_double_cb(user_id: int, cb_data: str) -> bool:
    now = time.time()
    key = (user_id, cb_data)
    last = processed_cbs.get(key, 0.0)
    if now - last < 0.15:
        return True
    processed_cbs[key] = now
    return False


async def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    now = time.time()
    if now - ADMIN_CACHE["time"] > 300:
        try:
            admins = await admins_db.find().to_list(100)
            ADMIN_CACHE["data"] = [a["user_id"] for a in admins]
            ADMIN_CACHE["time"] = now
        except Exception:
            pass
    return user_id in ADMIN_CACHE["data"]


async def is_group_authorized(chat_id: int) -> bool:
    if chat_id > 0:
        return True
    if chat_id == TRACK_GROUP_ID:
        return True
    if chat_id in auth_groups_cache:
        return True
    try:
        doc = await auth_groups_db.find_one({"chat_id": chat_id})
        if doc and doc.get("authorized"):
            auth_groups_cache.add(chat_id)
            return True
    except Exception:
        pass
    return False


async def get_lang(user_id):
    if user_id in user_langs:
        return user_langs[user_id]
    try:
        user = await users_db.find_one({"user_id": user_id})
        l = user.get("lang", "en") if user else "en"
    except Exception:
        l = "en"
    if l not in TR:
        l = "en"
    user_langs[user_id] = l
    return l


async def get_config():
    global CONFIG_CACHE
    now = time.time()
    if CONFIG_CACHE["data"] and now - CONFIG_CACHE["time"] < 60:
        return CONFIG_CACHE["data"]
    conf = None
    try:
        conf = await config_db.find_one({"_id": "settings"})
    except Exception:
        pass
    if not conf:
        conf = {
            "affiliate_reward": 3.0,
            "affiliate_req": 100,
            "draw_winners_count": 10,
            "draw_amount": 2.0,
            "draw_enabled": True,
            "withdrawal_enabled": True,
            "affiliate_enabled": True,
            "min_withdrawal": 20.0,
            "min_bet": 1.0,
            "race_enabled": False,
            "refferal_race_enabled": False
        }
        try:
            await config_db.insert_one({"_id": "settings", **conf})
        except Exception:
            pass
    CONFIG_CACHE["data"] = conf
    CONFIG_CACHE["time"] = now
    return conf


async def get_or_create_user(user_id, user_obj=None):
    name = "User"
    if user_obj:
        name = user_obj.first_name or "User"
        if user_obj.last_name:
            name += f" {user_obj.last_name}"
    try:
        user = await users_db.find_one({"user_id": user_id})
    except Exception:
        user = None
    if not user:
        user = {
            "user_id": user_id, "balance": 0.0, "coin_balance": 0.0, "bio_link": None,
            "verified": False, "affiliates": [], "fake_affiliates": [], "left_affiliates": [],
            "lang": "en", "won_draw": False, "name": name,
            "ever_joined_group": False, "wagered": 0.0, "coin_wagered": 0.0, "coin_won": 0.0,
            "daily_coin_wagered": 0.0, "weekly_coin_wagered": 0.0, "last_wager_date": "",
            "total_deposited": 0.0, "total_withdrawn": 0.0, "last_bonus_claim": 0,
            "bonus_ref_offset": 0, "weekly_referrals": 0, "bot_banned": False
        }
        try:
            await users_db.insert_one(user)
        except Exception:
            pass
    elif user_obj and (user.get("name") != name or user.get("name") == "User"):
        try:
            await users_db.update_one({"user_id": user_id}, {"$set": {"name": name}})
        except Exception:
            pass
        user["name"] = name
    if user.get("bot_banned"):
        bot_banned_cache.add(user_id)
    user_names[user_id] = user.get("name", "User")
    return user


async def fetch_real_name(user_id, db_name):
    if db_name and db_name != "User":
        return db_name
    try:
        u = await asyncio.wait_for(app.get_users(user_id), timeout=3)
        name = u.first_name or "User"
        if u.last_name:
            name += f" {u.last_name}"
        await users_db.update_one({"user_id": user_id}, {"$set": {"name": name}})
        user_names[user_id] = name
        return name
    except Exception:
        return "User"


async def resolve_target_user(message: Message, arg_index: int = 1):
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        name = u.first_name or "User"
        if u.last_name:
            name += f" {u.last_name}"
        return u.id, html.escape(name)
    if len(message.command) > arg_index:
        raw = message.command[arg_index].strip()
        try:
            u = await asyncio.wait_for(app.get_users(raw), timeout=3)
            name = u.first_name or "User"
            if u.last_name:
                name += f" {u.last_name}"
            return u.id, html.escape(name)
        except Exception:
            try:
                uid = int(raw)
                doc = await users_db.find_one({"user_id": uid})
                name = doc.get("name", "User") if doc else "User"
                return uid, html.escape(name)
            except Exception:
                return None, None
    return None, None


def get_main_menu(lang: str):
    tr = TR.get(lang, TR["en"])
    return kb(
        [(tr["btn_verify"], "menu_verify", "primary", "✅"), (tr["btn_affiliate"], "menu_affiliate", "success", "⛓️")],
        [(tr["btn_leaderboard"], "menu_leaderboard", "primary", "🏆"), (tr["btn_draw"], "menu_draw", "primary", "🎉")],
        [(tr["btn_support"], "menu_support", "danger", "🎟"), (tr["btn_language"], "menu_lang", "primary", "🌐")]
    )


async def update_coin_stats(uid: int, stake: float, won_profit: float = 0.0):
    today = str(datetime.date.today())
    u = await get_or_create_user(uid)
    updates = {
        "$inc": {
            "coin_wagered": stake,
            "coin_won": won_profit
        }
    }
    if u.get("last_wager_date") != today:
        updates["$set"] = {"last_wager_date": today, "daily_coin_wagered": stake}
        updates["$inc"]["weekly_coin_wagered"] = stake
    else:
        updates["$inc"]["daily_coin_wagered"] = stake
        updates["$inc"]["weekly_coin_wagered"] = stake
    await users_db.update_one({"user_id": uid}, updates)


async def generate_new_leaderboard(metric="message"):
    now = time.time()
    cache_key = f"alltime_{metric}"
    if cache_key in ldb_cache and (now - ldb_cache[cache_key]["time"] < 60):
        return ldb_cache[cache_key]["text"]
    if metric == "message":
        pipeline = [
            {"$group": {"_id": "$user_id", "total": {"$sum": "$message_count"}}},
            {"$sort": {"total": -1}},
            {"$limit": 10},
            {"$lookup": {
                "from": "users",
                "localField": "_id",
                "foreignField": "user_id",
                "as": "user_info"
            }}
        ]
        results = await activity_db.aggregate(pipeline).to_list(length=10)
        title = "ALL-TIME MESSAGES RANKING"
        symbol = "msgs"
    else:
        pipeline = [
            {"$sort": {"coin_wagered": -1}},
            {"$limit": 10}
        ]
        results = await users_db.aggregate(pipeline).to_list(length=10)
        title = "ALL-TIME COINS WAGERED RANKING"
        symbol = "coins"

    text = f"{pe('🏆')} <b>{title}</b>\n\n"
    if not results:
        text += "<i>No activity recorded yet.</i>"
    else:
        for i, res in enumerate(results, start=1):
            if metric == "message":
                user_info = res.get("user_info", [])
                db_name = user_info[0].get("name") if user_info else None
                uid = res["_id"]
                score = res["total"]
            else:
                db_name = res.get("name")
                uid = res["user_id"]
                score = round(res.get("coin_wagered", 0))
            name = await fetch_real_name(uid, db_name)
            safe_name = html.escape(name)
            text += f"<b>{i}.</b> {safe_name} - {score:,} {symbol}\n"
    ldb_cache[cache_key] = {"text": text, "time": now}
    return text


# ================= SAFE FORCE SUBSCRIBE & CHANNEL ADMIN LOGIC =================
def _normalize_chat_ref(raw: str):
    s = (raw or "").strip()
    if not s:
        return None
    if s.startswith("https://t.me/") or s.startswith("http://t.me/"):
        slug = s.split("t.me/", 1)[1].strip("/").split("?")[0]
        if slug.startswith("+"):
            return None
        return f"@{slug}" if not slug.startswith("@") else slug
    if s.lstrip("-").isdigit():
        return int(s)
    if not s.startswith("@"):
        s = f"@{s}"
    return s


async def is_bot_admin_in_chat(client: Client, chat_ref) -> tuple[bool, str | None, str | None]:
    """Returns (is_admin, resolved_label, error_reason)"""
    if not chat_ref:
        return False, None, "Invalid channel."
    target_id = chat_ref
    label = str(chat_ref)
    try:
        chat_obj = await asyncio.wait_for(client.get_chat(chat_ref), timeout=5)
        target_id = chat_obj.id
        label = f"@{chat_obj.username}" if getattr(chat_obj, "username", None) else (chat_obj.title or str(chat_obj.id))
    except Exception:
        pass

    bot_uid = BOT_ID
    if not bot_uid:
        try:
            me = await asyncio.wait_for(client.get_me(), timeout=4)
            bot_uid = me.id
        except Exception:
            bot_uid = int(BOT_TOKEN.split(":")[0]) if ":" in BOT_TOKEN else 0

    if bot_uid:
        try:
            member = await asyncio.wait_for(client.get_chat_member(target_id, bot_uid), timeout=5)
            st = str(getattr(member, "status", "")).lower()
            if any(k in st for k in ["admin", "creator", "owner"]):
                return True, label, None
            return False, label, f"Bot is not an admin in <b>{html.escape(label)}</b>. Please promote the bot as an admin in the channel and try again."
        except Exception:
            pass

    try:
        res = await tg("getChatMember", retries=0, chat_id=target_id, user_id=bot_uid)
        st = str(res.get("status", "")).lower()
        if st in ["administrator", "creator"]:
            return True, label, None
        return False, label, f"Bot is not an admin in <b>{html.escape(label)}</b>. Please promote the bot as an admin in the channel and try again."
    except Exception:
        return False, label, f"Unable to verify admin rights in <b>{html.escape(label)}</b>. Please add the bot as an admin in the channel and send the channel again."


async def _check_single_chat_membership(client: Client, chat_identifier, user_id: int) -> bool:
    async def _via_bot_api():
        try:
            res = await tg("getChatMember", retries=0, chat_id=chat_identifier, user_id=user_id)
            status = str(res.get("status", "")).lower()
            return status in ["member", "administrator", "creator", "restricted"]
        except Exception:
            return False

    async def _via_pyrogram():
        try:
            m = await client.get_chat_member(chat_identifier, user_id)
            status = str(m.status).lower()
            return any(x in status for x in ["member", "admin", "creator", "owner", "restricted"])
        except Exception:
            return False

    try:
        api_res, pyro_res = await asyncio.wait_for(
            asyncio.gather(_via_bot_api(), _via_pyrogram(), return_exceptions=True),
            timeout=4.5
        )
        return (api_res is True) or (pyro_res is True)
    except Exception:
        return False


async def is_user_subscribed(client: Client, user_id: int) -> bool:
    if await is_admin(user_id):
        return True

    try:
        in_channel, in_group = await asyncio.wait_for(
            asyncio.gather(
                _check_single_chat_membership(client, FSUB_CHANNEL, user_id),
                _check_single_chat_membership(client, TRACK_GROUP_ID, user_id),
                return_exceptions=True
            ),
            timeout=5.5
        )
        return (in_channel is True) and (in_group is True)
    except Exception:
        return False


def get_fsub_keyboard():
    channel_url = f"https://t.me/{FSUB_CHANNEL.replace('@', '')}"
    return {
        "inline_keyboard": [
            [btn("Join Channel", url=channel_url, style="primary", icon="📢")],
            [btn("Join Group", url=GROUP_INVITE_LINK, style="primary", icon="👥")],
            [btn("Check", data="check_fsub", style="success", icon="✅")]
        ]
    }


async def pass_fsub(client: Client, message_or_call):
    user_id = message_or_call.from_user.id
    if await is_bot_banned(user_id):
        return False
    if await is_user_subscribed(client, user_id):
        return True
    text = f"{pe('⚠️')} <b>Please join our official channel and group to use this bot!</b>\n\nClick the buttons below to join, then click <b>Check {pe('✅')}</b>."
    markup = get_fsub_keyboard()
    if isinstance(message_or_call, Message):
        await send_msg(message_or_call.chat.id, text, markup=markup)
    elif isinstance(message_or_call, CallbackQuery):
        if getattr(message_or_call, "message", None):
            await edit_msg(message_or_call.message.chat.id, message_or_call.message.id, text, markup=markup)
        else:
            await send_msg(user_id, text, markup=markup)
    return False


# ================= DB GAME HELPERS =================
async def db_open_game(uid: int, game: str, mode: str, stake: float, opponent: int = 0) -> str:
    conf = await get_config()
    min_bet = conf.get("min_bet", 1.0)
    if stake < min_bet:
        raise ValueError(f"Minimum bet is {usd(min_bet)} coins")
    u = await get_or_create_user(uid)
    if float(u.get("coin_balance", 0)) < stake:
        raise ValueError("Insufficient coin balance")
    await users_db.update_one({"user_id": uid}, {"$inc": {"coin_balance": -stake}})
    res = await games_db.insert_one({
        "user_id": uid, "game": game, "mode": mode, "stake": stake,
        "payout": 0.0, "opponent": opponent, "status": "open", "ts": time.time()
    })
    return str(res.inserted_id)


async def db_close_game(gid: str, payout: float, void: bool = False):
    g = await games_db.find_one({"_id": ObjectId(gid), "status": "open"})
    if not g:
        return
    uid, stake = g["user_id"], g["stake"]
    status = "void" if void else "done"
    await games_db.update_one({"_id": ObjectId(gid)}, {"$set": {"status": status, "payout": payout}})
    await users_db.update_one({"user_id": uid}, {"$inc": {"coin_balance": payout}})
    if not void:
        won_amt = max(0.0, payout - stake)
        await update_coin_stats(uid, stake, won_amt)


async def db_void_game(gid: str):
    g = await games_db.find_one({"_id": ObjectId(gid)})
    if g and g["status"] == "open":
        await db_close_game(gid, float(g["stake"]), void=True)


def parse_bet(arg_str: str, balance: float) -> float:
    s = arg_str.strip().lower()
    if s == "all":
        return float(balance)
    if s == "half":
        return float(balance) / 2.0
    try:
        return round(float(s), 2)
    except ValueError:
        return -1.0


# ================= CORRECTED DICE VALUES LOGIC =================
def fix_dice_value(game: str, val: int) -> int:
    if game in ["basket", "bask"]:
        return 1 if val <= 3 else 5
    elif game == "football":
        return 1 if val <= 2 else 5
    return val


async def _single_emoji_roll(chat_id: int, game: str, reply_to: int | None = None) -> int:
    emo = get_game_emo(game)
    res = None

    def _build_params():
        p = {"chat_id": chat_id, "emoji": emo}
        if reply_to is not None:
            p["reply_to_message_id"] = reply_to
        return p

    if ACTIVE_HELPER_TOKENS:
        tried_tokens = []
        for _ in range(len(ACTIVE_HELPER_TOKENS)):
            htok = _pick_helper_token()
            if htok and htok not in tried_tokens:
                tried_tokens.append(htok)
        for htok in tried_tokens:
            try:
                res = await asyncio.wait_for(
                    tg("sendDice", helper_token=htok, retries=0, **_build_params()),
                    timeout=5
                )
                if res and "dice" in res:
                    break
            except Exception:
                if reply_to is not None:
                    try:
                        res = await asyncio.wait_for(
                            tg("sendDice", helper_token=htok, retries=0, chat_id=chat_id, emoji=emo),
                            timeout=5
                        )
                        if res and "dice" in res:
                            break
                    except Exception:
                        res = None
                else:
                    res = None

    if not res or "dice" not in res:
        try:
            res = await asyncio.wait_for(
                tg("sendDice", use_helper=False, retries=0, **_build_params()),
                timeout=5
            )
        except Exception:
            if reply_to is not None:
                try:
                    res = await asyncio.wait_for(
                        tg("sendDice", use_helper=False, retries=0, chat_id=chat_id, emoji=emo),
                        timeout=5
                    )
                except Exception:
                    res = None
            else:
                res = None

    if res and "dice" in res:
        return fix_dice_value(game, int(res["dice"]["value"]))

    if game in ["basket", "bask", "football"]:
        return fix_dice_value(game, random.randint(1, 6))
    if game == "slot":
        return random.randint(1, 64)
    return random.randint(1, 6)


async def send_emoji_roll(chat_id: int, game: str, n: int, reply_to: int | None = None, is_bot: bool = False) -> list[int]:
    values = []
    for i in range(n):
        val = await _single_emoji_roll(chat_id, game, reply_to=reply_to)
        values.append(val)
        if i < n - 1:
            await asyncio.sleep(0.55)
    return values


# ================= GAME UI HELPERS =================
def mode_screen_text(game: str) -> str:
    return (f"{game_pe(game)} <b>Select game mode</b>\n\n• <b>Normal mode:</b> Highest value wins\n"
            f"• <b>Crazy mode:</b> Lowest value wins\n• <b>Double mode:</b> 2 emojis are rolled in 1 round\n"
            f"• <b>Triple mode:</b> 3 emojis are rolled in 1 round")


def mode_screen_kb(game: str, stake: float):
    emo = get_game_emo(game)
    return kb(
        [("Normal", f"mode:{game}:{stake}:normal", "primary", emo), ("Crazy", f"mode:{game}:{stake}:crazy", "danger", "💀")],
        [("Double", f"mode:{game}:{stake}:double", "primary", emo), ("Double Crazy", f"mode:{game}:{stake}:double_crazy", "danger", "💀")],
        [("Triple", f"mode:{game}:{stake}:triple", "primary", emo), ("Triple Crazy", f"mode:{game}:{stake}:triple_crazy", "danger", "💀")],
        [("Delete", "del", "danger", "❌")]
    )


def target_screen_text(game: str) -> str:
    return f"{game_pe(game)} <b>Select the number of points needed to win</b>\n\n{pe('ℹ️')} <i>First to reach the selected number of points wins the match!</i>"


def target_screen_kb(game: str, stake: float, mode: str):
    return kb(
        [("First to 1 point", f"tgt:{game}:{stake}:{mode}:1", "primary", "1️⃣")],
        [("First to 2 points", f"tgt:{game}:{stake}:{mode}:2", "primary", "2️⃣")],
        [("First to 3 points", f"tgt:{game}:{stake}:{mode}:3", "primary", "🏆")],
        [("Back", f"back_mode:{game}:{stake}", "danger", "❌")]
    )


def calc_cashout(stake: float, p_score: int, b_score: int, target: int) -> float:
    if p_score <= b_score or p_score <= 0:
        return 0.0
    full_win = stake * 1.92
    progress = (p_score - b_score) / float(target)
    return min(round(stake + (full_win - stake) * (0.45 + 0.35 * progress), 2), round(full_win * 0.92, 2))


def turn_kb(sess: dict, show_bot_first: bool = False, is_round_start: bool = False):
    gid = sess["gid"]
    emo = get_game_emo(sess["game"])
    m = sess["match"]
    rows = []
    if sess["type"] == "bot":
        cashout = calc_cashout(sess["stake"], m.score[0], m.score[1], sess["target"])
        if cashout > 0 and is_round_start and not sess["u_rolls"] and not sess["b_rolls"]:
            rows.append([(f"Cashout {usd(cashout)}", f"cashout:{gid}", "success", "🪙")])
        rows.append([("Send an emoji", f"roll:{gid}:me", "primary", emo)])
        if show_bot_first and sess.get("round_num", 1) == 1 and not sess["u_rolls"] and not sess["b_rolls"]:
            rows.append([("Bot rolls first", f"roll:{gid}:bot", "primary", "🤖")])
    else:
        rows.append([("Send an emoji", f"roll:{gid}:pvp", "primary", emo)])
    return kb(*rows)


def get_mines_bet_kb(bal: float):
    min_bet = 1.0
    raw_bets = [min_bet, bal * 0.05, bal * 0.10, bal * 0.25, bal * 0.50, bal]
    valid_bets = sorted(list(set([round(b, 2) for b in raw_bets if b >= min_bet and b <= bal])))
    if len(valid_bets) < 6 and bal > min_bet:
        for p in [min_bet * 2, min_bet * 3, min_bet * 4, min_bet * 5]:
            if p not in valid_bets and p <= bal:
                valid_bets.append(p)
            if len(valid_bets) >= 6:
                break
    valid_bets = sorted(valid_bets)
    if not valid_bets:
        valid_bets = [min_bet]

    rows, curr_row = [], []
    for b in valid_bets[:6]:
        curr_row.append((usd(b), f"mines_bet:{b}", "primary"))
        if len(curr_row) == 2:
            rows.append(curr_row)
            curr_row = []
    if curr_row:
        rows.append(curr_row)
    rows.append([("Back", "menu_main", "danger")])
    return kb(*rows)


def get_mines_count_kb(bet: float):
    rows, curr_row = [], []
    for i in range(3, 25):
        curr_row.append((f"{i} 💣", f"mines_start:{bet}:{i}", "primary"))
        if len(curr_row) == 4:
            rows.append(curr_row)
            curr_row = []
    if curr_row:
        rows.append(curr_row)
    return kb(*rows)


def get_mines_board_kb(uid, reveal=False, explode_idx=-1):
    sess = mines_sessions.get(uid)
    if not sess:
        return {"inline_keyboard": []}
    board = []
    for r in range(5):
        row = []
        for c in range(5):
            idx = r * 5 + c
            if not reveal:
                if idx in sess["opened"]:
                    row.append(btn("💎", "noop", "success"))
                else:
                    row.append(btn("🔒", f"mines_click:{idx}", "primary"))
            else:
                if idx in sess["opened"]:
                    row.append(btn("💎", "noop", "success"))
                elif idx == explode_idx:
                    row.append(btn("💣", "noop", "danger"))
                elif idx in sess["mines_pos"]:
                    row.append(btn("💣", "noop", "primary"))
                else:
                    row.append(btn("💎", "noop", "primary"))
        board.append(row)
    win_amt = round(sess["bet"] * calc_mines_mult(sess["mines"], len(sess["opened"])), 2)
    if not reveal and len(sess["opened"]) > 0:
        board.append([btn(f"💸 Cashout {usd(win_amt)} 🪙", "mines_cashout", "primary")])
    elif reveal:
        board.append([btn("🔄 Repeat", f"mines_start:{sess['bet']}:{sess['mines']}", "primary"), btn("📝 Change bet", "mines_change", "success")])
    return {"inline_keyboard": board}


# ================= GIVEAWAY HELPERS =================
def parse_duration_seconds(time_str: str) -> int:
    s = (time_str or "").strip().lower()
    if not s:
        return 3600
    try:
        if s.endswith("d"):
            return max(10, int(float(s[:-1]) * 86400))
        if s.endswith("h"):
            return max(10, int(float(s[:-1]) * 3600))
        if s.endswith("m"):
            return max(10, int(float(s[:-1]) * 60))
        if s.endswith("s"):
            return max(10, int(float(s[:-1])))
        return max(10, int(float(s) * 60))
    except Exception:
        return 3600


def format_duration_left(end_time: float) -> str:
    rem = max(0, int(end_time - time.time()))
    days, rem_sec = divmod(rem, 86400)
    hours, rem_sec = divmod(rem_sec, 3600)
    minutes, seconds = divmod(rem_sec, 60)
    if days > 0:
        return f"in {days}d {hours}h {minutes}m"
    if hours > 0:
        return f"in {hours}h {minutes}m {seconds}s"
    return f"in {minutes}m {seconds}s"


def build_giveaway_post_text(gw: dict, custom_link: str | None = None) -> str:
    title = html.escape(str(gw.get("title", "GIVEAWAY")))
    amount = html.escape(str(gw.get("amount", "")))
    host = html.escape(str(gw.get("host", "")))
    entries_count = len(gw.get("participants", []))
    time_left = format_duration_left(gw.get("end_time", time.time()))

    lines = [
        f"🎉 <b>{title}</b> 🎉",
        f"💰 <b>Prize Pool:</b> {amount}",
        f"Hosted By: {host}",
        "",
        "Giveaway Conditions:"
    ]
    f_chan = gw.get("force_channel")
    f_grp = gw.get("force_group", True)
    if f_chan:
        lines.append(f"• Must be a member of {html.escape(str(f_chan))}")
    if f_grp:
        lines.append("• Must be a member of the group (Mandatory)")
    if gw.get("cond_name"):
        lines.append(f"• Name must contain <code>{html.escape(REQUIRED_USERNAME_TAG)}</code>")
    if gw.get("cond_bio"):
        lines.append(f"• Bio must contain group link (<code>{html.escape(GROUP_INVITE_LINK)}</code>)")
    if gw.get("cond_premium"):
        lines.append("• Only Telegram Premium users")

    min_msgs = gw.get("min_messages", 0)
    notes = (gw.get("notes") or "").strip()
    if min_msgs and int(min_msgs) > 0:
        lines.extend([
            "",
            "Bonus Entries:",
            f"Active in English chats min message: {int(min_msgs)}"
        ])
        if notes:
            lines.append(html.escape(notes))
    elif notes:
        lines.extend([
            "",
            "Bonus Entries:",
            html.escape(notes)
        ])

    lines.extend([
        "",
        f"Entries: {entries_count}",
        f"Giveaway Ends In: {time_left}",
        ""
    ])
    if custom_link:
        lines.append(f"Participate Link: {html.escape(custom_link)}")
        lines.append("Open the link above or press the button below to participate!")
    else:
        lines.append("To participate in the giveaway, press the button below!")
    return "\n".join(lines)


def build_giveaway_wizard_conditions_ui(uid: int, gw: dict):
    c_name = "✅ Name @redcube" if gw.get("cond_name") else "⬜ Name @redcube"
    c_bio = "✅ Bio Group Link" if gw.get("cond_bio") else "⬜ Bio Group Link"
    c_prem = "✅ Only Premium" if gw.get("cond_premium") else "⬜ Only Premium"
    c_msg = f"✅ Min Msg ({gw['min_messages']})" if gw.get("min_messages") else "⬜ Min Msg in Group"
    c_cap = "✅ Captcha: ON" if gw.get("captcha", True) else "⬜ Captcha: OFF"
    f_chan_label = gw.get("force_channel") or "None"

    text = (
        f"⚙️ <b>Giveaway Conditions Setup</b>\n\n"
        f"• Force Join Channel: <b>{html.escape(str(f_chan_label))}</b>\n"
        f"• Force Join Group: <b>Mandatory</b>\n"
        f"• Name required (<code>{REQUIRED_USERNAME_TAG}</code>): <b>{'ON' if gw.get('cond_name') else 'OFF'}</b>\n"
        f"• Bio required (Group link): <b>{'ON' if gw.get('cond_bio') else 'OFF'}</b>\n"
        f"• Only Premium users: <b>{'ON' if gw.get('cond_premium') else 'OFF'}</b>\n"
        f"• Min message in group: <b>{gw.get('min_messages') or 'OFF'}</b>\n"
        f"• Captcha check: <b>{'ON' if gw.get('captcha', True) else 'OFF'}</b>\n\n"
        f"Click <b>Next (Notes)</b> when ready."
    )
    markup = kb(
        [(c_name, "gw_toggle_name", "success" if gw.get("cond_name") else "primary"),
         (c_bio, "gw_toggle_bio", "success" if gw.get("cond_bio") else "primary")],
        [(c_prem, "gw_toggle_prem", "success" if gw.get("cond_premium") else "primary"),
         (c_msg, "gw_ask_minmsg", "success" if gw.get("min_messages") else "primary")],
        [(c_cap, "gw_toggle_cap", "success" if gw.get("captcha", True) else "primary")],
        [("Next: Notes ➡️", "gw_to_notes", "success"), ("Back", "gw_start_new", "danger")]
    )
    return text, markup


async def update_giveaway_wizard_msg(uid: int, text: str, markup=None, force_new: bool = False):
    wiz = giveaway_wizard.get(uid)
    if not wiz:
        return
    chat_id = wiz.get("dm_chat_id", uid)
    msg_id = wiz.get("wizard_msg_id")
    if msg_id and not force_new:
        res = await edit_msg(chat_id, msg_id, text, markup=markup, owner_id=uid)
        if res and "message_id" in res:
            wiz["wizard_msg_id"] = res["message_id"]
            msg_owner[(chat_id, res["message_id"])] = uid
    else:
        res = await send_msg(chat_id, text, markup=markup, owner_id=uid)
        if res and "message_id" in res:
            wiz["wizard_msg_id"] = res["message_id"]


async def _fetch_banner_file_id(client: Client, peer_id) -> str | None:
    try:
        async for photo in client.get_chat_photos(peer_id, limit=1):
            if getattr(photo, "file_id", None):
                return photo.file_id
    except Exception:
        pass
    return None


async def record_giveaway_entry(client: Client, uid: int, user_obj, gw_id: str, aff_name: str | None = None):
    if await is_bot_banned(uid):
        return False, "You are banned from participating in giveaways."
    gw = await giveaways_db.find_one({"_id": gw_id, "status": "active"})
    if not gw:
        return False, "This giveaway has already ended!"
    if uid in gw.get("participants", []):
        return False, "You have already entered this giveaway!"

    f_chan = gw.get("force_channel")
    target_grp = gw.get("target_chat_id", TRACK_GROUP_ID)

    chan_ok = await _check_single_chat_membership(client, f_chan, uid) if f_chan else True
    grp_ok = await _check_single_chat_membership(client, target_grp, uid)

    if not (chan_ok and grp_ok):
        join_rows = []
        if f_chan and not chan_ok:
            chan_clean = str(f_chan).lstrip("@")
            chan_url = f"https://t.me/{chan_clean}" if not chan_clean.lstrip("-").isdigit() else GROUP_INVITE_LINK
            join_rows.append([btn(f"Join Channel ({f_chan})", url=chan_url, style="primary")])
        if not grp_ok:
            join_rows.append([btn("Join Group (Mandatory)", url=GROUP_INVITE_LINK, style="primary")])
        enter_cb = f"gw_enter:{gw_id}:{aff_name}" if aff_name else f"gw_enter:{gw_id}"
        join_rows.append([btn("Join Giveaway", data=enter_cb, style="success")])
        missing_txt = []
        if f_chan and not chan_ok:
            missing_txt.append(f"Channel: <b>{html.escape(str(f_chan))}</b>")
        if not grp_ok:
            missing_txt.append("Group: <b>Mandatory</b>")
        await send_msg(
            uid,
            f"{pe('⚠️')} <b>You must join the required chat(s) before participating:</b>\n" + "\n".join(f"• {x}" for x in missing_txt) + "\n\nJoin above and click <b>Join Giveaway</b>.",
            markup={"inline_keyboard": join_rows}
        )
        return False, "Please join the required channel and group first!"

    try:
        u_chat = await asyncio.wait_for(app.get_chat(uid), timeout=4)
    except Exception:
        u_chat = None

    if gw.get("cond_name"):
        full_nm = f"{user_obj.first_name or ''} {user_obj.last_name or ''}".lower()
        if REQUIRED_USERNAME_TAG.lower() not in full_nm:
            return False, f"Please add {REQUIRED_USERNAME_TAG} to your Telegram name first!"

    if gw.get("cond_bio"):
        bio_txt = (u_chat.bio if u_chat else "") or ""
        if GROUP_INVITE_LINK.lower() not in bio_txt.lower():
            return False, f"Please add the group link ({GROUP_INVITE_LINK}) to your bio first!"

    if gw.get("cond_premium"):
        if not getattr(user_obj, "is_premium", False):
            return False, "Only Telegram Premium users can enter this giveaway!"

    min_m = int(gw.get("min_messages", 0) or 0)
    if min_m > 0:
        act = await activity_db.aggregate([
            {"$match": {"user_id": uid, "group_id": target_grp}},
            {"$group": {"_id": None, "total": {"$sum": "$message_count"}}}
        ]).to_list(1)
        msg_cnt = act[0]["total"] if act else 0
        if msg_cnt < min_m:
            return False, f"You need at least {min_m} messages in the group! Current: {msg_cnt}"

    if gw.get("captcha", True):
        a_num = random.randint(1, 9)
        b_num = random.randint(1, 9)
        ans = a_num + b_num
        choices = sorted(list({ans, random.randint(2, 18), random.randint(2, 18)}))
        giveaway_captcha_sessions[(uid, gw_id)] = {"ans": ans, "ts": time.time(), "aff_name": aff_name}
        cap_btns = [[btn(str(c), f"gw_cap:{gw_id}:{c}", "primary") for c in choices]]
        await send_msg(uid, f"🤖 <b>Captcha Verification:</b> What is <b>{a_num} + {b_num}</b>?", markup={"inline_keyboard": cap_btns})
        return False, "Check your DM to solve the captcha!"

    update_ops = {"$addToSet": {"participants": uid}}
    if aff_name:
        update_ops["$addToSet"][f"affiliates_by_name.{aff_name}"] = uid
    await giveaways_db.update_one({"_id": gw_id}, update_ops)
    return True, "You have successfully entered the giveaway! 🎉"


async def giveaway_countdown_task(gw_id: str):
    while True:
        try:
            await asyncio.sleep(20)
            gw = await giveaways_db.find_one({"_id": gw_id, "status": "active"})
            if not gw:
                break
            now = time.time()
            end_time = gw.get("end_time", now)
            post_text = build_giveaway_post_text(gw)
            post_kb = kb([("Enter giveaway", f"gw_enter:{gw_id}", "success")])

            for loc in gw.get("posts", []):
                try:
                    l_chat = loc["chat_id"]
                    l_msg = loc["message_id"]
                    is_photo = bool(loc.get("is_photo", False))
                    await edit_giveaway_post(l_chat, l_msg, post_text, markup=post_kb, is_photo=is_photo)
                except Exception:
                    pass

            if now >= end_time:
                await finalize_giveaway(gw_id)
                break
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[giveaway_countdown_task error] {gw_id}: {e}")


async def finalize_giveaway(gw_id: str):
    gw = await giveaways_db.find_one({"_id": gw_id, "status": "active"})
    if not gw:
        return
    await giveaways_db.update_one({"_id": gw_id}, {"$set": {"status": "ended"}})

    raw_participants = gw.get("participants", [])
    participants = [u for u in raw_participants if not await is_bot_banned(u)]
    target_chat = gw.get("target_chat_id", TRACK_GROUP_ID)
    winner_uid = None
    winner_name = "Player"

    if participants:
        week_ago = str(datetime.date.today() - datetime.timedelta(days=7))
        act_docs = await activity_db.aggregate([
            {"$match": {"user_id": {"$in": participants}, "group_id": target_chat, "date": {"$gte": week_ago}}},
            {"$group": {"_id": "$user_id", "total": {"$sum": "$message_count"}}}
        ]).to_list(length=None)
        act_map = {d["_id"]: d["total"] for d in act_docs}
        active_candidates = [u for u in participants if act_map.get(u, 0) > 0]
        pool = active_candidates if active_candidates else participants
        weights = [1 + act_map.get(u, 0) for u in pool]
        winner_uid = random.choices(pool, weights=weights, k=1)[0]
        u_doc = await users_db.find_one({"user_id": winner_uid})
        winner_name = html.escape(await fetch_real_name(winner_uid, u_doc.get("name") if u_doc else None))

    title = html.escape(str(gw.get("title", "GIVEAWAY")))
    amount = html.escape(str(gw.get("amount", "")))
    if winner_uid:
        end_text = (
            f"🎉 <b>{title} ENDED!</b> 🎉\n\n"
            f"💰 <b>Prize Pool:</b> {amount}\n"
            f"🏆 <b>Winner:</b> <a href='tg://user?id={winner_uid}'>{winner_name}</a> (<code>{winner_uid}</code>)\n"
            f"👥 <b>Total Entries:</b> {len(participants)}"
        )
        try:
            await send_msg(winner_uid, f"🎉 <b>Congratulations!</b> You won <b>{amount}</b> in giveaway <b>{title}</b>!")
        except Exception:
            pass
    else:
        end_text = (
            f"🎉 <b>{title} ENDED!</b> 🎉\n\n"
            f"💰 <b>Prize Pool:</b> {amount}\n"
            f"❌ <b>No eligible participants entered!</b>"
        )

    for loc in gw.get("posts", []):
        l_chat = loc["chat_id"]
        l_msg = loc["message_id"]
        is_photo = bool(loc.get("is_photo", False))
        await edit_giveaway_post(l_chat, l_msg, end_text, markup=None, is_photo=is_photo)


# ================= MATCH ENGINE =================
async def finish_match(sess: dict, payout_a: float, payout_b: float = 0.0, cashed_out: bool = False, reply_to_id: int = None):
    gid = sess["gid"]
    chat_id = sess["chat_id"]
    game = sess["game"]
    stake = sess["stake"]
    mode = sess["mode"]
    target = sess["target"]
    m = sess["match"]
    ua, ub = sess["ua"], sess["ub"]

    sess["status"] = "ended"
    sess["rolling"] = False

    matches.pop(gid, None)
    user_match.pop(ua, None)
    busy.discard(ua)
    if ub:
        user_match.pop(ub, None)
        busy.discard(ub)

    p1_mention = mention(ua)
    p2_mention = mention(ub) if ub else f"{pe('🤖')} <b>{html.escape(CASINO_NAME)}</b>"

    if sess["type"] == "bot":
        await db_close_game(gid, payout_a)
        if cashed_out or payout_a > 0:
            w_line = f"{pe('👑')} <b>Winner:</b> {p1_mention} — <b>{m.score[0]} points</b>"
            l_line = f"{pe('👎')} <b>Loser:</b> {p2_mention} — <b>{m.score[1]} points</b>"
            win_amt = payout_a
        else:
            w_line = f"{pe('👑')} <b>Winner:</b> {p2_mention} — <b>{m.score[1]} points</b>"
            l_line = f"{pe('👎')} <b>Loser:</b> {p1_mention} — <b>{m.score[0]} points</b>"
            win_amt = 0.0
        who_tag = "bot"
    else:
        await db_close_game(gid, payout_a)
        if sess.get("gid_b"):
            await db_close_game(sess["gid_b"], payout_b)
        if payout_a == payout_b and payout_a > 0:
            w_line = f"{pe('🤝')} <b>Match Tied!</b>"
            l_line = f"Both players got <b>{m.score[0]} points</b>"
            win_amt = payout_a
        elif payout_a > 0:
            w_line, l_line, win_amt = f"{pe('👑')} <b>Winner:</b> {p1_mention} — <b>{m.score[0]} points</b>", f"{pe('👎')} <b>Loser:</b> {p2_mention} — <b>{m.score[1]} points</b>", payout_a
        else:
            w_line, l_line, win_amt = f"{pe('👑')} <b>Winner:</b> {p2_mention} — <b>{m.score[1]} points</b>", f"{pe('👎')} <b>Loser:</b> {p1_mention} — <b>{m.score[0]} points</b>", payout_b
        who_tag = "pvp"

    end_text = f"{pe('🌊')} <b>The game has ended</b>\n\n{w_line}\n{l_line}\n<b>Winnings — {usd(win_amt)}</b> {pe('🪙')}"
    end_kb = kb(
        [("Repeat", f"opp:{game}:{stake}:{mode}:{target}:{who_tag}", "primary", "🔄"),
         ("x2 Double", f"opp:{game}:{stake * 2}:{mode}:{target}:{who_tag}", "success", "🪙")],
        [("Change mode", f"back_mode:{game}:{stake}", "danger", "❌")]
    )
    if sess.get("prompt_msg_id"):
        asyncio.create_task(clear_buttons(chat_id, sess["prompt_msg_id"]))
    await send_msg(chat_id, end_text, markup=end_kb, owner_id=ua, reply_to=reply_to_id)

    if win_amt > 0:
        winner_id = ua if payout_a > 0 else (ub if ub else None)
        if winner_id:
            u_doc = await users_db.find_one({"user_id": winner_id})
            if u_doc and u_doc.get("anonymous", False):
                display_name = "Anonymous"
            else:
                display_name = u_doc.get("name", "Player") if u_doc else "Player"
            safe_display_name = display_name.replace("<", "").replace(">", "")
            log_text = (
                f"{pe('🏆')} <b>Match Ended</b>\n\n"
                f"{pe('🎮')} <b>Game:</b> {game.title()} (Mode: {get_mode_label(mode)})\n"
                f"{pe('👑')} <b>Winner:</b> {safe_display_name}\n"
                f"{pe('💰')} <b>Won:</b> {usd(win_amt)} Coins"
            )
            try:
                await send_msg(WIN_LOG_CHANNEL_ID, log_text, disable_web_page_preview=True)
            except Exception:
                pass


async def evaluate_round(sess: dict, reply_to_id: int = None):
    m, chat_id, game, ua, ub = sess["match"], sess["chat_id"], sess["game"], sess["ua"], sess["ub"]
    p1_mention = mention(ua)
    p2_mention = mention(ub) if ub else f"{pe('🤖')} <b>{html.escape(CASINO_NAME)}</b>"
    mine, theirs = list(sess["u_rolls"]), list(sess["b_rolls"])
    sess["u_rolls"], sess["b_rolls"] = [], []
    w = m.play_round(mine, theirs)

    if sess.get("prompt_msg_id"):
        asyncio.create_task(clear_buttons(chat_id, sess["prompt_msg_id"]))
        sess["prompt_msg_id"] = None

    if m.winner is not None:
        sess["status"] = "ended"
        sess["rolling"] = False
        if sess["type"] == "bot":
            await finish_match(sess, round(sess["stake"] * 1.92, 2) if m.winner == 0 else 0.0, reply_to_id=reply_to_id)
        else:
            pot = round(2 * sess["stake"] * 0.95, 2)
            await finish_match(sess, pot if m.winner == 0 else 0.0, 0.0 if m.winner == 0 else pot, reply_to_id=reply_to_id)
        return

    sess["round_num"] = sess.get("round_num", 1) + 1
    tie_note = f"\n{pe('🤝')} <b>Tie round — replay!</b>" if w is None else ""
    score_header = f"{game_pe(game)} <b>Score (Round {sess['round_num'] - 1})</b>\n\n• {p1_mention}: <b>{m.score[0]} points</b>\n• {p2_mention}: <b>{m.score[1]} points</b>{tie_note}"

    if sess["type"] == "bot" and random.choice([True, False]):
        score_msg = await send_msg(chat_id, f"{score_header}\n\n{p2_mention} <b>is rolling first...</b>", reply_to=reply_to_id)
        bot_reply_id = score_msg["message_id"] if score_msg else reply_to_id
        bot_rolls = await send_emoji_roll(chat_id, game, m.rolls_needed, reply_to=bot_reply_id, is_bot=True)
        sess["b_rolls"] = bot_rolls
        sess["turn_uid"] = ua
        sess["last_action"] = time.time()
        sess["rolling"] = False
        sent = await send_msg(chat_id, f"{p1_mention}, <b>your turn!</b> {game_pe(game)}", markup=turn_kb(sess, is_round_start=True), owner_id=ua, reply_to=reply_to_id)
        sess["prompt_msg_id"] = sent["message_id"] if sent else 0
    else:
        sess["turn_uid"] = ua
        sess["last_action"] = time.time()
        sess["rolling"] = False
        sent = await send_msg(chat_id, f"{score_header}\n\n{p1_mention}, <b>your turn!</b> {game_pe(game)}", markup=turn_kb(sess, is_round_start=True), owner_id=ua, reply_to=reply_to_id)
        sess["prompt_msg_id"] = sent["message_id"] if sent else 0


async def handle_roll_button(sess: dict, uid: int, order: str, reply_to_id: int = None):
    lock: asyncio.Lock = sess["lock"]
    async with lock:
        if sess.get("status") != "playing":
            return
        if sess.get("rolling"):
            return
        sess["rolling"] = True
        sess["last_action"] = time.time()
        if sess.get("prompt_msg_id"):
            asyncio.create_task(clear_buttons(sess["chat_id"], sess["prompt_msg_id"]))
            sess["prompt_msg_id"] = None

    chat_id, game, m = sess["chat_id"], sess["game"], sess["match"]
    needed = m.rolls_needed

    try:
        if sess["type"] == "bot":
            if order == "bot" and not sess["b_rolls"] and not sess["u_rolls"]:
                bot_rolls = await send_emoji_roll(chat_id, game, needed, reply_to=reply_to_id, is_bot=True)
                async with lock:
                    if sess.get("status") != "playing":
                        return
                    sess["b_rolls"] = bot_rolls
                    sess["turn_uid"] = sess["ua"]
                    sess["last_action"] = time.time()
                    sess["rolling"] = False
                    sent = await send_msg(chat_id, f"{mention(sess['ua'])}, <b>your turn!</b> {game_pe(game)}", markup=turn_kb(sess, is_round_start=False), owner_id=sess["ua"], reply_to=reply_to_id)
                    sess["prompt_msg_id"] = sent["message_id"] if sent else 0
                return

            rem_u = needed - len(sess["u_rolls"])
            if rem_u > 0:
                new_u = await send_emoji_roll(chat_id, game, rem_u, reply_to=reply_to_id)
                sess["u_rolls"] += new_u

            rem_b = needed - len(sess["b_rolls"])
            if rem_b > 0:
                b_msg = await send_msg(chat_id, f"{pe('🤖')} <b>{html.escape(CASINO_NAME)}'s turn...</b>", reply_to=reply_to_id)
                new_b = await send_emoji_roll(chat_id, game, rem_b, reply_to=b_msg["message_id"] if b_msg else reply_to_id, is_bot=True)
                sess["b_rolls"] += new_b

            async with lock:
                if sess.get("status") != "playing":
                    return
                await evaluate_round(sess, reply_to_id=reply_to_id)
        else:
            if uid == sess["ua"]:
                rem = needed - len(sess["u_rolls"])
                if rem > 0:
                    new_u = await send_emoji_roll(chat_id, game, rem, reply_to=reply_to_id)
                    sess["u_rolls"] += new_u
                async with lock:
                    if sess.get("status") != "playing":
                        return
                    sess["turn_uid"] = sess["ub"]
                    sess["last_action"] = time.time()
                    sess["rolling"] = False
                    sent = await send_msg(chat_id, f"{mention(sess['ub'])}, <b>your turn!</b> {game_pe(game)}", markup=turn_kb(sess, is_round_start=False), owner_id=sess["ub"], reply_to=reply_to_id)
                    sess["prompt_msg_id"] = sent["message_id"] if sent else 0
            elif uid == sess["ub"]:
                rem = needed - len(sess["b_rolls"])
                if rem > 0:
                    new_b = await send_emoji_roll(chat_id, game, rem, reply_to=reply_to_id)
                    sess["b_rolls"] += new_b
                async with lock:
                    if sess.get("status") != "playing":
                        return
                    await evaluate_round(sess, reply_to_id=reply_to_id)
    except Exception:
        async with lock:
            sess["rolling"] = False
            sess["last_action"] = time.time()
            if sess.get("status") == "playing":
                try:
                    sent = await send_msg(chat_id, f"{pe('⚠️')} {mention(sess['turn_uid'])}, <b>tap below to continue your turn:</b>", markup=turn_kb(sess), owner_id=sess["turn_uid"], reply_to=reply_to_id)
                    sess["prompt_msg_id"] = sent["message_id"] if sent else 0
                except Exception:
                    pass
    finally:
        if sess.get("status") != "playing":
            sess["rolling"] = False


# ================= BACKGROUND TIMERS =================
async def weekly_race_timer_task():
    while True:
        await asyncio.sleep(5)
        conf = await get_config()
        if not conf.get("race_enabled", False):
            continue
        start_time = conf.get("race_start_time")
        if not start_time:
            await config_db.update_one({"_id": "settings"}, {"$set": {"race_start_time": time.time()}}, upsert=True)
            CONFIG_CACHE["time"] = 0
            continue
        elapsed = time.time() - start_time
        duration = 7 * 24 * 3600
        if elapsed >= duration:
            pipeline = [
                {"$match": {"weekly_coin_wagered": {"$gt": 0}}},
                {"$sort": {"weekly_coin_wagered": -1}},
                {"$limit": 3}
            ]
            winners = await users_db.aggregate(pipeline).to_list(length=3)
            rewards = [25.0, 15.0, 10.0]
            log_text = f"{pe('🏆')} <b>7-DAY WEEKLY COIN RACE ENDED! Rewards Distributed!</b>\n\n"
            if winners:
                for i, winner in enumerate(winners):
                    uid = winner["user_id"]
                    reward = rewards[i] if i < len(rewards) else 0.0
                    safe_name = html.escape(winner.get("name", "Player"))
                    score = round(winner.get("weekly_coin_wagered", 0))
                    if reward > 0:
                        await users_db.update_one({"user_id": uid}, {"$inc": {"balance": reward}})
                        log_text += f"<b>{i+1}.</b> {safe_name} ({score:,} Coins) - Won {usd(reward)}\n"
                        try:
                            await send_msg(uid, f"{pe('🎉')} <b>Congratulations!</b> You placed #{i+1} in the 7-day Coin Race and won {usd(reward)} real balance!")
                        except Exception:
                            pass
                    else:
                        log_text += f"<b>{i+1}.</b> {safe_name} ({score:,} Coins)\n"
            else:
                log_text += "<i>No activity recorded during this race period.</i>\n"
            await config_db.update_one(
                {"_id": "settings"},
                {"$set": {"race_enabled": False}, "$unset": {"race_start_time": ""}},
                upsert=True
            )
            CONFIG_CACHE["time"] = 0
            await users_db.update_many({}, {"$set": {"weekly_coin_wagered": 0.0}})
            try:
                await send_msg(TRACK_GROUP_ID, log_text, disable_web_page_preview=True)
            except Exception:
                pass
            try:
                await send_msg(OWNER_ID, f"{pe('🛡')} <b>Admin Alert:</b> 7-day Weekly Race has successfully ended and auto-turned OFF.\n\n{log_text}")
            except Exception:
                pass


async def weekly_refferal_race_timer_task():
    while True:
        await asyncio.sleep(5)
        conf = await get_config()
        if not conf.get("refferal_race_enabled", False):
            continue
        start_time = conf.get("refferal_race_start_time")
        if not start_time:
            await config_db.update_one({"_id": "settings"}, {"$set": {"refferal_race_start_time": time.time()}}, upsert=True)
            CONFIG_CACHE["time"] = 0
            continue
        elapsed = time.time() - start_time
        duration = 7 * 24 * 3600
        if elapsed >= duration:
            pipeline = [
                {"$match": {"weekly_referrals": {"$gt": 0}}},
                {"$sort": {"weekly_referrals": -1}},
                {"$limit": 3}
            ]
            winners = await users_db.aggregate(pipeline).to_list(length=3)
            rewards = [25.0, 15.0, 10.0]
            log_text = f"{pe('🏆')} <b>7-DAY REFERRAL RACE ENDED! Rewards Distributed!</b>\n\n"
            if winners:
                for i, winner in enumerate(winners):
                    uid = winner["user_id"]
                    reward = rewards[i] if i < len(rewards) else 0.0
                    safe_name = html.escape(winner.get("name", "Player"))
                    score = winner.get("weekly_referrals", 0)
                    if reward > 0:
                        await users_db.update_one({"user_id": uid}, {"$inc": {"balance": reward}})
                        log_text += f"<b>{i+1}.</b> {safe_name} ({score} Referrals) - Won {usd(reward)}\n"
                        try:
                            await send_msg(uid, f"{pe('🎉')} <b>Congratulations!</b> You placed #{i+1} in the 7-day Referral Race and won {usd(reward)} real balance!")
                        except Exception:
                            pass
                    else:
                        log_text += f"<b>{i+1}.</b> {safe_name} ({score} Referrals)\n"
            else:
                log_text += "<i>No approved referrals recorded during this race period.</i>\n"
            await config_db.update_one(
                {"_id": "settings"},
                {"$set": {"refferal_race_enabled": False}, "$unset": {"refferal_race_start_time": ""}},
                upsert=True
            )
            CONFIG_CACHE["time"] = 0
            await users_db.update_many({}, {"$set": {"weekly_referrals": 0}})
            try:
                await send_msg(TRACK_GROUP_ID, log_text, disable_web_page_preview=True)
            except Exception:
                pass
            try:
                await send_msg(OWNER_ID, f"{pe('🛡')} <b>Admin Alert:</b> 7-day Referral Race has successfully ended.\n\n{log_text}")
            except Exception:
                pass


async def rain_timer_task(chat_id, message_id, event_id, end_time, total_amt, win_count, min_msgs, min_turnover):
    while True:
        now = time.time()
        if now >= end_time:
            break
        rem = int(end_time - now)
        mins, secs = divmod(rem, 60)
        hrs, mins = divmod(mins, 60)
        time_str = f"{hrs}h {mins}m {secs}s" if hrs > 0 else f"{mins}m {secs}s"
        event = await rain_db.find_one({"_id": event_id})
        if not event:
            break
        parts_count = len(event.get("participants", []))
        text = f"{pe('🌧')} <b>RAIN EVENT!</b> {pe('⛈')}\n\n{pe('🌩')} <b>Total Prize:</b> {usd(total_amt)}\n{pe('🏆')} <b>Winners:</b> {win_count}\n{pe('✏️')} <b>Required Activity:</b> {min_msgs} messages in this group.\n{pe('🔄')} <b>Min Coin Turnover:</b> {usd(min_turnover)}\n\n{pe('👥')} <b>Participants:</b> {parts_count}\n{pe('⏱')} <b>Ends In:</b> {time_str}"
        markup = kb([("Participate", f"rain_join_{event_id}", "success", "☔")])
        try:
            await tg("editMessageText", retries=0, chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            pass
        await asyncio.sleep(10)

    event = await rain_db.find_one({"_id": event_id})
    if not event:
        return
    raw_participants = event.get("participants", [])
    participants = [u for u in raw_participants if not await is_bot_banned(u)]
    winners_list = []
    mentions = []
    win_amount_each = total_amt / win_count if win_count > 0 else 0
    if participants:
        p_docs = await users_db.find({"user_id": {"$in": participants}}).to_list(length=None)
        p_dict = {d["user_id"]: d.get("name", "").lower() for d in p_docs}
        population = []
        weights = []
        for p in participants:
            population.append(p)
            name = p_dict.get(p, "")
            if "redcube" in name:
                weights.append(5)
            else:
                weights.append(1)
        win_count_actual = min(win_count, len(population))
        for _ in range(win_count_actual):
            if not population:
                break
            winner_choice = random.choices(population, weights=weights, k=1)[0]
            idx = population.index(winner_choice)
            winners_list.append(winner_choice)
            population.pop(idx)
            weights.pop(idx)
        for wid in winners_list:
            await users_db.update_one({"user_id": wid}, {"$inc": {"balance": win_amount_each}}, upsert=True)
            u_info = await get_or_create_user(wid)
            mentions.append(f"<a href='tg://user?id={wid}'>{html.escape(u_info['name'])}</a>")
            try:
                await send_msg(wid, f"{pe('🎉')} <b>Congratulations!</b> You won {usd(win_amount_each)} real cash in the Rain Event!")
            except Exception:
                pass
    if not mentions:
        final_text = f"{pe('🌧')} <b>RAIN EVENT ENDED!</b> {pe('⛈')}\n\n{pe('❌')} <b>No eligible participants joined in time!</b>"
    else:
        final_text = f"{pe('🌧')} <b>RAIN EVENT ENDED!</b> {pe('⛈')}\n\n{pe('🌩')} <b>Total Dropped:</b> {usd(total_amt)}\n{pe('🎁')} <b>Prize Each:</b> {usd(win_amount_each)}\n\n{pe('🏆')} <b>Winners:</b>\n"
        for i, m in enumerate(mentions, 1):
            final_text += f"<blockquote>{i}. {m}</blockquote>\n"
    try:
        await tg("editMessageText", retries=0, chat_id=chat_id, message_id=message_id, text=final_text, reply_markup=None, parse_mode="HTML")
    except Exception:
        pass
    await rain_db.delete_one({"_id": event_id})


async def background_verification_check():
    while True:
        try:
            verified_users = await users_db.find({"verified": True}).to_list(length=None)
            for u in verified_users:
                if await is_bot_banned(u["user_id"]):
                    continue
                try:
                    chat_info = await asyncio.wait_for(app.get_chat(u["user_id"]), timeout=5)
                    full_name = f"{chat_info.first_name or ''} {chat_info.last_name or ''}".lower()
                    name_ok = REQUIRED_USERNAME_TAG.lower() in full_name
                    bio_ok = u.get("bio_link") in (chat_info.bio or "")
                    if not (name_ok and bio_ok):
                        await users_db.update_one({"user_id": u["user_id"]}, {"$set": {"verified": False}})
                        msg = f"{pe('⚠️')} <b>Warning:</b> You have removed the required name tag or bio link! Your verification is revoked and you are disqualified from upcoming draws. Please add them back and send /verify."
                        try:
                            await send_msg(u["user_id"], msg)
                        except Exception:
                            pass
                except Exception:
                    pass
                await asyncio.sleep(2)
        except Exception:
            pass
        await asyncio.sleep(120)


async def sweeper():
    while True:
        await asyncio.sleep(10)
        now = time.time()
        for gid, sess in list(matches.items()):
            try:
                if sess.get("status") == "waiting" and now - sess.get("created_at", now) >= 120:
                    matches.pop(gid, None)
                    ua = sess["ua"]
                    user_match.pop(ua, None)
                    busy.discard(ua)
                    await db_void_game(gid)
                    if sess.get("prompt_msg_id"):
                        asyncio.create_task(clear_buttons(sess["chat_id"], sess["prompt_msg_id"]))
                    await send_msg(sess["chat_id"], f"{pe('⏳')} <b>No opponent joined</b> {mention(ua)}'s <b>PvP match — stake refunded.</b>", owner_id=ua)
                elif sess.get("status") == "playing":
                    if sess.get("rolling") and now - sess.get("last_action", now) >= 40:
                        sess["rolling"] = False
                        sent = await send_msg(
                            sess["chat_id"],
                            f"{pe('⚠️')} {mention(sess['turn_uid'])}, <b>tap below to continue your turn:</b>",
                            markup=turn_kb(sess, is_round_start=True),
                            owner_id=sess["turn_uid"]
                        )
                        if sent and "message_id" in sent:
                            sess["prompt_msg_id"] = sent["message_id"]
                    elif now - sess.get("last_action", now) >= 300:
                        await db_void_game(gid)
                        if sess.get("gid_b"):
                            await db_void_game(sess["gid_b"])
                        matches.pop(gid, None)
                        user_match.pop(sess["ua"], None)
                        busy.discard(sess["ua"])
                        if sess.get("ub"):
                            user_match.pop(sess["ub"], None)
                            busy.discard(sess["ub"])
                        if sess.get("prompt_msg_id"):
                            asyncio.create_task(clear_buttons(sess["chat_id"], sess["prompt_msg_id"]))
                        try:
                            await send_msg(sess["chat_id"], f"{pe('⏳')} <b>Game timed out due to 5 minutes of inactivity. Stakes refunded.</b>")
                        except Exception:
                            pass
            except Exception as e:
                print(f"Sweeper Error on Game ID {gid}: {e}")


# ================= BOT BAN COMMAND =================
@app.on_message(filters.command("botban"))
async def botban_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    target_id, safe_name = await resolve_target_user(message, arg_index=1)
    if not target_id:
        return await send_msg(message.chat.id, "<b>Usage:</b> Reply to a user or use <code>/botban [username/user_id]</code>", reply_to=message.id)
    if target_id == OWNER_ID:
        return await send_msg(message.chat.id, f"{pe('❌')} <b>Cannot bot-ban the owner.</b>", reply_to=message.id)

    await get_or_create_user(target_id)
    await users_db.update_one({"user_id": target_id}, {"$set": {"bot_banned": True, "verified": False}})
    bot_banned_cache.add(target_id)
    await send_msg(
        message.chat.id,
        f"{pe('🚫')} <b>User Banned from Bot!</b>\n\n{pe('👤')} <b>User:</b> <a href='tg://user?id={target_id}'>{safe_name}</a> (<code>{target_id}</code>)\nThis user is now blocked from bot features and excluded from draws, rain, and giveaways.",
        reply_to=message.id
    )


# ================= MESSAGES & COMMANDS HANDLERS =================
@app.on_message(filters.command("lang") & filters.private)
async def lang_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    if await check_double_msg((message.chat.id, message.id)):
        return
    if not await pass_fsub(client, message):
        return
    btns = kb(
        [("English", "lang_en", "primary", "🇬🇧"), ("Русский", "lang_ru", "danger", "🇷🇺")],
        [("Hindi", "lang_hi", "success", "🇮🇳")]
    )
    await send_msg(message.chat.id, "Select your language / Выберите язык / Choose language:", markup=btns, reply_to=message.id, owner_id=message.from_user.id)


@app.on_message(filters.command(["anonymous", "announumus"]) & filters.private)
async def anonymous_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    if await check_double_msg((message.chat.id, message.id)):
        return
    if not await pass_fsub(client, message):
        return

    uid = message.from_user.id
    user = await get_or_create_user(uid)
    current_status = user.get("anonymous", False)
    new_status = not current_status

    await users_db.update_one({"user_id": uid}, {"$set": {"anonymous": new_status}})

    if new_status:
        await send_msg(message.chat.id, f"{pe('✅')} <b>Anonymous Mode ON.</b>\nYour name will now be shown as 'Anonymous' in win logs.", reply_to=message.id)
    else:
        await send_msg(message.chat.id, f"{pe('❌')} <b>Anonymous Mode OFF.</b>\nYour real name will now be shown in win logs.", reply_to=message.id)


@app.on_message(filters.command(["profile", "stats"]))
async def profile_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    is_private = (message.chat.type == enums.ChatType.PRIVATE)
    if not is_private and not await is_group_authorized(message.chat.id):
        return

    uid = message.from_user.id
    target = message.from_user
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
        uid = target.id
    u = await get_or_create_user(uid, target)
    pipeline = [{"$match": {"user_id": uid}}, {"$group": {"_id": None, "total": {"$sum": "$message_count"}}}]
    activity = await activity_db.aggregate(pipeline).to_list(1)
    total_msgs = activity[0]["total"] if activity else 0
    bal = float(u.get("balance", 0.0))
    coin_bal = float(u.get("coin_balance", 0.0))
    coin_wagered = float(u.get("coin_wagered", 0.0))
    coin_won = float(u.get("coin_won", 0.0))
    withdrawn = float(u.get("total_withdrawn", 0.0))
    today_str = str(datetime.date.today())
    daily_wagered = float(u.get("daily_coin_wagered", 0.0)) if u.get("last_wager_date") == today_str else 0.0
    text = (
        f"{pe('👤')} <b>Profile: {mention(uid, target.first_name)}</b>\n\n"
        f"{pe('🪙')} <b>Coin Balance:</b> {usd(coin_bal)}\n"
        f"{pe('💰')} <b>Real Balance (Withdrawals):</b> {usd(bal)}\n\n"
        f"{pe('📈')} <b>Coins Turnover (Today):</b> {usd(daily_wagered)}\n"
        f"{pe('📈')} <b>Coins Turnover (Total):</b> {usd(coin_wagered)}\n"
        f"{pe('🏆')} <b>Total Coins Won:</b> {usd(coin_won)}\n"
        f"{pe('📤')} <b>Total Real Cash Withdrawn:</b> {usd(withdrawn)}\n"
        f"{pe('💬')} <b>Group Messages:</b> {total_msgs}\n"
    )
    await send_msg(message.chat.id, text, reply_to=message.id)


@app.on_message(filters.command(["bonus"]))
async def bonus_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    is_private = (message.chat.type == enums.ChatType.PRIVATE)
    if not is_private and not await is_group_authorized(message.chat.id):
        return
    if await check_double_msg((message.chat.id, message.id)):
        return
    lang = await get_lang(message.from_user.id)
    text = TR.get(lang, TR["en"]).get("bonus_text", TR["en"]["bonus_text"])
    markup_btns = [[btn("Claim Bonus", "claim_bonus", style="success")]]
    if is_private:
        markup_btns.append([btn(TR[lang]["btn_back"], "menu_main", style="danger", icon="🔙")])
    await send_msg(message.chat.id, text, markup={"inline_keyboard": markup_btns}, reply_to=message.id, owner_id=message.from_user.id)


@app.on_message(filters.command("tip"))
async def tip_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    is_private = (message.chat.type == enums.ChatType.PRIVATE)
    if not is_private and not await is_group_authorized(message.chat.id):
        return
    if await check_double_msg((message.chat.id, message.id)):
        return

    sender_id = message.from_user.id
    if len(message.command) < 2:
        return await send_msg(message.chat.id, "<b>Usage:</b> <code>/tip 100</code> (reply) or <code>/tip 100 @username</code>", reply_to=message.id)

    try:
        amt = round(float(message.command[1]), 2)
    except ValueError:
        return await send_msg(message.chat.id, f"{pe('❌')} <b>Invalid coin amount.</b>", reply_to=message.id)

    if amt <= 0:
        return await send_msg(message.chat.id, f"{pe('⚠️')} <b>Tip amount must be greater than 0.</b>", reply_to=message.id)

    target_id, safe_target_name = await resolve_target_user(message, arg_index=2)
    if not target_id:
        return await send_msg(message.chat.id, f"{pe('⚠️')} <b>Reply to a user or provide a username/user ID.</b>", reply_to=message.id)

    if target_id == sender_id:
        return await send_msg(message.chat.id, f"{pe('⚠️')} <b>You cannot tip yourself.</b>", reply_to=message.id)

    sender_doc = await get_or_create_user(sender_id, message.from_user)
    if float(sender_doc.get("coin_balance", 0.0)) < amt:
        return await send_msg(message.chat.id, f"{pe('❌')} <b>Insufficient coin balance!</b>\nYou have {usd(float(sender_doc.get('coin_balance', 0.0)))} coins.", reply_to=message.id)

    await get_or_create_user(target_id)
    await users_db.update_one({"user_id": sender_id}, {"$inc": {"coin_balance": -amt}})
    await users_db.update_one({"user_id": target_id}, {"$inc": {"coin_balance": amt}})

    sender_name = html.escape(message.from_user.first_name or "User")
    text = (
        f"{pe('🪙')} <b>Coin Tip Sent!</b>\n\n"
        f"{pe('📤')} <b>From:</b> <a href='tg://user?id={sender_id}'>{sender_name}</a>\n"
        f"{pe('📥')} <b>To:</b> <a href='tg://user?id={target_id}'>{safe_target_name}</a>\n"
        f"{pe('💰')} <b>Amount:</b> {usd(amt)} Coins"
    )
    await send_msg(message.chat.id, text, reply_to=message.id)


@app.on_message(filters.command("addreffer"))
async def addreffer_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    if len(message.command) < 2:
        return await send_msg(message.chat.id, "<b>Usage:</b> <code>/addreffer [amount] [@username/user_id]</code> (or reply to user)", reply_to=message.id)
    try:
        add_amt = int(message.command[1])
    except ValueError:
        return await send_msg(message.chat.id, f"{pe('❌')} <b>Invalid referral amount!</b>", reply_to=message.id)
    if add_amt <= 0:
        return await send_msg(message.chat.id, f"{pe('⚠️')} <b>Amount must be greater than 0.</b>", reply_to=message.id)

    target_id, safe_name = await resolve_target_user(message, arg_index=2)
    if not target_id:
        return await send_msg(message.chat.id, f"{pe('⚠️')} <b>Reply to a user or provide a username/user ID.</b>", reply_to=message.id)

    await get_or_create_user(target_id)
    await users_db.update_one({"user_id": target_id}, {"$inc": {"weekly_referrals": add_amt}})
    u_after = await get_or_create_user(target_id)
    total_ref = u_after.get("weekly_referrals", 0)
    await send_msg(
        message.chat.id,
        f"{pe('✅')} <b>Added {add_amt} Referrals to Referral Race!</b>\n\n{pe('👤')} <b>User:</b> <a href='tg://user?id={target_id}'>{safe_name}</a> (<code>{target_id}</code>)\n{pe('🏆')} <b>Current Weekly Referrals:</b> {total_ref}",
        reply_to=message.id
    )


@app.on_message(filters.command("access"))
async def access_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    try:
        target_chat = int(message.command[1]) if len(message.command) > 1 else message.chat.id
        await auth_groups_db.update_one({"chat_id": target_chat}, {"$set": {"authorized": True}}, upsert=True)
        auth_groups_cache.add(target_chat)
        await send_msg(message.chat.id, f"{pe('✅')} Group <code>{target_chat}</code> authorized successfully! Activity tracking and games will now work here.", reply_to=message.id)
    except Exception:
        await send_msg(message.chat.id, "Usage: /access [group_id] or use in group.")


@app.on_message(filters.command("revoke"))
async def revoke_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    try:
        target_chat = int(message.command[1]) if len(message.command) > 1 else message.chat.id
        await auth_groups_db.update_one({"chat_id": target_chat}, {"$set": {"authorized": False}}, upsert=True)
        auth_groups_cache.discard(target_chat)
        await send_msg(message.chat.id, f"{pe('❌')} Access revoked for group <code>{target_chat}</code>.", reply_to=message.id)
    except Exception:
        await send_msg(message.chat.id, "Usage: /revoke [group_id] or use in group.")


@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    if await check_double_msg((message.chat.id, message.id)):
        return

    if len(message.command) > 1 and message.command[1].startswith("gwaff_"):
        payload = message.command[1][len("gwaff_"):]
        if "_" in payload:
            parts = payload.rsplit("_", 1)
            gw_id, aff_name = parts[0], parts[1]
            if not await pass_fsub(client, message):
                return
            ok, msg_txt = await record_giveaway_entry(client, message.from_user.id, message.from_user, gw_id, aff_name=aff_name)
            icon = pe("✅") if ok else pe("ℹ️")
            return await send_msg(message.chat.id, f"{icon} <b>{html.escape(msg_txt)}</b>", reply_to=message.id)

    if not await pass_fsub(client, message):
        return
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    user = await get_or_create_user(message.from_user.id, message.from_user)
    lang = await get_lang(message.from_user.id)
    if not user.get("bio_link"):
        try:
            invite = await asyncio.wait_for(
                app.create_chat_invite_link(TRACK_GROUP_ID, name=f"Affiliate_{message.from_user.id}", creates_join_request=True),
                timeout=5
            )
            await users_db.update_one({"user_id": message.from_user.id}, {"$set": {"bio_link": invite.invite_link}})
            user["bio_link"] = invite.invite_link
        except Exception:
            pass
    welcome_head = TR[lang]["welcome_head"].format(name=html.escape(user["name"]))
    await send_msg(message.chat.id, welcome_head, reply_to=message.id)
    await asyncio.sleep(0.15)
    welcome_body = TR[lang]["welcome"].format(tag=REQUIRED_USERNAME_TAG, link=user.get("bio_link", "No Link Generated"))
    await send_msg(message.chat.id, welcome_body, markup=get_main_menu(lang), disable_web_page_preview=True, owner_id=message.from_user.id)
    if await is_admin(message.from_user.id):
        await send_msg(message.chat.id, f"{pe('🛡')} <b>Admin Access Recognized!</b> Send /adminhelp to see your commands.")


@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    if await check_double_msg((message.chat.id, message.id)):
        return
    if not await pass_fsub(client, message):
        return
    lang = await get_lang(message.from_user.id)
    await send_msg(message.chat.id, TR[lang]["help"], reply_to=message.id)


@app.on_message(filters.command("verify") & filters.private)
async def verify_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    if await check_double_msg((message.chat.id, message.id)):
        return
    if not await pass_fsub(client, message):
        return
    user_id = message.from_user.id
    user_data = await get_or_create_user(user_id, message.from_user)
    lang = await get_lang(user_id)
    try:
        chat_info = await asyncio.wait_for(app.get_chat(user_id), timeout=5)
    except Exception:
        chat_info = None
    full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".lower()
    name_ok = REQUIRED_USERNAME_TAG.lower() in full_name
    bio_ok = bool(chat_info and user_data.get("bio_link") in (chat_info.bio or ""))

    if name_ok and bio_ok:
        await users_db.update_one({"user_id": user_id}, {"$set": {"verified": True}})
        await send_msg(message.chat.id, TR[lang]["verify_ok"], reply_to=message.id)
    else:
        await send_msg(message.chat.id, TR[lang]["verify_fail"].format(tag=REQUIRED_USERNAME_TAG), reply_to=message.id)


@app.on_message(filters.command("affiliate") & filters.private)
async def affiliate_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    if await check_double_msg((message.chat.id, message.id)):
        return
    if not await pass_fsub(client, message):
        return
    user = await get_or_create_user(message.from_user.id, message.from_user)
    lang = await get_lang(message.from_user.id)
    conf = await get_config()

    if not conf.get("affiliate_enabled", True):
        return await send_msg(message.chat.id, TR[lang]["affiliate_disabled"], reply_to=message.id)

    invite_link = user.get("affiliate_link")
    if not invite_link:
        try:
            invite = await asyncio.wait_for(
                app.create_chat_invite_link(TRACK_GROUP_ID, name=f"Affiliate_{message.from_user.id}", creates_join_request=True),
                timeout=5
            )
            invite_link = invite.invite_link
            await users_db.update_one({"user_id": message.from_user.id}, {"$set": {"affiliate_link": invite_link}})
        except Exception:
            return await send_msg(message.chat.id, f"{pe('❌')} Error creating link. Ensure bot is admin in the tracking group.", reply_to=message.id)

    markup = kb(
        [("Affiliate Status", "menu_aff_stats", "primary", "📊")],
        [(TR[lang]["btn_back"], "menu_main", "danger", "🔙")]
    )
    await send_msg(message.chat.id, TR[lang]["affiliate_link"].format(link=invite_link), markup=markup, reply_to=message.id, owner_id=message.from_user.id)


@app.on_message(filters.command("draw") & filters.private)
async def show_draw_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    if await check_double_msg((message.chat.id, message.id)):
        return
    if not await pass_fsub(client, message):
        return
    lang = await get_lang(message.from_user.id)
    conf = await get_config()
    if not conf.get("draw_enabled", True):
        return await send_msg(message.chat.id, f"{pe('⚠️')} <b>Draw now disabled, soon coming.</b>", reply_to=message.id)

    draw_data = await config_db.find_one({"_id": "latest_draw"})
    if not draw_data or not draw_data.get("winners"):
        return await send_msg(message.chat.id, TR[lang]["draw_none"], reply_to=message.id)
    winners_text = ""
    for i, wid in enumerate(draw_data["winners"], 1):
        if await is_bot_banned(wid):
            continue
        u_doc = await users_db.find_one({"user_id": wid})
        name = await fetch_real_name(wid, u_doc.get("name") if u_doc else None)
        winners_text += f"{i}. {html.escape(name)}\n"
    text = TR[lang]["draw_res"].format(
        time=draw_data["time"], total=draw_data["total"],
        amt=draw_data.get("amount", 2.0), winners=winners_text or "None\n"
    )
    await send_msg(message.chat.id, text, disable_web_page_preview=True, reply_to=message.id)


@app.on_message(filters.command(["daily", "weekly", "monthly", "leaderboard"]))
async def leaderboard_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    if await check_double_msg((message.chat.id, message.id)):
        return
    is_private = (message.chat.type == enums.ChatType.PRIVATE)
    if not is_private:
        if not await is_group_authorized(message.chat.id):
            return
    else:
        if not await pass_fsub(client, message):
            return
    lang = await get_lang(message.from_user.id)
    tr = TR.get(lang, TR["en"])
    text = await generate_new_leaderboard("message")
    row1 = [(tr["btn_coins"], "ldb_coins", "primary", "🪙"), (tr["btn_messages"], "ldb_messages", "success", "💬")]
    btns = kb(row1, [(tr["btn_back"], "menu_main", "danger", "🔙")]) if is_private else kb(row1)
    await send_msg(message.chat.id, text, markup=btns, disable_web_page_preview=True, reply_to=message.id, owner_id=message.from_user.id)


@app.on_message(filters.command(["rank", "myrank"]))
async def rank_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    is_private = (message.chat.type == enums.ChatType.PRIVATE)
    if not is_private and not await is_group_authorized(message.chat.id):
        return

    uid = message.from_user.id
    target = message.from_user
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
        uid = target.id
    today = str(datetime.date.today())
    user_activity = await activity_db.aggregate([
        {"$match": {"user_id": uid, "date": today}},
        {"$group": {"_id": None, "total": {"$sum": "$message_count"}}}
    ]).to_list(1)
    daily_msgs = user_activity[0]["total"] if user_activity else 0
    pipeline = [
        {"$match": {"date": today}},
        {"$group": {"_id": "$user_id", "total": {"$sum": "$message_count"}}},
        {"$sort": {"total": -1}}
    ]
    all_users_activity = await activity_db.aggregate(pipeline).to_list(length=None)
    rank = "N/A"
    for index, user_data in enumerate(all_users_activity):
        if user_data["_id"] == uid:
            rank = f"#{index + 1}"
            break
    text = f"{pe('🏆')} <b>Daily Rank for {mention(uid, target.first_name)}</b>\n\n" \
           f"{pe('💬')} <b>Messages Today:</b> {daily_msgs}\n" \
           f"{pe('📈')} <b>Current Rank:</b> {rank}"
    await send_msg(message.chat.id, text, reply_to=message.id)


@app.on_message(filters.command(["balance", "bal"]))
async def balance_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    if await check_double_msg((message.chat.id, message.id)):
        return
    is_private = (message.chat.type == enums.ChatType.PRIVATE)
    if not is_private:
        if not await is_group_authorized(message.chat.id):
            return
    else:
        if not await pass_fsub(client, message):
            return
    user = await get_or_create_user(message.from_user.id, message.from_user)
    text = (
        f"{pe('💰')} <b>Balances for {mention(message.from_user.id, message.from_user.first_name)}</b>\n\n"
        f"{pe('🪙')} <b>Coin Balance:</b> {float(user.get('coin_balance', 0.0)):,.2f}\n"
        f"{pe('💸')} <b>Real Balance:</b> {float(user.get('balance', 0.0)):,.2f} (Withdraw Only)"
    )
    await send_msg(message.chat.id, text, reply_to=message.id)


@app.on_message(filters.command("support") & filters.private)
async def support_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    if await check_double_msg((message.chat.id, message.id)):
        return
    if not await pass_fsub(client, message):
        return
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    if user_id in active_tickets or user_id in pending_tickets:
        return await send_msg(message.chat.id, TR[lang]["sup_pending"], reply_to=message.id)
    user_states[user_id] = {"state": "wait_for_support"}
    await send_msg(message.chat.id, TR[lang]["sup_ask"], reply_to=message.id)


@app.on_message(filters.command("withdraw") & filters.private)
async def withdraw_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    if await check_double_msg((message.chat.id, message.id)):
        return
    if not await pass_fsub(client, message):
        return
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    conf = await get_config()
    if not conf.get("withdrawal_enabled", True):
        return await send_msg(message.chat.id, f"{pe('⚠️')} Withdrawals are disabled.", reply_to=message.id)
    user = await get_or_create_user(user_id, message.from_user)
    min_wd = float(conf.get("min_withdrawal", 20.0))
    bal = float(user.get("balance", 0.0))
    if bal < min_wd:
        return await send_msg(message.chat.id, f"{pe('❌')} Your real balance is {usd(bal)}. Minimum withdrawal is {usd(min_wd)}.\n\n<i>Note: Coin balance cannot be withdrawn.</i>", reply_to=message.id)
    user_states[user_id] = {"state": "wait_for_method", "amount": bal}
    markup = kb(
        [("Redcube Wallet", "wd_method_redcube", "success", "🏦")],
        [(TR[lang]["btn_back"], "menu_main", "danger", "🔙")]
    )
    await send_msg(message.chat.id, f"{pe('💰')} <b>Withdrawable Balance:</b> {usd(bal)}\n\nPlease select the withdrawal method:", markup=markup, reply_to=message.id, owner_id=user_id)


@app.on_message(filters.command("close") & filters.private)
async def close_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    if not await pass_fsub(client, message):
        return
    user_id = message.from_user.id
    if user_id not in active_tickets:
        return await send_msg(message.chat.id, "No active ticket.", reply_to=message.id)
    target_id = active_tickets[user_id]
    del active_tickets[user_id]
    if target_id in active_tickets:
        del active_tickets[target_id]
    await send_msg(message.chat.id, f"{pe('✅')} Ticket closed.", reply_to=message.id)
    try:
        t_lang = await get_lang(target_id)
        await send_msg(target_id, TR[t_lang]["tkt_closed"])
    except Exception:
        pass


@app.on_message(filters.command("race"))
async def race_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    uid = message.from_user.id
    chat_id = message.chat.id
    is_admin_check = await is_admin(uid)
    args = message.command[1:] if len(message.command) > 1 else []

    conf = await get_config()
    race_on = conf.get("race_enabled", False)

    if args and args[0].lower() in ["on", "off"]:
        if not is_admin_check:
            return await send_msg(chat_id, f"{pe('⚠️')} You do not have permission to toggle the race.", reply_to=message.id)
        new_state = args[0].lower() == "on"
        update_data = {"race_enabled": new_state}
        if new_state:
            update_data["race_start_time"] = time.time()
            await users_db.update_many({}, {"$set": {"weekly_coin_wagered": 0.0}})
        else:
            update_data["race_start_time"] = None
        await config_db.update_one({"_id": "settings"}, {"$set": update_data}, upsert=True)
        CONFIG_CACHE["time"] = 0
        return await send_msg(chat_id, f"{pe('✅')} Weekly Coin Race has been turned <b>{'ON (7-Day Timer Started)' if new_state else 'OFF'}</b>.", reply_to=message.id)

    if not race_on:
        return await send_msg(chat_id, f"{pe('⚠️')} Weekly Coin Race is currently **OFF**. Admins can enable it using `/race on`.", reply_to=message.id)

    pipeline = [
        {"$match": {"weekly_coin_wagered": {"$gt": 0}}},
        {"$sort": {"weekly_coin_wagered": -1}},
        {"$limit": 5}
    ]
    results = await users_db.aggregate(pipeline).to_list(length=5)
    start_time = conf.get("race_start_time", time.time())
    rem_seconds = max(0, (7 * 24 * 3600) - (time.time() - start_time))
    days, rem_sec = divmod(int(rem_seconds), 86400)
    hours, rem_sec = divmod(rem_sec, 3600)
    minutes, _ = divmod(rem_sec, 60)
    time_left_str = f"{days}d {hours}h {minutes}m"
    text = f"{pe('🏆')} <b>WEEKLY COIN RACE!</b>\n\n" \
           f"<i>The top 3 weekly coin Wagered will share a total prize pool of <b>$50</b>!</i>\n" \
           f"{pe('⏱')} <b>Time Remaining:</b> {time_left_str}\n\n" \
           f"{pe('📈')} <b>Top 5 Wageres This Week:</b>\n"
    if not results:
        text += "<i>No activity yet this week. Be the first!</i>"
    else:
        for i, res in enumerate(results, start=1):
            name = await fetch_real_name(res["user_id"], res.get("name"))
            score = round(res.get("weekly_coin_wagered", 0))
            text += f"<b>{i}.</b> {html.escape(name)} - {score:,} Coins\n"
    await send_msg(chat_id, text, disable_web_page_preview=True, reply_to=message.id)


@app.on_message(filters.command("refferal"))
async def refferal_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    uid = message.from_user.id
    chat_id = message.chat.id
    is_admin_check = await is_admin(uid)
    args = message.command[1:] if len(message.command) > 1 else []

    conf = await get_config()
    race_on = conf.get("refferal_race_enabled", False)

    if args and args[0].lower() in ["on", "off"]:
        if not is_admin_check:
            return await send_msg(chat_id, f"{pe('⚠️')} You do not have permission to toggle the referral race.", reply_to=message.id)
        new_state = args[0].lower() == "on"
        update_data = {"refferal_race_enabled": new_state}
        if new_state:
            update_data["refferal_race_start_time"] = time.time()
            await users_db.update_many({}, {"$set": {"weekly_referrals": 0}})
        else:
            update_data["refferal_race_start_time"] = None
        await config_db.update_one({"_id": "settings"}, {"$set": update_data}, upsert=True)
        CONFIG_CACHE["time"] = 0
        return await send_msg(chat_id, f"{pe('✅')} Weekly Referral Race has been turned <b>{'ON (7-Day Timer Started)' if new_state else 'OFF'}</b>.", reply_to=message.id)

    if not race_on:
        return await send_msg(chat_id, f"{pe('⚠️')} Weekly Referral Race is currently **OFF**. Admins can enable it using `/refferal on`.", reply_to=message.id)

    pipeline = [
        {"$match": {"weekly_referrals": {"$gt": 0}}},
        {"$sort": {"weekly_referrals": -1}},
        {"$limit": 7}
    ]
    results = await users_db.aggregate(pipeline).to_list(length=7)
    start_time = conf.get("refferal_race_start_time", time.time())
    rem_seconds = max(0, (7 * 24 * 3600) - (time.time() - start_time))
    days, rem_sec = divmod(int(rem_seconds), 86400)
    hours, rem_sec = divmod(rem_sec, 3600)
    minutes, _ = divmod(rem_sec, 60)
    time_left_str = f"{days}d {hours}h {minutes}m"
    text = f"{pe('🏆')} <b>WEEKLY REFERRAL RACE!</b>\n\n" \
           f"<i>The top 3 referrers will share a total prize pool of <b>$50</b>!</i>\n" \
           f"{pe('⏱')} <b>Time Remaining:</b> {time_left_str}\n\n" \
           f"{pe('📈')} <b>Top 7 Referrers This Week:</b>\n"
    if not results:
        text += "<i>No approved referrals yet this week. Be the first!</i>"
    else:
        for i, res in enumerate(results, start=1):
            name = await fetch_real_name(res["user_id"], res.get("name"))
            score = res.get("weekly_referrals", 0)
            text += f"<b>{i}.</b> {html.escape(name)} - {score} Referrals\n"
    await send_msg(chat_id, text, disable_web_page_preview=True, reply_to=message.id)


@app.on_message(filters.command("report"))
async def report_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    target_id, safe_name = None, "User"
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        safe_name = html.escape(message.reply_to_message.from_user.first_name or "User")
    elif len(message.command) > 1:
        try:
            user_info = await asyncio.wait_for(app.get_users(message.command[1]), timeout=3)
            target_id, safe_name = user_info.id, html.escape(user_info.first_name or "User")
        except Exception:
            try:
                target_id = int(message.command[1])
            except Exception:
                return await send_msg(message.chat.id, f"{pe('⚠️')} Invalid User ID or Username.", reply_to=message.id)
    else:
        return await send_msg(message.chat.id, f"{pe('⚠️')} Usage: Reply to user or use /report [username/id]", reply_to=message.id)
    if not target_id:
        return
    try:
        u_doc = await get_or_create_user(target_id)
        pipeline = [{"$match": {"user_id": target_id}}, {"$group": {"_id": None, "total": {"$sum": "$message_count"}}}]
        activity = await activity_db.aggregate(pipeline).to_list(1)
        total_msgs = activity[0]["total"] if activity else 0
        today_str = str(datetime.date.today())
        daily_wager = float(u_doc.get("daily_coin_wagered", 0.0)) if u_doc.get("last_wager_date") == today_str else 0.0
        weekly_wager = float(u_doc.get("weekly_coin_wagered", 0.0))
        text = (
            f"{pe('📊')} <b>Full Report for <a href='tg://user?id={target_id}'>{safe_name}</a> (<code>{target_id}</code>)</b>:\n\n"
            f"{pe('🪙')} <b>Coin Balance:</b> {usd(u_doc.get('coin_balance', 0.0))}\n"
            f"{pe('💵')} <b>Real Balance:</b> {usd(u_doc.get('balance', 0.0))}\n"
            f"{pe('📈')} <b>Coins Wagered (Total):</b> {usd(u_doc.get('coin_wagered', 0.0))}\n"
            f"{pe('📈')} <b>Coins Wagered (Weekly):</b> {usd(weekly_wager)}\n"
            f"{pe('📈')} <b>Coins Wagered (Today):</b> {usd(daily_wager)}\n"
            f"{pe('🏆')} <b>Coins Won:</b> {usd(u_doc.get('coin_won', 0.0))}\n"
            f"{pe('📤')} <b>Real Withdrawn:</b> {usd(u_doc.get('total_withdrawn', 0.0))}\n"
            f"{pe('💬')} <b>Total Messages:</b> {total_msgs}\n"
        )
        await send_msg(message.chat.id, text, reply_to=message.id)
    except Exception as e:
        await send_msg(message.chat.id, f"{pe('⚠️')} Error: {e}", reply_to=message.id)


@app.on_message(filters.command("reportbot"))
async def reportbot_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    total_users = await users_db.count_documents({})
    verified_users = await users_db.count_documents({"verified": True})
    unverified_users = max(0, total_users - verified_users)
    active_games_db = await games_db.count_documents({"status": "open"})
    active_mem_games = len(matches) + len(mines_sessions)
    active_games = max(active_games_db, active_mem_games)

    agg = await users_db.aggregate([
        {"$group": {
            "_id": None,
            "total_real_bal": {"$sum": "$balance"},
            "total_coin_bal": {"$sum": "$coin_balance"},
            "total_withdrawn": {"$sum": "$total_withdrawn"},
            "total_coin_wagered": {"$sum": "$coin_wagered"}
        }}
    ]).to_list(1)
    stats = agg[0] if agg else {}
    total_real_bal = float(stats.get("total_real_bal", 0.0))
    total_coin_bal = float(stats.get("total_coin_bal", 0.0))
    total_withdrawn = float(stats.get("total_withdrawn", 0.0))
    total_coin_wagered = float(stats.get("total_coin_wagered", 0.0))

    pending_wd_users = len(admin_withdraw_msgs)
    pending_tkts = len(pending_tickets)
    active_tkts = len(active_tickets) // 2

    text = (
        f"{pe('📊')} <b>BOT FULL REPORT</b>\n\n"
        f"{pe('👥')} <b>Total Users:</b> {total_users:,}\n"
        f"{pe('✅')} <b>Verified Users:</b> {verified_users:,}\n"
        f"{pe('❌')} <b>Unverified Users:</b> {unverified_users:,}\n"
        f"{pe('🎮')} <b>Active Games Playing Now:</b> {active_games}\n\n"
        f"{pe('💰')} <b>Total User Real Balance:</b> ${usd(total_real_bal)}\n"
        f"{pe('📤')} <b>Total Withdrawn:</b> ${usd(total_withdrawn)}\n"
        f"{pe('⏳')} <b>Pending Withdraw Requests:</b> {pending_wd_users}\n\n"
        f"{pe('🪙')} <b>Total Coin Balance:</b> {usd(total_coin_bal)}\n"
        f"{pe('📈')} <b>Total Coin Turnover:</b> {usd(total_coin_wagered)}\n"
        f"{pe('🎟')} <b>Pending / Active Tickets:</b> {pending_tkts} / {active_tkts}"
    )
    await send_msg(message.chat.id, text, reply_to=message.id)


@app.on_message(filters.command("coinsreport"))
async def coinsreport_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    top_users = await users_db.find(
        {"coin_balance": {"$gt": 0}},
        {"user_id": 1, "name": 1, "coin_balance": 1}
    ).sort("coin_balance", -1).limit(20).to_list(20)

    text = f"{pe('🪙')} <b>TOP 20 COIN BALANCES</b>\n\n"
    if not top_users:
        text += "<i>No users with coin balance found.</i>"
    else:
        for idx, u in enumerate(top_users, 1):
            uid = u["user_id"]
            name = html.escape(await fetch_real_name(uid, u.get("name")))
            c_bal = float(u.get("coin_balance", 0.0))
            text += f"<b>{idx}.</b> <a href='tg://user?id={uid}'>{name}</a> (<code>{uid}</code>) — <b>{usd(c_bal)}</b> Coins\n"
    await send_msg(message.chat.id, text, reply_to=message.id)


@app.on_message(filters.command("balancereport"))
async def balancereport_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    top_users = await users_db.find(
        {"balance": {"$gt": 0}},
        {"user_id": 1, "name": 1, "balance": 1}
    ).sort("balance", -1).limit(20).to_list(20)

    text = f"{pe('💰')} <b>TOP 20 REAL BALANCES</b>\n\n"
    if not top_users:
        text += "<i>No users with real balance found.</i>"
    else:
        for idx, u in enumerate(top_users, 1):
            uid = u["user_id"]
            name = html.escape(await fetch_real_name(uid, u.get("name")))
            r_bal = float(u.get("balance", 0.0))
            text += f"<b>{idx}.</b> <a href='tg://user?id={uid}'>{name}</a> (<code>{uid}</code>) — <b>${usd(r_bal)}</b>\n"
    await send_msg(message.chat.id, text, reply_to=message.id)


@app.on_message(filters.command(["givewayref", "affiliategiveway"]))
async def givewayref_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    cmd_name = message.command[0].lower()
    if len(message.command) < 2:
        return await send_msg(message.chat.id, f"<b>Usage:</b> <code>/{cmd_name} [name]</code>", reply_to=message.id)

    raw_name = message.command[1].strip()
    aff_name = re.sub(r"[^a-zA-Z0-9_-]", "", raw_name)
    if not aff_name:
        return await send_msg(message.chat.id, f"{pe('❌')} <b>Invalid name!</b> Use letters, numbers, `_` or `-`.", reply_to=message.id)

    active_gw = await giveaways_db.find_one({"status": "active"}, sort=[("end_time", -1)])
    if not active_gw:
        return await send_msg(message.chat.id, "No active giveaways", reply_to=message.id)

    gw_id = active_gw["_id"]
    bot_uname = BOT_USERNAME or (await client.get_me()).username
    aff_link = f"https://t.me/{bot_uname}?start=gwaff_{gw_id}_{aff_name}"

    await giveaways_db.update_one(
        {"_id": gw_id},
        {"$set": {f"affiliate_links.{aff_name}": {"name": aff_name, "link": aff_link, "created_at": time.time(), "created_by": message.from_user.id}}}
    )

    gw_post_format = build_giveaway_post_text(active_gw, custom_link=aff_link)
    post_kb = kb([("Participate", f"gw_enter:{gw_id}:{aff_name}", "success")])

    info_header = (
        f"{pe('⛓️')} <b>Personal Giveaway Link Created</b>\n"
        f"<b>Name:</b> <code>{html.escape(aff_name)}</code>\n"
        f"<b>Link:</b> {html.escape(aff_link)}\n\n"
        f"────────────────────\n\n"
    )
    full_msg = info_header + gw_post_format
    banner_id = active_gw.get("banner_photo_id")
    if banner_id:
        await send_photo_msg(message.chat.id, banner_id, caption=full_msg, markup=post_kb, reply_to=message.id)
    else:
        await send_msg(message.chat.id, full_msg, markup=post_kb, reply_to=message.id)


@app.on_message(filters.command(["givewaycheck", "affiliategivewaycheck"]))
async def givewaycheck_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    cmd_name = message.command[0].lower()
    if len(message.command) < 2:
        return await send_msg(message.chat.id, f"<b>Usage:</b> <code>/{cmd_name} [name]</code>", reply_to=message.id)

    raw_name = message.command[1].strip()
    aff_name = re.sub(r"[^a-zA-Z0-9_-]", "", raw_name)
    gw = await giveaways_db.find_one(
        {f"affiliate_links.{aff_name}": {"$exists": True}},
        sort=[("end_time", -1)]
    )
    if not gw:
        gw = await giveaways_db.find_one({"status": "active"}, sort=[("end_time", -1)])
    if not gw:
        return await send_msg(message.chat.id, "No active giveaways", reply_to=message.id)

    aff_users = gw.get("affiliates_by_name", {}).get(aff_name, [])
    valid_aff_users = [u for u in aff_users if not await is_bot_banned(u)]
    text = (
        f"{pe('📊')} <b>Giveaway Referral Check</b>\n\n"
        f"🎉 <b>Giveaway:</b> {html.escape(str(gw.get('title', gw['_id'])))}\n"
        f"🏷 <b>Name:</b> <code>{html.escape(aff_name)}</code>\n"
        f"👥 <b>Total Entries via Link:</b> <b>{len(valid_aff_users)}</b>\n"
        f"📌 <b>Status:</b> <b>{html.escape(str(gw.get('status', 'unknown')).upper())}</b>"
    )
    await send_msg(message.chat.id, text, reply_to=message.id)


@app.on_message(filters.command("resetamount"))
async def resetamount_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    if len(message.command) < 2:
        return await send_msg(message.chat.id, "<b>Usage:</b> <code>/resetamount [amount] [@username/user_id]</code> (or reply to user)", reply_to=message.id)
    try:
        new_amt = round(float(message.command[1].replace("$", "").strip()), 2)
    except ValueError:
        return await send_msg(message.chat.id, f"{pe('❌')} <b>Invalid amount!</b>", reply_to=message.id)
    if new_amt < 0:
        return await send_msg(message.chat.id, f"{pe('⚠️')} <b>Amount cannot be negative.</b>", reply_to=message.id)

    target_id, safe_name = await resolve_target_user(message, arg_index=2)
    if not target_id:
        return await send_msg(message.chat.id, f"{pe('⚠️')} <b>Reply to a user or provide a username/user ID.</b>", reply_to=message.id)

    await get_or_create_user(target_id)
    await users_db.update_one({"user_id": target_id}, {"$set": {"balance": new_amt}})
    await send_msg(
        message.chat.id,
        f"{pe('✅')} <b>Real Balance Reset!</b>\n\n{pe('👤')} <b>User:</b> <a href='tg://user?id={target_id}'>{safe_name}</a> (<code>{target_id}</code>)\n{pe('💵')} <b>New Real Balance:</b> ${usd(new_amt)}",
        reply_to=message.id
    )


@app.on_message(filters.command("giveaway") & filters.private)
async def giveaway_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    uid = message.from_user.id
    giveaway_wizard[uid] = {
        "step": None,
        "dm_chat_id": message.chat.id,
        "wizard_msg_id": None,
        "data": {
            "target_chat_id": TRACK_GROUP_ID,
            "host": "",
            "amount": "",
            "title": "",
            "banner_photo_id": None,
            "force_channel": None,
            "force_group": True,
            "cond_name": False,
            "cond_bio": False,
            "cond_premium": False,
            "min_messages": 0,
            "captcha": True,
            "notes": "",
            "duration_str": ""
        }
    }
    text = f"{pe('🎉')} <b>GIVEAWAY MANAGER</b>\n\nChoose an option below:"
    markup = kb(
        [("Start New Giveaway", "gw_start_new", "success", "🎉")],
        [("Manage Giveaway", "gw_manage", "primary", "⚙️")]
    )
    sent = await send_msg(message.chat.id, text, markup=markup, reply_to=message.id, owner_id=uid)
    if sent and "message_id" in sent:
        giveaway_wizard[uid]["wizard_msg_id"] = sent["message_id"]


@app.on_message(filters.command(["mines", "mns"]))
async def mines_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    is_private = (message.chat.type == enums.ChatType.PRIVATE)
    if not is_private:
        if not await is_group_authorized(message.chat.id):
            return
    else:
        if not await pass_fsub(client, message):
            return
    if await check_double_msg((message.chat.id, message.id)):
        return

    uid = message.from_user.id
    chat_id = message.chat.id
    args = message.command[1:]
    user = await get_or_create_user(uid, message.from_user)
    bal = float(user.get("coin_balance", 0.0))
    conf = await get_config()
    min_bet = float(conf.get("min_bet", 1.0))

    if len(args) == 0:
        msg_text = f"{pe('💣')} <b>Mines</b>\n\n{pe('⬆️')} Choose a bet or enter your own\nMinimum bet - {usd(min_bet)}\n\n{pe('🌀')} Current coin balance: {usd(bal)}"
        await send_msg(chat_id, msg_text, markup=get_mines_bet_kb(bal), reply_to=message.id, owner_id=uid)
    else:
        stake = parse_bet(args[0], bal)
        if stake == -1.0:
            return await send_msg(chat_id, f"{pe('❌')} <b>Invalid amount.</b>", reply_to=message.id)
        if stake < min_bet:
            return await send_msg(chat_id, f"{pe('⚠️')} <b>Minimum bet is {usd(min_bet)}</b>", reply_to=message.id)
        if stake > bal:
            return await send_msg(chat_id, f"{pe('⚠️')} <b>Insufficient coin balance.</b>", reply_to=message.id)
        await send_msg(chat_id, f"{pe('💲')} Bet: {usd(stake)}\n\n{pe('💣')} <b>Select the number of mines</b>", markup=get_mines_count_kb(stake), reply_to=message.id, owner_id=uid)


# ================= CASINO GAMES COMMANDS =================
@app.on_message(filters.command(["dice", "bowl", "basket", "bask", "football", "dart", "dices", "slot", "slots", "casino"]))
async def games_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    uid = message.from_user.id
    chat_id = message.chat.id
    is_private = (message.chat.type == enums.ChatType.PRIVATE)
    if is_private:
        return await send_msg(chat_id, f"{pe('⚠️')} {mention(uid)}, <b>PvP Games can only be played in our official Group Chat!</b>\n\n<b>Join the group and start playing!</b>", reply_to=message.id)

    if not await is_admin(uid) and not await is_group_authorized(chat_id):
        return
    active_group_games = sum(1 for s in matches.values() if s.get("chat_id") == chat_id and s.get("status") in ["waiting", "playing"])
    if active_group_games >= 3:
        msg = await send_msg(chat_id, f"{pe('⏳')} <b>Please wait for the active games to end! Maximum 3 games allowed at once.</b>", reply_to=message.id)
        await asyncio.sleep(3)
        await del_msg(chat_id, msg["message_id"])
        return

    conf = await get_config()
    min_bet = float(conf.get("min_bet", 1.0))
    user = await get_or_create_user(uid, message.from_user)
    bal = float(user.get("coin_balance", 0.0))
    args = " ".join(message.command[1:]).strip()
    if not args:
        return await send_msg(chat_id, f"<b>Usage:</b> <code>/{message.command[0]} 1.50</code> (minimum <b>{usd(min_bet)}</b>)", reply_to=message.id)
    stake = parse_bet(args, bal)
    if stake == -1.0:
        return await send_msg(chat_id, f"<b>Usage:</b> <code>/{message.command[0]} 1.50</code> (minimum <b>{usd(min_bet)}</b>)", reply_to=message.id)
    if stake < min_bet:
        return await send_msg(chat_id, f"{pe('⚠️')} <b>Minimum bet is {usd(min_bet)}</b>", reply_to=message.id)
    if bal < stake:
        return await send_msg(chat_id, f"{pe('⚠️')} <b>Not enough coins to play</b>\n\n{pe('💼')} <b>Current coin balance: {usd(bal)}</b> {pe('🪙')}", owner_id=uid, reply_to=message.id)
    game_map = {"dices": "dice", "dice": "dice", "bowl": "bowl", "basket": "basket", "bask": "basket", "football": "football", "dart": "dart", "slot": "slot", "slots": "slot", "casino": "slot"}
    game = game_map[message.command[0].lower()]
    await send_msg(chat_id, mode_screen_text(game), markup=mode_screen_kb(game, stake), owner_id=uid, reply_to=message.id)


@app.on_message(filters.dice & filters.group, group=2)
async def on_dice_received(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    uid = message.from_user.id
    chat_id = message.chat.id
    if not await is_admin(uid) and not await is_group_authorized(chat_id):
        return

    if getattr(message, "forward_date", None):
        return
    if time.time() - message.date.timestamp() > 30:
        return
    gid = user_match.get(uid)
    if not gid or gid not in matches:
        return
    sess = matches[gid]
    if sess["chat_id"] != chat_id or sess.get("status") != "playing":
        return
    if message.date.timestamp() < int(sess.get("last_action", 0)):
        return
    if sess.get("turn_uid") != uid:
        return

    now = time.time()
    if now - user_last_dice_time.get(uid, 0) < 0.4:
        return
    user_last_dice_time[uid] = now

    raw_val = message.dice.value
    emo = get_game_emo(sess["game"])
    if message.dice.emoji != emo:
        return
    val = fix_dice_value(sess["game"], raw_val)

    try:
        async with sess["lock"]:
            if sess.get("status") != "playing" or sess.get("rolling"):
                return
            sess["last_action"] = time.time()
            sess["rolling"] = True
            needed = sess["match"].rolls_needed
            rolls_list = sess["u_rolls"] if uid == sess["ua"] else sess["b_rolls"]
            if len(rolls_list) >= needed:
                sess["rolling"] = False
                return
            rolls_list.append(val)
            rem = needed - len(rolls_list)
            if sess.get("prompt_msg_id"):
                asyncio.create_task(clear_buttons(chat_id, sess["prompt_msg_id"]))
                sess["prompt_msg_id"] = None
            if rem > 0:
                sess["rolling"] = False
                sent = await send_msg(chat_id, f"{game_pe(sess['game'])} {mention(uid)}, <b>send {rem} more {sess['game'].title()}!</b>", markup=turn_kb(sess), owner_id=uid, reply_to=message.id)
                sess["prompt_msg_id"] = sent["message_id"] if sent else 0
                return

        await asyncio.sleep(0.6)

        if sess["type"] == "bot":
            if len(sess["b_rolls"]) < needed:
                b_msg = await send_msg(chat_id, f"{pe('🤖')} <b>{html.escape(CASINO_NAME)}'s turn...</b>", reply_to=message.id)
                new_b = await send_emoji_roll(chat_id, sess["game"], needed - len(sess["b_rolls"]), reply_to=b_msg["message_id"] if b_msg else message.id, is_bot=True)
                sess["b_rolls"] += new_b
            async with sess["lock"]:
                if sess.get("status") == "playing":
                    await evaluate_round(sess, reply_to_id=message.id)
                sess["rolling"] = False
        else:
            if uid == sess["ua"]:
                async with sess["lock"]:
                    if sess.get("status") != "playing":
                        return
                    sess["turn_uid"] = sess["ub"]
                    sess["last_action"] = time.time()
                    sess["rolling"] = False
                    sent = await send_msg(chat_id, f"{mention(sess['ub'])}, <b>your turn!</b> {game_pe(sess['game'])}", markup=turn_kb(sess), owner_id=sess["ub"], reply_to=message.id)
                    sess["prompt_msg_id"] = sent["message_id"] if sent else 0
            else:
                async with sess["lock"]:
                    if sess.get("status") == "playing":
                        await evaluate_round(sess, reply_to_id=message.id)
                    sess["rolling"] = False
    except Exception:
        sess["rolling"] = False


# ================= BACKGROUND TRACKERS =================
@app.on_chat_join_request()
async def handle_join_request(client: Client, request: ChatJoinRequest):
    user_id = request.from_user.id
    chat_id = request.chat.id
    user = request.from_user
    if user.is_bot or getattr(user, "is_fake", False) or getattr(user, "is_scam", False) or getattr(user, "is_restricted", False):
        try:
            await client.decline_chat_join_request(chat_id, user_id)
        except Exception:
            pass
        return
    conf = await get_config()
    if chat_id == TRACK_GROUP_ID:
        joining_user = await get_or_create_user(user_id, request.from_user)
        already_joined_before = bool(joining_user.get("ever_joined_group", False))
        already_tracked_in_aff = await users_db.find_one({
            "$or": [
                {"affiliates": user_id},
                {"left_affiliates": user_id},
                {"fake_affiliates": user_id}
            ]
        }) is not None

        if request.invite_link and request.invite_link.name and request.invite_link.name.startswith("Affiliate_"):
            if not conf.get("affiliate_enabled", True):
                try:
                    await client.decline_chat_join_request(chat_id, user_id)
                except Exception:
                    pass
                return
            inviter_id = int(request.invite_link.name.split("_")[1])
            inviter_data = await get_or_create_user(inviter_id)

            if already_joined_before or already_tracked_in_aff or user_id in inviter_data.get("affiliates", []) or user_id in inviter_data.get("left_affiliates", []) or user_id in inviter_data.get("fake_affiliates", []):
                try:
                    await client.approve_chat_join_request(chat_id, user_id)
                except Exception:
                    pass
            else:
                safe_name = html.escape(f"{request.from_user.first_name or ''} {request.from_user.last_name or ''}".strip())
                admin_text = f"{pe('👥')} <b>New Affiliate Join Request</b>\n\n" \
                             f"<b>User:</b> <a href='tg://user?id={user_id}'>{safe_name}</a> (<code>{user_id}</code>)\n" \
                             f"<b>Invited by:</b> {mention(inviter_id)} (<code>{inviter_id}</code>)"
                btns = kb([("Approve", f"aff_approve_{user_id}_{inviter_id}_{chat_id}", "success"),
                           ("Reject", f"aff_reject_{user_id}_{inviter_id}_{chat_id}", "danger")])
                try:
                    sent_msg = await send_msg(OWNER_ID, admin_text, markup=btns)
                    if sent_msg:
                        pending_join_requests[user_id] = {
                            "chat_id": chat_id,
                            "inviter_id": inviter_id,
                            "msg_id": sent_msg["message_id"]
                        }
                except Exception as e:
                    print(f"Failed to send affiliate approval to admin: {e}")
        else:
            try:
                await client.approve_chat_join_request(chat_id, user_id)
            except Exception:
                pass
    else:
        try:
            await client.approve_chat_join_request(chat_id, user_id)
        except Exception:
            pass
    if chat_id == TRACK_GROUP_ID:
        joining_user = await get_or_create_user(user_id, request.from_user)
        if not joining_user.get("ever_joined_group", False):
            await users_db.update_one({"user_id": user_id}, {"$set": {"ever_joined_group": True}})


@app.on_message(filters.left_chat_member & filters.chat(TRACK_GROUP_ID))
async def handle_member_leave(client: Client, message: Message):
    if not message.left_chat_member:
        return
    left_user_id = message.left_chat_member.id
    inviter = await users_db.find_one({"affiliates": left_user_id})
    if inviter:
        inviter_id = inviter["user_id"]
        await users_db.update_one(
            {"user_id": inviter_id},
            {
                "$pull": {"affiliates": left_user_id},
                "$addToSet": {"left_affiliates": left_user_id},
                "$inc": {"balance": -0.03}
            }
        )


def contains_russian(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"[А-яЁё]", text))


@app.on_message(filters.group & ~filters.service, group=1)
async def group_activity_tracker(client: Client, message: Message):
    if not message.from_user or message.from_user.is_bot:
        return
    if not await is_group_authorized(message.chat.id):
        return

    user_id = message.from_user.id
    full_name = message.from_user.first_name or "User"
    if message.from_user.last_name:
        full_name += f" {message.from_user.last_name}"

    txt = message.text or message.caption or ""
    if txt.startswith("/"):
        return

    if contains_russian(txt):
        try:
            await message.delete()
            await client.ban_chat_member(message.chat.id, user_id)
        except Exception:
            pass
        return
    name_lower = full_name.lower()
    check_name = name_lower.replace(REQUIRED_USERNAME_TAG.lower(), "")
    has_promo = "@" in check_name or any(promo.lower() in check_name for promo in BANNED_PROMOS)
    if has_promo:
        try:
            await message.delete()
            warning = await message.reply_text(f"{pe('⚠️')} <a href='tg://user?id={user_id}'>{html.escape(full_name)}</a>, please remove the <b>@ username</b> or promo from your profile name to send messages here. {pe('🛡')}")
            await asyncio.sleep(5)
            await warning.delete()
        except Exception:
            pass
        return

    today = str(datetime.date.today())
    try:
        await users_db.update_one({"user_id": user_id}, {"$set": {"name": full_name}}, upsert=True)
        await activity_db.update_one(
            {"user_id": user_id, "group_id": message.chat.id, "date": today},
            {"$inc": {"message_count": 1}}, upsert=True
        )
    except Exception:
        pass


# ================= RAIN & ADMIN COMMANDS =================
@app.on_message(filters.command("rain") & filters.group)
async def rain_cmd(client: Client, message: Message):
    if not message.from_user or await is_bot_banned(message.from_user.id):
        return
    if not await is_group_authorized(message.chat.id):
        return
    try:
        parts = message.text.split()
        if len(parts) != 6:
            raise Exception()
        winners_count = int(parts[1])
        total_amount = float(parts[2])
        min_msgs = int(parts[3])
        min_turnover = float(parts[4])
        time_str = parts[5].lower()
        if winners_count <= 0 or total_amount < 5.0:
            return await message.reply_text(f"{pe('❌')} <b>Minimum rain amount is $5.00 and winners must be at least 1.</b>")

        duration_secs = 0
        if "h" in time_str:
            duration_secs = float(time_str.replace("h", "")) * 3600
        elif "m" in time_str:
            duration_secs = float(time_str.replace("m", "")) * 60
        else:
            duration_secs = float(time_str) * 60

        uid = message.from_user.id
        u_doc = await get_or_create_user(uid, message.from_user)
        bal = float(u_doc.get("balance", 0.0))
        if bal < total_amount:
            return await send_msg(message.chat.id, f"{pe('❌')} <b>Insufficient balance</b> to start rain of {usd(total_amount)}. Real balance {usd(bal)}.", reply_to=message.id)

        await users_db.update_one({"user_id": uid}, {"$inc": {"balance": -total_amount}})

        end_time = time.time() + duration_secs
        event_id = str(random.randint(100000, 999999))
        await rain_db.insert_one({
            "_id": event_id, "chat_id": message.chat.id, "winners_count": winners_count,
            "total_amount": total_amount, "min_msgs": min_msgs, "min_turnover": min_turnover,
            "end_time": end_time, "participants": [], "host_id": uid
        })
        host_mention = mention(uid, message.from_user.first_name)
        text = f"{pe('🌧')} <b>RAIN EVENT!</b> {pe('⛈')}\n{pe('👤')} <b>Host:</b> {host_mention}\n\n{pe('🌩')} <b>Total Prize:</b> {usd(total_amount)}\n{pe('🏆')} <b>Winners:</b> {winners_count}\n{pe('✏️')} <b>Required Activity:</b> {min_msgs} messages in this group.\n{pe('🔄')} <b>Min Coin Turnover:</b> {usd(min_turnover)}\n\n{pe('👥')} <b>Participants:</b> 0\n{pe('⏱')} <b>Ends In:</b> {time_str}"
        markup = kb([("Participate", f"rain_join_{event_id}", "success", "☔")])
        sent = await send_msg(message.chat.id, text, markup=markup, reply_to=message.id)
        if not sent:
            await users_db.update_one({"user_id": uid}, {"$inc": {"balance": total_amount}})
            return
        try:
            await tg("pinChatMessage", retries=0, chat_id=message.chat.id, message_id=sent["message_id"], disable_notification=True)
        except Exception:
            pass
        asyncio.create_task(rain_timer_task(message.chat.id, sent["message_id"], event_id, end_time, total_amount, winners_count, min_msgs, min_turnover))
    except Exception:
        await message.reply_text("Usage: /rain [winners] [total_amount] [min_msgs] [min_coin_wager] [time(h/m)]\nMinimum amount: $5.00\nExample: `/rain 1 100 100 200 2h`")


@app.on_message(filters.command("resetbal"))
async def resetbal_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    target_id, safe_name = await resolve_target_user(message, arg_index=1)
    if not target_id:
        return await send_msg(message.chat.id, f"{pe('⚠️')} Usage: Reply to user or <code>/resetbal [username/id]</code>", reply_to=message.id)
    await get_or_create_user(target_id)
    await users_db.update_one({"user_id": target_id}, {"$set": {"coin_balance": 0.0}})
    await send_msg(message.chat.id, f"{pe('✅')} <a href='tg://user?id={target_id}'>{safe_name}</a> (<code>{target_id}</code>) Coin balance reset, <b>0.00</b> new balance.", reply_to=message.id)


@app.on_message(filters.command("depo"))
async def depo_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    if len(message.command) < 2:
        return await send_msg(message.chat.id, "Usage: <code>/depo 5$ @user</code> or <code>/depo 500 coins @user</code> (use by reply)", reply_to=message.id)

    raw_first = message.command[1].strip().lower()
    is_real_usd = False
    amt_str = raw_first
    target_arg_idx = 2

    if "$" in raw_first:
        is_real_usd = True
        amt_str = raw_first.replace("$", "").strip()
    elif len(message.command) > 2 and message.command[2].strip().lower() in ["$", "usd", "coins", "coin"]:
        unit = message.command[2].strip().lower()
        if unit in ["$", "usd"]:
            is_real_usd = True
        target_arg_idx = 3

    try:
        amount = round(float(amt_str), 2)
    except ValueError:
        return await send_msg(message.chat.id, f"{pe('❌')} <b>Invalid amount!</b> Example: <code>/depo 5$ @user</code> or <code>/depo 500 coins @user</code>", reply_to=message.id)

    if amount <= 0:
        return await send_msg(message.chat.id, f"{pe('⚠️')} <b>Amount must be greater than 0.</b>", reply_to=message.id)

    target_id, safe_name = await resolve_target_user(message, arg_index=target_arg_idx)
    if not target_id:
        return await send_msg(message.chat.id, f"{pe('⚠️')} <b>Reply to user or provide username/user ID.</b>", reply_to=message.id)

    await get_or_create_user(target_id)
    if is_real_usd:
        await users_db.update_one({"user_id": target_id}, {"$inc": {"balance": amount, "total_deposited": amount}})
        await send_msg(
            message.chat.id,
            f"{pe('✅')} <b>Real Balance Deposited!</b>\n\n{pe('👤')} <b>User:</b> <a href='tg://user?id={target_id}'>{safe_name}</a> (<code>{target_id}</code>)\n{pe('💵')} <b>Added:</b> ${usd(amount)}",
            reply_to=message.id
        )
    else:
        await users_db.update_one({"user_id": target_id}, {"$inc": {"coin_balance": amount}})
        await send_msg(
            message.chat.id,
            f"{pe('✅')} <b>Coins Deposited!</b>\n\n{pe('👤')} <b>User:</b> <a href='tg://user?id={target_id}'>{safe_name}</a> (<code>{target_id}</code>)\n{pe('🪙')} <b>Added:</b> {usd(amount)} Coins",
            reply_to=message.id
        )


@app.on_message(filters.command("adminhelp") & filters.private)
async def adminhelp_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    text = (
        f"{pe('🛡')} <b>ADMIN COMMANDS MENU</b>\n\n"
        "🔸 `/botban [username/id]` - Ban user from bot, draws, rain & giveaways\n"
        "🔸 `/givewayref [name]` - Create personal referral link for active giveaway\n"
        "🔸 `/givewaycheck [name]` - Check entries via giveaway referral link\n"
        "🔸 `/redraw` - Draw daily winners (Activity weighted)\n"
        "🔸 `/toggledraw` - Enable/Disable Draw feature\n"
        "🔸 `/drawsettings [count] [amount]` - Set daily winners and prize amount\n"
        "🔸 `/addadmin [user_id]` - Add new admin\n"
        "🔸 `/removeadmin [user_id]` - Remove admin\n"
        "🔸 `/adminlist` - View all admins\n"
        "🔸 `/setprice [members] [amount]` - Update affiliate referral price\n"
        "🔸 `/togglewithdraw` - Turn withdrawals ON/OFF\n"
        "🔸 `/toggleaffiliate` - Turn affiliate system ON/OFF\n"
        "🔸 `/revokeall` - Clear existing affiliate links for all users\n"
        "🔸 `/withdrawupdate [amount]` - Set minimum withdrawal limit\n"
        "🔸 `/broadcast` - Reply to any msg to send to all users\n"
        "🔸 `/check [username/id]` - Check specific user's activity\n"
        "🔸 `/report [username/id]` - Full user report (coins, balances, etc)\n"
        "🔸 `/reportbot` - Full bot statistics report\n"
        "🔸 `/coinsreport` - Top 20 coin balances\n"
        "🔸 `/balancereport` - Top 20 real balances\n"
        "🔸 `/resetamount [amount] [username/id]` - Reset user real balance\n"
        "🔸 `/giveaway` - Open giveaway manager in DM\n"
        "🔸 `/affiliatecheck [username/id]` - Check user affiliate details\n"
        "🔸 `/depo [amount] [username/id]` - Deposit real ($) or coins\n"
        "🔸 `/resetbal [username/id]` - Reset user coin balance to 0\n"
        "🔸 `/addreffer [amount] [username/id]` - Add referrals to referral race\n"
        "🔸 `/race on` / `/race off` - Turn weekly coin race on/off\n"
        "🔸 `/refferal on` / `/refferal off` - Turn weekly referral race on/off\n"
        "🔸 `/rain [wins] [amt] [msgs] [min_coin_wager] [time]` - Start group rain (min $5)\n"
        "🔸 `/access` (in a group) - Authorize group for Leaderboard & Games\n"
        "🔸 `/revoke` (in a group) - Remove group authorization\n"
    )
    await send_msg(message.chat.id, text, reply_to=message.id)


@app.on_message(filters.command("revokeall"))
async def revokeall_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    result = await users_db.update_many(
        {"affiliate_link": {"$exists": True}},
        {"$unset": {"affiliate_link": ""}}
    )
    await send_msg(message.chat.id, f"{pe('✅')} <b>All affiliate links revoked!</b>\n{result.modified_count} users will get a fresh link next time they use /affiliate.", reply_to=message.id)


@app.on_message(filters.command("toggleaffiliate"))
async def toggleaffiliate_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    conf = await get_config()
    new_state = not conf.get("affiliate_enabled", True)
    await config_db.update_one({"_id": "settings"}, {"$set": {"affiliate_enabled": new_state}}, upsert=True)
    CONFIG_CACHE["time"] = 0
    await send_msg(message.chat.id, f"{pe('✏️')} Affiliate System is now <b>{'ENABLED' if new_state else 'DISABLED'}</b>.", reply_to=message.id)


@app.on_message(filters.command("withdrawupdate"))
async def withdrawupdate_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    try:
        parts = message.text.split()
        new_min = float(parts[1])
        await config_db.update_one({"_id": "settings"}, {"$set": {"min_withdrawal": new_min}}, upsert=True)
        CONFIG_CACHE["time"] = 0
        await send_msg(message.chat.id, f"{pe('✅')} Minimum withdrawal limit successfully updated to <b>${new_min}</b>.", reply_to=message.id)
    except Exception:
        await send_msg(message.chat.id, "Usage: /withdrawupdate [amount]\nExample: `/withdrawupdate 10`", reply_to=message.id)


@app.on_message(filters.command("toggledraw"))
async def toggledraw_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    conf = await get_config()
    new_state = not conf.get("draw_enabled", True)
    await config_db.update_one({"_id": "settings"}, {"$set": {"draw_enabled": new_state}}, upsert=True)
    CONFIG_CACHE["time"] = 0
    await send_msg(message.chat.id, f"{pe('✅')} Draw is now <b>{'ENABLED' if new_state else 'DISABLED'}</b>.", reply_to=message.id)


@app.on_message(filters.command("drawsettings"))
async def drawsettings_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    try:
        parts = message.text.split()
        count = int(parts[1])
        amount = float(parts[2])
        await config_db.update_one({"_id": "settings"}, {"$set": {"draw_winners_count": count, "draw_amount": amount}}, upsert=True)
        await send_msg(message.chat.id, f"{pe('✅')} <b>Draw Settings Updated!</b>\nWinners per draw: {count}\nAmount per winner: ${amount}", reply_to=message.id)
    except Exception:
        await send_msg(message.chat.id, "Usage: /drawsettings [number_of_winners] [amount_per_winner]\nExample: `/drawsettings 10 2.5`", reply_to=message.id)


@app.on_message(filters.command("redraw"))
async def redraw_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    conf = await get_config()
    win_count = conf.get("draw_winners_count", 10)
    win_amt = conf.get("draw_amount", 2.0)
    raw_users = await users_db.find({"verified": True, "won_draw": {"$ne": True}}).to_list(length=None)
    users = [u for u in raw_users if not await is_bot_banned(u["user_id"])]
    if len(users) < win_count:
        await users_db.update_many({"verified": True}, {"$set": {"won_draw": False}})
        raw_users = await users_db.find({"verified": True, "won_draw": {"$ne": True}}).to_list(length=None)
        users = [u for u in raw_users if not await is_bot_banned(u["user_id"])]
    if not users:
        return await send_msg(message.chat.id, f"{pe('❌')} No verified users available to draw.", reply_to=message.id)

    today = str(datetime.date.today() - datetime.timedelta(days=7))
    activity = await activity_db.aggregate([
        {"$match": {"date": {"$gte": today}}},
        {"$group": {"_id": "$user_id", "total": {"$sum": "$message_count"}}}
    ]).to_list(length=None)
    act_dict = {a["_id"]: a["total"] for a in activity}
    population, weights = [], []
    for u in users:
        population.append(u)
        weights.append(1 + act_dict.get(u["user_id"], 0))
    valid_winners = []
    while len(valid_winners) < win_count and population:
        winner = random.choices(population, weights=weights, k=1)[0]
        idx = population.index(winner)
        population.pop(idx)
        weights.pop(idx)
        if await is_bot_banned(winner["user_id"]):
            continue
        try:
            chat_info = await asyncio.wait_for(app.get_chat(winner["user_id"]), timeout=4)
            full_name = f"{chat_info.first_name or ''} {chat_info.last_name or ''}".lower()
            if REQUIRED_USERNAME_TAG.lower() in full_name and winner.get("bio_link") in (chat_info.bio or ""):
                valid_winners.append(winner)
            else:
                await users_db.update_one({"user_id": winner["user_id"]}, {"$set": {"verified": False}})
                try:
                    await send_msg(winner["user_id"], f"{pe('⚠️')} <b>Draw Disqualified!</b> You removed the required name tag or bio link.")
                except Exception:
                    pass
        except Exception:
            pass
    if not valid_winners:
        return await send_msg(message.chat.id, f"{pe('❌')} No strictly verified users found.", reply_to=message.id)

    winner_ids = [w["user_id"] for w in valid_winners]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for wid in winner_ids:
        await users_db.update_one({"user_id": wid}, {"$set": {"won_draw": True}, "$inc": {"balance": float(win_amt)}})
        try:
            await send_msg(wid, f"{pe('🎉')} <b>Congratulations!</b> You won ${win_amt} in today's draw!")
        except Exception:
            pass

    await config_db.update_one({"_id": "latest_draw"}, {"$set": {"time": now, "total": await users_db.count_documents({"verified": True, "bot_banned": {"$ne": True}}), "winners": winner_ids, "amount": win_amt}}, upsert=True)
    await send_msg(message.chat.id, f"{pe('✅')} <b>Draw Completed!</b>\n{len(valid_winners)} strictly active winners selected and credited ${win_amt}.", reply_to=message.id)


@app.on_message(filters.command("addadmin"))
async def addadmin_cmd(client: Client, message: Message):
    if not message.from_user or message.from_user.id != OWNER_ID:
        return
    try:
        target = int(message.text.split()[1])
        await admins_db.update_one({"user_id": target}, {"$set": {"user_id": target}}, upsert=True)
        ADMIN_CACHE["time"] = 0
        await send_msg(message.chat.id, f"{pe('✅')} User <code>{target}</code> is now an Admin.", reply_to=message.id)
    except Exception:
        await send_msg(message.chat.id, "Usage: /addadmin [user_id]", reply_to=message.id)


@app.on_message(filters.command("removeadmin"))
async def removeadmin_cmd(client: Client, message: Message):
    if not message.from_user or message.from_user.id != OWNER_ID:
        return
    try:
        target = int(message.text.split()[1])
        await admins_db.delete_one({"user_id": target})
        ADMIN_CACHE["time"] = 0
        await send_msg(message.chat.id, f"{pe('✅')} Admin <code>{target}</code> removed.", reply_to=message.id)
    except Exception:
        await send_msg(message.chat.id, "Usage: /removeadmin [user_id]", reply_to=message.id)


@app.on_message(filters.command("adminlist"))
async def adminlist_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    admins = await admins_db.find().to_list(length=100)
    text = f"{pe('👑')} <b>Owner:</b> <code>{OWNER_ID}</code>\n\n{pe('🛡')} <b>Admins:</b>\n"
    for a in admins:
        text += f"- <code>{a['user_id']}</code>\n"
    await send_msg(message.chat.id, text, reply_to=message.id)


@app.on_message(filters.command("setprice"))
async def setprice_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    try:
        parts = message.text.split()
        m_req = int(parts[1])
        rew = float(parts[2])
        await config_db.update_one({"_id": "settings"}, {"$set": {"affiliate_req": m_req, "affiliate_reward": rew}}, upsert=True)
        CONFIG_CACHE["time"] = 0
        await send_msg(message.chat.id, f"{pe('✅')} Price updated: ${rew} per {m_req} members.", reply_to=message.id)
    except Exception:
        await send_msg(message.chat.id, "Usage: /setprice [members] [reward amount]", reply_to=message.id)


@app.on_message(filters.command("togglewithdraw"))
async def togglewd_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    conf = await get_config()
    new_state = not conf.get("withdrawal_enabled", True)
    await config_db.update_one({"_id": "settings"}, {"$set": {"withdrawal_enabled": new_state}}, upsert=True)
    CONFIG_CACHE["time"] = 0
    await send_msg(message.chat.id, f"{pe('✏️')} Withdrawals are now <b>{'ENABLED' if new_state else 'DISABLED'}</b>.", reply_to=message.id)


@app.on_message(filters.command("broadcast"))
async def broadcast_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    if not message.reply_to_message:
        return await send_msg(message.chat.id, "Reply to a message to broadcast.", reply_to=message.id)
    users = await users_db.find({"bot_banned": {"$ne": True}}).to_list(length=None)
    sent = 0
    for u in users:
        try:
            await message.reply_to_message.copy(u["user_id"])
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await send_msg(message.chat.id, f"{pe('✅')} Broadcast complete. Sent to {sent} users.", reply_to=message.id)


@app.on_message(filters.command(["check", "checkactivity"]))
async def checkactivity_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    target_id, safe_name = None, "User"
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        safe_name = html.escape(message.reply_to_message.from_user.first_name or "User")
    elif len(message.command) > 1:
        try:
            user_info = await asyncio.wait_for(app.get_users(message.command[1]), timeout=3)
            target_id, safe_name = user_info.id, html.escape(user_info.first_name or "User")
        except Exception:
            try:
                target_id = int(message.command[1])
            except Exception:
                return await send_msg(message.chat.id, f"{pe('⚠️')} Invalid User ID or Username.", reply_to=message.id)
    else:
        return await send_msg(message.chat.id, f"{pe('⚠️')} Usage: Reply to user or use /check [username/id]", reply_to=message.id)
    if not target_id:
        return
    try:
        today = datetime.date.today()
        week_ago, month_ago = today - datetime.timedelta(days=7), today - datetime.timedelta(days=30)
        records = await activity_db.aggregate([{"$match": {"user_id": target_id}}, {"$group": {"_id": "$date", "total": {"$sum": "$message_count"}}}]).to_list(length=None)
        d_count, w_count, m_count = 0, 0, 0
        for r in records:
            try:
                r_date = datetime.date.fromisoformat(r["_id"])
                if r_date == today:
                    d_count += r["total"]
                if r_date >= week_ago:
                    w_count += r["total"]
                if r_date >= month_ago:
                    m_count += r["total"]
            except Exception:
                pass
        await send_msg(message.chat.id, f"{pe('📈')} <b>Activity Report for <a href='tg://user?id={target_id}'>{safe_name}</a> (<code>{target_id}</code>)</b>:\n\n{pe('📅')} <b>Today:</b> {d_count} msgs\n{pe('📅')} <b>This Week:</b> {w_count} msgs\n{pe('📅')} <b>This Month:</b> {m_count} msgs", reply_to=message.id)
    except Exception as e:
        await send_msg(message.chat.id, f"{pe('⚠️')} Error: {e}", reply_to=message.id)


@app.on_message(filters.command("affiliatecheck"))
async def affiliatecheck_cmd(client: Client, message: Message):
    if not message.from_user or not await is_admin(message.from_user.id):
        return
    target_id, safe_name = None, "User"
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        safe_name = html.escape(message.reply_to_message.from_user.first_name or "User")
    elif len(message.command) > 1:
        try:
            user_info = await asyncio.wait_for(app.get_users(message.command[1]), timeout=3)
            target_id, safe_name = user_info.id, html.escape(user_info.first_name or "User")
        except Exception:
            try:
                target_id = int(message.command[1])
            except Exception:
                return await send_msg(message.chat.id, f"{pe('⚠️')} Invalid User ID or Username.", reply_to=message.id)
    else:
        return await send_msg(message.chat.id, f"{pe('⚠️')} Usage: Reply to user or use /affiliatecheck [username/id]", reply_to=message.id)
    if not target_id:
        return
    u_doc = await users_db.find_one({"user_id": target_id})
    if not u_doc:
        return await send_msg(message.chat.id, f"{pe('❌')} User not found in database.", reply_to=message.id)
    invites, left, bal = len(u_doc.get("affiliates", [])), len(u_doc.get("left_affiliates", [])), u_doc.get("balance", 0.0)
    await send_msg(message.chat.id, f"{pe('📊')} <b>Affiliate Check for <a href='tg://user?id={target_id}'>{safe_name}</a></b>:\n\n{pe('👥')} Active Invites: {invites}\n{pe('❌')} Left Invites: {left}\n{pe('💰')} Wallet Balance: {usd(bal)}", reply_to=message.id)


# ================= INLINE ROUTER =================
@app.on_callback_query()
async def cb_router(client: Client, call: CallbackQuery):
    cb_id = call.id
    data = call.data or ""
    uid = call.from_user.id
    msg = call.message
    if not msg:
        return await answer_cb(cb_id)
    chat_id = msg.chat.id
    msg_id = msg.id
    is_private = (msg.chat.type == enums.ChatType.PRIVATE)

    if await is_bot_banned(uid):
        return await answer_cb(cb_id, "You are banned from using this bot.", show_alert=True)

    if await check_double_cb(uid, f"{chat_id}:{msg_id}:{data}"):
        return await answer_cb(cb_id, show_alert=False)

    if data == "check_fsub":
        if await is_user_subscribed(client, uid):
            await answer_cb(cb_id, "Verified! Welcome.", show_alert=False)
            user = await get_or_create_user(uid, call.from_user)
            lang = await get_lang(uid)
            welcome_body = TR[lang]["welcome"].format(tag=REQUIRED_USERNAME_TAG, link=user.get("bio_link", "No Link Generated"))
            return await edit_msg(chat_id, msg_id, welcome_body, markup=get_main_menu(lang), owner_id=uid)
        return await answer_cb(cb_id, "Please join both Channel and Group first!", show_alert=True)

    shared_prefixes = ("pvp_join:", "rain_join_", "aff_approve_", "aff_reject_", "ldb_", "gw_enter:", "gw_cap:")
    owner = msg_owner.get((chat_id, msg_id))
    if owner and owner != uid and not data.startswith(shared_prefixes):
        return await answer_cb(cb_id, "This button is not yours!", show_alert=True)

    if data == "claim_bonus":
        now = time.time()
        user = await get_or_create_user(uid, call.from_user)
        last_claim = float(user.get("last_bonus_claim", 0) or 0)
        if last_claim > 0 and (now - last_claim) < BONUS_COOLDOWN_SECONDS:
            rem = int(BONUS_COOLDOWN_SECONDS - (now - last_claim))
            mins, secs = divmod(rem, 60)
            hrs, mins = divmod(mins, 60)
            time_str = f"{hrs}h {mins}m {secs}s" if hrs > 0 else f"{mins}m {secs}s"
            return await answer_cb(cb_id, f"Bonus can be claimed every 4 hours! Time left: {time_str}", show_alert=True)

        total_aff = len(user.get("affiliates", []))
        offset = int(user.get("bonus_ref_offset", 0) or 0)
        bonus_refs = max(0, total_aff - offset)
        reward_coins = calc_bonus_coins(bonus_refs)

        await users_db.update_one(
            {"user_id": uid},
            {"$set": {"last_bonus_claim": now, "bonus_ref_offset": total_aff}, "$inc": {"coin_balance": reward_coins}}
        )
        await answer_cb(cb_id, f"Bonus claimed! +{reward_coins:,} Coins added.", show_alert=True)
        return await edit_msg(
            chat_id,
            msg_id,
            f"{pe('✅')} <b>Bonus Claimed!</b>\n\n"
            f"<b>+{reward_coins:,} Coins</b> have been added to your coin balance "
            f"(<b>{BASE_BONUS_COINS:,}</b> base + <b>{bonus_refs * EXTRA_REF_COINS:,}</b> referral bonus from <b>{bonus_refs}</b> referrals).\n"
            f"Your <b>4-hour</b> bonus timer has been reset!",
            markup=None
        )

    if not data.startswith(("rain_join_", "aff_approve_", "aff_reject_", "gw_enter:", "gw_cap:")):
        await answer_cb(cb_id, show_alert=False)

    if data.startswith("gw_"):
        if not await is_admin(uid):
            return await answer_cb(cb_id, "This button is not yours!", show_alert=True)
        wiz = giveaway_wizard.get(uid)
        if not wiz:
            giveaway_wizard[uid] = {
                "step": None,
                "dm_chat_id": chat_id,
                "wizard_msg_id": msg_id,
                "data": {
                    "target_chat_id": TRACK_GROUP_ID,
                    "host": "", "amount": "", "title": "",
                    "banner_photo_id": None,
                    "force_channel": None, "force_group": True,
                    "cond_name": False, "cond_bio": False, "cond_premium": False,
                    "min_messages": 0, "captcha": True, "notes": "", "duration_str": ""
                }
            }
            wiz = giveaway_wizard[uid]
        wiz["dm_chat_id"] = chat_id
        gw_data = wiz["data"]

        if data == "gw_start_new":
            wiz["step"] = "confirm_chat"
            target_grp = gw_data.get("target_chat_id", TRACK_GROUP_ID)
            txt = f"{pe('🎉')} <b>Start New Giveaway</b>\n\nTarget Group ID: <code>{target_grp}</code> (Mandatory)\n\nConfirm this chat to continue?"
            await update_giveaway_wizard_msg(uid, txt, kb([("Confirm", "gw_confirm_chat", "success"), ("Back", "gw_back_menu", "danger")]))
        elif data == "gw_back_menu":
            wiz["step"] = None
            await update_giveaway_wizard_msg(uid, f"{pe('🎉')} <b>GIVEAWAY MANAGER</b>\n\nChoose an option below:", kb(
                [("Start New Giveaway", "gw_start_new", "success", "🎉")],
                [("Manage Giveaway", "gw_manage", "primary", "⚙️")]
            ))
        elif data == "gw_confirm_chat":
            wiz["step"] = "wait_host"
            await update_giveaway_wizard_msg(uid, f"{pe('✏️')} <b>Enter Host Name</b> (e.g. <code>@redcube</code> or host name):", kb([("Cancel", "gw_back_menu", "danger")]))
        elif data in ("gw_skip_banner", "gw_use_pfp"):
            if data == "gw_skip_banner":
                gw_data["banner_photo_id"] = None
                prefix_txt = ""
            else:
                pfp_id = await _fetch_banner_file_id(client, gw_data.get("target_chat_id", TRACK_GROUP_ID)) or await _fetch_banner_file_id(client, uid)
                gw_data["banner_photo_id"] = pfp_id
                prefix_txt = "<i>PFP banner attached.</i>\n\n" if pfp_id else "<i>No PFP found, continuing without banner.</i>\n\n"

            wiz["step"] = "wait_force_channel"
            await update_giveaway_wizard_msg(
                uid,
                f"{prefix_txt}{pe('📢')} <b>Force Join Channel Setup</b>\n\nSend the <b>Channel @username or Channel ID</b> that users must join to participate (Group join is already mandatory), or tap <b>Skip Channel</b>:",
                kb([("Skip Channel", "gw_fsub_skip", "primary"), ("Cancel", "gw_back_menu", "danger")]),
                force_new=True
            )
        elif data == "gw_fsub_skip":
            gw_data["force_channel"] = None
            gw_data["force_group"] = True
            wiz["step"] = "conditions"
            c_txt, c_kb = build_giveaway_wizard_conditions_ui(uid, gw_data)
            await update_giveaway_wizard_msg(uid, c_txt, c_kb)
        elif data == "gw_toggle_name":
            gw_data["cond_name"] = not gw_data.get("cond_name", False)
            c_txt, c_kb = build_giveaway_wizard_conditions_ui(uid, gw_data)
            await update_giveaway_wizard_msg(uid, c_txt, c_kb)
        elif data == "gw_toggle_bio":
            gw_data["cond_bio"] = not gw_data.get("cond_bio", False)
            c_txt, c_kb = build_giveaway_wizard_conditions_ui(uid, gw_data)
            await update_giveaway_wizard_msg(uid, c_txt, c_kb)
        elif data == "gw_toggle_prem":
            gw_data["cond_premium"] = not gw_data.get("cond_premium", False)
            c_txt, c_kb = build_giveaway_wizard_conditions_ui(uid, gw_data)
            await update_giveaway_wizard_msg(uid, c_txt, c_kb)
        elif data == "gw_ask_minmsg":
            wiz["step"] = "wait_minmsg"
            await update_giveaway_wizard_msg(uid, f"{pe('✏️')} <b>Enter minimum required messages in group</b> (number), or tap <b>Skip</b>:", kb([("Skip", "gw_skip_minmsg", "primary")]))
        elif data == "gw_skip_minmsg":
            gw_data["min_messages"] = 0
            wiz["step"] = "conditions"
            c_txt, c_kb = build_giveaway_wizard_conditions_ui(uid, gw_data)
            await update_giveaway_wizard_msg(uid, c_txt, c_kb)
        elif data == "gw_toggle_cap":
            gw_data["captcha"] = not gw_data.get("captcha", True)
            c_txt, c_kb = build_giveaway_wizard_conditions_ui(uid, gw_data)
            await update_giveaway_wizard_msg(uid, c_txt, c_kb)
        elif data == "gw_to_notes":
            wiz["step"] = "wait_notes"
            await update_giveaway_wizard_msg(uid, f"{pe('✏️')} <b>Enter any extra notes</b> for the giveaway post, or tap <b>Skip</b>:", kb([("Skip", "gw_skip_notes", "primary")]))
        elif data == "gw_skip_notes":
            gw_data["notes"] = ""
            wiz["step"] = "wait_duration"
            await update_giveaway_wizard_msg(uid, f"{pe('⏱')} <b>Enter giveaway duration</b> (e.g. <code>1m</code>, <code>1h</code>, <code>1d</code>):", kb([("Cancel", "gw_back_menu", "danger")]))
        elif data == "gw_manage":
            active_gws = await giveaways_db.find({"status": "active"}).to_list(10)
            if not active_gws:
                await update_giveaway_wizard_msg(uid, f"{pe('ℹ️')} <b>No active giveaways right now.</b>", kb([("Back", "gw_back_menu", "danger")]))
            else:
                rows = []
                for g in active_gws:
                    rows.append([(f"End: {g.get('title', g['_id'])}", f"gw_end_now:{g['_id']}", "danger")])
                rows.append([("Back", "gw_back_menu", "primary")])
                await update_giveaway_wizard_msg(uid, f"{pe('⚙️')} <b>Manage Active Giveaways</b>\n\nSelect a giveaway to end immediately:", kb(*rows))
        elif data.startswith("gw_end_now:"):
            target_gw_id = data.split(":", 1)[1]
            await finalize_giveaway(target_gw_id)
            await update_giveaway_wizard_msg(uid, f"{pe('✅')} Giveaway <code>{html.escape(target_gw_id)}</code> ended and winner announced.", kb([("Back", "gw_back_menu", "primary")]))
        return

    if data.startswith("gw_enter:"):
        parts = data.split(":")
        gw_id = parts[1]
        aff_name = parts[2] if len(parts) > 2 and parts[2] else None
        ok, status_msg = await record_giveaway_entry(client, uid, call.from_user, gw_id, aff_name=aff_name)
        return await answer_cb(cb_id, status_msg, show_alert=True)

    elif data.startswith("gw_cap:"):
        _, gw_id, picked_str = data.split(":", 2)
        cap = giveaway_captcha_sessions.get((uid, gw_id))
        if not cap or time.time() - cap["ts"] > 120:
            return await answer_cb(cb_id, "Captcha expired. Click Enter giveaway again.", show_alert=True)
        if int(picked_str) != int(cap["ans"]):
            return await answer_cb(cb_id, "Wrong answer! Try again.", show_alert=True)
        aff_name = cap.get("aff_name")
        giveaway_captcha_sessions.pop((uid, gw_id), None)
        gw = await giveaways_db.find_one({"_id": gw_id, "status": "active"})
        if not gw:
            return await answer_cb(cb_id, "Giveaway ended.", show_alert=True)
        update_ops = {"$addToSet": {"participants": uid}}
        if aff_name:
            update_ops["$addToSet"][f"affiliates_by_name.{aff_name}"] = uid
        await giveaways_db.update_one({"_id": gw_id}, update_ops)
        await edit_msg(chat_id, msg_id, f"{pe('✅')} <b>Captcha passed!</b> You are now entered in <b>{html.escape(gw.get('title', 'Giveaway'))}</b>.", markup=None)
        return await answer_cb(cb_id, "Entered giveaway! 🎉", show_alert=True)

    if data.startswith("aff_approve_"):
        if not await is_admin(uid):
            return await answer_cb(cb_id, "You are not an admin!", show_alert=True)
        _, _, user_id_str, inviter_id_str, target_chat_str = data.split("_")
        user_id, inviter_id, target_chat = int(user_id_str), int(inviter_id_str), int(target_chat_str)
        try:
            await client.approve_chat_join_request(target_chat, user_id)
            conf = await get_config()
            await users_db.update_one({"user_id": inviter_id}, {"$addToSet": {"affiliates": user_id}, "$inc": {"coin_balance": EXTRA_REF_COINS}})
            await users_db.update_one({"user_id": user_id}, {"$set": {"ever_joined_group": True}}, upsert=True)
            inviter_data = await get_or_create_user(inviter_id)
            new_count = len(inviter_data.get("affiliates", [])) + 1
            if new_count % conf["affiliate_req"] == 0:
                reward = conf["affiliate_reward"]
                await users_db.update_one({"user_id": inviter_id}, {"$inc": {"balance": reward}})
                reward_msg = f"{pe('🎉')} <b>Congratulations!</b> You reached {conf['affiliate_req']} members. ${reward} added!"
                try:
                    await send_msg(inviter_id, reward_msg)
                except Exception:
                    pass
            try:
                await send_msg(inviter_id, f"{pe('🪙')} <b>Referral Approved!</b> You received <b>+{EXTRA_REF_COINS} Coins</b>.")
            except Exception:
                pass
            if conf.get("refferal_race_enabled", False):
                await users_db.update_one({"user_id": inviter_id}, {"$inc": {"weekly_referrals": 1}})
            await edit_msg(chat_id, msg_id, f"{msg.text}\n\n{pe('✅')} <b>Approved by {mention(uid)}</b>", markup=None)
            await answer_cb(cb_id, "Request Approved!", show_alert=True)
        except Exception as e:
            await answer_cb(cb_id, f"Error: {e}", show_alert=True)
        return

    elif data.startswith("aff_reject_"):
        if not await is_admin(uid):
            return await answer_cb(cb_id, "You are not an admin!", show_alert=True)
        _, _, user_id_str, inviter_id_str, target_chat_str = data.split("_")
        user_id, inviter_id, target_chat = int(user_id_str), int(inviter_id_str), int(target_chat_str)
        try:
            await client.decline_chat_join_request(target_chat, user_id)
            await users_db.update_one({"user_id": inviter_id}, {"$addToSet": {"fake_affiliates": user_id}})
            await edit_msg(chat_id, msg_id, f"{msg.text}\n\n{pe('❌')} <b>Rejected by {mention(uid)}</b>", markup=None)
            await answer_cb(cb_id, "Request Rejected!", show_alert=True)
        except Exception as e:
            await answer_cb(cb_id, f"Error: {e}", show_alert=True)
        return

    if data == "del":
        await del_msg(chat_id, msg_id)
        return

    if data.startswith("back_mode:"):
        if is_private:
            return
        _, game, stake = data.split(":")
        await edit_msg(chat_id, msg_id, mode_screen_text(game), markup=mode_screen_kb(game, float(stake)), owner_id=uid)
        return

    elif data.startswith("mode:"):
        if is_private:
            return
        _, game, stake, mode = data.split(":")
        await edit_msg(chat_id, msg_id, target_screen_text(game), markup=target_screen_kb(game, float(stake), mode), owner_id=uid)
        return

    elif data.startswith("tgt:"):
        if is_private:
            return
        _, game, stake, mode, target = data.split(":")
        base = f"{game}:{stake}:{mode}:{target}"
        await edit_msg(chat_id, msg_id, f"{game_pe(game)} <b>{game.title()} · {usd(float(stake))}</b>\n<b>Player:</b> {mention(uid)}\n<b>Mode: {get_mode_label(mode)} ({target} points)</b>\n\n<b>Choose your opponent:</b>", markup=kb([("Play vs Bot", f"opp:{base}:bot", "success", "🤖"), ("Play PvP", f"opp:{base}:pvp", "primary", "👤")], [("Back", f"mode:{game}:{stake}:{mode}", "danger", "❌")]), owner_id=uid)
        return

    elif data.startswith("opp:"):
        if is_private:
            return
        _, game, stake, mode, target, who = data.split(":")
        stake, target = float(stake), int(target)
        if uid in busy:
            return await answer_cb(cb_id, "Finish your current game first!", show_alert=True)
        active_group_games = sum(1 for s in matches.values() if s.get("chat_id") == chat_id and s.get("status") in ["waiting", "playing"])
        if active_group_games >= 3:
            return await answer_cb(cb_id, "Please wait for the active games to end! Maximum 3 games allowed at once.", show_alert=True)

        user = await get_or_create_user(uid, call.from_user)
        bal = float(user.get("coin_balance", 0.0))
        if bal < stake:
            return await answer_cb(cb_id, f"Not enough coins! Current balance: {usd(bal)}", show_alert=True)
        try:
            gid = await db_open_game(uid, game, mode, stake, opponent=0 if who == "bot" else -1)
        except ValueError as e:
            return await answer_cb(cb_id, str(e), show_alert=True)

        busy.add(uid)
        user_match[uid] = gid

        if who == "bot":
            m_obj = Match(game, mode, target, stake, (uid, 0))
            sess = {"gid": gid, "type": "bot", "status": "playing", "chat_id": chat_id, "game": game, "mode": mode, "target": target, "stake": stake, "ua": uid, "ub": 0, "match": m_obj, "turn_uid": uid, "u_rolls": [], "b_rolls": [], "rolling": False, "round_num": 1, "last_action": time.time(), "lock": asyncio.Lock(), "prompt_msg_id": msg_id}
            matches[gid] = sess
            await edit_msg(chat_id, msg_id, f"{pe('🌊')} <b>The game has started</b>\n\n<b>Player 1:</b> {mention(uid)}\n<b>Player 2:</b> {pe('🤖')} <b>{html.escape(CASINO_NAME)}</b>\n<b>Bet: {usd(stake)}</b> {pe('🪙')}\n<b>Mode: {get_mode_label(mode)} — {target} points</b>\n\n<b>Roll the {game.title()}</b> {game_pe(game)}", markup=turn_kb(sess, show_bot_first=True, is_round_start=True), owner_id=uid)
        else:
            sess = {"gid": gid, "type": "pvp", "status": "waiting", "chat_id": chat_id, "game": game, "mode": mode, "target": target, "stake": stake, "ua": uid, "ub": 0, "u_rolls": [], "b_rolls": [], "rolling": False, "round_num": 1, "created_at": time.time(), "last_action": time.time(), "lock": asyncio.Lock(), "prompt_msg_id": msg_id}
            matches[gid] = sess
            await edit_msg(chat_id, msg_id, f"{pe('🎮')} <b>PvP Match Created</b>\n\n<b>Player 1:</b> {mention(uid)}\n<b>Game:</b> {game_pe(game)} <b>{game.title()}</b>\n<b>Bet: {usd(stake)}</b> {pe('🪙')}\n<b>Mode: {get_mode_label(mode)} — {target} points</b>\n\n<i>Click «Accept game» to start PvP!</i>", markup=kb([("Accept game", f"pvp_join:{gid}", "success", "✅")], [("Cancel game", f"cancel_pvp:{gid}", "danger", "❌")]), owner_id=uid)
        return

    elif data.startswith("pvp_join:"):
        gid = data.split(":")[1]
        sess = matches.get(gid)
        if not sess or sess.get("status") != "waiting":
            return await answer_cb(cb_id, "This match is no longer available!", show_alert=True)
        if uid == sess["ua"]:
            return await answer_cb(cb_id, "You cannot accept your own match!", show_alert=True)
        if uid in busy:
            return await answer_cb(cb_id, "Finish your current game first!", show_alert=True)

        user = await get_or_create_user(uid, call.from_user)
        bal = float(user.get("coin_balance", 0.0))
        stake = sess["stake"]
        if bal < stake:
            return await answer_cb(cb_id, f"Not enough coins! Need {usd(stake)}.", show_alert=True)
        try:
            gid_b = await db_open_game(uid, sess["game"], sess["mode"], stake, opponent=sess["ua"])
        except ValueError as e:
            return await answer_cb(cb_id, str(e), show_alert=True)

        await games_db.update_one({"_id": ObjectId(gid)}, {"$set": {"opponent": uid}})
        sess["ub"] = uid
        sess["gid_b"] = gid_b
        sess["status"] = "playing"
        sess["match"] = Match(sess["game"], sess["mode"], sess["target"], stake, (sess["ua"], uid))
        sess["turn_uid"] = sess["ua"]
        sess["last_action"] = time.time()
        busy.add(uid)
        user_match[uid] = gid

        start_txt = f"{pe('🌊')} <b>The game has started</b>\n\n<b>Player 1:</b> {mention(sess['ua'])}\n<b>Player 2:</b> {mention(uid)}\n<b>Bet: {usd(stake)}</b> {pe('🪙')}\n<b>Mode: {get_mode_label(sess['mode'])} — {sess['target']} points</b>\n\n{mention(sess['ua'])}, <b>your turn!</b>"
        asyncio.create_task(clear_buttons(chat_id, msg_id))
        sent = await send_msg(chat_id, start_txt, markup=turn_kb(sess, show_bot_first=False, is_round_start=True), owner_id=sess["ua"])
        sess["prompt_msg_id"] = sent["message_id"] if sent else 0
        return

    elif data.startswith("cancel_pvp:"):
        gid = data.split(":")[1]
        sess = matches.get(gid)
        if not sess or sess.get("status") != "waiting" or sess["ua"] != uid:
            return
        await db_void_game(gid)
        matches.pop(gid, None)
        user_match.pop(uid, None)
        busy.discard(uid)
        await edit_msg(chat_id, msg_id, f"{pe('⭕️')} <b>PvP match cancelled by</b> {mention(uid)} — <b>stake refunded.</b>", owner_id=uid)
        return

    elif data.startswith("roll:"):
        _, gid_str, order = data.split(":")
        sess = matches.get(gid_str)
        if not sess or sess.get("status") != "playing":
            return
        if sess.get("turn_uid") != uid:
            return
        needed = sess["match"].rolls_needed
        my_rolls = sess["u_rolls"] if uid == sess["ua"] else sess["b_rolls"]
        if sess.get("rolling") or len(my_rolls) >= needed:
            return
        asyncio.create_task(handle_roll_button(sess, uid, order, reply_to_id=msg_id))
        return

    elif data.startswith("cashout:"):
        gid = data.split(":")[1]
        sess = matches.get(gid)
        if not sess or sess["ua"] != uid or sess.get("rolling"):
            return
        cashout_amt = calc_cashout(sess["stake"], sess["match"].score[0], sess["match"].score[1], sess["target"])
        if cashout_amt <= 0:
            return
        asyncio.create_task(clear_buttons(chat_id, msg_id))
        await finish_match(sess, cashout_amt, cashed_out=True, reply_to_id=msg_id)
        return

    if data == "menu_main":
        if not await pass_fsub(client, call):
            return
        if uid in user_states:
            del user_states[uid]
        user = await get_or_create_user(uid, call.from_user)
        lang = await get_lang(uid)
        welcome_body = TR[lang]["welcome"].format(tag=REQUIRED_USERNAME_TAG, link=user.get("bio_link", "No Link Generated"))
        await edit_msg(chat_id, msg_id, welcome_body, markup=get_main_menu(lang), owner_id=uid)
    elif data == "wd_method_redcube":
        user_states[uid] = {"state": "wait_for_wd_amount", "method": "Redcube Wallet"}
        await edit_msg(chat_id, msg_id, f"{pe('🏦')} <b>Method: Redcube Wallet</b>\n\n{pe('✏️')} <b>Please send your Withdraw Amount:</b>", owner_id=uid)
        return await answer_cb(cb_id)
    elif data == "menu_verify":
        if not await pass_fsub(client, call):
            return
        user_data = await get_or_create_user(uid, call.from_user)
        lang = await get_lang(uid)
        try:
            chat_info = await asyncio.wait_for(app.get_chat(uid), timeout=5)
        except Exception:
            chat_info = None
        full_name = f"{call.from_user.first_name or ''} {call.from_user.last_name or ''}".lower()
        name_ok = REQUIRED_USERNAME_TAG.lower() in full_name
        bio_ok = bool(chat_info and user_data.get("bio_link") in (chat_info.bio or ""))
        markup = kb([(TR[lang]["btn_back"], "menu_main", "danger", "🔙")])
        if name_ok and bio_ok:
            await users_db.update_one({"user_id": uid}, {"$set": {"verified": True}})
            await edit_msg(chat_id, msg_id, TR[lang]["verify_ok"], markup=markup, owner_id=uid)
        else:
            await edit_msg(chat_id, msg_id, TR[lang]["verify_fail"].format(tag=REQUIRED_USERNAME_TAG), markup=markup, owner_id=uid)

    elif data == "menu_affiliate":
        if not await pass_fsub(client, call):
            return
        user = await get_or_create_user(uid, call.from_user)
        lang = await get_lang(uid)
        conf = await get_config()
        if not conf.get("affiliate_enabled", True):
            markup = kb([(TR[lang]["btn_back"], "menu_main", "danger", "🔙")])
            return await edit_msg(chat_id, msg_id, TR[lang]["affiliate_disabled"], markup=markup, owner_id=uid)
        invite_link = user.get("affiliate_link")
        if not invite_link:
            try:
                invite = await asyncio.wait_for(
                    app.create_chat_invite_link(TRACK_GROUP_ID, name=f"Affiliate_{uid}", creates_join_request=True),
                    timeout=5
                )
                invite_link = invite.invite_link
                await users_db.update_one({"user_id": uid}, {"$set": {"affiliate_link": invite_link}})
            except Exception:
                return await send_msg(chat_id, "Error creating link. Bot must be admin.")
        markup = kb([("Affiliate Status", "menu_aff_stats", "primary", "📊")], [(TR[lang]["btn_back"], "menu_main", "danger", "🔙")])
        await edit_msg(chat_id, msg_id, TR[lang]["affiliate_link"].format(link=invite_link), markup=markup, disable_web_page_preview=True, owner_id=uid)

    elif data == "menu_aff_stats":
        if not await pass_fsub(client, call):
            return
        user = await get_or_create_user(uid, call.from_user)
        lang = await get_lang(uid)
        conf = await get_config()
        markup = kb([(TR[lang]["btn_back"], "menu_affiliate", "danger", "🔙")])
        await edit_msg(chat_id, msg_id, TR[lang]["affiliate_stats"].format(real=len(user.get("affiliates", [])), left=len(user.get("left_affiliates", [])), fake=len(user.get("fake_affiliates", [])), reward=conf["affiliate_reward"], req=conf["affiliate_req"]), markup=markup, owner_id=uid)

    elif data == "menu_support":
        if not await pass_fsub(client, call):
            return
        lang = await get_lang(uid)
        if uid in active_tickets or uid in pending_tickets:
            return await send_msg(chat_id, "You already have an active/pending ticket.")
        user_states[uid] = {"state": "wait_for_support"}
        markup = kb([(TR[lang]["btn_back"], "menu_main", "danger", "🔙")])
        await edit_msg(chat_id, msg_id, TR[lang]["sup_ask"], markup=markup, owner_id=uid)

    elif data == "menu_draw":
        if not await pass_fsub(client, call):
            return
        lang = await get_lang(uid)
        conf = await get_config()
        markup = kb([(TR[lang]["btn_back"], "menu_main", "danger", "🔙")])
        if not conf.get("draw_enabled", True):
            return await edit_msg(chat_id, msg_id, f"{pe('⚠️')} <b>Draw now disabled, soon coming.</b>", markup=markup, owner_id=uid)
        draw_data = await config_db.find_one({"_id": "latest_draw"})
        if not draw_data or not draw_data.get("winners"):
            return await edit_msg(chat_id, msg_id, TR[lang]["draw_none"], markup=markup, owner_id=uid)
        winners_text = ""
        for i, wid in enumerate(draw_data["winners"], 1):
            if await is_bot_banned(wid):
                continue
            u_doc = await users_db.find_one({"user_id": wid})
            name = await fetch_real_name(wid, u_doc.get("name") if u_doc else None)
            winners_text += f"{i}. {html.escape(name)}\n"
        text = TR[lang]["draw_res"].format(time=draw_data["time"], total=draw_data["total"], amt=draw_data.get("amount", 2.0), winners=winners_text or "None\n")
        await edit_msg(chat_id, msg_id, text, markup=markup, disable_web_page_preview=True, owner_id=uid)

    elif data == "menu_lang":
        if not await pass_fsub(client, call):
            return
        lang = await get_lang(uid)
        btns = kb([("English", "lang_en", "primary", "🇬🇧"), ("Русский", "lang_ru", "danger", "🇷🇺")], [("Hindi", "lang_hi", "success", "🇮🇳")], [(TR[lang]["btn_back"], "menu_main", "danger", "🔙")])
        await edit_msg(chat_id, msg_id, "Select your language / Выберите язык / Choose language:", markup=btns, owner_id=uid)

    elif data.startswith("lang_"):
        if not await pass_fsub(client, call):
            return
        new_lang = data.split("_")[1]
        if new_lang not in TR:
            new_lang = "en"
        await users_db.update_one({"user_id": uid}, {"$set": {"lang": new_lang}})
        user_langs[uid] = new_lang
        user = await get_or_create_user(uid, call.from_user)
        welcome_body = TR[new_lang]["welcome"].format(tag=REQUIRED_USERNAME_TAG, link=user.get("bio_link", ""))
        await edit_msg(chat_id, msg_id, TR[new_lang]["lang_set"])
        await asyncio.sleep(0.15)
        await send_msg(chat_id, welcome_body, markup=get_main_menu(new_lang), disable_web_page_preview=True, owner_id=uid)

    elif data == "menu_leaderboard":
        if is_private and not await pass_fsub(client, call):
            return
        if not is_private and not await is_group_authorized(chat_id):
            return
        lang = await get_lang(uid)
        tr = TR.get(lang, TR["en"])
        text = await generate_new_leaderboard("message")
        row1 = [(tr["btn_coins"], "ldb_coins", "primary", "🪙"), (tr["btn_messages"], "ldb_messages", "success", "💬")]
        btns = kb(row1, [(tr["btn_back"], "menu_main", "danger", "🔙")]) if is_private else kb(row1)
        await edit_msg(chat_id, msg_id, text, markup=btns, disable_web_page_preview=True, owner_id=uid)

    elif data.startswith("ldb_"):
        metric = data.split("_")[1]
        lang = await get_lang(uid)
        tr = TR.get(lang, TR["en"])
        text = await generate_new_leaderboard(metric)
        c_style = "success" if metric == "coins" else "primary"
        m_style = "success" if metric in ["message", "messages"] else "primary"
        row1 = [(tr["btn_coins"], "ldb_coins", c_style, "🪙"), (tr["btn_messages"], "ldb_messages", m_style, "💬")]
        btns = kb(row1, [(tr["btn_back"], "menu_main", "danger", "🔙")]) if is_private else kb(row1)
        try:
            await edit_msg(chat_id, msg_id, text, markup=btns, disable_web_page_preview=True)
        except Exception:
            pass
        return await answer_cb(cb_id)

    elif data.startswith("tktacc_"):
        if not await is_admin(uid):
            return
        target_id = int(data.split("_")[1])
        if target_id not in pending_tickets:
            return await send_msg(chat_id, "This ticket is no longer pending or has been closed.")
        pending_tickets.pop(target_id, None)
        active_tickets[target_id] = uid
        active_tickets[uid] = target_id
        admin_name = html.escape(call.from_user.first_name or "Admin")
        update_text = f"{pe('✅')} <b>Ticket Accepted & Resolved by <a href='tg://user?id={uid}'>{admin_name}</a></b>"
        if target_id in admin_ticket_msgs:
            for aid, mid in admin_ticket_msgs[target_id].items():
                try:
                    await edit_msg(aid, mid, update_text, markup=None)
                except Exception:
                    pass
            del admin_ticket_msgs[target_id]
        else:
            await edit_msg(chat_id, msg_id, update_text, markup=None)
        t_lang = await get_lang(target_id)
        await send_msg(target_id, TR[t_lang]["tkt_joined"])
        await send_msg(uid, f"{pe('✅')} Session Started with <code>{target_id}</code>.\nUse /close to end.")

    elif data.startswith("tktrej_"):
        if not await is_admin(uid):
            return
        target_id = int(data.split("_")[1])
        ticket_id = re.search(r"#TKT\d+", msg.text or msg.caption or "").group(0) if re.search(r"#TKT\d+", msg.text or msg.caption or "") else "#TKT_UNKNOWN"
        pending_tickets.pop(target_id, None)
        admin_name = html.escape(call.from_user.first_name or "Admin")
        update_text = f"{pe('❌')} <b>Ticket Rejected by <a href='tg://user?id={uid}'>{admin_name}</a></b>"
        if target_id in admin_ticket_msgs:
            for aid, mid in admin_ticket_msgs[target_id].items():
                try:
                    await edit_msg(aid, mid, update_text, markup=None)
                except Exception:
                    pass
            del admin_ticket_msgs[target_id]
        else:
            await edit_msg(chat_id, msg_id, update_text, markup=None)
        t_lang = await get_lang(target_id)
        try:
            await send_msg(target_id, TR[t_lang]["tkt_rejected"].format(tkt=ticket_id))
        except Exception:
            pass

    elif data.startswith("wdone_"):
        if not await is_admin(uid):
            return
        _, target_id, amount = data.split("_")
        user_states[uid] = {"state": "wait_for_txlink", "target_id": int(target_id), "amount": amount}
        admin_name = html.escape(call.from_user.first_name or "Admin")
        update_text = f"{pe('✅')} <b>Withdrawal Processed by <a href='tg://user?id={uid}'>{admin_name}</a></b>"
        target_id = int(target_id)
        if target_id in admin_withdraw_msgs:
            for aid, mid in admin_withdraw_msgs[target_id].items():
                try:
                    await edit_msg(aid, mid, update_text, markup=None)
                except Exception:
                    pass
            del admin_withdraw_msgs[target_id]
        else:
            await edit_msg(chat_id, msg_id, update_text, markup=None)
        await send_msg(chat_id, f"{pe('✏️')} <b>Please type the Transaction Link for this withdrawal:</b>")

    elif data.startswith("wrej_"):
        if not await is_admin(uid):
            return
        _, target_id, amount = data.split("_")
        user_states[uid] = {"state": "wait_for_reason", "target_id": int(target_id), "amount": amount}
        admin_name = html.escape(call.from_user.first_name or "Admin")
        update_text = f"{pe('❌')} <b>Withdrawal Rejected by <a href='tg://user?id={uid}'>{admin_name}</a></b>"
        target_id = int(target_id)
        if target_id in admin_withdraw_msgs:
            for aid, mid in admin_withdraw_msgs[target_id].items():
                try:
                    await edit_msg(aid, mid, update_text, markup=None)
                except Exception:
                    pass
            del admin_withdraw_msgs[target_id]
        else:
            await edit_msg(chat_id, msg_id, update_text, markup=None)
        await send_msg(chat_id, f"{pe('✏️')} <b>Please type the reason for rejection:</b>")

    elif data.startswith("rain_join_"):
        if await is_bot_banned(uid):
            return await answer_cb(cb_id, "You are banned from participating in Rain events.", show_alert=True)
        event_id = data.split("_")[2]
        event = await rain_db.find_one({"_id": event_id})
        if not event:
            return await answer_cb(cb_id, "This event has ended!", show_alert=True)
        if uid in event.get("participants", []):
            return await answer_cb(cb_id, "You are already participating!", show_alert=True)
        min_msgs = event.get("min_msgs", 0)
        min_turnover = event.get("min_turnover", 0.0)
        activity = await activity_db.aggregate([{"$match": {"user_id": uid, "group_id": chat_id}}, {"$group": {"_id": None, "total": {"$sum": "$message_count"}}}]).to_list(1)
        total_sent = activity[0]["total"] if activity else 0
        if total_sent < min_msgs:
            return await answer_cb(cb_id, f"You need at least {min_msgs} messages in this group to participate!\n\nYou currently have {total_sent} messages.", show_alert=True)
        u_data = await get_or_create_user(uid)
        today = str(datetime.date.today())
        if u_data.get("last_wager_date") == today:
            turnover = float(u_data.get("daily_coin_wagered", 0.0))
        else:
            turnover = 0.0
        if turnover < min_turnover:
            return await answer_cb(cb_id, f"You need at least {usd(min_turnover)} turnover (wagered coins) to participate!\n\nYou currently have {usd(turnover)}.", show_alert=True)
        await answer_cb(cb_id, "You have successfully joined the Rain Event! 💧", show_alert=True)
        await rain_db.update_one({"_id": event_id}, {"$addToSet": {"participants": uid}})

    elif data.startswith("mines_bet:"):
        bet = float(data.split(":")[1])
        user = await get_or_create_user(uid)
        bal = float(user.get("coin_balance", 0))
        if bal < bet:
            return await answer_cb(cb_id, "Insufficient coin balance!", show_alert=True)
        await edit_msg(chat_id, msg_id, f"{pe('💲')} Bet: {usd(bet)}\n\n{pe('💣')} <b>Select the number of mines</b>", markup=get_mines_count_kb(bet), owner_id=uid)
        return await answer_cb(cb_id)

    elif data == "mines_change":
        user = await get_or_create_user(uid)
        bal = float(user.get("coin_balance", 0))
        conf = await get_config()
        min_bet = float(conf.get("min_bet", 1.0))
        msg_text = f"{pe('💣')} <b>Mines</b>\n\n{pe('⬆️')} Choose a bet or enter your own\nMinimum bet - {usd(min_bet)}\n\n{pe('🌀')} Current coin balance: {usd(bal)}"
        await edit_msg(chat_id, msg_id, msg_text, markup=get_mines_bet_kb(bal), owner_id=uid)
        return await answer_cb(cb_id)

    elif data.startswith("mines_start:"):
        _, bet_str, mines_str = data.split(":")
        bet, mines = float(bet_str), int(mines_str)
        user = await get_or_create_user(uid)
        bal = float(user.get("coin_balance", 0))
        if bal < bet:
            return await answer_cb(cb_id, "Insufficient coin balance!", show_alert=True)
        await users_db.update_one({"user_id": uid}, {"$inc": {"coin_balance": -bet}})
        mines_pos = random.sample(range(25), mines)
        mines_sessions[uid] = {
            "bet": bet, "mines": mines, "mines_pos": mines_pos,
            "opened": [], "chat_id": chat_id, "msg_id": msg_id,
            "lock": asyncio.Lock()
        }
        txt = f"{pe('💲')} Bet: {usd(bet)}\n{pe('💣')} Mines: {mines}\n{pe('💎')} Crystals opened: 0\n\n{pe('🏆')} Win: {usd(bet)}"
        await edit_msg(chat_id, msg_id, txt, markup=get_mines_board_kb(uid), owner_id=uid)
        return await answer_cb(cb_id)

    elif data.startswith("mines_click:"):
        idx = int(data.split(":")[1])
        sess = mines_sessions.get(uid)
        if not sess or sess["chat_id"] != chat_id or sess["msg_id"] != msg_id:
            return await answer_cb(cb_id, "Session expired.", show_alert=True)
        async with sess["lock"]:
            if idx in sess["opened"]:
                return await answer_cb(cb_id)
            if idx in sess["mines_pos"]:
                await update_coin_stats(uid, sess["bet"], 0)
                bal = float((await get_or_create_user(uid)).get("coin_balance", 0))
                txt = f"{pe('💲')} Bet: {usd(sess['bet'])}\n{pe('💣')} Mines: {sess['mines']}\n{pe('💎')} Crystals opened: {len(sess['opened'])}\n\n{pe('⭐')} Game over\n{pe('🏆')} Win: $0.00\n\n{pe('🌀')} Current coin balance: {usd(bal)}"
                await edit_msg(chat_id, msg_id, txt, markup=get_mines_board_kb(uid, reveal=True, explode_idx=idx), owner_id=uid)
                del mines_sessions[uid]
                return await answer_cb(cb_id, "💣 BOOM!", show_alert=True)
            else:
                sess["opened"].append(idx)
                hits = len(sess["opened"])
                max_safe = 25 - sess["mines"]
                mult = calc_mines_mult(sess["mines"], hits)
                win_amt = round(sess["bet"] * mult, 2)
                if hits >= max_safe:
                    await users_db.update_one({"user_id": uid}, {"$inc": {"coin_balance": win_amt}})
                    await update_coin_stats(uid, sess["bet"], max(0, win_amt - sess["bet"]))
                    bal = float((await get_or_create_user(uid)).get("coin_balance", 0))
                    txt = f"{pe('💲')} Bet: {usd(sess['bet'])}\n{pe('💣')} Mines: {sess['mines']}\n{pe('💎')} Crystals opened: {hits}\n\n{pe('⭐')} Max Win! (x{mult})\n{pe('🏆')} Win: {usd(win_amt)}\n\n{pe('🌀')} Current coin balance: {usd(bal)}"
                    await edit_msg(chat_id, msg_id, txt, markup=get_mines_board_kb(uid, reveal=True), owner_id=uid)
                    del mines_sessions[uid]
                    return await answer_cb(cb_id, f"🎉 Won {usd(win_amt)}!", show_alert=True)
                else:
                    txt = f"{pe('💲')} Bet: {usd(sess['bet'])}\n{pe('💣')} Mines: {sess['mines']}\n{pe('💎')} Crystals opened: {hits}\n\n{pe('🏆')} Win: {usd(win_amt)} (x{mult})"
                    await edit_msg(chat_id, msg_id, txt, markup=get_mines_board_kb(uid), owner_id=uid)
                    return await answer_cb(cb_id)

    elif data == "mines_cashout":
        sess = mines_sessions.get(uid)
        if not sess or sess["chat_id"] != chat_id or sess["msg_id"] != msg_id or len(sess["opened"]) == 0:
            return await answer_cb(cb_id, "Cannot cashout right now.", show_alert=True)
        async with sess["lock"]:
            hits = len(sess["opened"])
            mult = calc_mines_mult(sess["mines"], hits)
            win_amt = round(sess["bet"] * mult, 2)
            await users_db.update_one({"user_id": uid}, {"$inc": {"coin_balance": win_amt}})
            await update_coin_stats(uid, sess["bet"], max(0, win_amt - sess["bet"]))
            bal = float((await get_or_create_user(uid)).get("coin_balance", 0))
            txt = f"{pe('💲')} Bet: {usd(sess['bet'])}\n{pe('💣')} Mines: {sess['mines']}\n{pe('💎')} Crystals opened: {hits}\n\n{pe('⭐')} Game over (x{mult})\n{pe('🏆')} Win: {usd(win_amt)}\n\n{pe('🌀')} Current coin balance: {usd(bal)}"
            await edit_msg(chat_id, msg_id, txt, markup=get_mines_board_kb(uid, reveal=True), owner_id=uid)
            del mines_sessions[uid]
            return await answer_cb(cb_id, f"💸 Cashed out {usd(win_amt)}!", show_alert=True)


# ================= PRIVATE STATES & LIVE TICKET CHAT =================
@app.on_message(filters.private & ~filters.command(["start", "help", "lang", "verify", "affiliate", "leaderboard", "draw", "support", "withdraw", "close", "redraw", "addadmin", "removeadmin", "adminlist", "setprice", "togglewithdraw", "broadcast", "adminhelp", "daily", "weekly", "monthly", "check", "checkactivity", "affiliatecheck", "depo", "resetbal", "toggledraw", "drawsettings", "withdrawupdate", "toggleaffiliate", "revokeall", "balance", "bal", "profile", "stats", "rank", "myrank", "bonus", "tip", "addreffer", "race", "refferal", "report", "reportbot", "coinsreport", "balancereport", "givewayref", "affiliategiveway", "givewaycheck", "affiliategivewaycheck", "resetamount", "giveaway", "access", "revoke", "mines", "mns", "dice", "bowl", "basket", "bask", "football", "dart", "dices", "slot", "slots", "casino", "botban"]))
async def private_states(client: Client, message: Message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    if await is_bot_banned(user_id):
        return
    txt = (message.text or message.caption or "").strip()

    wiz = giveaway_wizard.get(user_id)
    if wiz and wiz.get("step") and await is_admin(user_id):
        step = wiz["step"]
        gw_data = wiz["data"]
        if step == "wait_host":
            if not txt:
                return await send_msg(message.chat.id, "Please send a valid Host name.", reply_to=message.id)
            gw_data["host"] = txt
            wiz["step"] = "wait_amount"
            await update_giveaway_wizard_msg(user_id, f"{pe('💰')} <b>Enter Prize Amount</b> (e.g. <code>$50 USDT</code> or <code>5000 Coins</code>):", kb([("Cancel", "gw_back_menu", "danger")]))
            return
        elif step == "wait_amount":
            if not txt:
                return await send_msg(message.chat.id, "Please send a valid Amount.", reply_to=message.id)
            gw_data["amount"] = txt
            wiz["step"] = "wait_title"
            await update_giveaway_wizard_msg(user_id, f"{pe('🏆')} <b>Enter Giveaway Title</b> (e.g. <code>WEEKEND GIVEAWAY</code>):", kb([("Cancel", "gw_back_menu", "danger")]))
            return
        elif step == "wait_title":
            if not txt:
                return await send_msg(message.chat.id, "Please send a valid Title.", reply_to=message.id)
            gw_data["title"] = txt
            wiz["step"] = "wait_banner"
            await update_giveaway_wizard_msg(
                user_id,
                f"{pe('🖼')} <b>Send Banner Photo</b> for the giveaway, tap <b>Use PFP</b>, or tap <b>Skip Banner</b>:",
                kb([("Use PFP", "gw_use_pfp", "success"), ("Skip Banner", "gw_skip_banner", "primary")])
            )
            return
        elif step == "wait_banner":
            if message.photo:
                gw_data["banner_photo_id"] = message.photo.file_id
                wiz["step"] = "wait_force_channel"
                await update_giveaway_wizard_msg(
                    user_id,
                    f"{pe('✅')} Banner saved!\n\n{pe('📢')} <b>Force Join Channel Setup</b>\nSend the <b>Channel @username or Channel ID</b> that users must join to participate (Group join is already mandatory), or tap <b>Skip Channel</b>:",
                    kb([("Skip Channel", "gw_fsub_skip", "primary"), ("Cancel", "gw_back_menu", "danger")]),
                    force_new=True
                )
            else:
                await send_msg(message.chat.id, f"{pe('⚠️')} Please send a photo or tap <b>Use PFP</b> / <b>Skip Banner</b>.", reply_to=message.id)
            return
        elif step == "wait_force_channel":
            chan_ref = _normalize_chat_ref(txt)
            if not chan_ref:
                return await send_msg(
                    message.chat.id,
                    f"{pe('❌')} <b>Invalid channel format!</b> Send a public channel <code>@username</code>, <code>https://t.me/channel</code>, or numeric Channel ID (e.g. <code>-1001234567890</code>).",
                    reply_to=message.id
                )
            ok_adm, chan_label, err_reason = await is_bot_admin_in_chat(client, chan_ref)
            if not ok_adm:
                return await send_msg(
                    message.chat.id,
                    f"{pe('❌')} <b>Bot is not an admin in the channel!</b>\n\n{err_reason or 'Please promote the bot as an admin in that channel and send the channel again.'}",
                    reply_to=message.id
                )
            gw_data["force_channel"] = chan_label or str(chan_ref)
            gw_data["force_group"] = True
            wiz["step"] = "conditions"
            c_txt, c_kb = build_giveaway_wizard_conditions_ui(user_id, gw_data)
            await update_giveaway_wizard_msg(
                user_id,
                f"{pe('✅')} Force join channel set to <b>{html.escape(gw_data['force_channel'])}</b> (Bot verified as admin).\n\n" + c_txt,
                c_kb,
                force_new=True
            )
            return
        elif step == "wait_minmsg":
            if not txt.isdigit():
                return await send_msg(message.chat.id, "Please enter a valid number (e.g. <code>20</code>).", reply_to=message.id)
            gw_data["min_messages"] = int(txt)
            wiz["step"] = "conditions"
            c_txt, c_kb = build_giveaway_wizard_conditions_ui(user_id, gw_data)
            await update_giveaway_wizard_msg(user_id, c_txt, c_kb)
            return
        elif step == "wait_notes":
            gw_data["notes"] = txt
            wiz["step"] = "wait_duration"
            await update_giveaway_wizard_msg(user_id, f"{pe('⏱')} <b>Enter giveaway duration</b> (e.g. <code>1m</code>, <code>1h</code>, <code>1d</code>):", kb([("Cancel", "gw_back_menu", "danger")]))
            return
        elif step == "wait_duration":
            dur_secs = parse_duration_seconds(txt)
            gw_id = f"gw_{int(time.time())}_{random.randint(100, 999)}"
            end_time = time.time() + dur_secs
            target_chat = gw_data.get("target_chat_id", TRACK_GROUP_ID)
            gw_doc = {
                "_id": gw_id,
                "status": "active",
                "created_by": user_id,
                "target_chat_id": target_chat,
                "host": gw_data["host"],
                "amount": gw_data["amount"],
                "title": gw_data["title"],
                "banner_photo_id": gw_data.get("banner_photo_id"),
                "force_channel": gw_data.get("force_channel"),
                "force_group": True,
                "cond_name": gw_data.get("cond_name", False),
                "cond_bio": gw_data.get("cond_bio", False),
                "cond_premium": gw_data.get("cond_premium", False),
                "min_messages": gw_data.get("min_messages", 0),
                "captcha": gw_data.get("captcha", True),
                "notes": gw_data.get("notes", ""),
                "end_time": end_time,
                "participants": [],
                "posts": []
            }
            post_text = build_giveaway_post_text(gw_doc)
            post_kb = kb([("Enter giveaway", f"gw_enter:{gw_id}", "success")])
            posted_locs = []
            banner_id = gw_doc.get("banner_photo_id")

            # Post to target group
            if banner_id:
                sent_grp = await send_photo_msg(target_chat, banner_id, caption=post_text, markup=post_kb)
                is_ph_grp = bool(sent_grp and "photo" in sent_grp)
            else:
                sent_grp = await send_msg(target_chat, post_text, markup=post_kb)
                is_ph_grp = False
            if sent_grp and "message_id" in sent_grp:
                posted_locs.append({"chat_id": target_chat, "message_id": sent_grp["message_id"], "is_photo": is_ph_grp})

            # Post to force join channel if configured
            f_chan = gw_doc.get("force_channel")
            if f_chan:
                if banner_id:
                    sent_ch = await send_photo_msg(f_chan, banner_id, caption=post_text, markup=post_kb)
                    is_ph_ch = bool(sent_ch and "photo" in sent_ch)
                else:
                    sent_ch = await send_msg(f_chan, post_text, markup=post_kb)
                    is_ph_ch = False
                if sent_ch and "message_id" in sent_ch:
                    posted_locs.append({"chat_id": f_chan, "message_id": sent_ch["message_id"], "is_photo": is_ph_ch})

            gw_doc["posts"] = posted_locs
            await giveaways_db.insert_one(gw_doc)
            giveaway_wizard.pop(user_id, None)
            asyncio.create_task(giveaway_countdown_task(gw_id))
            await send_msg(
                message.chat.id,
                f"{pe('✅')} <b>Giveaway Published & Running!</b>\n"
                f"• <b>ID:</b> <code>{gw_id}</code>\n"
                f"• <b>Group:</b> <code>{target_chat}</code> (Mandatory)\n"
                f"• <b>Force Channel:</b> <b>{html.escape(str(f_chan or 'None'))}</b>",
                reply_to=message.id
            )
            return

    if user_id in active_tickets:
        partner_id = active_tickets[user_id]
        try:
            await message.copy(partner_id)
        except Exception:
            await send_msg(message.chat.id, f"{pe('❌')} Failed to deliver message.")
        return

    if user_id not in user_states:
        return
    state = user_states[user_id]["state"]
    lang = await get_lang(user_id)

    if state == "wait_for_support":
        del user_states[user_id]
        pending_tickets[user_id] = True
        ticket_id = f"#TKT{random.randint(1000, 9999)}"
        await send_msg(message.chat.id, TR[lang]["sup_sent"].format(tkt=ticket_id))
        admins = await admins_db.find().to_list(100)
        admin_ids = set([OWNER_ID] + [a["user_id"] for a in admins])
        btns = kb([("Accept", f"tktacc_{user_id}", "success"), ("Reject", f"tktrej_{user_id}", "danger")])
        user_mention = mention(user_id, message.from_user.first_name)
        admin_text = f"{pe('🎟')} <b>New Support Ticket ({ticket_id})</b>\nFrom: {user_mention} (<code>{user_id}</code>)\n\n<b>Reason:</b> {html.escape(message.text or '')}"
        admin_ticket_msgs[user_id] = {}
        for aid in admin_ids:
            try:
                sent_m = await send_msg(aid, admin_text, markup=btns)
                if sent_m:
                    admin_ticket_msgs[user_id][aid] = sent_m["message_id"]
            except Exception:
                pass

    elif state == "wait_for_wd_amount":
        try:
            wd_amt = float(message.text.strip())
            conf = await get_config()
            min_wd = float(conf.get("min_withdrawal", 20.0))
            u_doc = await get_or_create_user(user_id)
            curr_bal = float(u_doc.get("balance", 0.0))

            if wd_amt < min_wd:
                return await send_msg(message.chat.id, f"{pe('⚠️')} Minimum withdrawal amount is <b>{usd(min_wd)}</b>. Please send a valid amount:")
            if wd_amt > curr_bal:
                return await send_msg(message.chat.id, f"{pe('❌')} Insufficient real balance! Your current real balance is <b>{usd(curr_bal)}</b>. Please send a valid amount:")

            user_states[user_id] = {
                "state": "wait_for_wallet",
                "amount": wd_amt,
                "method": user_states[user_id]["method"]
            }
            await send_msg(message.chat.id, f"{pe('💰')} <b>Withdraw Amount:</b> {usd(wd_amt)}\n\n{pe('✏️')} <b>Please send your Redcube Wallet ID:</b>")
        except ValueError:
            await send_msg(message.chat.id, f"{pe('❌')} Please send a valid numeric amount (e.g., 25):")

    elif state == "wait_for_wallet":
        wallet = message.text.strip()
        amount = float(user_states[user_id]["amount"])
        method = user_states[user_id]["method"]
        del user_states[user_id]

        u_doc = await get_or_create_user(user_id)
        if float(u_doc.get("balance", 0.0)) < amount:
            return await send_msg(message.chat.id, f"{pe('❌')} Insufficient real balance.")

        await users_db.update_one({"user_id": user_id}, {"$inc": {"balance": -amount}})
        await send_msg(message.chat.id, f"{pe('✅')} Withdrawal request for <b>{usd(amount)}</b> sent to admins!")

        admins = await admins_db.find().to_list(100)
        admin_ids = set([OWNER_ID] + [a["user_id"] for a in admins])
        btns = kb([("Done", f"wdone_{user_id}_{amount}", "success"), ("Reject", f"wrej_{user_id}_{amount}", "danger")])
        user_mention = mention(user_id, message.from_user.first_name)
        admin_text = f"{pe('💰')} <b>New Withdrawal Request</b>\nUser: {user_mention} (<code>{user_id}</code>)\nAmount: <b>{usd(amount)}</b>\nMethod: {method}\nWallet: <code>{html.escape(wallet)}</code>"
        admin_withdraw_msgs[user_id] = {}
        for aid in admin_ids:
            try:
                sent_m = await send_msg(aid, admin_text, markup=btns)
                if sent_m:
                    admin_withdraw_msgs[user_id][aid] = sent_m["message_id"]
            except Exception:
                pass

    elif state == "wait_for_txlink":
        tx_link = message.text.strip()
        target_id = user_states[user_id]["target_id"]
        amount = float(user_states[user_id]["amount"])
        del user_states[user_id]
        await users_db.update_one({"user_id": target_id}, {"$inc": {"total_withdrawn": amount}})
        await send_msg(message.chat.id, f"{pe('✅')} Transaction link sent to user!")
        try:
            await send_msg(target_id, f"{pe('✅')} <b>Your withdrawal of {usd(amount)} is completed!</b>\nTransaction Link: {html.escape(tx_link)}")
        except Exception:
            pass

    elif state == "wait_for_reason":
        reason = message.text
        target_id = user_states[user_id]["target_id"]
        amount = float(user_states[user_id]["amount"])
        del user_states[user_id]
        await users_db.update_one({"user_id": target_id}, {"$inc": {"balance": amount}})
        await send_msg(message.chat.id, f"{pe('✅')} Rejected and refunded.")
        t_lang = await get_lang(target_id)
        try:
            await send_msg(target_id, TR[t_lang]["wd_rej"].format(amount=usd(amount), reason=html.escape(reason)))
        except Exception:
            pass


# ================= KEEP-ALIVE WEB SERVER =================
async def start_web_server():
    async def handle(request):
        return web.Response(text="Bot is Alive and Running 24/7!")
    server = web.Application()
    server.router.add_get("/", handle)
    runner = web.AppRunner(server)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    global BOT_USERNAME, BOT_ID
    await start_web_server()
    await app.start()
    me = await app.get_me()
    BOT_USERNAME = me.username or ""
    BOT_ID = me.id
    print(f"✅ Bot Started (@{BOT_USERNAME}) with {len(ACTIVE_HELPER_TOKENS)} helper tokens...")

    active_gws = await giveaways_db.find({"status": "active"}).to_list(length=None)
    for gw in active_gws:
        asyncio.create_task(giveaway_countdown_task(gw["_id"]))

    asyncio.create_task(background_verification_check())
    asyncio.create_task(weekly_race_timer_task())
    asyncio.create_task(weekly_refferal_race_timer_task())
    asyncio.create_task(sweeper())
    await idle()
    if HTTP_SESSION and not HTTP_SESSION.closed:
        await HTTP_SESSION.close()
    await app.stop()


if __name__ == "__main__":
    app.run(main())
