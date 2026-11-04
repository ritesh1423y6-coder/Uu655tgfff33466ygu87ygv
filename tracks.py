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
from pyrogram.types import Message, CallbackQuery, ChatJoinRequest, BotCommand
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web
from bson.objectid import ObjectId

# Ensure pvp.py exists in your directory with MODES and Match
try:
    from pvp import MODES, Match
except ImportError:
    print("⚠️ WARNING: pvp.py not found! Games will crash without it.")

# ================= PYROGRAM ASYNCIO FIX (FOR NEWER PYTHON VERSIONS) =================
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
# ====================================================================================

# ================= PYDROID 3 / ANDROID DNS FIX =================
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8', '8.8.4.4']

# ================= CONFIGURATION =================
BOT_TOKEN = "9102679894:AAHF8ZqGiOJ-S_pdN10tpQARgcgHpXOcmhk"

# Put your helper bot tokens here (to bypass telegram dice limits)
HELPER_BOT_TOKEN_1 = "9018656267:AAGDUHGH5a2gcoeetlDNWfcGy-YLW95bdUc"
HELPER_BOT_TOKEN_2 = "9202520474:AAEWpPA0OJSBAn7enPldnDfTgB-KbWGvSOY"
ACTIVE_HELPER_TOKENS = [t.strip() for t in [HELPER_BOT_TOKEN_1, HELPER_BOT_TOKEN_2] if t.strip()]

API_ID = 35831190  
API_HASH = "f625657330797a7f149855cbdfcf9dae"
MONGO_URI = "mongodb+srv://Cricket_231:Rohit1616%40@zolmdho.mongodb.net/?appName=Cluster0" 
OWNER_ID = 7691071175 
TRACK_GROUP_ID = -1003946482336  
REQUIRED_USERNAME_TAG = "@redcube"
FSUB_CHANNEL = "@redcube_en"  
GROUP_INVITE_LINK = "https://t.me/+rdKCTKOlxUE1Mjc8"
BANNED_PROMOS = ["@raika", "@dices", "@booplay", "@axoms", "casino"]
CASINO_NAME = "Redcube Casino"

# ================= HTTP SESSION & GAME STATE =================
HTTP_SESSION: aiohttp.ClientSession | None = None

matches: dict[str, dict] = {}
user_match: dict[int, str] = {}
msg_owner: dict[tuple[int, int], int] = {}
busy: set[int] = set()
user_last_dice_time = {}
user_names: dict[int, str] = {}
auth_groups_cache: set[int] = set()

# Pending join requests {user_id: {"chat_id": chat_id, "inviter_id": inviter_id, "msg_id": msg_id}}
pending_join_requests: dict[int, dict] = {}

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
    "💸": "5893473283696759404", "📥": "5879841310902324730",
    "📤": "5879841310902324730", "🔄": "6030657343744644592",
    "🔁": "6030657343744644592", "💬": "6034831751308644168"
}

def pe(emoji_char: str) -> str:
    eid = PREMIUM_EMOJIS.get(emoji_char)
    if eid: return f'<tg-emoji emoji-id="{eid}">{emoji_char}</tg-emoji>'
    return emoji_char

def get_game_emo(game: str) -> str:
    mapping = {"dice": "🎲", "basket": "🏀", "bask": "🏀", "football": "⚽", "bowl": "🎳", "dart": "🎯", "slot": "🎰"}
    return mapping.get(game, "🎲")

def game_pe(game: str) -> str: return pe(get_game_emo(game))

def usd(amount: float) -> str: return f"${amount:.2f}"

def mention(uid: int, name: str = None) -> str:
    label = name or user_names.get(uid) or "Player"
    return f'<a href="tg://user?id={uid}">{html.escape(str(label))}</a>'

# ================= HTTP REQUEST ENGINE =================
async def get_session() -> aiohttp.ClientSession:
    global HTTP_SESSION
    if HTTP_SESSION is None or HTTP_SESSION.closed:
        connector = aiohttp.TCPConnector(limit=150, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=20, connect=8)
        HTTP_SESSION = aiohttp.ClientSession(connector=connector, timeout=timeout)
    return HTTP_SESSION

async def tg(method: str, use_helper: bool = False, retries: int = 2, **params):
    clean = {k: v for k, v in params.items() if v is not None}
    tok = BOT_TOKEN
    if use_helper and ACTIVE_HELPER_TOKENS:
        tok = random.choice(ACTIVE_HELPER_TOKENS)
        
    base = f"https://api.telegram.org/bot{tok}/"
    req_timeout = 12
    for attempt in range(retries + 1):
        try:
            s = await get_session()
            async with s.post(base + method, json=clean, timeout=req_timeout) as r:
                res = await r.json()
            if res.get("ok"): return res["result"]
            retry_after = res.get("parameters", {}).get("retry_after")
            if retry_after and attempt < retries:
                await asyncio.sleep(min(float(retry_after), 5.0))
                continue
            raise RuntimeError(res.get("description", str(res)))
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            if attempt < retries:
                await asyncio.sleep(0.4)
                continue
            raise RuntimeError(f"Network timeout on {method}: {e}")

# ================= BUTTON & KEYBOARD GENERATORS =================
def btn(text: str, data: str = None, style: str = None, url: str = None, icon: str = None) -> dict:
    b = {"text": str(text)} 
    if url: b["url"] = str(url)
    else: b["callback_data"] = str(data) if data else "noop"
    if style: b["style"] = style
    if icon and icon in PREMIUM_EMOJIS: b["icon_custom_emoji_id"] = PREMIUM_EMOJIS[icon]
    return b

def kb(*rows) -> dict:
    board = []
    for row in rows:
        r = []
        for item in row:
            if isinstance(item, dict): r.append(item)
            elif len(item) >= 4: r.append(btn(item[0], item[1], style=item[2], icon=item[3]))
            elif len(item) == 3: r.append(btn(item[0], item[1], style=item[2]))
            elif len(item) == 2: r.append(btn(item[0], item[1]))
            elif len(item) == 1: r.append(btn(item[0], item[0]))
        if r: board.append(r)
    return {"inline_keyboard": board}

async def send_msg(chat_id: int, text: str, markup=None, parse_mode="HTML", reply_to: int = None, owner_id: int = None, disable_web_page_preview=True):
    try:
        res = await tg("sendMessage", chat_id=chat_id, text=text, reply_markup=markup, parse_mode=parse_mode, reply_to_message_id=reply_to, disable_web_page_preview=disable_web_page_preview)
        if owner_id and res and "message_id" in res:
            msg_owner[(chat_id, res["message_id"])] = owner_id
        return res
    except Exception as e:
        pass

async def edit_msg(chat_id: int, message_id: int, text: str, markup=None, parse_mode="HTML", owner_id: int = None, disable_web_page_preview=True):
    try:
        res = await tg("editMessageText", chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
        if owner_id: msg_owner[(chat_id, message_id)] = owner_id
        return res
    except Exception:
        return await send_msg(chat_id, text, markup=markup, parse_mode=parse_mode, owner_id=owner_id, disable_web_page_preview=disable_web_page_preview)

async def clear_buttons(chat_id: int, message_id: int):
    if not message_id: return
    try: await tg("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id, reply_markup=None, retries=1)
    except Exception: pass

async def del_msg(chat_id: int, message_id: int):
    try: await tg("deleteMessage", chat_id=chat_id, message_id=message_id, retries=1)
    except Exception: pass

async def answer_cb(cb_id: str, text: str = None, show_alert: bool = False):
    try: await tg("answerCallbackQuery", callback_query_id=cb_id, text=text, show_alert=show_alert, retries=1)
    except Exception: pass

# ================= INITIALIZATION =================
app = Client("my_advanc9768e6d_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

client = AsyncIOMotorClient(MONGO_URI, maxPoolSize=50)
db = client['Advanced56BotDB']
users_db = db['users']
admins_db = db['admins']
config_db = db['config']
activity_db = db['activity']
auth_groups_db = db['authorized_groups'] 
rain_db = db['rain_events']
games_db = db['games']

user_states = {}
active_tickets = {}   
pending_tickets = {}  
user_langs = {}  

# Admin Notification Tracking
admin_ticket_msgs = {}
admin_withdraw_msgs = {} 

processed_msgs = {}
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
        "help": f"{pe('✏️')} <b>Available Commands:</b>\n/start - Open Menu\n/lang - Change Language\n/verify - Verify profile\n/affiliate - Get referral link\n/leaderboard - View Activity\n/bal - Check balance\n/support - Contact support\n/close - Close active ticket\n/deposit - Deposit funds\n/profile - View Stats",
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
        "wd_addr": f"{pe('📍')} Please send your {pe('💎')} TON withdrawal address:\n\n<b>Example:</b> <code>UQ...</code>",
        "wd_rej": f"{pe('❌')} <b>Withdrawal Rejected!</b>\nAmount: ${{amount}}\nReason: {{reason}}\nFunds refunded.",
        "deposit_text": f"{pe('📥')} <b>Deposit Funds</b>\n\nTo deposit, please join our official group and send your desired amount to <b>@cinex</b> via <b>@redcube</b>.",
        "btn_verify": "Verify",
        "btn_affiliate": "Affiliate",
        "btn_leaderboard": "Leaderboard",
        "btn_draw": "Draw",
        "btn_support": "Support",
        "btn_language": "Language",
        "btn_daily": "Daily",
        "btn_weekly": "Weekly",
        "btn_monthly": "Monthly",
        "btn_back": "Back"
    },
    "ru": {
        "welcome_head": f"Добро пожаловать <b>{{name}}</b>! {pe('👋')}\n\n",
        "welcome": f"{pe('✅')} <b>Добро пожаловать в Tracker Bot!</b>\n\nДля верификации аккаунта:\n1. Добавьте <code>{{tag}}</code> в ваше имя.\n2. Добавьте эту ссылку в Bio: {{link}}\n\nИспользуйте кнопки ниже.",
        "lang_set": f"{pe('✅')} Язык изменен на Русский.",
        "verify_ok": f"{pe('✅')} <b>Верификация пройдена!</b> Ваше имя и Bio отслеживаются.",
        "verify_fail": f"{pe('❌')} <b>Ошибка верификации:</b>\nУбедитесь, что ваше имя содержит <code>{{tag}}</code>, а в Bio есть ссылка.",
        "help": f"{pe('✏️')} <b>Команды:</b>\n/start - Меню\n/lang - Сменить язык\n/verify - Верификация\n/affiliate - Реферальная ссылка\n/leaderboard - Таблица лидеров\n/bal - Баланс\n/support - Поддержка\n/close - Закрыть тикет\n/deposit - Пополнить баланс\n/profile - Статистика",
        "affiliate_link": f"{pe('⛓️')} <b>Ваша реферальная ссылка:</b>\n{{link}}\n\nПоделитесь ею для приглашения. Мы automatically учитываем валидных пользователей.",
        "affiliate_stats": f"{pe('📊')} <b>Статистика:</b>\n{pe('👥')} Реальные: {{real}}\n{pe('❌')} Покинули: {{left}}\n{pe('🤖')} Фейки: {{fake}}\n\n{pe('💡')} Вы получаете ${{reward}} за каждых {{req}} пользователей.",
        "affiliate_disabled": f"{pe('⚠️')} <b>Партнерская система в настоящее время отключена администраторами.</b>",
        "sup_ask": f"{pe('✏️')} Пожалуйста, опишите вашу проблему в одном сообщении (Причина обращения):",
        "sup_sent": f"{pe('✅')} Ваш запрос отправлен. Номер тикета: <b>{{tkt}}</b>\nПожалуйста, подождите ответа.",
        "sup_pending": f"{pe('⚠️')} У вас already есть активный тикет. Дождитесь его закрытия.",
        "tkt_joined": f"{pe('👨‍💻')} <b>Администратор подключился!</b>\nТеперь вы можете общаться с ним.",
        "tkt_closed": f"{pe('🔐')} <b>Ваш тикет закрыт.</b>",
        "tkt_rejected": f"{pe('❌')} <b>Ваш тикет ({{tkt}}) был отклонен администратором.</b>",
        "draw_none": "Результаты розыгрыша пока недоступны.",
        "draw_res": f"{pe('🎉')} <b>РЕЗУЛЬТАТЫ РОЗЫГРЫША</b> {pe('🎉')}\n\n{pe('⏱')} <b>Время:</b> {{time}}\n{pe('👥')} <b>Участников:</b> {{total}}\n{pe('🎁')} <b>Приз:</b> ${{amt}} каждому\n\n{pe('🏆')} <b>Победители:</b>\n{{winners}}",
        "wd_addr": f"{pe('📍')} Пожалуйста, отправьте ваш адрес {pe('💎')} TON:\n\n<b>Пример:</b> <code>UQ...</code>",
        "wd_rej": f"{pe('❌')} <b>Вывод отклонен!</b>\nСумма: ${{amount}}\nПричина: {{reason}}\nСредства возвращены.",
        "deposit_text": f"{pe('📥')} <b>Пополнить баланс</b>\n\nДля пополнения присоединяйтесь к нашей официальной группе и отправьте желаемую сумму <b>@cinex</b> через <b>@redcube</b>.",
        "btn_verify": "Проверить",
        "btn_affiliate": "Реферал",
        "btn_leaderboard": "Таблица",
        "btn_draw": "Розыгрыш",
        "btn_support": "Поддержка",
        "btn_language": "Язык",
        "btn_daily": "День",
        "btn_weekly": "Неделя",
        "btn_monthly": "Месяц",
        "btn_back": "Назад"
    },
    "hi": {
        "welcome_head": f"स्वागत है <b>{{name}}</b>! {pe('👋')}\n\n",
        "welcome": f"{pe('✅')} <b>ट्रैकर बॉट में आपका स्वागत है!</b>\n\nअपने अकाउंट को वेरीफाई करने के लिए:\n1. अपने टेलीग्राम नाम में <code>{{tag}}</code> जोड़ें।\n2. अपने Bio में यह लिंक जोड़ें: {{link}}\n\nनेविगेट करने के लिए नीचे दिए गए बटन्स का उपयोग करें।",
        "lang_set": f"{pe('✅')} भाषा हिंदी में सेट हो गई है।",
        "verify_ok": f"{pe('✅')} <b>सत्यापन सफल!</b> आपका नाम और बायो अब ट्रैक किया जा रहा है।",
        "verify_fail": f"{pe('❌')} <b>सत्यापन विफल:</b>\nकृपया सुनिश्चित करें कि आपके नाम में <code>{{tag}}</code> है और आपके बायो में ट्रैकिंग लिंक है।",
        "help": f"{pe('✏️')} <b>उपलब्ध कमांड्स:</b>\n/start - मेन्यू खोलें\n/lang - भाषा बदलें\n/verify - प्रोफाइल वेरीफाई करें\n/affiliate - रेफरल लिंक प्राप्त करें\n/leaderboard - लीडरबोर्ड देखें\n/bal - बैलेंस देखें\n/support - सहायता प्राप्त करें\n/close - सक्रिय टिकट बंद करें\n/deposit - बैलेंस जमा करें\n/profile - स्टैट्स देखें",
        "affiliate_link": f"{pe('⛓️')} <b>आपका पर्सनल एफिलिएट लिंक:</b>\n{{link}}\n\nयूजर्स को इनवाइट करने के लिए इसे शेयर करें।",
        "affiliate_stats": f"{pe('📊')} <b>एफिलिएट आँकड़े:</b>\n{pe('👥')} असली इनवाइट: {{real}}\n{pe('❌')} छोड़ दिया: {{left}}\n{pe('🤖')} फेक/फ़िल्टर: {{fake}}\n\n{pe('💡')} हर {{req}} मेंबर्स पर आपको ${{reward}} मिलेंगे।",
        "affiliate_disabled": f"{pe('⚠️')} <b>एफिलिएट सिस्टम वर्तमान में एडमिन द्वारा बंद कर दिया गया है।</b>",
        "sup_ask": f"{pe('✏️')} कृपया अपनी समस्या एक मैसेज में लिखें (सहायता का कारण):",
        "sup_sent": f"{pe('✅')} आपका अनुरोध एडमिन को भेज दिया गया है। टिकट नंबर: <b>{{tkt}}</b>\nकृपया प्रतीक्षा करें।",
        "sup_pending": f"{pe('⚠️')} आपके पास पहले से ही एक सक्रिय टिकट है। कृपया इसके समाधान की प्रतीक्षा करें।",
        "tkt_joined": f"{pe('👨‍💻')} <b>एक एडमिन चैट में शामिल हो गया है!</b>\nअब आप सीधे उनसे बात कर सकते हैं।",
        "tkt_closed": f"{pe('🔐')} <b>आपका टिकट बंद कर दिया गया है।</b>",
        "tkt_rejected": f"{pe('❌')} <b>आपका टिकट ({{tkt}}) एडमिन द्वारा अस्वीकार कर दिया गया है।</b>",
        "draw_none": "अभी तक कोई ड्रा रिज़ल्ट उपलब्ध नहीं है।",
        "draw_res": f"{pe('🎉')} <b>डेली ड्रा रिज़ल्ट</b> {pe('🎉')}\n\n{pe('⏱')} <b>समय:</b> {{time}}\n{pe('👥')} <b>कुल प्रतिभागी:</b> {{total}}\n{pe('🎁')} <b>इनाम:</b> ${{amt}} प्रत्येक\n\n{pe('🏆')} <b>विजेता:</b>\n{{winners}}",
        "wd_addr": f"{pe('📍')} कृपया अपना {pe('💎')} TON निकासी पता भेजें:\n\n<b>उदाहरण:</b> <code>UQ...</code>",
        "wd_rej": f"{pe('❌')} <b>निकासी अस्वीकृत!</b>\nरकम: ${{amount}}\nकारण: {{reason}}\nफंड्स वापस कर दिए गए हैं।",
        "deposit_text": f"{pe('📥')} <b>फंड्स जमा करें</b>\n\nजमा करने के लिए, कृपया हमारे आधिकारिक ग्रुप में शामिल हों और अपनी राशि <b>@cinex</b> को <b>@redcube</b> के माध्यम से भेजें।",
        "btn_verify": "सत्यापन",
        "btn_affiliate": "रेफरल",
        "btn_leaderboard": "लीडरबोर्ड",
        "btn_draw": "ड्रा",
        "btn_support": "सहायता",
        "btn_language": "भाषा",
        "btn_daily": "दैनिक",
        "btn_weekly": "साप्ताहिक",
        "btn_monthly": "मासिक",
        "btn_back": "पीछे"
    }
}

# ================= HELPER FUNCTIONS =================
async def check_double_msg(user_id: int) -> bool:
    now = time.time()
    if user_id in processed_msgs and now - processed_msgs[user_id] < 1.5:
        return True 
    processed_msgs[user_id] = now
    return False

async def is_admin(user_id):
    if user_id == OWNER_ID: return True
    now = time.time()
    if now - ADMIN_CACHE["time"] > 300: 
        admins = await admins_db.find().to_list(100)
        ADMIN_CACHE["data"] = [a["user_id"] for a in admins]
        ADMIN_CACHE["time"] = now
    return user_id in ADMIN_CACHE["data"]

async def is_group_authorized(chat_id: int) -> bool:
    if chat_id > 0: return True 
    if chat_id == TRACK_GROUP_ID: return True
    if chat_id in auth_groups_cache: return True
    doc = await auth_groups_db.find_one({"chat_id": chat_id})
    if doc and doc.get("authorized"):
        auth_groups_cache.add(chat_id)
        return True
    return False

async def get_lang(user_id):
    if user_id in user_langs: return user_langs[user_id]
    user = await users_db.find_one({"user_id": user_id})
    l = user.get("lang", "en") if user else "en"
    user_langs[user_id] = l
    return l

async def get_config():
    now = time.time()
    if CONFIG_CACHE["data"] and now - CONFIG_CACHE["time"] < 60: 
        return CONFIG_CACHE["data"]
        
    conf = await config_db.find_one({"_id": "settings"})
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
            "min_bet": 1.0
        }
        await config_db.insert_one({"_id": "settings", **conf})
        
    CONFIG_CACHE["data"] = conf
    CONFIG_CACHE["time"] = now
    return conf

