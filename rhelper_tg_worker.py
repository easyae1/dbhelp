import json
import socket
import ssl
import time
import urllib.parse
from pathlib import Path

TOKEN = "9047569762:AAE-9K8WiFcbVOCjsz4bupkKbPhiJCz7yzQ"
HOST = "api.telegram.org"
IP = "149.154.167.220"
STATE_FILE = Path(r"C:\Users\ya\AppData\Local\Programs\Arizona Games Launcher\bin\rodina\moonloader\config\RHelper_tg_state.txt")
BIND_FILE = Path(r"C:\Users\ya\AppData\Local\Programs\Arizona Games Launcher\bin\rodina\moonloader\config\RHelper_tg_bind.json")

KB = json.dumps({
    "keyboard": [
        [{"text": "📊 Статистика"}, {"text": "💰 Баланс"}],
        [{"text": "💤 PayDay / AFK"}, {"text": "🎒 Инвентарь"}],
    ],
    "resize_keyboard": True,
}, ensure_ascii=False)


def tg_call(path_query, timeout=6):
    raw_sock = socket.create_connection((IP, 443), timeout=timeout)
    raw_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    ctx = ssl.create_default_context()
    bio_in = ssl.MemoryBIO()
    bio_out = ssl.MemoryBIO()
    ssl_obj = ctx.wrap_bio(bio_in, bio_out, server_hostname=HOST)
    first = True
    while True:
        try:
            ssl_obj.do_handshake()
            break
        except ssl.SSLWantReadError:
            out = bio_out.read()
            if out:
                if first and len(out) > 15:
                    raw_sock.send(out[:2])
                    raw_sock.send(out[2:15])
                    raw_sock.send(out[15:])
                    first = False
                else:
                    raw_sock.send(out)
            chunk = raw_sock.recv(4096)
            if not chunk:
                raw_sock.close()
                return {}
            bio_in.write(chunk)
    req = (
        f"GET /bot{TOKEN}/{path_query} HTTP/1.1\r\n"
        f"Host: {HOST}\r\n"
        f"User-Agent: Mozilla/5.0\r\n"
        f"Connection: close\r\n\r\n"
    ).encode("utf-8")
    ssl_obj.write(req)
    while True:
        out = bio_out.read()
        if not out:
            break
        raw_sock.send(out)
    resp = b""
    while True:
        try:
            c = ssl_obj.read(4096)
            if not c:
                break
            resp += c
        except ssl.SSLWantReadError:
            chunk = raw_sock.recv(4096)
            if not chunk:
                break
            bio_in.write(chunk)
        except ssl.SSLZeroReturnError:
            break
    raw_sock.close()
    raw = resp.split(b"\r\n\r\n", 1)[-1].decode("utf-8", "replace")
    i = raw.find("{")
    j = raw.rfind("}")
    if i != -1 and j != -1 and j > i:
        return json.loads(raw[i:j + 1])
    return {}


def tg_send(cid, text):
    try:
        params = urllib.parse.urlencode({
            "chat_id": str(cid),
            "parse_mode": "HTML",
            "text": text,
            "reply_markup": KB,
        })
        return tg_call(f"sendMessage?{params}", timeout=6)
    except Exception:
        return {}


def read_state():
    st = {
        "enabled": "true", "chatId": "1957872948", "secret": "", "endpoint": "http://153.52.155.64:8787/api/state", "notifyPayday": "true", "notifyInv": "true",
        "paydaySeq": "0", "testSeq": "0", "itemSeq": "0", "lastItem": "",
        "nick": "Игрок", "level": "0", "exp": "0/0",
        "cash": "0 р.", "bank": "0 р.", "dep": "0 р.", "total": "0 р.", "az": "0",
        "afkTime": "0 ч 0 мин", "afkPaydays": "0", "afkRub": "0 р.",
        "afkDep": "0 р.", "afkSal": "0 р.", "afkAz": "0", "afkPerHour": "0 р.",
        "invSlots": "0", "invAt": "-", "addedCount": "0", "items": [], "curitems": [],
    }
    if not STATE_FILE.exists():
        return st
    try:
        raw_bytes = STATE_FILE.read_bytes()
        lines = []
        for bline in raw_bytes.splitlines():
            try:
                lines.append(bline.decode("utf-8"))
            except UnicodeDecodeError:
                lines.append(bline.decode("cp1251", errors="replace"))
        for line in lines:
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k == "item":
                st["items"].append(v)
            elif k == "curitem":
                st["curitems"].append(v)
            else:
                st[k] = v
    except Exception:
        pass
    return st