async def get_or_create_user(user_id, user_obj=None):
    user = await users_db.find_one({"user_id": user_id})
    name = "User"
    if user_obj:
        name = user_obj.first_name or "User"
        if user_obj.last_name: name += f" {user_obj.last_name}"
        
    if not user:
        user = {
            "user_id": user_id, "balance": 0.0, "bio_link": None, 
            "verified": False, "affiliates": [], "fake_affiliates": [], "left_affiliates": [],
            "lang": "en", "won_draw": False, "name": name,
            "ever_joined_group": False, "wagered": 0.0, "won": 0.0,
            "total_deposited": 0.0, "total_withdrawn": 0.0
        }
        await users_db.insert_one(user)
    elif user_obj and (user.get("name") != name or user.get("name") == "User"):
        await users_db.update_one({"user_id": user_id}, {"$set": {"name": name}})
        user["name"] = name
    user_names[user_id] = user.get("name", "User")
    return user

async def fetch_real_name(user_id, db_name):
    if db_name and db_name != "User":
        return db_name
    try:
        u = await app.get_users(user_id)
        name = u.first_name or "User"
        if u.last_name: name += f" {u.last_name}"
        await users_db.update_one({"user_id": user_id}, {"$set": {"name": name}})
        user_names[user_id] = name
        return name
    except:
        return "User"

def get_main_menu(lang: str):
    tr = TR.get(lang, TR["en"])
    return kb(
        [(tr["btn_verify"], "menu_verify", "primary", "✅"), (tr["btn_affiliate"], "menu_affiliate", "success", "⛓️")],
        [(tr["btn_leaderboard"], "menu_leaderboard", "primary", "🏆"), (tr["btn_draw"], "menu_draw", "primary", "🎉")],
        [(tr["btn_support"], "menu_support", "danger", "🎟"), (tr["btn_language"], "menu_lang", "primary", "🌐")]
    )

async def generate_leaderboard_text(period, page):
    today = datetime.date.today()
    if period == "daily":
        match_date = {"$gte": str(today)}
        title = "DAILY ACTIVITY RANKING"
    elif period == "weekly":
        match_date = {"$gte": str(today - datetime.timedelta(days=7))}
        title = "WEEKLY ACTIVITY RANKING"
    else: 
        match_date = {"$gte": str(today - datetime.timedelta(days=30))}
        title = "MONTHLY ACTIVITY RANKING"

    now = datetime.datetime.now().timestamp()
    cache_key = f"{period}_{page}"
    
    if cache_key in ldb_cache and (now - ldb_cache[cache_key]["time"] < 60):
        return ldb_cache[cache_key]["text"], ldb_cache[cache_key]["max_pages"]
    
    pipeline = [
        {"$match": {"date": match_date}},
        {"$group": {"_id": "$user_id", "total": {"$sum": "$message_count"}}},
        {"$sort": {"total": -1}},
        {"$skip": page * 10},
        {"$limit": 10},
        {"$lookup": {
            "from": "users",
            "localField": "_id",
            "foreignField": "user_id",
            "as": "user_info"
        }}
    ]
    
    results = await activity_db.aggregate(pipeline).to_list(length=10)
    unique_users_list = await activity_db.distinct("user_id", {"date": match_date})
    total_users_period = len(unique_users_list)
    max_pages = max(0, (total_users_period - 1) // 10)
    
    text = f"{pe('🏆')} <b>{title}</b>\n\n"
    if not results:
        text += "<i>No activity recorded yet.</i>"
    else:
        for i, res in enumerate(results, start=(page*10)+1):
            user_info = res.get('user_info', [])
            db_name = user_info[0].get("name") if user_info else None
            name = await fetch_real_name(res['_id'], db_name)
            safe_name = html.escape(name)
            text += f"<b>{i}.</b> {safe_name} - {res['total']} msgs\n"
            
    ldb_cache[cache_key] = {"text": text, "max_pages": max_pages, "time": now}
    return text, max_pages

# ================= SAFE FORCE SUBSCRIBE LOGIC =================
async def is_user_subscribed(client: Client, user_id: int) -> bool:
    if await is_admin(user_id):
        return True
    
    async def check_chat(chat_identifier):
        try:
            m = await client.get_chat_member(chat_identifier, user_id)
            status = str(m.status).lower()
            if any(x in status for x in ["member", "admin", "creator", "owner", "restricted"]):
                return True
        except Exception:
            pass
        try:
            res = await tg("getChatMember", chat_id=chat_identifier, user_id=user_id)
            status = res.get("status", "").lower()
            if status in ["member", "administrator", "creator", "restricted"]:
                return True
        except Exception:
            pass
        return False

    in_channel = await check_chat(FSUB_CHANNEL)
    if not in_channel: return False
    in_group = await check_chat(TRACK_GROUP_ID)
    return in_group

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
    if stake < min_bet: raise ValueError(f"Minimum bet is {usd(min_bet)}")
    
    u = await get_or_create_user(uid)
    if float(u.get("balance", 0)) < stake: raise ValueError("Insufficient balance")
    
    await users_db.update_one({"user_id": uid}, {"$inc": {"balance": -stake}})
    res = await games_db.insert_one({
        "user_id": uid, "game": game, "mode": mode, "stake": stake, 
        "payout": 0.0, "opponent": opponent, "status": "open", "ts": time.time()
    })
    return str(res.inserted_id)

async def db_close_game(gid: str, payout: float, void: bool = False):
    g = await games_db.find_one({"_id": ObjectId(gid), "status": "open"})
    if not g: return
    uid, stake = g["user_id"], g["stake"]
    status = "void" if void else "done"
    
    await games_db.update_one({"_id": ObjectId(gid)}, {"$set": {"status": status, "payout": payout}})
    await users_db.update_one({"user_id": uid}, {"$inc": {"balance": payout}})
    
    if not void:
        won_amt = max(0.0, payout - stake)
        await users_db.update_one({"user_id": uid}, {"$inc": {"wagered": stake, "won": won_amt}})

async def db_void_game(gid: str):
    g = await games_db.find_one({"_id": ObjectId(gid)})
    if g and g["status"] == "open":
        await db_close_game(gid, float(g["stake"]), void=True)

def parse_bet(arg_str: str, balance: float) -> float:
    s = arg_str.strip().lower()
    if s == "all": return float(balance)
    if s == "half": return float(balance) / 2.0
    try: return round(float(s), 2)
    except ValueError: return -1.0

# ================= CORRECTED DICE VALUES LOGIC =================
def fix_dice_value(game: str, val: int) -> int:
    # Basketball: 1-3 is a miss, 4-5 is a score (binary win/lose logic kept)
    if game in ["basket", "bask"]:
        return 1 if val <= 3 else 5
    # Football: 1-2 is a miss, 3-5 is a score (binary win/lose logic kept)
    elif game == "football":
        return 1 if val <= 2 else 5
    # Dart, Bowl, Dice, Slot: These have natural progressive values (1 to 6)
    # We return the exact value so the game logic counts actual pins (for bowl)
    # or actual hit proximity (for darts), allowing fair and correct scoring!
    return val
# ===============================================================

async def send_emoji_roll(chat_id: int, game: str, n: int, reply_to: int = None) -> list[int]:
    values = []
    emo = get_game_emo(game)
    for i in range(n):
        res = None
        if ACTIVE_HELPER_TOKENS:
            try: res = await tg("sendDice", use_helper=True, retries=1, chat_id=chat_id, emoji=emo, reply_to_message_id=reply_to)
            except Exception: res = None
        if not res:
            res = await tg("sendDice", use_helper=False, retries=2, chat_id=chat_id, emoji=emo, reply_to_message_id=reply_to)
        if res: 
            raw_val = res["dice"]["value"]
            values.append(fix_dice_value(game, raw_val))
        if i < n - 1: await asyncio.sleep(0.12)
    await asyncio.sleep(2.0)
    return values

# ================= GAME UI HELPERS =================
def mode_screen_text(game: str) -> str:
    return (f"{game_pe(game)} <b>Select game mode</b>\n\n• <b>Normal mode:</b> Highest value wins\n"
            f"• <b>Crazy mode:</b> Lowest value wins\n• <b>Double mode:</b> 2 emojis are rolled in 1 round\n"
            f"• <b>Triple mode:</b> 3 emojis are rolled in 1 round")

def mode_screen_kb(game: str, stake: float):
    emo = get_game_emo(game)
    return kb([("Normal", f"mode:{game}:{stake}:normal", "primary", emo), ("Crazy", f"mode:{game}:{stake}:crazy", "danger", "💀")],
              [("Double", f"mode:{game}:{stake}:double", "primary", emo), ("Double Crazy", f"mode:{game}:{stake}:double_crazy", "danger", "💀")],
              [("Triple", f"mode:{game}:{stake}:triple", "primary", emo), ("Triple Crazy", f"mode:{game}:{stake}:triple_crazy", "danger", "💀")],
              [("Delete", "del", "danger", "❌")])

def target_screen_text(game: str) -> str:
    return f"{game_pe(game)} <b>Select the number of points needed to win</b>\n\n{pe('ℹ️')} <i>First to reach the selected number of points wins the match!</i>"

def target_screen_kb(game: str, stake: float, mode: str):
    return kb([("First to 1 point", f"tgt:{game}:{stake}:{mode}:1", "primary", "1️⃣")],
              [("First to 2 points", f"tgt:{game}:{stake}:{mode}:2", "primary", "2️⃣")],
              [("First to 3 points", f"tgt:{game}:{stake}:{mode}:3", "primary", "🏆")],
              [("Back", f"back_mode:{game}:{stake}", "danger", "❌")])

def calc_cashout(stake: float, p_score: int, b_score: int, target: int) -> float:
    if p_score <= b_score or p_score <= 0: return 0.0
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
        # Only show cashout option at the start of a round when NO ONE has rolled yet
        if cashout > 0 and is_round_start and not sess["u_rolls"] and not sess["b_rolls"]: 
            rows.append([(f"Cashout {usd(cashout)}", f"cashout:{gid}", "success", "🪙")])
        rows.append([("Send an emoji", f"roll:{gid}:me", "primary", emo)])
        if show_bot_first and sess.get("round_num", 1) == 1 and not sess["u_rolls"] and not sess["b_rolls"]:
            rows.append([("Bot rolls first", f"roll:{gid}:bot", "primary", "🤖")])
    else: rows.append([("Send an emoji", f"roll:{gid}:pvp", "primary", emo)])
    return kb(*rows)

# ================= MATCH ENGINE =================
async def finish_match(sess: dict, payout_a: float, payout_b: float = 0.0, cashed_out: bool = False):
    gid = sess["gid"]
    chat_id = sess["chat_id"]
    game = sess["game"]
    stake = sess["stake"]
    mode = sess["mode"]
    target = sess["target"]
    m = sess["match"]
    ua, ub = sess["ua"], sess["ub"]

    sess["status"] = "ended"

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
    end_kb = kb([("Repeat", f"opp:{game}:{stake}:{mode}:{target}:{who_tag}", "primary", "🔄"),
                 ("x2 Double", f"opp:{game}:{stake * 2}:{mode}:{target}:{who_tag}", "success", "🪙")],
                [("Change mode", f"back_mode:{game}:{stake}", "danger", "❌")])
    await edit_msg(chat_id, sess.get("prompt_msg_id", 0), end_text, markup=end_kb, owner_id=ua)

async def evaluate_round(sess: dict):
    m, chat_id, game, ua, ub = sess["match"], sess["chat_id"], sess["game"], sess["ua"], sess["ub"]
    p1_mention = mention(ua)
    p2_mention = mention(ub) if ub else f"{pe('🤖')} <b>{html.escape(CASINO_NAME)}</b>"
    
    mine, theirs = sess["u_rolls"], sess["b_rolls"]
    sess["u_rolls"], sess["b_rolls"] = [], []
    w = m.play_round(mine, theirs)

    if m.winner is not None:
        sess["status"] = "ended"
        if sess["type"] == "bot": await finish_match(sess, round(sess["stake"] * 1.92, 2) if m.winner == 0 else 0.0)
        else:
            pot = round(2 * sess["stake"] * 0.95, 2)
            await finish_match(sess, pot if m.winner == 0 else 0.0, 0.0 if m.winner == 0 else pot)
        return

    sess["round_num"] = sess.get("round_num", 1) + 1
    score_header = f"{game_pe(game)} <b>Score (Round {sess['round_num'] - 1})</b>\n\n• {p1_mention}: <b>{m.score[0]} points</b>\n• {p2_mention}: <b>{m.score[1]} points</b>{f'{pe("🤝")} <b>Tie round — replay!</b>' if w is None else ''}"

    if sess["type"] == "bot" and random.choice([True, False]):
        sess["rolling"] = True
        await edit_msg(chat_id, sess.get("prompt_msg_id", 0), f"{score_header}\n\n{p2_mention} <b>is rolling first...</b>")
        sess["b_rolls"] = await send_emoji_roll(chat_id, game, m.rolls_needed, reply_to=sess.get("prompt_msg_id", 0))
        sess["turn_uid"] = ua
        sess["last_action"] = time.time()
        sess["rolling"] = False
        sent = await send_msg(chat_id, f"{p1_mention}, <b>your turn!</b> {game_pe(game)}", markup=turn_kb(sess, is_round_start=True), owner_id=ua)
        sess["prompt_msg_id"] = sent["message_id"] if sent else 0
    else:
        sess["rolling"] = False
        sess["turn_uid"] = ua
        sess["last_action"] = time.time()
        await edit_msg(chat_id, sess.get("prompt_msg_id", 0), f"{score_header}\n\n{p1_mention}, <b>your turn!</b> {game_pe(game)}", markup=turn_kb(sess, is_round_start=True), owner_id=ua)

async def handle_roll_button(sess: dict, uid: int, order: str):
    lock: asyncio.Lock = sess["lock"]
    if lock.locked(): return
    async with lock:
        if sess.get("status") != "playing": return
        sess["rolling"] = True
        sess["last_action"] = time.time()
        chat_id, game, m = sess["chat_id"], sess["game"], sess["match"]
        needed = m.rolls_needed
        if sess.get("prompt_msg_id"):
            asyncio.create_task(clear_buttons(chat_id, sess["prompt_msg_id"]))
            sess["prompt_msg_id"] = None
        try:
            if sess["type"] == "bot":
                if order == "bot" and not sess["b_rolls"] and not sess["u_rolls"]:
                    sess["b_rolls"] = await send_emoji_roll(chat_id, game, needed)
                    sess["turn_uid"], sess["rolling"], sess["last_action"] = sess["ua"], False, time.time()
                    sent = await send_msg(chat_id, f"{mention(sess['ua'])}, <b>your turn!</b> {game_pe(game)}", markup=turn_kb(sess, is_round_start=False), owner_id=sess["ua"])
                    sess["prompt_msg_id"] = sent["message_id"] if sent else 0
                    return
                rem_u = needed - len(sess["u_rolls"])
                if rem_u > 0: sess["u_rolls"] += await send_emoji_roll(chat_id, game, rem_u)
                if len(sess["b_rolls"]) < needed:
                    b_msg = await send_msg(chat_id, f"{pe('🤖')} <b>{html.escape(CASINO_NAME)}'s turn...</b>")
                    sess["b_rolls"] += await send_emoji_roll(chat_id, game, needed - len(sess["b_rolls"]), reply_to=b_msg["message_id"] if b_msg else None)
                await evaluate_round(sess)
            else:
                if uid == sess["ua"]:
                    rem = needed - len(sess["u_rolls"])
                    if rem > 0: sess["u_rolls"] += await send_emoji_roll(chat_id, game, rem)
                    sess["turn_uid"], sess["rolling"], sess["last_action"] = sess["ub"], False, time.time()
                    sent = await send_msg(chat_id, f"{mention(sess['ub'])}, <b>your turn!</b> {game_pe(game)}", markup=turn_kb(sess, is_round_start=False), owner_id=sess["ub"])
                    sess["prompt_msg_id"] = sent["message_id"] if sent else 0
                elif uid == sess["ub"]:
                    rem = needed - len(sess["b_rolls"])
                    if rem > 0: sess["b_rolls"] += await send_emoji_roll(chat_id, game, rem)
                    await evaluate_round(sess)
        except Exception:
            sess["rolling"], sess["last_action"] = False, time.time()
            try:
                sent = await send_msg(chat_id, f"{pe('⚠️')} {mention(sess['turn_uid'])}, <b>tap below to continue your turn:</b>", markup=turn_kb(sess), owner_id=sess["turn_uid"])
                sess["prompt_msg_id"] = sent["message_id"] if sent else 0
            except Exception: pass

# ================= BACKGROUND TIMERS =================
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
        if not event: break
        
        parts_count = len(event.get("participants", []))
        
        text = f"{pe('🌧')} <b>RAIN EVENT!</b> {pe('⛈')}\n\n{pe('🌩')} <b>Total Prize:</b> {usd(total_amt)}\n{pe('🏆')} <b>Winners:</b> {win_count}\n{pe('✏️')} <b>Required Activity:</b> {min_msgs} messages in this group.\n{pe('🔄')} <b>Min Turnover:</b> {usd(min_turnover)}\n\n{pe('👥')} <b>Participants:</b> {parts_count}\n{pe('⏱')} <b>Ends In:</b> {time_str}"
        markup = kb([("Participate", f"rain_join_{event_id}", "success", "☔")])
        
        try:
            await tg("editMessageText", chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            pass 
            
        await asyncio.sleep(10)
        
    event = await rain_db.find_one({"_id": event_id})
    if not event: return
    
    participants = event.get("participants", [])
    winners_list = []
    
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
            if not population: break
            winner_choice = random.choices(population, weights=weights, k=1)[0]
            idx = population.index(winner_choice)
            winners_list.append(winner_choice)
            population.pop(idx)
            weights.pop(idx)
        
    win_amount_each = total_amt / win_count if win_count > 0 else 0
    
    mentions = []
    for wid in winners_list:
        await users_db.update_one({"user_id": wid}, {"$inc": {"balance": win_amount_each}}, upsert=True)
        u_info = await get_or_create_user(wid)
        mentions.append(f"<a href='tg://user?id={wid}'>{html.escape(u_info['name'])}</a>")
        try: await send_msg(wid, f"{pe('🎉')} <b>Congratulations!</b> You won {usd(win_amount_each)} in the Rain Event!")
        except: pass
        
    if not mentions:
        final_text = f"{pe('🌧')} <b>RAIN EVENT ENDED!</b> {pe('⛈')}\n\n{pe('❌')} <b>No eligible participants joined in time!</b>"
    else:
        final_text = f"{pe('🌧')} <b>RAIN EVENT ENDED!</b> {pe('⛈')}\n\n{pe('🌩')} <b>Total Dropped:</b> {usd(total_amt)}\n{pe('🎁')} <b>Prize Each:</b> {usd(win_amount_each)}\n\n{pe('🏆')} <b>Winners:</b>\n"
        for i, m in enumerate(mentions, 1):
            final_text += f"<blockquote>{i}. {m}</blockquote>\n"
            
    try:
        await tg("editMessageText", chat_id=chat_id, message_id=message_id, text=final_text, reply_markup=None, parse_mode="HTML")
    except: pass
    await rain_db.delete_one({"_id": event_id})

async def background_verification_check():
    while True:
        try:
            verified_users = await users_db.find({"verified": True}).to_list(length=None)
            for u in verified_users:
                try:
                    chat_info = await app.get_chat(u["user_id"])
                    full_name = f"{chat_info.first_name or ''} {chat_info.last_name or ''}".lower()
                    name_ok = REQUIRED_USERNAME_TAG.lower() in full_name
                    bio_ok = u.get("bio_link") in (chat_info.bio or "")
                    
                    if not (name_ok and bio_ok):
                        await users_db.update_one({"user_id": u["user_id"]}, {"$set": {"verified": False}})
                        lang = await get_lang(u["user_id"])
                        msg = f"{pe('⚠️')} <b>Warning:</b> You have removed the required name tag or bio link! Your verification is revoked and you are disqualified from upcoming draws. Please add them back and send /verify."
                        if lang == "ru":
                            msg = f"{pe('⚠️')} <b>Внимание:</b> Вы удалили тег из имени или ссылку из Bio! Ваша верификация аннулирована. Пожалуйста, верните их и отправьте /verify."
                        elif lang == "hi":
                            msg = f"{pe('⚠️')} <b>चेतावनी:</b> आपने नाम से टैग या बायो से लिंक हटा दिया है! आपका सत्यापन रद्द कर दिया गया है। कृपया उन्हें वापस जोड़ें और /verify भेजें।"
                        try: await send_msg(u["user_id"], msg)
                        except: pass
                except: pass
                await asyncio.sleep(2) 
        except: pass
        await asyncio.sleep(120)

async def sweeper():
    while True:
        await asyncio.sleep(10)
        now = time.time()
        try:
            for gid, sess in list(matches.items()):
                if sess.get("status") == "waiting" and now - sess.get("created_at", now) >= 120:
                    matches.pop(gid, None)
                    ua = sess["ua"]
                    user_match.pop(ua, None)
                    busy.discard(ua)
                    await db_void_game(gid)
                    await edit_msg(sess["chat_id"], sess.get("prompt_msg_id", 0), f"{pe('⏳')} <b>No opponent joined</b> {mention(ua)}'s <b>PvP match — stake refunded.</b>", owner_id=ua)
                elif sess.get("status") == "playing" and sess.get("rolling") and now - sess.get("last_action", now) >= 15:
                    sess["rolling"], sess["last_action"] = False, now
        except Exception: pass


# ================= MESSAGES & COMMANDS HANDLERS =================
@app.on_message(filters.command("lang") & filters.private)
async def lang_cmd(client: Client, message: Message):
    if await check_double_msg(message.from_user.id): return
    if not await pass_fsub(client, message): return 
    btns = kb(
        [("English", "lang_en", "primary", "🇬🇧"), ("Русский", "lang_ru", "danger", "🇷🇺")],
        [("हिंदी (Hindi)", "lang_hi", "success", "🇮🇳")]
    )
    await send_msg(message.chat.id, "Select your language / Выберите язык / भाषा चुनें:", markup=btns)

@app.on_message(filters.command(["profile", "stats"]))
async def profile_cmd(client: Client, message: Message):
    is_private = (message.chat.type == enums.ChatType.PRIVATE)
    if not is_private:
        if not await is_group_authorized(message.chat.id):
            return

    uid = message.from_user.id
    target = message.from_user
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        uid = target.id
        
    u = await get_or_create_user(uid, target)
    
    pipeline = [{"$match": {"user_id": uid}}, {"$group": {"_id": None, "total": {"$sum": "$message_count"}}}]
    activity = await activity_db.aggregate(pipeline).to_list(1)
    total_msgs = activity[0]["total"] if activity else 0
    
    bal = float(u.get("balance", 0.0))
    wagered = float(u.get("wagered", 0.0))
    won = float(u.get("won", 0.0))
    deposited = float(u.get("total_deposited", 0.0))
    withdrawn = float(u.get("total_withdrawn", 0.0))
    
    text = (
        f"{pe('👤')} <b>Profile: {mention(uid, target.first_name)}</b>\n\n"
        f"{pe('💰')} <b>Balance:</b> {usd(bal)}\n"
        f"{pe('📈')} <b>Turnover (Wagered):</b> {usd(wagered)}\n"
        f"{pe('🏆')} <b>Total Won:</b> {usd(won)}\n"
        f"{pe('📥')} <b>Total Deposited:</b> {usd(deposited)}\n"
        f"{pe('📤')} <b>Total Withdrawn:</b> {usd(withdrawn)}\n"
        f"{pe('💬')} <b>Group Messages:</b> {total_msgs}\n"
    )
    await send_msg(message.chat.id, text)

@app.on_message(filters.command("deposit"))
async def deposit_cmd(client: Client, message: Message):
    is_private = (message.chat.type == enums.ChatType.PRIVATE)
    if not is_private:
        if not await is_group_authorized(message.chat.id): return

    if await check_double_msg(message.from_user.id): return
    lang = await get_lang(message.from_user.id)
    
    text = TR.get(lang, TR["en"]).get("deposit_text", TR["en"]["deposit_text"])
    markup_btns = [[btn("Join Group", url=GROUP_INVITE_LINK, style="primary", icon="👥")]]
    
    if is_private:
        markup_btns.append([btn(TR[lang]["btn_back"], "menu_main", style="danger", icon="🔙")])
        
    await send_msg(message.chat.id, text, markup={"inline_keyboard": markup_btns}, disable_web_page_preview=True)

@app.on_message(filters.command("depo"))
async def admin_depo_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    
    args = message.command[1:]
    if not args:
        return await send_msg(message.chat.id, f"<b>Usage:</b> `/depo <amount>` (reply to user)\nOr `/depo <amount> <username/ID>`")
        
    try:
        amount = float(args[0])
    except ValueError:
        return await send_msg(message.chat.id, f"{pe('⚠️')} Invalid amount.")
        
    if amount <= 0:
        return await send_msg(message.chat.id, f"{pe('⚠️')} Amount must be greater than 0.")
        
    target_id = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
    elif len(args) > 1:
        target_identifier = args[1]
        try:
            if target_identifier.isdigit() or (target_identifier.startswith('-') and target_identifier[1:].isdigit()):
                target_id = int(target_identifier)
            else:
                user_obj = await app.get_users(target_identifier)
                target_id = user_obj.id
        except Exception:
            return await send_msg(message.chat.id, f"{pe('⚠️')} Could not find that user.")
            
    if not target_id:
        return await send_msg(message.chat.id, f"{pe('⚠️')} You must specify a user ID/username or reply to their message.")
        
    # Update user DB
    await get_or_create_user(target_id)
    await users_db.update_one(
        {"user_id": target_id},
        {"$inc": {"balance": amount, "total_deposited": amount}}
    )
    
    # Notify Admin and Target
    await send_msg(message.chat.id, f"{pe('✅')} <b>Successfully deposited {usd(amount)} to {mention(target_id)}!</b>")
    try:
        await send_msg(target_id, f"{pe('📥')} <b>{usd(amount)} has been deposited to your account by an admin!</b>")
    except:
        pass

@app.on_message(filters.command("access"))
async def access_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    try:
        target_chat = int(message.command[1]) if len(message.command) > 1 else message.chat.id
        await auth_groups_db.update_one({"chat_id": target_chat}, {"$set": {"authorized": True}}, upsert=True)
        auth_groups_cache.add(target_chat)
        await send_msg(message.chat.id, f"{pe('✅')} Group <code>{target_chat}</code> authorized successfully! Activity tracking and games will now work here.")
    except Exception as e:
        await send_msg(message.chat.id, "Usage: /access [group_id] or use in group.")

@app.on_message(filters.command("revoke"))
async def revoke_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    try:
        target_chat = int(message.command[1]) if len(message.command) > 1 else message.chat.id
        await auth_groups_db.update_one({"chat_id": target_chat}, {"$set": {"authorized": False}}, upsert=True)
        auth_groups_cache.discard(target_chat)
        await send_msg(message.chat.id, f"{pe('❌')} Access revoked for group <code>{target_chat}</code>.")
    except Exception as e:
        await send_msg(message.chat.id, "Usage: /revoke [group_id] or use in group.")

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    if await check_double_msg(message.from_user.id): return
    if not await pass_fsub(client, message): return 
    
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
        
    user = await get_or_create_user(message.from_user.id, message.from_user)
    lang = await get_lang(message.from_user.id)
    
    if not user.get("bio_link"):
        try:
            invite = await app.create_chat_invite_link(TRACK_GROUP_ID, name=f"Affiliate_{message.from_user.id}", creates_join_request=True)
            await users_db.update_one({"user_id": message.from_user.id}, {"$set": {"bio_link": invite.invite_link}})
            user["bio_link"] = invite.invite_link
        except:
            pass 
            
    welcome_head = TR[lang]["welcome_head"].format(name=html.escape(user['name']))
    await send_msg(message.chat.id, welcome_head, disable_web_page_preview=True)
    
    welcome_body = TR[lang]["welcome"].format(tag=REQUIRED_USERNAME_TAG, link=user.get('bio_link', 'No Link Generated'))
    await send_msg(message.chat.id, welcome_body, markup=get_main_menu(lang), disable_web_page_preview=True)
    
    if await is_admin(message.from_user.id):
        await send_msg(message.chat.id, f"{pe('🛡')} <b>Admin Access Recognized!</b> Send /adminhelp to see your commands.")

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client: Client, message: Message):
    if await check_double_msg(message.from_user.id): return
    if not await pass_fsub(client, message): return 
    lang = await get_lang(message.from_user.id)
    await send_msg(message.chat.id, TR[lang]["help"])

@app.on_message(filters.command("verify") & filters.private)
async def verify_cmd(client: Client, message: Message):
    if await check_double_msg(message.from_user.id): return
    if not await pass_fsub(client, message): return 
    user_id = message.from_user.id
    user_data = await get_or_create_user(user_id, message.from_user)
    lang = await get_lang(user_id)
    
    chat_info = await app.get_chat(user_id)
    full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".lower()
    
    name_ok = REQUIRED_USERNAME_TAG.lower() in full_name
    bio_ok = user_data.get("bio_link") in (chat_info.bio or "")

    if name_ok and bio_ok:
        await users_db.update_one({"user_id": user_id}, {"$set": {"verified": True}})
        await send_msg(message.chat.id, TR[lang]["verify_ok"])
    else:
        await send_msg(message.chat.id, TR[lang]["verify_fail"].format(tag=REQUIRED_USERNAME_TAG))

@app.on_message(filters.command("affiliate") & filters.private)
async def affiliate_cmd(client: Client, message: Message):
    if await check_double_msg(message.from_user.id): return
    if not await pass_fsub(client, message): return 
    user = await get_or_create_user(message.from_user.id, message.from_user)
    lang = await get_lang(message.from_user.id)
    conf = await get_config()

    if not conf.get("affiliate_enabled", True):
        return await send_msg(message.chat.id, TR[lang]["affiliate_disabled"])

    invite_link = user.get("affiliate_link")
    if not invite_link:
        try:
            invite = await app.create_chat_invite_link(TRACK_GROUP_ID, name=f"Affiliate_{message.from_user.id}", creates_join_request=True)
            invite_link = invite.invite_link
            await users_db.update_one({"user_id": message.from_user.id}, {"$set": {"affiliate_link": invite_link}})
        except:
            return await send_msg(message.chat.id, f"{pe('❌')} Error creating link. Ensure bot is admin in the tracking group.")

    markup = kb(
        [("Affiliate Status", "menu_aff_stats", "primary", "📊")],
        [(TR[lang]["btn_back"], "menu_main", "danger", "🔙")]
    )
    await send_msg(message.chat.id, TR[lang]["affiliate_link"].format(link=invite_link), markup=markup)

@app.on_message(filters.command("draw") & filters.private)
async def show_draw_cmd(client: Client, message: Message):
    if await check_double_msg(message.from_user.id): return
    if not await pass_fsub(client, message): return 
    lang = await get_lang(message.from_user.id)
    conf = await get_config()
    
    if not conf.get("draw_enabled", True):
        return await send_msg(message.chat.id, f"{pe('⚠️')} <b>Draw now disabled, soon coming.</b>")

    draw_data = await config_db.find_one({"_id": "latest_draw"})
    
    if not draw_data or not draw_data.get("winners"):
        return await send_msg(message.chat.id, TR[lang]["draw_none"])
        
    winners_text = ""
    for i, wid in enumerate(draw_data["winners"], 1):
        u_doc = await users_db.find_one({"user_id": wid})
        name = await fetch_real_name(wid, u_doc.get("name") if u_doc else None)
        winners_text += f"{i}. {html.escape(name)}\n"
        
    text = TR[lang]["draw_res"].format(
        time=draw_data["time"], total=draw_data["total"], 
        amt=draw_data.get("amount", 2.0), winners=winners_text
    )
    await send_msg(message.chat.id, text, disable_web_page_preview=True)

@app.on_message(filters.command(["daily", "weekly", "monthly", "leaderboard"]))
async def leaderboard_cmd(client: Client, message: Message):
    if await check_double_msg(message.from_user.id): return
    
    if message.chat.type == enums.ChatType.GROUP or message.chat.type == enums.ChatType.SUPERGROUP:
        if not await is_group_authorized(message.chat.id):
            return
    else:
        if not await pass_fsub(client, message): return 
        
    cmd = message.command[0].lower()
    period = cmd if cmd in ["daily", "weekly", "monthly"] else "weekly"
    lang = await get_lang(message.from_user.id)
    tr = TR.get(lang, TR["en"])
    
    text, max_pages = await generate_leaderboard_text(period, 0)
    
    d_style = "success" if period == "daily" else "primary"
    w_style = "success" if period == "weekly" else "primary"
    m_style = "success" if period == "monthly" else "primary"
    
    if message.chat.type == enums.ChatType.PRIVATE:
        btns = kb(
            [(tr["btn_daily"], "ldb_daily_0", d_style, "📅"), (tr["btn_weekly"], "ldb_weekly_0", w_style, "📅"), (tr["btn_monthly"], "ldb_monthly_0", m_style, "📅")],
            [(tr["btn_back"], "menu_main", "danger", "🔙")]
        )
    else:
        btns = kb(
            [(tr["btn_daily"], "ldb_daily_0", d_style, "📅"), (tr["btn_weekly"], "ldb_weekly_0", w_style, "📅"), (tr["btn_monthly"], "ldb_monthly_0", m_style, "📅")]
        )
        
    await send_msg(message.chat.id, text, markup=btns, disable_web_page_preview=True)

@app.on_message(filters.command(["rank", "myrank"]))
async def rank_cmd(client: Client, message: Message):
    is_private = (message.chat.type == enums.ChatType.PRIVATE)
    if not is_private:
        if not await is_group_authorized(message.chat.id):
            return

    uid = message.from_user.id
    target = message.from_user
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        uid = target.id
        
    today = str(datetime.date.today())
    
    # Get user's messages for today
    user_activity = await activity_db.aggregate([
        {"$match": {"user_id": uid, "date": today}},
        {"$group": {"_id": None, "total": {"$sum": "$message_count"}}}
    ]).to_list(1)
    
    daily_msgs = user_activity[0]["total"] if user_activity else 0
    
    # Calculate rank based on today's messages
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
           
    await send_msg(message.chat.id, text)

@app.on_message(filters.command(["balance", "bal"]))
async def balance_cmd(client: Client, message: Message):
    if await check_double_msg(message.from_user.id): return
    
    is_private = (message.chat.type == enums.ChatType.PRIVATE)
    if not is_private:
        if not await is_group_authorized(message.chat.id):
            return
    else:
        if not await pass_fsub(client, message): return
        
    user = await get_or_create_user(message.from_user.id, message.from_user)
    await send_msg(message.chat.id, f"{pe('💰')} <b>Your Current Balance:</b> {usd(float(user.get('balance', 0.0)))}")

@app.on_message(filters.command("support") & filters.private)
async def support_cmd(client: Client, message: Message):
    if await check_double_msg(message.from_user.id): return
    if not await pass_fsub(client, message): return 
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    
    if user_id in active_tickets or user_id in pending_tickets:
        return await send_msg(message.chat.id, TR[lang]["sup_pending"])
        
    user_states[user_id] = {"state": "wait_for_support"}
    await send_msg(message.chat.id, TR[lang]["sup_ask"])

@app.on_message(filters.command("withdraw") & filters.private)
async def withdraw_cmd(client: Client, message: Message):
    if await check_double_msg(message.from_user.id): return
    if not await pass_fsub(client, message): return 
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    conf = await get_config()
    
    if not conf.get("withdrawal_enabled", True): 
        return await send_msg(message.chat.id, f"{pe('⚠️')} Withdrawals are disabled.")
        
    user = await get_or_create_user(user_id, message.from_user)
    min_wd = float(conf.get("min_withdrawal", 20.0))
    bal = float(user.get("balance", 0.0))
    
    if bal < min_wd: 
        return await send_msg(message.chat.id, f"{pe('❌')} Your wallet balance is {usd(bal)}. Minimum withdrawal is {usd(min_wd)}.")
        
    user_states[user_id] = {"state": "wait_for_method", "amount": bal}
    
    markup = kb(
        [("Redcube Wallet", "wd_method_redcube", "success", "🏦")], 
        [(TR[lang]["btn_back"], "menu_main", "danger", "🔙")]
    )
    await send_msg(message.chat.id, f"{pe('💰')} <b>Balance:</b> {usd(bal)}\n\nPlease select the withdrawal method:", markup=markup)

@app.on_message(filters.command("close") & filters.private)
async def close_cmd(client: Client, message: Message):
    if not await pass_fsub(client, message): return 
    user_id = message.from_user.id
    
    if user_id not in active_tickets: 
        return await send_msg(message.chat.id, "No active ticket.")
        
    target_id = active_tickets[user_id]
    
    del active_tickets[user_id]
    if target_id in active_tickets: 
        del active_tickets[target_id]
        
    await send_msg(message.chat.id, f"{pe('✅')} Ticket closed.")
    
    try: 
        t_lang = await get_lang(target_id)
        await send_msg(target_id, TR[t_lang]["tkt_closed"])
    except: pass

# ================= CASINO GAMES COMMANDS =================
@app.on_message(filters.command(["dice", "bowl", "basket", "bask", "football", "dart", "dices", "slot", "slots", "casino"]))
async def games_cmd(client: Client, message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    is_private = (message.chat.type == enums.ChatType.PRIVATE)
    
    if is_private:
        return await send_msg(chat_id, f"{pe('⚠️')} {mention(uid)}, <b>PvP Games can only be played in our official Group Chat!</b>\n\n<b>Join the group and start playing!</b>")

    if not await is_admin(uid) and not await is_group_authorized(chat_id):
        return # Block game commands in unauthorized groups
        
    # MAX 3 GAMES ENFORCEMENT AT COMMAND LEVEL (optional fast block)
    active_group_games = sum(1 for s in matches.values() if s.get("chat_id") == chat_id and s.get("status") in ["waiting", "playing"])
    if active_group_games >= 3:
        msg = await send_msg(chat_id, f"{pe('⏳')} <b>Please wait for the active games to end! Maximum 3 games allowed at once.</b>", reply_to=message.id)
        await asyncio.sleep(4)
        await del_msg(chat_id, msg['message_id'])
        return

    conf = await get_config()
    min_bet = float(conf.get("min_bet", 1.0))
    user = await get_or_create_user(uid, message.from_user)
    bal = float(user.get("balance", 0.0))
    
    args = " ".join(message.command[1:]).strip()
    if not args:
        return await send_msg(chat_id, f"<b>Usage:</b> <code>/{message.command[0]} 1.50</code>  (minimum <b>{usd(min_bet)}</b>)")
        
    stake = parse_bet(args, bal)
    
    if stake == -1.0: return await send_msg(chat_id, f"<b>Usage:</b> <code>/{message.command[0]} 1.50</code>  (minimum <b>{usd(min_bet)}</b>)")
    if stake < min_bet: return await send_msg(chat_id, f"{pe('⚠️')} <b>Minimum bet is {usd(min_bet)}</b>")
    if bal < stake: return await send_msg(chat_id, f"{pe('⚠️')} <b>Not enough funds to play</b>\n\n{pe('💼')} <b>Current coin balance: {usd(bal)}</b> {pe('🪙')}", owner_id=uid)
    
    game_map = {"dices": "dice", "dice": "dice", "bowl": "bowl", "basket": "basket", "bask": "basket", "football": "football", "dart": "dart", "slot": "slot", "slots": "slot", "casino": "slot"}
    game = game_map[message.command[0].lower()]
    
    await send_msg(chat_id, mode_screen_text(game), markup=mode_screen_kb(game, stake), owner_id=uid)

@app.on_message(filters.dice & filters.group, group=2)
async def on_dice_received(client: Client, message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    
    if not await is_admin(uid) and not await is_group_authorized(chat_id):
        return

    if getattr(message, "forward_date", None): return
    if time.time() - message.date.timestamp() > 30: return
    
    gid = user_match.get(uid)
    if not gid or gid not in matches: return
    sess = matches[gid]
    
    if sess["chat_id"] != chat_id or sess.get("status") != "playing": return
    if message.date.timestamp() < int(sess.get("last_action", 0)): return
    
    if sess.get("rolling"):
        await send_msg(chat_id, f"⏳ {mention(uid)}, please wait for the current roll to finish before sending another dice!", reply_to=message.id)
        return
        
    if sess.get("turn_uid") != uid: return

    now = time.time()
    if now - user_last_dice_time.get(uid, 0) < 1.0: return
    user_last_dice_time[uid] = now

    raw_val = message.dice.value
    emo = get_game_emo(sess["game"])
    if message.dice.emoji != emo: return
    
    val = fix_dice_value(sess["game"], raw_val)

    async with sess["lock"]:
        if sess.get("status") != "playing": return
        sess["last_action"] = time.time()
        
        if sess.get("prompt_msg_id"):
            asyncio.create_task(clear_buttons(chat_id, sess["prompt_msg_id"]))
            sess["prompt_msg_id"] = None
            
        needed = sess["match"].rolls_needed
        rolls_list = sess["u_rolls"] if uid == sess["ua"] else sess["b_rolls"]
        if len(rolls_list) >= needed: return
        rolls_list.append(val)
        rem = needed - len(rolls_list)
        
        if rem > 0:
            sent = await send_msg(chat_id, f"{game_pe(sess['game'])} {mention(uid)}, <b>send {rem} more {sess['game'].title()}!</b>", markup=turn_kb(sess), owner_id=uid, reply_to=message.id)
            sess["prompt_msg_id"] = sent["message_id"] if sent else 0
            return
            
        sess["rolling"] = True
        try:
            await asyncio.sleep(2.0)
            if sess["type"] == "bot":
                if len(sess["b_rolls"]) < needed:
                    b_msg = await send_msg(chat_id, f"{pe('🤖')} <b>{html.escape(CASINO_NAME)}'s turn...</b>", reply_to=message.id)
                    sess["b_rolls"] += await send_emoji_roll(chat_id, sess["game"], needed - len(sess["b_rolls"]), reply_to=b_msg["message_id"] if b_msg else None)
                await evaluate_round(sess)
            else:
                if uid == sess["ua"]:
                    sess["turn_uid"], sess["rolling"], sess["last_action"] = sess["ub"], False, time.time()
                    sent = await send_msg(chat_id, f"{mention(sess['ub'])}, <b>your turn!</b> {game_pe(sess['game'])}", markup=turn_kb(sess), owner_id=sess["ub"], reply_to=message.id)
                    sess["prompt_msg_id"] = sent["message_id"] if sent else 0
                else:
                    await evaluate_round(sess)
        except Exception: sess["rolling"] = False

# ================= BACKGROUND TRACKERS =================
@app.on_chat_join_request()
async def handle_join_request(client: Client, request: ChatJoinRequest):
    user_id = request.from_user.id
    chat_id = request.chat.id
    
    user = request.from_user
    if user.is_bot or getattr(user, 'is_fake', False) or getattr(user, 'is_scam', False) or getattr(user, 'is_restricted', False):
        try: await client.decline_chat_join_request(chat_id, user_id)
        except: pass
        return
        
    conf = await get_config()
    
    if chat_id == TRACK_GROUP_ID:
        if request.invite_link and request.invite_link.name and request.invite_link.name.startswith("Affiliate_"):
            if not conf.get("affiliate_enabled", True): 
                try: await client.decline_chat_join_request(chat_id, user_id)
                except: pass
                return
                
            inviter_id = int(request.invite_link.name.split("_")[1])
            inviter_data = await get_or_create_user(inviter_id)
            
            # Check if user is already an affiliate or has left before
            if user_id not in inviter_data.get("affiliates", []) and user_id not in inviter_data.get("left_affiliates", []):
                # Send manual approval request to owner
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
                 # If they are already an affiliate or left previously, just approve silently without giving credit again
                 try: await client.approve_chat_join_request(chat_id, user_id)
                 except Exception: pass
        else:
            # Normal join request (not affiliate), auto-approve
            try: await client.approve_chat_join_request(chat_id, user_id)
            except Exception: pass

    else:
        # Not tracking group, auto-approve
        try: await client.approve_chat_join_request(chat_id, user_id)
        except Exception: pass
        
    if chat_id == TRACK_GROUP_ID:
        joining_user = await get_or_create_user(user_id, request.from_user)
        if not joining_user.get("ever_joined_group", False):
            await users_db.update_one({"user_id": user_id}, {"$set": {"ever_joined_group": True}})

@app.on_message(filters.left_chat_member & filters.chat(TRACK_GROUP_ID))
async def handle_member_leave(client: Client, message: Message):
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
    if not text: return False
    return bool(re.search(r'[А-яЁё]', text))

@app.on_message(filters.group, group=1)
async def group_activity_tracker(client: Client, message: Message):
    if not message.from_user: return
    if not await is_group_authorized(message.chat.id): return

    user_id = message.from_user.id
    full_name = message.from_user.first_name or "User"
    if message.from_user.last_name:
        full_name += f" {message.from_user.last_name}"
        
    if contains_russian(message.text or message.caption):
        try:
            await message.delete()
            await client.ban_chat_member(message.chat.id, user_id)
        except: pass
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
        except: pass
        return

    today = str(datetime.date.today())
    await users_db.update_one({"user_id": user_id}, {"$set": {"name": full_name}}, upsert=True)
    await activity_db.update_one(
        {"user_id": user_id, "group_id": message.chat.id, "date": today},
        {"$inc": {"message_count": 1}}, upsert=True
    )

# ================= ADMIN COMMANDS =================
@app.on_message(filters.command("rain") & filters.group)
async def rain_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    try:
        parts = message.text.split()
        if len(parts) != 6: raise Exception()
        
        winners_count = int(parts[1])
        total_amount = float(parts[2])
        min_msgs = int(parts[3])
        min_turnover = float(parts[4])
        time_str = parts[5].lower()
        
        duration_secs = 0
        if "h" in time_str: duration_secs = float(time_str.replace("h", "")) * 3600
        elif "m" in time_str: duration_secs = float(time_str.replace("m", "")) * 60
        else: duration_secs = float(time_str) * 60 
            
        end_time = time.time() + duration_secs
        event_id = str(random.randint(100000, 999999))
        
        await rain_db.insert_one({
            "_id": event_id, "chat_id": message.chat.id, "winners_count": winners_count,
            "total_amount": total_amount, "min_msgs": min_msgs, "min_turnover": min_turnover,
            "end_time": end_time, "participants": []
        })
        
        text = f"{pe('🌧')} <b>RAIN EVENT!</b> {pe('⛈')}\n\n{pe('🌩')} <b>Total Prize:</b> {usd(total_amount)}\n{pe('🏆')} <b>Winners:</b> {winners_count}\n{pe('✏️')} <b>Required Activity:</b> {min_msgs} messages in this group.\n{pe('🔄')} <b>Min Turnover:</b> {usd(min_turnover)}\n\n{pe('👥')} <b>Participants:</b> 0\n{pe('⏱')} <b>Ends In:</b> {time_str}"
        markup = kb([("Participate", f"rain_join_{event_id}", "success", "☔")])
        
        sent = await send_msg(message.chat.id, text, markup=markup, reply_to=message.id)
        if not sent: return 
        
        asyncio.create_task(rain_timer_task(message.chat.id, sent["message_id"], event_id, end_time, total_amount, winners_count, min_msgs, min_turnover))
    except Exception as e:
        await message.reply_text("Usage: /rain [winners] [total_amount] [min_msgs] [min_turnover] [time(h/m)]\nExample: `/rain 1 100 100 200 2h`")

@app.on_message(filters.command("adminhelp") & filters.private)
async def adminhelp_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    text = (
        f"{pe('🛡')} <b>ADMIN COMMANDS MENU</b>\n\n"
        "🔸 `/depo [amount]` - Add balance to user (reply or provide ID)\n"
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
        "🔸 `/affiliatecheck [username/id]` - Check user affiliate details\n"
        "🔸 `/rain [wins] [amt] [msgs] [min_wager] [time]` - Start group rain\n"
        "🔸 `/access` (in a group) - Authorize group for Leaderboard & Games\n"
        "🔸 `/revoke` (in a group) - Remove group authorization\n"
    )
    await send_msg(message.chat.id, text)

@app.on_message(filters.command("revokeall"))
async def revokeall_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    result = await users_db.update_many(
        {"affiliate_link": {"$exists": True}},
        {"$unset": {"affiliate_link": ""}}
    )
    await send_msg(message.chat.id, f"{pe('✅')} <b>All affiliate links revoked!</b>\n{result.modified_count} users will get a fresh link next time they use /affiliate.")

@app.on_message(filters.command("toggleaffiliate"))
async def toggleaffiliate_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    conf = await get_config()
    new_state = not conf.get("affiliate_enabled", True)
    await config_db.update_one({"_id": "settings"}, {"$set": {"affiliate_enabled": new_state}}, upsert=True)
    global CONFIG_CACHE; CONFIG_CACHE["time"] = 0 
    await send_msg(message.chat.id, f"{pe('✏️')} Affiliate System is now <b>{'ENABLED' if new_state else 'DISABLED'}</b>.")

@app.on_message(filters.command("withdrawupdate"))
async def withdrawupdate_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    try:
        parts = message.text.split()
        new_min = float(parts[1])
        await config_db.update_one({"_id": "settings"}, {"$set": {"min_withdrawal": new_min}}, upsert=True)
        global CONFIG_CACHE; CONFIG_CACHE["time"] = 0
        await send_msg(message.chat.id, f"{pe('✅')} Minimum withdrawal limit successfully updated to <b>${new_min}</b>.")
    except:
        await send_msg(message.chat.id, "Usage: /withdrawupdate [amount]\nExample: `/withdrawupdate 10`")

@app.on_message(filters.command("toggledraw"))
async def toggledraw_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    conf = await get_config()
    new_state = not conf.get("draw_enabled", True)
    await config_db.update_one({"_id": "settings"}, {"$set": {"draw_enabled": new_state}}, upsert=True)
    global CONFIG_CACHE; CONFIG_CACHE["time"] = 0 
    await send_msg(message.chat.id, f"{pe('✅')} Draw is now <b>{'ENABLED' if new_state else 'DISABLED'}</b>.")

@app.on_message(filters.command("drawsettings"))
async def drawsettings_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    try:
        parts = message.text.split()
        count = int(parts[1])
        amount = float(parts[2])
        await config_db.update_one({"_id": "settings"}, {"$set": {"draw_winners_count": count, "draw_amount": amount}}, upsert=True)
        await send_msg(message.chat.id, f"{pe('✅')} <b>Draw Settings Updated!</b>\nWinners per draw: {count}\nAmount per winner: ${amount}")
    except:
        await send_msg(message.chat.id, "Usage: /drawsettings [number_of_winners] [amount_per_winner]\nExample: `/drawsettings 10 2.5`")

@app.on_message(filters.command("redraw"))
async def redraw_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    conf = await get_config()
    win_count = conf.get("draw_winners_count", 10)
    win_amt = conf.get("draw_amount", 2.0)
    
    users = await users_db.find({"verified": True, "won_draw": {"$ne": True}}).to_list(length=None)
    if len(users) < win_count:
        await users_db.update_many({"verified": True}, {"$set": {"won_draw": False}})
        users = await users_db.find({"verified": True, "won_draw": {"$ne": True}}).to_list(length=None)
        
    if not users: return await send_msg(message.chat.id, f"{pe('❌')} No verified users available to draw.")

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
        population.pop(idx); weights.pop(idx)
        
        try:
            chat_info = await app.get_chat(winner['user_id'])
            full_name = f"{chat_info.first_name or ''} {chat_info.last_name or ''}".lower()
            if REQUIRED_USERNAME_TAG.lower() in full_name and winner.get("bio_link") in (chat_info.bio or ""):
                valid_winners.append(winner)
            else:
                await users_db.update_one({"user_id": winner['user_id']}, {"$set": {"verified": False}})
                try: await send_msg(winner['user_id'], f"{pe('⚠️')} <b>Draw Disqualified!</b> You removed the required name tag or bio link.")
                except: pass
        except: pass
            
    if not valid_winners: return await send_msg(message.chat.id, f"{pe('❌')} No strictly verified users found.")

    winner_ids = [w['user_id'] for w in valid_winners]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for wid in winner_ids:
        await users_db.update_one({"user_id": wid}, {"$set": {"won_draw": True}, "$inc": {"balance": float(win_amt)}})
        try: await send_msg(wid, f"{pe('🎉')} <b>Congratulations!</b> You won ${win_amt} in today's draw!")
        except: pass

    await config_db.update_one({"_id": "latest_draw"}, {"$set": {"time": now, "total": await users_db.count_documents({"verified": True}), "winners": winner_ids, "amount": win_amt}}, upsert=True)
    await send_msg(message.chat.id, f"{pe('✅')} <b>Draw Completed!</b>\n{len(valid_winners)} strictly active winners selected and credited ${win_amt}.")

@app.on_message(filters.command("addadmin"))
async def addadmin_cmd(client: Client, message: Message):
    if message.from_user.id != OWNER_ID: return
    try:
        target = int(message.text.split()[1])
        await admins_db.update_one({"user_id": target}, {"$set": {"user_id": target}}, upsert=True)
        await send_msg(message.chat.id, f"{pe('✅')} User <code>{target}</code> is now an Admin.")
    except: await send_msg(message.chat.id, "Usage: /addadmin [user_id]")

@app.on_message(filters.command("removeadmin"))
async def removeadmin_cmd(client: Client, message: Message):
    if message.from_user.id != OWNER_ID: return
    try:
        target = int(message.text.split()[1])
        await admins_db.delete_one({"user_id": target})
        await send_msg(message.chat.id, f"{pe('✅')} Admin <code>{target}</code> removed.")
    except: await send_msg(message.chat.id, "Usage: /removeadmin [user_id]")

@app.on_message(filters.command("adminlist"))
async def adminlist_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    admins = await admins_db.find().to_list(length=100)
    text = f"{pe('👑')} <b>Owner:</b> <code>{OWNER_ID}</code>\n\n{pe('🛡')} <b>Admins:</b>\n"
    for a in admins: text += f"- <code>{a['user_id']}</code>\n"
    await send_msg(message.chat.id, text)

@app.on_message(filters.command("setprice"))
async def setprice_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    try:
        parts = message.text.split()
        m_req = int(parts[1])
        rew = float(parts[2])
        await config_db.update_one({"_id": "settings"}, {"$set": {"affiliate_req": m_req, "affiliate_reward": rew}}, upsert=True)
        await send_msg(message.chat.id, f"{pe('✅')} Price updated: ${rew} per {m_req} members.")
    except: await send_msg(message.chat.id, "Usage: /setprice [members] [reward amount]")

@app.on_message(filters.command("togglewithdraw"))
async def togglewd_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    conf = await get_config()
    new_state = not conf.get("withdrawal_enabled", True)
    await config_db.update_one({"_id": "settings"}, {"$set": {"withdrawal_enabled": new_state}}, upsert=True)
    global CONFIG_CACHE; CONFIG_CACHE["time"] = 0 
    await send_msg(message.chat.id, f"{pe('✏️')} Withdrawals are now <b>{'ENABLED' if new_state else 'DISABLED'}</b>.")

@app.on_message(filters.command("broadcast"))
async def broadcast_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    if not message.reply_to_message: return await send_msg(message.chat.id, "Reply to a message to broadcast.")
    users = await users_db.find().to_list(length=None)
    sent = 0
    for u in users:
        try:
            await message.reply_to_message.copy(u["user_id"])
            sent += 1
            await asyncio.sleep(0.05) 
        except: pass
    await send_msg(message.chat.id, f"{pe('✅')} Broadcast complete. Sent to {sent} users.")

@app.on_message(filters.command(["check", "checkactivity"]))
async def checkactivity_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    target_id, safe_name = None, "User"
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        safe_name = html.escape(message.reply_to_message.from_user.first_name or "User")
    elif len(message.command) > 1:
        try:
            user_info = await app.get_users(message.command[1])
            target_id, safe_name = user_info.id, html.escape(user_info.first_name or "User")
        except:
            try: target_id = int(message.command[1])
            except: return await send_msg(message.chat.id, f"{pe('⚠️')} Invalid User ID or Username.")
    else: return await send_msg(message.chat.id, f"{pe('⚠️')} Usage: Reply to user or use /check [username/id]")
        
    if not target_id: return
    try:
        today = datetime.date.today()
        week_ago, month_ago = today - datetime.timedelta(days=7), today - datetime.timedelta(days=30)
        records = await activity_db.aggregate([{"$match": {"user_id": target_id}}, {"$group": {"_id": "$date", "total": {"$sum": "$message_count"}}}]).to_list(length=None)
        
        d_count, w_count, m_count = 0, 0, 0
        for r in records:
            try:
                r_date = datetime.date.fromisoformat(r["_id"])
                if r_date == today: d_count += r["total"]
                if r_date >= week_ago: w_count += r["total"]
                if r_date >= month_ago: m_count += r["total"]
            except: pass
        await send_msg(message.chat.id, f"{pe('📈')} <b>Activity Report for <a href='tg://user?id={target_id}'>{safe_name}</a> (<code>{target_id}</code>)</b>:\n\n{pe('📅')} <b>Today:</b> {d_count} msgs\n{pe('📅')} <b>This Week:</b> {w_count} msgs\n{pe('📅')} <b>This Month:</b> {m_count} msgs")
    except Exception as e: await send_msg(message.chat.id, f"{pe('⚠️')} Error: {e}")

@app.on_message(filters.command("affiliatecheck"))
async def affiliatecheck_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id): return
    target_id, safe_name = None, "User"
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        safe_name = html.escape(message.reply_to_message.from_user.first_name or "User")
    elif len(message.command) > 1:
        try:
            user_info = await app.get_users(message.command[1])
            target_id, safe_name = user_info.id, html.escape(user_info.first_name or "User")
        except:
            try: target_id = int(message.command[1])
            except: return await send_msg(message.chat.id, f"{pe('⚠️')} Invalid User ID or Username.")
    else: return await send_msg(message.chat.id, f"{pe('⚠️')} Usage: Reply to user or use /affiliatecheck [username/id]")
        
    if not target_id: return
    u_doc = await users_db.find_one({"user_id": target_id})
    if not u_doc: return await send_msg(message.chat.id, f"{pe('❌')} User not found in database.")
        
    invites, left, bal = len(u_doc.get("affiliates", [])), len(u_doc.get("left_affiliates", [])), u_doc.get("balance", 0.0)
    await send_msg(message.chat.id, f"{pe('📊')} <b>Affiliate Check for <a href='tg://user?id={target_id}'>{safe_name}</a></b>:\n\n{pe('👥')} Active Invites: {invites}\n{pe('❌')} Left Invites: {left}\n{pe('💰')} Wallet Balance: {usd(bal)}")

# ================= INLINE ROUTER =================
@app.on_callback_query()
async def cb_router(client: Client, call: CallbackQuery):
    cb_id = call.id
    data = call.data
    uid = call.from_user.id
    msg = call.message
    
    if data.startswith("rain_join_") or data.startswith("aff_approve_") or data.startswith("aff_reject_"):
        pass 
    else:
        await answer_cb(cb_id)
        
    if not msg:
        return
        
    chat_id = msg.chat.id
    msg_id = msg.id
    is_private = (msg.chat.type == enums.ChatType.PRIVATE)
    
    # AFFILIATE APPROVAL ROUTING
    if data.startswith("aff_approve_"):
        if not await is_admin(uid):
            return await answer_cb(cb_id, "You are not an admin!", show_alert=True)
            
        _, user_id_str, inviter_id_str, target_chat_str = data.split("_")
        user_id, inviter_id, target_chat = int(user_id_str), int(inviter_id_str), int(target_chat_str)
        
        try:
            await client.approve_chat_join_request(target_chat, user_id)
            
            # Update Inviter Stats
            conf = await get_config()
            await users_db.update_one({"user_id": inviter_id}, {"$addToSet": {"affiliates": user_id}})
            inviter_data = await get_or_create_user(inviter_id)
            new_count = len(inviter_data.get("affiliates", [])) + 1
            
            if new_count % conf["affiliate_req"] == 0:
                reward = conf["affiliate_reward"]
                await users_db.update_one({"user_id": inviter_id}, {"$inc": {"balance": reward}})
                lang = await get_lang(inviter_id)
                reward_msg = f"{pe('🎉')} <b>Congratulations!</b> You reached {conf['affiliate_req']} members. ${reward} added!"
                try: await send_msg(inviter_id, reward_msg)
                except: pass
                
            await edit_msg(chat_id, msg_id, f"{msg.text}\n\n{pe('✅')} <b>Approved by {mention(uid)}</b>", markup=None)
            await answer_cb(cb_id, "Request Approved!")
        except Exception as e:
            await answer_cb(cb_id, f"Error: {e}", show_alert=True)
        return

    elif data.startswith("aff_reject_"):
        if not await is_admin(uid):
            return await answer_cb(cb_id, "You are not an admin!", show_alert=True)
            
        _, user_id_str, inviter_id_str, target_chat_str = data.split("_")
        user_id, inviter_id, target_chat = int(user_id_str), int(inviter_id_str), int(target_chat_str)
        
        try:
            await client.decline_chat_join_request(target_chat, user_id)
            # Update Inviter Fake Stats
            await users_db.update_one({"user_id": inviter_id}, {"$addToSet": {"fake_affiliates": user_id}})
            
            await edit_msg(chat_id, msg_id, f"{msg.text}\n\n{pe('❌')} <b>Rejected by {mention(uid)}</b>", markup=None)
            await answer_cb(cb_id, "Request Rejected!")
        except Exception as e:
            await answer_cb(cb_id, f"Error: {e}", show_alert=True)
        return

    # GAME ROUTING
    if data == "del":
        await del_msg(chat_id, msg_id)
        return

    owner = msg_owner.get((chat_id, msg_id))
    if owner and owner != uid and not data.startswith("pvp_join:") and not data.startswith("rain_join_") and not data.startswith("aff_approve_") and not data.startswith("aff_reject_"):
        return await answer_cb(cb_id, "This button is not for you!", show_alert=True)

    if data.startswith("back_mode:"):
        if is_private: return
        _, game, stake = data.split(":")
        await edit_msg(chat_id, msg_id, mode_screen_text(game), markup=mode_screen_kb(game, float(stake)), owner_id=uid)
        return
        
    elif data.startswith("mode:"):
        if is_private: return
        _, game, stake, mode = data.split(":")
        await edit_msg(chat_id, msg_id, target_screen_text(game), markup=target_screen_kb(game, float(stake), mode), owner_id=uid)
        return
        
    elif data.startswith("tgt:"):
        if is_private: return
        _, game, stake, mode, target = data.split(":")
        base = f"{game}:{stake}:{mode}:{target}"
        await edit_msg(chat_id, msg_id, f"{game_pe(game)} <b>{game.title()} · {usd(float(stake))}</b>\n<b>Player:</b> {mention(uid)}\n<b>Mode: {MODES[mode]['label']} ({target} points)</b>\n\n<b>Choose your opponent:</b>", markup=kb([("Play vs Bot", f"opp:{base}:bot", "success", "🤖"), ("Play PvP", f"opp:{base}:pvp", "primary", "👤")], [("Back", f"mode:{game}:{stake}:{mode}", "danger", "❌")]), owner_id=uid)
        return
        
    elif data.startswith("opp:"):
        if is_private: return
        _, game, stake, mode, target, who = data.split(":")
        stake, target = float(stake), int(target)
        if uid in busy: return await answer_cb(cb_id, "Finish your current game first!", show_alert=True)
        
        # ACTIVE GAMES LIMIT ENFORCEMENT - Max 3 group games
        active_group_games = sum(1 for s in matches.values() if s.get("chat_id") == chat_id and s.get("status") in ["waiting", "playing"])
        if active_group_games >= 3:
            return await answer_cb(cb_id, "Please wait for the active games to end! Maximum 3 games allowed at once.", show_alert=True)

        user = await get_or_create_user(uid)
        bal = float(user.get("balance", 0.0))
        if bal < stake:
            return await edit_msg(chat_id, msg_id, f"{pe('⚠️')} <b>Not enough funds to play</b>\n\n{pe('💼')} <b>Current coin balance: {usd(bal)}</b> {pe('🪙')}", owner_id=uid)
        
        try: gid = await db_open_game(uid, game, mode, stake, opponent=0 if who == "bot" else -1)
        except ValueError as e: return await answer_cb(cb_id, str(e), show_alert=True)

        busy.add(uid)
        user_match[uid] = gid

        if who == "bot":
            m_obj = Match(game, mode, target, stake, (uid, 0))
            sess = {"gid": gid, "type": "bot", "status": "playing", "chat_id": chat_id, "game": game, "mode": mode, "target": target, "stake": stake, "ua": uid, "ub": 0, "match": m_obj, "turn_uid": uid, "u_rolls": [], "b_rolls": [], "rolling": False, "round_num": 1, "last_action": time.time(), "lock": asyncio.Lock(), "prompt_msg_id": msg_id}
            matches[gid] = sess
            await edit_msg(chat_id, msg_id, f"{pe('🌊')} <b>The game has started</b>\n\n<b>Player 1:</b> {mention(uid)}\n<b>Player 2:</b> {pe('🤖')} <b>{html.escape(CASINO_NAME)}</b>\n<b>Bet: {usd(stake)}</b> {pe('🪙')}\n<b>Mode: {MODES[mode]['label']} — {target} points</b>\n\n<b>Roll the {game.title()}</b> {game_pe(game)}", markup=turn_kb(sess, show_bot_first=True, is_round_start=True), owner_id=uid)
        else:
            sess = {"gid": gid, "type": "pvp", "status": "waiting", "chat_id": chat_id, "game": game, "mode": mode, "target": target, "stake": stake, "ua": uid, "ub": 0, "u_rolls": [], "b_rolls": [], "rolling": False, "round_num": 1, "created_at": time.time(), "last_action": time.time(), "lock": asyncio.Lock(), "prompt_msg_id": msg_id}
            matches[gid] = sess
            await edit_msg(chat_id, msg_id, f"{pe('🎮')} <b>PvP Match Created</b>\n\n<b>Player 1:</b> {mention(uid)}\n<b>Game:</b> {game_pe(game)} <b>{game.title()}</b>\n<b>Bet: {usd(stake)}</b> {pe('🪙')}\n<b>Mode: {MODES[mode]['label']} — {target} points</b>\n\n<i>Click «Accept game» to start PvP!</i>", markup=kb([("Accept game", f"pvp_join:{gid}", "success", "✅")], [("Cancel game", f"cancel_pvp:{gid}", "danger", "❌")]), owner_id=uid)
        return

    elif data.startswith("pvp_join:"):
        gid = data.split(":")[1]
        sess = matches.get(gid)
        if not sess or sess.get("status") != "waiting": return await answer_cb(cb_id, "This match is no longer available!", show_alert=True)
        if uid == sess["ua"]: return await answer_cb(cb_id, "You cannot accept your own match!", show_alert=True)
        if uid in busy: return await answer_cb(cb_id, "Finish your current game first!", show_alert=True)

        user = await get_or_create_user(uid)
        bal = float(user.get("balance", 0.0))
        stake = sess["stake"]
        if bal < stake: return await answer_cb(cb_id, f"Not enough balance! Need {usd(stake)}.", show_alert=True)
        
        try: gid_b = await db_open_game(uid, sess["game"], sess["mode"], stake, opponent=-1)
        except ValueError as e: return await answer_cb(cb_id, str(e), show_alert=True)

        sess["ub"] = uid
        sess["gid_b"] = gid_b
        sess["status"] = "playing"
        sess["match"] = Match(sess["game"], sess["mode"], sess["target"], stake, (sess["ua"], uid))
        sess["turn_uid"] = sess["ua"]
        sess["last_action"] = time.time()
        busy.add(uid)
        user_match[uid] = gid

        start_txt = f"{pe('🌊')} <b>The game has started</b>\n\n<b>Player 1:</b> {mention(sess['ua'])}\n<b>Player 2:</b> {mention(uid)}\n<b>Bet: {usd(stake)}</b> {pe('🪙')}\n<b>Mode: {MODES[sess['mode']]['label']} — {sess['target']} points</b>\n\n{mention(sess['ua'])}, <b>your turn!</b>"
        await edit_msg(chat_id, msg_id, start_txt, markup=turn_kb(sess, show_bot_first=False, is_round_start=True), owner_id=sess["ua"])
        sess["prompt_msg_id"] = msg_id
        return

    elif data.startswith("cancel_pvp:"):
        gid = data.split(":")[1]
        sess = matches.get(gid)
        if not sess or sess.get("status") != "waiting" or sess["ua"] != uid: return
        await db_void_game(gid)
        matches.pop(gid, None); user_match.pop(uid, None); busy.discard(uid)
        await edit_msg(chat_id, msg_id, f"{pe('⭕️')} <b>PvP match cancelled by</b> {mention(uid)} — <b>stake refunded.</b>", owner_id=uid)
        return

    elif data.startswith("roll:"):
        _, gid_str, order = data.split(":")
        sess = matches.get(gid_str)
        if not sess or sess.get("status") != "playing": return
        if sess.get("turn_uid") != uid: return
        needed = sess["match"].rolls_needed
        my_rolls = sess["u_rolls"] if uid == sess["ua"] else sess["b_rolls"]
        if sess.get("rolling") or sess["lock"].locked() or len(my_rolls) >= needed: return
        asyncio.create_task(handle_roll_button(sess, uid, order))
        return

    elif data.startswith("cashout:"):
        gid = data.split(":")[1]
        sess = matches.get(gid)
        if not sess or sess["ua"] != uid or sess.get("rolling") or sess["lock"].locked(): return
        cashout_amt = calc_cashout(sess["stake"], sess["match"].score[0], sess["match"].score[1], sess["target"])
        if cashout_amt <= 0: return
        asyncio.create_task(clear_buttons(chat_id, msg_id))
        await finish_match(sess, cashout_amt, cashed_out=True)
        return

    # MENU ROUTING
    if data == "menu_main":
        if not await pass_fsub(client, call): return 
        if uid in user_states: del user_states[uid]
        user = await get_or_create_user(uid, call.from_user)
        lang = await get_lang(uid)
        welcome_body = TR[lang]["welcome"].format(tag=REQUIRED_USERNAME_TAG, link=user.get('bio_link', 'No Link Generated'))
        await edit_msg(chat_id, msg_id, welcome_body, markup=get_main_menu(lang))
        
    elif data == "menu_verify":
        if not await pass_fsub(client, call): return 
        user_data = await get_or_create_user(uid, call.from_user)
        lang = await get_lang(uid)
        chat_info = await app.get_chat(uid)
        full_name = f"{call.from_user.first_name or ''} {call.from_user.last_name or ''}".lower()
        name_ok = REQUIRED_USERNAME_TAG.lower() in full_name
        bio_ok = user_data.get("bio_link") in (chat_info.bio or "")
        markup = kb([(TR[lang]["btn_back"], "menu_main", "danger", "🔙")])
        if name_ok and bio_ok:
            await users_db.update_one({"user_id": uid}, {"$set": {"verified": True}})
            await edit_msg(chat_id, msg_id, TR[lang]["verify_ok"], markup=markup)
        else:
            await edit_msg(chat_id, msg_id, TR[lang]["verify_fail"].format(tag=REQUIRED_USERNAME_TAG), markup=markup)

    elif data == "menu_affiliate":
        if not await pass_fsub(client, call): return 
        user = await get_or_create_user(uid, call.from_user)
        lang = await get_lang(uid)
        conf = await get_config()
        if not conf.get("affiliate_enabled", True):
            markup = kb([(TR[lang]["btn_back"], "menu_main", "danger", "🔙")])
            return await edit_msg(chat_id, msg_id, TR[lang]["affiliate_disabled"], markup=markup)
        invite_link = user.get("affiliate_link")
        if not invite_link:
            try:
                invite = await app.create_chat_invite_link(TRACK_GROUP_ID, name=f"Affiliate_{uid}", creates_join_request=True)
                invite_link = invite.invite_link
                await users_db.update_one({"user_id": uid}, {"$set": {"affiliate_link": invite_link}})
            except:
                return await send_msg(chat_id, "Error creating link. Bot must be admin.")
        markup = kb([("Affiliate Status", "menu_aff_stats", "primary", "📊")], [(TR[lang]["btn_back"], "menu_main", "danger", "🔙")])
        await edit_msg(chat_id, msg_id, TR[lang]["affiliate_link"].format(link=invite_link), markup=markup, disable_web_page_preview=True)

    elif data == "menu_aff_stats":
        if not await pass_fsub(client, call): return 
        user = await get_or_create_user(uid, call.from_user)
        lang = await get_lang(uid)
        conf = await get_config()
        markup = kb([(TR[lang]["btn_back"], "menu_affiliate", "danger", "🔙")])
        await edit_msg(chat_id, msg_id, TR[lang]["affiliate_stats"].format(real=len(user.get("affiliates", [])), left=len(user.get("left_affiliates", [])), fake=len(user.get("fake_affiliates", [])), reward=conf['affiliate_reward'], req=conf['affiliate_req']), markup=markup)

    elif data == "menu_support":
        if not await pass_fsub(client, call): return 
        lang = await get_lang(uid)
        if uid in active_tickets or uid in pending_tickets: return await send_msg(chat_id, "You already have an active/pending ticket.")
        user_states[uid] = {"state": "wait_for_support"}
        markup = kb([(TR[lang]["btn_back"], "menu_main", "danger", "🔙")])
        await edit_msg(chat_id, msg_id, TR[lang]["sup_ask"], markup=markup)

    elif data == "menu_draw":
        if not await pass_fsub(client, call): return 
        lang = await get_lang(uid)
        conf = await get_config()
        markup = kb([(TR[lang]["btn_back"], "menu_main", "danger", "🔙")])
        if not conf.get("draw_enabled", True): return await edit_msg(chat_id, msg_id, f"{pe('⚠️')} <b>Draw now disabled, soon coming.</b>", markup=markup)
        draw_data = await config_db.find_one({"_id": "latest_draw"})
        if not draw_data or not draw_data.get("winners"): return await edit_msg(chat_id, msg_id, TR[lang]["draw_none"], markup=markup)
        winners_text = ""
        for i, wid in enumerate(draw_data["winners"], 1):
            u_doc = await users_db.find_one({"user_id": wid})
            name = await fetch_real_name(wid, u_doc.get("name") if u_doc else None)
            winners_text += f"{i}. {html.escape(name)}\n"
        text = TR[lang]["draw_res"].format(time=draw_data["time"], total=draw_data["total"], amt=draw_data.get("amount", 2.0), winners=winners_text)
        await edit_msg(chat_id, msg_id, text, markup=markup, disable_web_page_preview=True)

    elif data == "menu_lang":
        if not await pass_fsub(client, call): return 
        lang = await get_lang(uid)
        btns = kb([("English", "lang_en", "primary", "🇬🇧"), ("Русский", "lang_ru", "danger", "🇷🇺")], [("हिंदी (Hindi)", "lang_hi", "success", "🇮🇳")], [(TR[lang]["btn_back"], "menu_main", "danger", "🔙")])
        await edit_msg(chat_id, msg_id, "Select your language / Выберите язык / भाषा चुनें:", markup=btns)

    elif data.startswith("lang_"):
        if not await pass_fsub(client, call): return 
        new_lang = data.split("_")[1]
        await users_db.update_one({"user_id": uid}, {"$set": {"lang": new_lang}})
        user_langs[uid] = new_lang
        user = await get_or_create_user(uid, call.from_user)
        welcome_body = TR[new_lang]["welcome"].format(tag=REQUIRED_USERNAME_TAG, link=user.get('bio_link', ''))
        await edit_msg(chat_id, msg_id, TR[new_lang]["lang_set"] + "\n\n" + welcome_body, markup=get_main_menu(new_lang))

    elif data == "menu_leaderboard":
        if is_private and not await pass_fsub(client, call): return 
        if not is_private and not await is_group_authorized(chat_id): return
        lang = await get_lang(uid)
        tr = TR.get(lang, TR["en"])
        text, _ = await generate_leaderboard_text("weekly", 0)
        btns = kb([(tr["btn_daily"], "ldb_daily_0", "primary", "📅"), (tr["btn_weekly"], "ldb_weekly_0", "success", "📅"), (tr["btn_monthly"], "ldb_monthly_0", "primary", "📅")], [(tr["btn_back"], "menu_main", "danger", "🔙")]) if is_private else kb([(tr["btn_daily"], "ldb_daily_0", "primary", "📅"), (tr["btn_weekly"], "ldb_weekly_0", "success", "📅"), (tr["btn_monthly"], "ldb_monthly_0", "primary", "📅")])
        await edit_msg(chat_id, msg_id, text, markup=btns, disable_web_page_preview=True)

    elif data.startswith("ldb_"):
        match = re.match(r"^ldb_(daily|weekly|monthly)_(\d+)$", data)
        if not match: return
        period, page = match.group(1), int(match.group(2))
        lang = await get_lang(uid)
        tr = TR.get(lang, TR["en"])
        text, _ = await generate_leaderboard_text(period, page)
        d_style = "success" if period == "daily" else "primary"
        w_style = "success" if period == "weekly" else "primary"
        m_style = "success" if period == "monthly" else "primary"
        row1 = [(tr["btn_daily"], f"ldb_daily_0", d_style, "📅"), (tr["btn_weekly"], f"ldb_weekly_0", w_style, "📅"), (tr["btn_monthly"], f"ldb_monthly_0", m_style, "📅")]
        btns = kb(row1, [(tr["btn_back"], "menu_main", "danger", "🔙")]) if is_private else kb(row1)
        await edit_msg(chat_id, msg_id, text, markup=btns, disable_web_page_preview=True)

    elif data == "menu_withdraw":
        if not await pass_fsub(client, call): return 
        lang = await get_lang(uid)
        conf = await get_config()
        if not conf.get("withdrawal_enabled", True): 
            return await edit_msg(chat_id, msg_id, f"{pe('⚠️')} Withdrawals are disabled.", markup=kb([(TR[lang]["btn_back"], "menu_main", "danger", "🔙")]))
        user = await get_or_create_user(uid, call.from_user)
        min_wd = float(conf.get("min_withdrawal", 20.0))
        bal = float(user.get("balance", 0.0))
        if bal < min_wd: 
            return await edit_msg(chat_id, msg_id, f"{pe('❌')} Your wallet balance is {usd(bal)}. Minimum withdrawal is {usd(min_wd)}.", markup=kb([(TR[lang]["btn_back"], "menu_main", "danger", "🔙")]))
        user_states[uid] = {"state": "wait_for_method", "amount": bal}
        await edit_msg(chat_id, msg_id, f"{pe('💰')} <b>Balance:</b> {usd(bal)}\n\nPlease select the withdrawal method:", markup=kb([("Redcube Wallet", "wd_method_redcube", "success", "🏦")], [(TR[lang]["btn_back"], "menu_main", "danger", "🔙")]))

    elif data == "wd_method_redcube":
        if not await pass_fsub(client, call): return 
        lang = await get_lang(uid)
        state_info = user_states.get(uid, {})
        if state_info.get("state") != "wait_for_method": return await send_msg(chat_id, "Session expired. Please request withdrawal again.")
        amount = state_info["amount"]
        await users_db.update_one({"user_id": uid}, {"$inc": {"balance": -float(amount)}})
        del user_states[uid]
        safe_name = html.escape(call.from_user.first_name or "User")
        admin_text = f"{pe('🆕')} <b>Withdrawal Request (Redcube Wallet)</b>\n{pe('👨‍💻')} User: <a href='tg://user?id={uid}'>{safe_name}</a> (<code>{uid}</code>)\n{pe('💰')} Amount: {usd(amount)}"
        btns = kb([("Accept", f"wdone_{uid}_{amount}", "success"), ("Reject", f"wrej_{uid}_{amount}", "danger")])
        admins = await admins_db.find().to_list(100)
        admin_withdraw_msgs[uid] = {}
        for aid in set([OWNER_ID] + [a["user_id"] for a in admins]):
            try: 
                sent_msg = await send_msg(aid, admin_text, markup=btns)
                if sent_msg: admin_withdraw_msgs[uid][aid] = sent_msg['message_id']
            except: pass
        await edit_msg(chat_id, msg_id, f"{pe('✅')} Your Redcube Wallet withdrawal request has been sent to admins.", markup=kb([(TR[lang]["btn_back"], "menu_main", "primary", "🔙")]))

    elif data.startswith("tktacc_"):
        if not await is_admin(uid): return
        target_id = int(data.split("_")[1])
        if target_id not in pending_tickets: return await send_msg(chat_id, "This ticket is no longer pending or has been closed.")
        pending_tickets.pop(target_id, None) 
        active_tickets[target_id] = uid; active_tickets[uid] = target_id
        admin_name = html.escape(call.from_user.first_name or "Admin")
        update_text = f"{pe('✅')} <b>Ticket Accepted & Resolved by <a href='tg://user?id={uid}'>{admin_name}</a></b>"
        if target_id in admin_ticket_msgs:
            for aid, mid in admin_ticket_msgs[target_id].items():
                try: await edit_msg(aid, mid, update_text, markup=None)
                except: pass
            del admin_ticket_msgs[target_id]
        else: await edit_msg(chat_id, msg_id, update_text, markup=None)
        t_lang = await get_lang(target_id)
        await send_msg(target_id, TR[t_lang]["tkt_joined"])
        await send_msg(uid, f"{pe('✅')} Session Started with <code>{target_id}</code>.\nUse /close to end.")

    elif data.startswith("tktrej_"):
        if not await is_admin(uid): return
        target_id = int(data.split("_")[1])
        ticket_id = re.search(r"#TKT\d+", msg.text or msg.caption or "").group(0) if re.search(r"#TKT\d+", msg.text or msg.caption or "") else "#TKT_UNKNOWN"
        pending_tickets.pop(target_id, None)
        admin_name = html.escape(call.from_user.first_name or "Admin")
        update_text = f"{pe('❌')} <b>Ticket Rejected by <a href='tg://user?id={uid}'>{admin_name}</a></b>"
        if target_id in admin_ticket_msgs:
            for aid, mid in admin_ticket_msgs[target_id].items():
                try: await edit_msg(aid, mid, update_text, markup=None)
                except: pass
            del admin_ticket_msgs[target_id]
        else: await edit_msg(chat_id, msg_id, update_text, markup=None)
        t_lang = await get_lang(target_id)
        try: await send_msg(target_id, TR[t_lang]["tkt_rejected"].format(tkt=ticket_id))
        except: pass

    elif data.startswith("wdone_"):
        if not await is_admin(uid): return
        _, target_id, amount = data.split("_")
        user_states[uid] = {"state": "wait_for_txlink", "target_id": int(target_id), "amount": amount}
        admin_name = html.escape(call.from_user.first_name or "Admin")
        update_text = f"{pe('✅')} <b>Withdrawal Processed by <a href='tg://user?id={uid}'>{admin_name}</a></b>"
        target_id = int(target_id)
        if target_id in admin_withdraw_msgs:
            for aid, mid in admin_withdraw_msgs[target_id].items():
                try: await edit_msg(aid, mid, update_text, markup=None)
                except: pass
            del admin_withdraw_msgs[target_id]
        else: await edit_msg(chat_id, msg_id, update_text, markup=None)
        await send_msg(chat_id, f"{pe('✏️')} <b>Please type the Transaction Link for this withdrawal:</b>")

    elif data.startswith("wrej_"):
        if not await is_admin(uid): return
        _, target_id, amount = data.split("_")
        user_states[uid] = {"state": "wait_for_reason", "target_id": int(target_id), "amount": amount}
        admin_name = html.escape(call.from_user.first_name or "Admin")
        update_text = f"{pe('❌')} <b>Withdrawal Rejected by <a href='tg://user?id={uid}'>{admin_name}</a></b>"
        target_id = int(target_id)
        if target_id in admin_withdraw_msgs:
            for aid, mid in admin_withdraw_msgs[target_id].items():
                try: await edit_msg(aid, mid, update_text, markup=None)
                except: pass
            del admin_withdraw_msgs[target_id]
        else: await edit_msg(chat_id, msg_id, update_text, markup=None)
        await send_msg(chat_id, f"{pe('✏️')} <b>Please type the reason for rejection:</b>")

    elif data.startswith("rain_join_"):
        event_id = data.split("_")[2]
        event = await rain_db.find_one({"_id": event_id})
        if not event: return await answer_cb(cb_id, "This event has ended!", show_alert=True)
        if uid in event.get("participants", []): return await answer_cb(cb_id, "You are already participating!", show_alert=True)
        min_msgs = event.get("min_msgs", 0)
        min_turnover = event.get("min_turnover", 0.0)
        
        # Check messages
        activity = await activity_db.aggregate([{"$match": {"user_id": uid, "group_id": chat_id}}, {"$group": {"_id": None, "total": {"$sum": "$message_count"}}}]).to_list(1)
        total_sent = activity[0]["total"] if activity else 0
        if total_sent < min_msgs: return await answer_cb(cb_id, f"You need at least {min_msgs} messages in this group to participate!\n\nYou currently have {total_sent} messages.", show_alert=True)
        
        # Check turnover
        u_data = await get_or_create_user(uid)
        turnover = float(u_data.get("wagered", 0.0))
        if turnover < min_turnover: return await answer_cb(cb_id, f"You need at least {usd(min_turnover)} turnover (wagered) to participate!\n\nYou currently have {usd(turnover)}.", show_alert=True)
        
        await answer_cb(cb_id, "You have successfully joined the Rain Event! 💧", show_alert=True)
        await rain_db.update_one({"_id": event_id}, {"$addToSet": {"participants": uid}})

@app.on_message(filters.private & filters.text & ~filters.regex(r"^/"))
async def plain_text_handler(client: Client, message: Message):
    if await check_double_msg(message.from_user.id): return
    if not await pass_fsub(client, message): return 
    uid = message.from_user.id
    lang = await get_lang(uid)
    state = user_states.get(uid, {}).get("state")
    safe_name = html.escape(message.from_user.first_name or "User")
    
    if state == "wait_for_support":
        reason = message.text
        del user_states[uid]
        ticket_id = f"#TKT{random.randint(10000, 99999)}"
        pending_tickets[uid] = ticket_id  
        btns = kb([("Accept", f"tktacc_{uid}", "success"), ("Reject", f"tktrej_{uid}", "danger")])
        admin_text = f"{pe('🎟')} <b>New Support Ticket ({ticket_id})</b>\n{pe('👥')} User: <a href='tg://user?id={uid}'>{safe_name}</a> (<code>{uid}</code>)\n{pe('✏️')} <b>Reason:</b> {html.escape(reason)}"
        admins = await admins_db.find().to_list(100)
        admin_ticket_msgs[uid] = {}
        for aid in set([OWNER_ID] + [a["user_id"] for a in admins]):
            try: 
                msg = await send_msg(aid, admin_text, markup=btns)
                if msg: admin_ticket_msgs[uid][aid] = msg['message_id']
            except: pass
        return await send_msg(message.chat.id, TR[lang]["sup_sent"].format(tkt=ticket_id), markup=kb([(TR[lang]["btn_back"], "menu_main", "primary", "🔙")]))

    if state == "wait_for_txlink":
        if not await is_admin(uid): return
        target_id = user_states[uid]["target_id"]
        amount = float(user_states[uid]["amount"])
        tx_link = message.text
        del user_states[uid]
        try: await send_msg(target_id, f"{pe('✅')} <b>Your withdrawal of {usd(amount)} has been successfully processed!</b>\n\n{pe('⛓️')} <b>Transaction Link:</b> {html.escape(tx_link)}", disable_web_page_preview=True)
        except: pass
        await users_db.update_one({"user_id": target_id}, {"$inc": {"total_withdrawn": amount}})
        return await send_msg(message.chat.id, f"{pe('✅')} Withdrawal marked as Paid and transaction link sent to user.")

    if state == "wait_for_reason":
        if not await is_admin(uid): return
        target_id = user_states[uid]["target_id"]
        amount = float(user_states[uid]["amount"])
        reason = message.text
        await users_db.update_one({"user_id": target_id}, {"$inc": {"balance": amount}})
        del user_states[uid]
        t_lang = await get_lang(target_id)
        try: await send_msg(target_id, TR[t_lang]["wd_rej"].format(amount=usd(amount), reason=html.escape(reason)))
        except: pass
        return await send_msg(message.chat.id, f"{pe('✅')} Rejection reason sent and funds refunded to user.")

    if uid in active_tickets:
        target_id = active_tickets[uid]
        try: 
            if await is_admin(uid): await message.copy(target_id)
            else: await message.forward(target_id)
        except: pass

# ================= SAFE DUMMY WEB SERVER (FOR RENDER) =================
async def web_server():
    async def handle(request):
        return web.Response(text="Bot is Alive and Running on Render! ✅")
    web_app = web.Application()
    web_app.router.add_get('/', handle)
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    try:
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        print(f"Fake Web Server Started on port {port} 🌐")
    except Exception as e:
        print(f"Port {port} in use! (Render deploy overlapping). Error: {e}")

# ================= STARTUP =================
async def main():
    await app.start()
    asyncio.create_task(web_server())
    asyncio.create_task(background_verification_check())
    asyncio.create_task(sweeper())
    await app.set_bot_commands([BotCommand("start", "Start Menu"), BotCommand("lang", "Change Language"), BotCommand("help", "Commands list")])
    print("Bot is successfully running! ✅ Games Integrated.")
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())