def load_bind():
    if BIND_FILE.exists():
        try:
            return json.loads(BIND_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"chats": [1957872948], "last_update": 0, "paydaySeq": "0", "testSeq": "0", "itemSeq": "0"}


def save_bind(b):
    try:
        BIND_FILE.parent.mkdir(parents=True, exist_ok=True)
        BIND_FILE.write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def build_msg(st, kind):
    if kind == "balance":
        return (
            f"💰 <b>Баланс персонажа ({st['nick']})</b>\n\n"
            f"💵 Наличка (на руках): <b>{st['cash']}</b>\n"
            f"🏦 Банк (на счету): <b>{st['bank']}</b>\n"
            f"📈 Депозит в банке: <b>{st['dep']}</b>\n"
            f"💎 Донат-счёт: <b>{st['az']} AZ</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"∑ Общая сумма: <b>{st['total']}</b>"
        )
    if kind == "afk":
        pd_at = st.get("pdAt", "-")
        pd_sal = st.get("pdSal", "0 руб.")
        pd_dep = st.get("pdDep", "0 руб.")
        pd_tot = st.get("pdTotal", "0 руб.")
        pd_az = st.get("pdAz", "0")
        pd_exp = st.get("pdExp", "0")
        return (
            f"🧾 <b>Банковский чек (PayDay в {pd_at})</b>\n"
            f"• Игровой уровень: <b>{st['level']}</b>, опыт: <b>{st['exp']} (+{pd_exp})</b>\n"
            f"• На банковском счету: <b>{st['bank']}</b> (пришло: <b>+{pd_sal}</b>)\n"
            f"• Депозит в банке: <b>{st['dep']}</b> (пришло: <b>+{pd_dep}</b>)\n"
            f"• Всего донат-очков: <b>{st['az']} AZ</b> (пришло: <b>+{pd_az} AZ</b>)\n"
            f"• Итого за этот PayDay: <b>+{pd_tot}</b>\n\n"
            f"💤 <b>Накоплено за всю сессию AFK ({st['afkTime']})</b>\n"
            f"• Получено PayDay: <b>{st['afkPaydays']}</b>\n"
            f"• Пришло с зарплаты/чеков: <b>+{st['afkSal']}</b>\n"
            f"• Пришло с депозита: <b>+{st['afkDep']}</b>\n"
            f"• Пришло доната: <b>+{st['afkAz']} AZ</b>\n"
            f"• Общий приход за сессию: <b>+{st['afkRub']}</b> (~{st['afkPerHour']} / час)\n\n"
            f"💰 <b>Текущий баланс по счетам:</b>\n"
            f"💵 Наличка: <b>{st['cash']}</b>\n"
            f"🏦 Банк: <b>{st['bank']}</b>\n"
            f"📈 Депозит: <b>{st['dep']}</b>\n"
            f"∑ Общая сумма: <b>{st['total']}</b>"
        )
    if kind == "inv":
        curitems = st.get("curitems") or []
        items = st.get("items") or []
        if not curitems:
            cur_text = "\n<i>Откройте инвентарь в игре (клавиша I), чтобы скрипт считал все текущие предметы.</i>"
        else:
            shown = curitems[:45]
            extra = f"\n<i>...и ещё {len(curitems) - 45} поз.</i>" if len(curitems) > 45 else ""
            cur_text = f"\n<b>📦 В инвентаре сейчас (обновлено в {st.get('invAt', '-')}):</b>\n" + "\n".join(f"• {x}" for x in shown) + extra
        add_text = "\n\n<b>🆕 Добавилось за сессию:</b>\nПока новых предметов не зафиксировано." if not items else (
            "\n\n<b>🆕 Добавилось за сессию:</b>\n" + "\n".join(f"• {x}" for x in reversed(items[-12:]))
        )
        return f"🎒 <b>Инвентарь персонажа ({st['nick']})</b>\nЗанято слотов: <b>{st['invSlots']}</b> (уникальных: <b>{len(curitems)}</b>){cur_text}{add_text}"
    return (
        f"📊 <b>Статистика персонажа</b>\n\n"
        f"👤 Ник: <b>{st['nick']}</b>\n"
        f"⭐ Уровень: <b>{st['level']}</b> (EXP: <b>{st['exp']}</b>)\n\n"
        f"💰 <b>Деньги по счетам:</b>\n"
        f"  💵 Наличка: <b>{st['cash']}</b>\n"
        f"  🏦 Банк: <b>{st['bank']}</b>\n"
        f"  📈 Депозит: <b>{st['dep']}</b>\n"
        f"  💎 Донат: <b>{st['az']} AZ</b>\n"
        f"  ∑ Общая сумма: <b>{st['total']}</b>\n\n"
        f"🔔 PayDay за сессию: <b>{st['afkPaydays']}</b> (+{st['afkRub']})\n"
        f"🎒 Новых предметов: <b>{st['addedCount']}</b>"
    )


def step(b):
    st = read_state()
    raw_cid = str(st.get("chatId") or "0").strip()
    cfg_cid = int(raw_cid) if raw_cid.lstrip("-").isdigit() and int(raw_cid) != 0 else 1957872948

    if st["enabled"] == "true" and cfg_cid != 0:
        if st["testSeq"] != b.get("testSeq", "0") and st["testSeq"] != "0":
            b["testSeq"] = st["testSeq"]
            save_bind(b)
            tg_send(cfg_cid, "✅ <b>Тестовая сводка RHelper:</b>\n\n" + build_msg(st, "stats"))
        if st["notifyPayday"] == "true" and st["paydaySeq"] != b.get("paydaySeq", "0") and st["paydaySeq"] != "0":
            b["paydaySeq"] = st["paydaySeq"]
            save_bind(b)
            tg_send(cfg_cid, "🔔 <b>Пришёл новый PayDay!</b>\n\n" + build_msg(st, "afk"))
        if st["notifyInv"] == "true" and st["itemSeq"] != b.get("itemSeq", "0") and st["itemSeq"] != "0":
            b["itemSeq"] = st["itemSeq"]
            save_bind(b)
            if st.get("lastItem"):
                tg_send(cfg_cid, f"🎒 <b>Новый предмет в инвентаре:</b>\n<b>{st['lastItem']}</b>")

    offset = int(b.get("last_update") or 0) + 1
    data = tg_call(f"getUpdates?offset={offset}&limit=10&timeout=0", timeout=6)
    if data.get("ok") and data.get("result"):
        for u in data["result"]:
            uid = u.get("update_id", 0)
            if uid > b.get("last_update", 0):
                b["last_update"] = uid
            msg = u.get("message") or {}
            chat = msg.get("chat") or {}
            cid = chat.get("id")
            fname = chat.get("first_name") or "Игрок"
            txt = (msg.get("text") or "").strip()
            if not cid or not txt:
                continue
            save_bind(b)
            if txt.startswith("/start") or txt.startswith("/id"):
                tg_send(
                    cid,
                    f"👋 Привет, <b>{fname}</b>!\n\n"
                    f"🆔 Ваш Chat ID: <code>{cid}</code>\n"
                    f"Вставьте этот Chat ID в меню RHelper (<b>F2 → AFK-фарм → Chat ID</b>), "
                    f"чтобы скрипт отправлял вам PayDay, баланс, статистику и новые предметы инвентаря.\n\n"
                    + (build_msg(st, "stats") if cid == cfg_cid else "Нажимайте кнопки ниже после привязки Chat ID:"),
                )
            elif cid != cfg_cid:
                tg_send(
                    cid,
                    f"🆔 Ваш Chat ID: <code>{cid}</code>\n"
                    f"⚠️ Этот Chat ID пока не вписан в меню вашего RHelper (F2 → AFK-фарм → Chat ID).",
                )
            elif "Баланс" in txt or "/balance" in txt or "/money" in txt:
                tg_send(cid, build_msg(st, "balance"))
            elif "PayDay" in txt or "AFK" in txt or "/afk" in txt:
                tg_send(cid, build_msg(st, "afk"))
            elif "Инвентарь" in txt or "/inv" in txt:
                tg_send(cid, build_msg(st, "inv"))
            else:
                tg_send(cid, build_msg(st, "stats"))


def main():
    b = load_bind()
    while True:
        try:
            step(b)
        except Exception:
            pass
        time.sleep(1.5)


if __name__ == "__main__":
    main()
