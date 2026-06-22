"""
Smart Factory — Full Security System
Android App built with Kivy
Supports USB (Serial) and WiFi (HTTP) connection to Arduino Mega
"""

import threading
import json
import time

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.uix.widget import Widget

# ── Window background ────────────────────────────────────────
Window.clearcolor = get_color_from_hex('#060E1F')

# ── Colors ───────────────────────────────────────────────────
NAVY   = get_color_from_hex('#060E1FFF')
NAVY2  = get_color_from_hex('#0A1628FF')
NAVY3  = get_color_from_hex('#0F1E38FF')
GOLD   = get_color_from_hex('#C9A84CFF')
CYAN   = get_color_from_hex('#00C8FFFF')
GREEN  = get_color_from_hex('#00E88FFF')
RED    = get_color_from_hex('#FF4444FF')
WARN   = get_color_from_hex('#FFB020FF')
MUTED  = get_color_from_hex('#7A8BAAFF')
WHITE  = get_color_from_hex('#CDD6F4FF')
DARK   = get_color_from_hex('#080E1EFF')

# ════════════════════════════════════════════════════════════
# GLOBAL STATE
# ════════════════════════════════════════════════════════════
state = {
    "temp": 0.0,
    "hum":  0.0,
    "gas":  0,
    "smoke": 0,
    "rain": 999,
    "dist": 999,
    "workers": 0,
    "door": False,
    "windows": False,
    "emergency": False,
    "fan": False,
    "pump": False,
    "mode": None,       # "usb" or "wifi"
    "ser":  None,       # serial.Serial object
    "wifi_url": "",     # http://ip
    "connected": False,
    "last_update": "--:--",
}

# ════════════════════════════════════════════════════════════
# DATA LAYER
# ════════════════════════════════════════════════════════════
def send_cmd(cmd):
    def _send():
        try:
            if state["mode"] == "usb" and state["ser"]:
                state["ser"].write((cmd + "\n").encode())
            elif state["mode"] == "wifi" and state["wifi_url"]:
                if HAS_REQUESTS:
                    requests.get(
                        f'{state["wifi_url"]}/cmd?c={cmd}',
                        timeout=3
                    )
        except Exception as e:
            print(f"[CMD ERROR] {e}")
    threading.Thread(target=_send, daemon=True).start()


def fetch_data():
    try:
        if state["mode"] == "usb" and state["ser"]:
            if state["ser"].in_waiting > 0:
                line = state["ser"].readline().decode("utf-8", errors="ignore").strip()
                if line.startswith("{"):
                    _parse_json(line)

        elif state["mode"] == "wifi" and state["wifi_url"] and HAS_REQUESTS:
            r = requests.get(
                f'{state["wifi_url"]}/api',
                timeout=3
            )
            if r.status_code == 200:
                _parse_json(r.text)

    except Exception as e:
        print(f"[FETCH ERROR] {e}")


def _parse_json(raw):
    try:
        d = json.loads(raw)
        state["temp"]      = float(d.get("t",  state["temp"]))
        state["hum"]       = float(d.get("h",  state["hum"]))
        state["gas"]       = int(d.get("g",    state["gas"]))
        state["smoke"]     = int(d.get("s",    state["smoke"]))
        state["rain"]      = int(d.get("r",    state["rain"]))
        state["dist"]      = int(d.get("d",    state["dist"]))
        state["workers"]   = int(d.get("w",    state["workers"]))
        state["door"]      = d.get("do", 0) == 1
        state["windows"]   = d.get("wi", 0) == 1
        state["emergency"] = d.get("e",  0) == 1
        t = time.localtime()
        state["last_update"] = f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}"
    except Exception as e:
        print(f"[PARSE ERROR] {e}")


# ════════════════════════════════════════════════════════════
# UI HELPERS
# ════════════════════════════════════════════════════════════
def make_card(orient='vertical', pad=12, space=8):
    box = BoxLayout(orientation=orient, padding=dp(pad), spacing=dp(space))
    with box.canvas.before:
        Color(rgba=NAVY3)
        box._bg = RoundedRectangle(
            pos=box.pos, size=box.size, radius=[dp(10)]
        )
    def _upd(inst, val):
        inst._bg.pos  = inst.pos
        inst._bg.size = inst.size
    box.bind(pos=_upd, size=_upd)
    return box


def lbl(text, size=14, color=WHITE, bold=False, halign='right'):
    l = Label(
        text=text,
        font_size=sp(size),
        color=color,
        bold=bold,
        halign=halign,
        valign='middle',
    )
    l.bind(size=lambda i, v: setattr(i, 'text_size', v))
    return l


def sep():
    w = Widget(size_hint_y=None, height=dp(1))
    with w.canvas:
        Color(rgba=get_color_from_hex('#1E2E4888'))
        Rectangle(pos=w.pos, size=w.size)
    w.bind(pos=lambda i,v: i.canvas.clear() or
           [Color(rgba=get_color_from_hex('#1E2E4888')),
            Rectangle(pos=i.pos, size=i.size)],
           size=lambda i,v: None)
    return w


def nav_btn(text, target, manager, color=GOLD):
    b = Button(
        text=text,
        font_size=sp(13),
        size_hint=(None, None),
        size=(dp(80), dp(40)),
        background_color=NAVY2,
        background_normal='',
        color=color,
    )
    b.bind(on_release=lambda x: setattr(manager, 'current', target))
    return b


def action_btn(text, cmd=None, bg=NAVY3, fg=CYAN, callback=None):
    b = Button(
        text=text,
        font_size=sp(14),
        bold=True,
        background_color=bg,
        background_normal='',
        color=fg,
        size_hint_y=None,
        height=dp(50),
    )
    if cmd:
        b.bind(on_release=lambda x: send_cmd(cmd))
    if callback:
        b.bind(on_release=callback)
    return b


def show_popup(title, msg, color=CYAN):
    content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
    content.add_widget(lbl(msg, 14, WHITE, halign='center'))
    ok = Button(
        text="حسناً",
        size_hint_y=None, height=dp(44),
        background_color=color,
        background_normal='',
        color=NAVY if color == GOLD else WHITE,
        font_size=sp(14), bold=True,
    )
    content.add_widget(ok)
    popup = Popup(
        title=title,
        content=content,
        size_hint=(0.88, None),
        height=dp(200),
        background='',
        separator_color=color,
        title_color=color,
    )
    ok.bind(on_release=popup.dismiss)
    popup.open()


# ════════════════════════════════════════════════════════════
# SCREEN: WELCOME
# ════════════════════════════════════════════════════════════
class WelcomeScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(rgba=NAVY)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda i,v: setattr(i._bg,'pos',v),
                  size=lambda i,v: setattr(i._bg,'size',v))

        root = BoxLayout(
            orientation='vertical',
            padding=dp(40),
            spacing=dp(18),
        )

        root.add_widget(Widget())  # spacer

        root.add_widget(lbl("🏭", 64, GOLD, halign='center'))
        root.add_widget(lbl("Smart Factory", 38, GOLD, bold=True, halign='center'))
        root.add_widget(lbl("Full Security System", 18, CYAN, halign='center'))

        root.add_widget(sep())

        root.add_widget(lbl(
            "نظام الأمان المتكامل للمصانع\nArdino Mega 2560 + ESP8266",
            13, MUTED, halign='center'
        ))

        root.add_widget(Widget(size_hint_y=None, height=dp(20)))

        start = Button(
            text="ابدأ معنا  ←",
            font_size=sp(18),
            bold=True,
            size_hint=(None, None),
            size=(dp(200), dp(54)),
            pos_hint={'center_x': .5},
            background_color=GOLD,
            background_normal='',
            color=NAVY,
        )
        start.bind(on_release=lambda x: setattr(
            self.manager, 'current', 'home'
        ))
        root.add_widget(start)

        root.add_widget(Widget())  # spacer
        self.add_widget(root)


# ════════════════════════════════════════════════════════════
# SCREEN: HOME
# ════════════════════════════════════════════════════════════
class HomeScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(14))

        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(50))
        with hdr.canvas.before:
            Color(rgba=NAVY2)
            hdr._bg = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda i,v: setattr(i._bg,'pos',v),
                 size=lambda i,v: setattr(i._bg,'size',v))
        hdr.add_widget(lbl("🏠  Smart Factory", 18, GOLD, bold=True))
        root.add_widget(hdr)

        root.add_widget(lbl(
            "نظام أمان صناعي متكامل — 17 عنصراً إلكترونياً",
            12, MUTED
        ))

        # Navigation cards
        items = [
            ("📊", "لوحة التحكم الحية",    "راقب وتحكّم في الزمن الفعلي",     'control', '#1A4A2A'),
            ("⚙️",  "مكونات النظام",        "17 عنصراً بالمواصفات الكاملة",     'components', '#0D2A4A'),
            ("🔌", "جدول التوصيلات",        "جميع التوصيلات بالألوان",           'wiring', '#2A1A4A'),
            ("ℹ️",  "عن المشروع",           "فكرة المشروع والأهداف",             'about', '#1A2A3A'),
        ]
        for icon, title, desc, target, col in items:
            card = make_card('horizontal', pad=16, space=14)
            card.size_hint_y = None
            card.height = dp(72)
            with card.canvas.before:
                Color(rgba=get_color_from_hex(col + 'EE'))
                card._bg2 = RoundedRectangle(
                    pos=card.pos, size=card.size, radius=[dp(10)]
                )
            card.bind(
                pos=lambda i,v: setattr(i._bg2,'pos',v),
                size=lambda i,v: setattr(i._bg2,'size',v)
            )
            card.add_widget(lbl(icon, 28, WHITE, halign='center'))
            info = BoxLayout(orientation='vertical')
            info.add_widget(lbl(title, 15, WHITE, bold=True))
            info.add_widget(lbl(desc, 11, MUTED))
            card.add_widget(info)
            arrow = lbl("›", 24, GOLD, halign='center')
            arrow.size_hint_x = None
            arrow.width = dp(30)
            card.add_widget(arrow)
            tgt = target
            card.bind(on_touch_down=lambda inst, touch, t=tgt:
                setattr(self.manager, 'current', t)
                if inst.collide_point(*touch.pos) else None
            )
            root.add_widget(card)

        root.add_widget(Widget())
        self.add_widget(root)


# ════════════════════════════════════════════════════════════
# SCREEN: COMPONENTS
# ════════════════════════════════════════════════════════════
class ComponentsScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._detail_lbl = None
        root = BoxLayout(orientation='vertical')

        # Header
        hdr = BoxLayout(
            size_hint_y=None, height=dp(52),
            padding=[dp(10), dp(6)], spacing=dp(8)
        )
        with hdr.canvas.before:
            Color(rgba=NAVY2)
            hdr._bg = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda i,v: setattr(i._bg,'pos',v),
                 size=lambda i,v: setattr(i._bg,'size',v))
        hdr.add_widget(nav_btn("← رجوع", 'home', self))
        hdr.add_widget(lbl("⚙️  مكونات النظام", 16, GOLD, bold=True))
        root.add_widget(hdr)

        scroll = ScrollView()
        grid = GridLayout(
            cols=1, spacing=dp(6), padding=dp(10),
            size_hint_y=None
        )
        grid.bind(minimum_height=grid.setter('height'))

        comps = [
            ("🧠","Arduino Mega 2560",  "المتحكم الرئيسي",  "جميع الأطراف",    "ATmega2560 — 16MHz — 54 منفذ رقمي — Flash 256KB — SRAM 8KB"),
            ("📶","ESP8266 WiFi",        "جسر الإنترنت",      "D18/D19 + 3.3V",  "Tensilica L106 32-bit — 80MHz — WiFi 802.11 b/g/n — HTTP Server"),
            ("🌡️","DHT11",               "حرارة + رطوبة",     "D23 + 10kΩ",       "0~50°C ± 2°C  |  20~90% RH ± 5%  |  يحتاج مقاومة Pull-up"),
            ("💨","MQ-2 Gas",            "كشف الغاز",          "A0",               "يكشف LPG,بروبان,ميثان,CO — دقيقتان للإحماء — عتبة: 400"),
            ("🔥","Flame Sensor",        "كشف اللهب",          "D22 — ⚠️3.3V",    "IR 760-1100nm — DO=LOW عند النار — زاوية 60° — مدى 100cm"),
            ("🌫️","Smoke Sensor",        "كشف الدخان",         "A2 مُصحَّح",        "⚠️ A2 وليس D21 (كان يتعارض مع SCL للـ LCD) — عتبة: 500"),
            ("🚶","PIR Motion",          "كشف الحركة",         "D24",              "Passive Infrared — مدى 5-7م — 110° — يعمل في الطوارئ فقط"),
            ("📡","HC-SR04",             "التراسونيك",          "D25/D26",          "40KHz — 2~400cm — ±3mm — distance=duration×0.034÷2"),
            ("🌧️","Rain Sensor",         "حساس المطر",         "A1",               "يغلق النوافذ عند القيمة < 300 — يحمي المعدات من الماء"),
            ("📱","RFID ×2",             "دخول + خروج",        "D53/D49 — ⚠️3.3V","13.56MHz — SPI مشترك — UID 4 bytes — RFID-1 دخول RFID-2 خروج"),
            ("⚙️","Servo ×5",            "باب + 4 شبابيك",    "D10,D6,D7,D8,D9", "SG90 PWM — 0°=مغلق 90°=مفتوح — ⚠️ PSU خارجي 5V/2A"),
            ("🖥️","LCD I2C 16×2",        "شاشة العرض",         "D20/D21",          "PCF8574 — 4 أسلاك فقط — اضبط التباين بالبوتنيومتر"),
            ("🔌","Relay 4CH",           "مروحة + مضخة",      "D30/D31",          "LOW=تشغيل HIGH=إيقاف — IN1:مروحة IN2:مضخة — 250V/10A"),
            ("🔔","Buzzer Active",       "إنذار صوتي",         "D33 + 100Ω",       "2.3kHz — HIGH=تشغيل — طوارئ مستمر — رفض بطاقة نبضتان"),
            ("💡","LED Red",             "إنذار بصري",         "D32 + 220Ω",       "⚠️ 220Ω إلزامي — (5-2)÷220=13.6mA — HIGH=إضاءة"),
        ]

        self._detail_lbl = lbl(
            "اضغط على أي عنصر لعرض التفاصيل الكاملة",
            12, MUTED
        )
        det_card = make_card(pad=12)
        det_card.size_hint_y = None
        det_card.height = dp(60)
        det_card.add_widget(self._detail_lbl)

        for icon, name, role, pin, detail in comps:
            row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None, height=dp(64),
                spacing=dp(10), padding=[dp(12), dp(6)]
            )
            with row.canvas.before:
                Color(rgba=NAVY3)
                row._bg = RoundedRectangle(
                    pos=row.pos, size=row.size, radius=[dp(8)]
                )
            row.bind(
                pos=lambda i,v: setattr(i._bg,'pos',v),
                size=lambda i,v: setattr(i._bg,'size',v)
            )
            row.add_widget(lbl(icon, 26, WHITE, halign='center'))
            info = BoxLayout(orientation='vertical')
            info.add_widget(lbl(name, 14, WHITE, bold=True))
            info.add_widget(lbl(role, 11, MUTED))
            row.add_widget(info)
            pin_w = lbl(pin, 11, CYAN, halign='center')
            pin_w.size_hint_x = None
            pin_w.width = dp(90)
            row.add_widget(pin_w)
            det_txt = f"{name} | {detail}"
            row.bind(on_touch_down=lambda inst, touch, t=det_txt:
                self._show_det(t) if inst.collide_point(*touch.pos) else None
            )
            grid.add_widget(row)

        grid.add_widget(det_card)
        scroll.add_widget(grid)
        root.add_widget(scroll)
        self.add_widget(root)

    def _show_det(self, txt):
        if self._detail_lbl:
            self._detail_lbl.text  = txt
            self._detail_lbl.color = CYAN


# ════════════════════════════════════════════════════════════
# SCREEN: WIRING
# ════════════════════════════════════════════════════════════
class WiringScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation='vertical')

        # Header
        hdr = BoxLayout(
            size_hint_y=None, height=dp(52),
            padding=[dp(10), dp(6)], spacing=dp(8)
        )
        with hdr.canvas.before:
            Color(rgba=NAVY2)
            hdr._bg = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda i,v: setattr(i._bg,'pos',v),
                 size=lambda i,v: setattr(i._bg,'size',v))
        hdr.add_widget(nav_btn("← رجوع", 'home', self))
        hdr.add_widget(lbl("🔌  جدول التوصيلات الكامل", 15, GOLD, bold=True))
        root.add_widget(hdr)

        # Warning
        warn_box = BoxLayout(
            size_hint_y=None, height=dp(44), padding=[dp(12), dp(6)]
        )
        with warn_box.canvas.before:
            Color(rgba=get_color_from_hex('#3A1A0AFF'))
            warn_box._bg = Rectangle(pos=warn_box.pos, size=warn_box.size)
        warn_box.bind(
            pos=lambda i,v: setattr(i._bg,'pos',v),
            size=lambda i,v: setattr(i._bg,'size',v)
        )
        warn_box.add_widget(lbl(
            "⚠️  RFID + ESP + Flame → 3.3V فقط  |  Servo → PSU خارجي  |  GND مشترك",
            11, WARN
        ))
        root.add_widget(warn_box)

        scroll = ScrollView()
        grid = GridLayout(
            cols=4, spacing=dp(2), padding=[dp(4), dp(4)],
            size_hint_y=None
        )
        grid.bind(minimum_height=grid.setter('height'))

        # Header row
        for h_txt in ["العنصر", "المنفذ", "اللون", "ملاحظة"]:
            lbl_h = Label(
                text=h_txt, font_size=sp(12), bold=True,
                color=GOLD, size_hint_y=None, height=dp(34)
            )
            with lbl_h.canvas.before:
                Color(rgba=NAVY)
                lbl_h._bg = Rectangle(pos=lbl_h.pos, size=lbl_h.size)
            lbl_h.bind(
                pos=lambda i,v: setattr(i._bg,'pos',v),
                size=lambda i,v: setattr(i._bg,'size',v)
            )
            grid.add_widget(lbl_h)

        # Wiring data: (component, pin, wire_color, note)
        rows = [
            # DHT11
            ("DHT11",           "D23",   "أصفر",    "5V + 10kΩ"),
            # MQ2
            ("MQ-2 Gas",        "A0",    "أصفر",    "5V — دقيقتان"),
            # Flame
            ("Flame ⚠️",        "D22",   "برتقالي", "3.3V فقط!"),
            # Smoke
            ("Smoke",           "A2",    "أصفر",    "وليس D21!"),
            # PIR
            ("PIR",             "D24",   "أخضر",    "5V"),
            # Ultrasonic
            ("TRIG",            "D25",   "أصفر",    "5V"),
            ("ECHO",            "D26",   "برتقالي", "5V"),
            # Rain
            ("Rain",            "A1",    "أزرق",    "5V"),
            # LCD
            ("LCD SDA",         "D20",   "برتقالي", "5V"),
            ("LCD SCL",         "D21",   "أصفر",    "5V"),
            # RFID
            ("RFID-1 SS ⚠️",   "D53",   "بنفسجي",  "3.3V!"),
            ("RFID-2 SS ⚠️",   "D49",   "بنفسجي",  "3.3V!"),
            ("RFID MOSI",       "D51",   "بنفسجي",  "SPI مشترك"),
            ("RFID MISO",       "D50",   "بنفسجي",  "SPI مشترك"),
            ("RFID SCK",        "D52",   "بنفسجي",  "SPI مشترك"),
            ("RFID RST",        "D5",    "برتقالي", "مشترك"),
            # Servo
            ("Servo باب",       "D10",   "أصفر",    "PSU خارجي!"),
            ("Servo ش1",        "D6",    "أصفر",    "PSU خارجي!"),
            ("Servo ش2",        "D7",    "أصفر",    "PSU خارجي!"),
            ("Servo ش3",        "D8",    "أصفر",    "PSU خارجي!"),
            ("Servo ش4",        "D9",    "أصفر",    "PSU خارجي!"),
            # Relay
            ("Relay Fan",       "D30",   "برتقالي", "LOW=تشغيل"),
            ("Relay Pump",      "D31",   "برتقالي", "LOW=تشغيل"),
            # Output
            ("Buzzer",          "D33",   "أصفر",    "100Ω"),
            ("LED Red",         "D32",   "أحمر",    "220Ω!"),
            # ESP
            ("ESP TX",          "D19",   "بنفسجي",  "مباشر"),
            ("ESP RX ⚠️",       "D18",   "بنفسجي",  "مقسم 1k+2kΩ"),
        ]

        for i, (comp, pin, col, note) in enumerate(rows):
            bg = NAVY3 if i % 2 == 0 else NAVY2
            warn = "⚠️" in comp or "!" in note

            for txt, fc in [
                (comp,  RED   if warn else WHITE),
                (pin,   CYAN),
                (col,   MUTED),
                (note,  RED   if warn else MUTED),
            ]:
                cell = Label(
                    text=txt,
                    font_size=sp(11),
                    color=fc,
                    size_hint_y=None,
                    height=dp(34),
                    halign='center',
                    valign='middle',
                )
                cell.bind(size=lambda i, v: setattr(i, 'text_size', v))
                with cell.canvas.before:
                    Color(rgba=bg)
                    cell._bg = Rectangle(pos=cell.pos, size=cell.size)
                cell.bind(
                    pos=lambda i, v: setattr(i._bg, 'pos', v),
                    size=lambda i, v: setattr(i._bg, 'size', v)
                )
                grid.add_widget(cell)

        scroll.add_widget(grid)
        root.add_widget(scroll)
        self.add_widget(root)


# ════════════════════════════════════════════════════════════
# SCREEN: CONTROL (Connection)
# ════════════════════════════════════════════════════════════
class ControlScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))

        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        with hdr.canvas.before:
            Color(rgba=NAVY2)
            hdr._bg = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda i,v: setattr(i._bg,'pos',v),
                 size=lambda i,v: setattr(i._bg,'size',v))
        hdr.add_widget(nav_btn("← رجوع", 'home', self))
        hdr.add_widget(lbl("🎮  طريقة الاتصال", 16, GOLD, bold=True))
        root.add_widget(hdr)

        # Mode selector
        mode_row = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(10))
        self._usb_btn  = Button(
            text="🔌  USB",
            font_size=sp(15), bold=True,
            background_color=NAVY3, background_normal='',
            color=CYAN,
        )
        self._wifi_btn = Button(
            text="📶  WiFi",
            font_size=sp(15), bold=True,
            background_color=NAVY3, background_normal='',
            color=CYAN,
        )
        self._usb_btn.bind( on_release=lambda x: self._show('usb'))
        self._wifi_btn.bind(on_release=lambda x: self._show('wifi'))
        mode_row.add_widget(self._usb_btn)
        mode_row.add_widget(self._wifi_btn)
        root.add_widget(mode_row)

        # ── USB form ──────────────────────────────────────────
        self.usb_box = BoxLayout(
            orientation='vertical', spacing=dp(10),
            size_hint_y=None, height=0, opacity=0
        )
        self.usb_box.add_widget(lbl("المنفذ التسلسلي:", 13, MUTED))
        self.port_spin = Spinner(
            text='اختر COM Port',
            values=self._get_ports(),
            size_hint_y=None, height=dp(46),
            font_size=sp(14),
            background_color=NAVY3, background_normal='',
            color=WHITE,
        )
        self.usb_box.add_widget(self.port_spin)
        self.usb_box.add_widget(lbl(
            "وصّل كابل OTG من الهاتف للأردوينو",
            11, MUTED
        ))
        btn_usb = Button(
            text="اتصال عبر USB",
            font_size=sp(15), bold=True,
            size_hint_y=None, height=dp(50),
            background_color=CYAN, background_normal='', color=NAVY,
        )
        btn_usb.bind(on_release=self._connect_usb)
        self.usb_box.add_widget(btn_usb)
        root.add_widget(self.usb_box)

        # ── WiFi form ─────────────────────────────────────────
        self.wifi_box = BoxLayout(
            orientation='vertical', spacing=dp(10),
            size_hint_y=None, height=0, opacity=0
        )
        self.wifi_box.add_widget(lbl("عنوان IP لوحدة ESP8266:", 13, MUTED))
        self.ip_inp = TextInput(
            hint_text='192.168.1.100',
            multiline=False,
            size_hint_y=None, height=dp(46),
            font_size=sp(16),
            foreground_color=WHITE,
            background_color=NAVY3,
            hint_text_color=MUTED,
            cursor_color=CYAN,
            padding=[dp(12), dp(12)],
        )
        self.wifi_box.add_widget(self.ip_inp)
        self.wifi_box.add_widget(lbl(
            "تأكد أن هاتفك متصل بنفس شبكة الـ ESP8266",
            11, MUTED
        ))
        btn_wifi = Button(
            text="اتصال عبر WiFi",
            font_size=sp(15), bold=True,
            size_hint_y=None, height=dp(50),
            background_color=get_color_from_hex('#0088ccFF'),
            background_normal='', color=WHITE,
        )
        btn_wifi.bind(on_release=self._connect_wifi)
        self.wifi_box.add_widget(btn_wifi)
        root.add_widget(self.wifi_box)

        # Status
        self.status = lbl("اختر طريقة الاتصال أعلاه", 13, MUTED, halign='center')
        root.add_widget(self.status)

        # AP Info
        ap_card = make_card(pad=12)
        ap_card.size_hint_y = None
        ap_card.height = dp(90)
        ap_card.add_widget(lbl("💡 وضع AP الاحتياطي", 13, GOLD, bold=True))
        ap_card.add_widget(lbl(
            "SSID: SmartFactory  |  كلمة المرور: 12345678\n"
            "IP: 192.168.4.1  (عند فشل الاتصال بالراوتر)",
            11, MUTED
        ))
        root.add_widget(ap_card)

        root.add_widget(Widget())
        self.add_widget(root)

    def _get_ports(self):
        if HAS_SERIAL:
            try:
                ports = [p.device for p in serial.tools.list_ports.comports()]
                return ports if ports else ['COM3', 'COM4', '/dev/ttyUSB0']
            except Exception:
                pass
        return ['COM3', 'COM4', 'COM5', '/dev/ttyUSB0', '/dev/ttyACM0']

    def _show(self, mode):
        if mode == 'usb':
            self.usb_box.height  = dp(190)
            self.usb_box.opacity = 1
            self.wifi_box.height  = 0
            self.wifi_box.opacity = 0
            self._usb_btn.background_color  = CYAN
            self._usb_btn.color             = NAVY
            self._wifi_btn.background_color = NAVY3
            self._wifi_btn.color            = CYAN
        else:
            self.wifi_box.height  = dp(190)
            self.wifi_box.opacity = 1
            self.usb_box.height   = 0
            self.usb_box.opacity  = 0
            self._wifi_btn.background_color = get_color_from_hex('#0088ccFF')
            self._wifi_btn.color            = WHITE
            self._usb_btn.background_color  = NAVY3
            self._usb_btn.color             = CYAN

    def _connect_usb(self, *a):
        port = self.port_spin.text
        if 'اختر' in port:
            self.status.text  = "⚠️ اختر منفذ COM أولاً"
            self.status.color = WARN
            return
        if not HAS_SERIAL:
            self.status.text  = "❌ مكتبة pyserial غير متاحة"
            self.status.color = RED
            return
        try:
            s = serial.Serial(port, 9600, timeout=1)
            state["ser"]       = s
            state["mode"]      = "usb"
            state["connected"] = True
            self.status.text   = f"✅ متصل عبر {port}"
            self.status.color  = GREEN
            Clock.schedule_once(lambda dt: setattr(
                self.manager, 'current', 'dashboard'
            ), 0.8)
        except Exception as e:
            self.status.text  = f"❌ فشل الاتصال: {e}"
            self.status.color = RED

    def _connect_wifi(self, *a):
        ip = self.ip_inp.text.strip()
        if not ip:
            self.status.text  = "⚠️ أدخل عنوان IP"
            self.status.color = WARN
            return
        # Basic IP validation
        parts = ip.split('.')
        if len(parts) != 4:
            self.status.text  = "❌ عنوان IP غير صحيح"
            self.status.color = RED
            return
        state["wifi_url"]  = f"http://{ip}"
        state["mode"]      = "wifi"
        state["connected"] = True
        self.status.text   = f"✅ تم الضبط — {ip}"
        self.status.color  = GREEN
        Clock.schedule_once(lambda dt: setattr(
            self.manager, 'current', 'dashboard'
        ), 0.8)


# ════════════════════════════════════════════════════════════
# SCREEN: DASHBOARD
# ════════════════════════════════════════════════════════════
class DashboardScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._vals   = {}
        self._event  = None
        self._door   = False
        self._win    = False
        self._fan    = False
        self._pump   = False

        root = BoxLayout(orientation='vertical')

        # ── Top bar ───────────────────────────────────────────
        hdr = BoxLayout(
            size_hint_y=None, height=dp(52),
            padding=[dp(10), dp(6)], spacing=dp(8)
        )
        with hdr.canvas.before:
            Color(rgba=NAVY2)
            hdr._bg = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda i,v: setattr(i._bg,'pos',v),
                 size=lambda i,v: setattr(i._bg,'size',v))
        hdr.add_widget(nav_btn("← رجوع", 'home', self))
        hdr.add_widget(lbl("📊  لوحة التحكم", 16, GOLD, bold=True))
        self.update_lbl = lbl("--:--", 11, MUTED, halign='left')
        hdr.add_widget(self.update_lbl)
        root.add_widget(hdr)

        # ── Emergency banner ──────────────────────────────────
        self.emrg_box = BoxLayout(size_hint_y=None, height=dp(40), padding=[dp(12),dp(6)])
        with self.emrg_box.canvas.before:
            Color(rgba=get_color_from_hex('#0A2A12FF'))
            self.emrg_box._bg = Rectangle(
                pos=self.emrg_box.pos, size=self.emrg_box.size
            )
        self.emrg_box.bind(
            pos=lambda i,v: setattr(i._bg,'pos',v),
            size=lambda i,v: setattr(i._bg,'size',v)
        )
        self.emrg_lbl = lbl("✅  وضع طبيعي — النظام يعمل بشكل سليم", 13, GREEN, bold=True, halign='center')
        self.emrg_box.add_widget(self.emrg_lbl)
        root.add_widget(self.emrg_box)

        # ── Scrollable content ────────────────────────────────
        scroll = ScrollView()
        content = BoxLayout(
            orientation='vertical', padding=dp(10),
            spacing=dp(10), size_hint_y=None
        )
        content.bind(minimum_height=content.setter('height'))

        # Stats 2×3 grid
        stats_grid = GridLayout(
            cols=2, spacing=dp(8),
            size_hint_y=None, height=dp(296)
        )
        stat_defs = [
            ("العمال داخل", "workers", GOLD,   "مسجّل دخول"),
            ("الحرارة",     "temp",    CYAN,   "حد: 35°C"),
            ("الرطوبة",     "hum",     WHITE,  "حد: 80%"),
            ("الغاز",       "gas",     GREEN,  "حد: 400"),
            ("الدخان",      "smoke",   GREEN,  "حد: 500"),
            ("المسافة",     "dist",    CYAN,   "تراسونيك"),
        ]
        for title, key, col, sub in stat_defs:
            card = make_card(pad=12, space=4)
            card.add_widget(lbl(title, 11, MUTED))
            v = lbl("--", 28, col, bold=True)
            self._vals[key] = v
            card.add_widget(v)
            card.add_widget(lbl(sub, 10, MUTED))
            stats_grid.add_widget(card)
        content.add_widget(stats_grid)

        # Extra stats row
        extra = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(80))
        rain_card = make_card(pad=12, space=4)
        rain_card.add_widget(lbl("المطر", 11, MUTED))
        self._vals["rain"] = lbl("جاف", 18, GREEN, bold=True)
        rain_card.add_widget(self._vals["rain"])
        extra.add_widget(rain_card)
        time_card = make_card(pad=12, space=4)
        time_card.add_widget(lbl("آخر تحديث", 11, MUTED))
        self.time_lbl = lbl("--:--", 18, MUTED, bold=True)
        time_card.add_widget(self.time_lbl)
        extra.add_widget(time_card)
        content.add_widget(extra)

        # ── Door & Windows ────────────────────────────────────
        door_card = make_card(pad=12, space=6)
        door_card.size_hint_y = None
        door_card.height = dp(110)
        door_card.add_widget(lbl("🚪  الباب والنوافذ", 13, GOLD, bold=True))
        door_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.door_st = lbl("مغلق", 13, RED)
        door_row.add_widget(self.door_st)
        door_row.add_widget(action_btn(
            "فتح الباب",   "DOOR_OPEN",
            bg=get_color_from_hex('#1A4A2AFF'), fg=GREEN
        ))
        door_row.add_widget(action_btn(
            "إغلاق",       "DOOR_CLOSE",
            bg=get_color_from_hex('#3A1A1AFF'), fg=RED
        ))
        door_card.add_widget(door_row)
        win_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.win_st = lbl("مغلقة", 13, RED)
        win_row.add_widget(self.win_st)
        win_row.add_widget(action_btn(
            "فتح النوافذ", "WIN_OPEN",
            bg=get_color_from_hex('#1A2A4AFF'), fg=CYAN
        ))
        win_row.add_widget(action_btn(
            "إغلاق",       "WIN_CLOSE",
            bg=get_color_from_hex('#2A1A3AFF'), fg=MUTED
        ))
        door_card.add_widget(win_row)
        content.add_widget(door_card)

        # ── Fan & Pump ────────────────────────────────────────
        fp_grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(120))
        # Fan
        fan_card = make_card(pad=12, space=6)
        fan_card.add_widget(lbl("💨  المروحة", 13, GOLD, bold=True))
        self.fan_st = lbl("متوقفة", 13, MUTED)
        fan_card.add_widget(self.fan_st)
        fan_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        fan_row.add_widget(action_btn(
            "تشغيل", "FAN_ON",
            bg=get_color_from_hex('#1A3A1AFF'), fg=GREEN,
            callback=lambda x: self._set_fan(True)
        ))
        fan_row.add_widget(action_btn(
            "إيقاف", "FAN_OFF",
            bg=NAVY2, fg=MUTED,
            callback=lambda x: self._set_fan(False)
        ))
        fan_card.add_widget(fan_row)
        fp_grid.add_widget(fan_card)
        # Pump
        pump_card = make_card(pad=12, space=6)
        pump_card.add_widget(lbl("💧  المضخة", 13, GOLD, bold=True))
        self.pump_st = lbl("متوقفة", 13, MUTED)
        pump_card.add_widget(self.pump_st)
        pump_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        pump_row.add_widget(action_btn(
            "تشغيل", "PUMP_ON",
            bg=get_color_from_hex('#1A2A3AFF'), fg=CYAN,
            callback=lambda x: self._set_pump(True)
        ))
        pump_row.add_widget(action_btn(
            "إيقاف", "PUMP_OFF",
            bg=NAVY2, fg=MUTED,
            callback=lambda x: self._set_pump(False)
        ))
        pump_card.add_widget(pump_row)
        fp_grid.add_widget(pump_card)
        content.add_widget(fp_grid)

        # ── Emergency ─────────────────────────────────────────
        emrg_btn = Button(
            text="🚨  تفعيل وضع الطوارئ  🚨",
            font_size=sp(16), bold=True,
            size_hint_y=None, height=dp(58),
            background_color=RED, background_normal='',
            color=WHITE,
        )
        emrg_btn.bind(on_release=self._emergency)
        content.add_widget(emrg_btn)

        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    # ── State helpers ─────────────────────────────────────────
    def _set_fan(self, on):
        self._fan = on
        self.fan_st.text  = "تعمل ✅" if on else "متوقفة"
        self.fan_st.color = GREEN if on else MUTED

    def _set_pump(self, on):
        self._pump = on
        self.pump_st.text  = "تعمل ✅" if on else "متوقفة"
        self.pump_st.color = CYAN if on else MUTED

    def _emergency(self, *a):
        send_cmd("EMERGENCY")
        show_popup(
            "🚨 طوارئ",
            "تم تفعيل وضع الطوارئ:\n"
            "• فتح الباب والنوافذ\n"
            "• تشغيل المضخة والمروحة\n"
            "• تفعيل الجرس والمصباح",
            RED
        )

    # ── Lifecycle ─────────────────────────────────────────────
    def on_enter(self):
        self._event = Clock.schedule_interval(self._tick, 1.5)

    def on_leave(self):
        if self._event:
            self._event.cancel()
            self._event = None

    def _tick(self, dt):
        threading.Thread(target=fetch_data, daemon=True).start()
        Clock.schedule_once(self._refresh, 0.6)

    def _refresh(self, dt):
        # Temperature
        t = state["temp"]
        self._vals["temp"].text  = f"{t:.1f}°C"
        self._vals["temp"].color = RED if t > 35 else CYAN

        # Humidity
        h = state["hum"]
        self._vals["hum"].text  = f"{h:.0f}%"
        self._vals["hum"].color = WARN if h > 80 else WHITE

        # Gas
        g = state["gas"]
        self._vals["gas"].text  = str(g)
        self._vals["gas"].color = RED if g > 400 else GREEN

        # Smoke
        s = state["smoke"]
        self._vals["smoke"].text  = str(s)
        self._vals["smoke"].color = RED if s > 500 else GREEN

        # Workers
        self._vals["workers"].text = str(state["workers"])

        # Distance
        self._vals["dist"].text = f'{state["dist"]}cm'

        # Rain
        r = state["rain"]
        self._vals["rain"].text  = "مطر 🌧️" if r < 300 else "جاف ☀️"
        self._vals["rain"].color = WARN if r < 300 else GREEN

        # Door
        self.door_st.text  = "مفتوح ✅" if state["door"] else "مغلق 🔒"
        self.door_st.color = GREEN if state["door"] else RED

        # Windows
        self.win_st.text  = "مفتوحة ✅" if state["windows"] else "مغلقة 🔒"
        self.win_st.color = GREEN if state["windows"] else RED

        # Emergency banner
        if state["emergency"]:
            self.emrg_lbl.text  = "🚨  وضع الطوارئ! — EMERGENCY MODE ACTIVE"
            self.emrg_lbl.color = RED
            with self.emrg_box.canvas.before:
                Color(rgba=get_color_from_hex('#3A0A0AFF'))
                Rectangle(pos=self.emrg_box.pos, size=self.emrg_box.size)
        else:
            self.emrg_lbl.text  = "✅  وضع طبيعي — النظام يعمل بشكل سليم"
            self.emrg_lbl.color = GREEN
            with self.emrg_box.canvas.before:
                Color(rgba=get_color_from_hex('#0A2A12FF'))
                Rectangle(pos=self.emrg_box.pos, size=self.emrg_box.size)

        # Time
        self.time_lbl.text = state["last_update"]
        mode = "USB" if state["mode"] == "usb" else "WiFi"
        self.update_lbl.text = f"متصل ({mode})"
        self.update_lbl.color = GREEN


# ════════════════════════════════════════════════════════════
# SCREEN: ABOUT
# ════════════════════════════════════════════════════════════
class AboutScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        scroll = ScrollView()
        box = BoxLayout(
            orientation='vertical', padding=dp(16),
            spacing=dp(12), size_hint_y=None
        )
        box.bind(minimum_height=box.setter('height'))

        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        hdr.add_widget(nav_btn("← رجوع", 'home', self))
        hdr.add_widget(lbl("ℹ️  عن المشروع", 16, GOLD, bold=True))
        box.add_widget(hdr)

        sections = [
            (
                "🎯 الهدف",
                "نظام أمان صناعي متكامل يحمي المصانع الصغيرة والمتوسطة "
                "بتكلفة منخفضة وأداء احترافي. يجمع 17 عنصراً في منظومة "
                "واحدة تعمل 24/7."
            ),
            (
                "🔧 المكونات الرئيسية",
                "• Arduino Mega 2560 — المتحكم المركزي\n"
                "• ESP8266 — WiFi Bridge\n"
                "• 7 حساسات: DHT11, MQ2, Flame, Smoke, PIR, HC-SR04, Rain\n"
                "• 5 سيرفوهات: 1 باب + 4 شبابيك\n"
                "• RFID ×2: دخول وخروج\n"
                "• LCD I2C + Relay 4CH + Buzzer + LED"
            ),
            (
                "📱 طرق الاتصال",
                "• USB (OTG): وصّل كابل OTG من هاتفك للأردوينو\n"
                "• WiFi: أدخل IP وحدة ESP8266\n"
                "• وضع AP: SmartFactory / 12345678 / 192.168.4.1"
            ),
            (
                "⚡ الأداء",
                "• استجابة طوارئ < 200ms\n"
                "• تحديث البيانات كل 1.5 ثانية\n"
                "• يعمل بدون إنترنت عبر USB أو AP"
            ),
            (
                "⚠️ تحذيرات التوصيل",
                "• RFID + ESP + Flame → 3.3V فقط\n"
                "• Servo → PSU خارجي 5V (ليس الأردوينو)\n"
                "• Smoke → A2 وليس D21\n"
                "• ESP RX → مقسم جهد 1kΩ+2kΩ"
            ),
        ]
        for title, body in sections:
            card = make_card(pad=14, space=6)
            card.size_hint_y = None
            card.height = dp(24 + body.count('\n') * 22 + 70)
            card.add_widget(lbl(title, 14, GOLD, bold=True))
            card.add_widget(lbl(body, 12, MUTED))
            box.add_widget(card)

        scroll.add_widget(box)
        self.add_widget(scroll)


# ════════════════════════════════════════════════════════════
# APP
# ════════════════════════════════════════════════════════════
class SmartFactoryApp(App):
    def build(self):
        self.title = "Smart Factory"
        sm = ScreenManager(transition=SlideTransition(duration=0.3))
        sm.add_widget(WelcomeScreen(name='welcome'))
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(ComponentsScreen(name='components'))
        sm.add_widget(WiringScreen(name='wiring'))
        sm.add_widget(ControlScreen(name='control'))
        sm.add_widget(DashboardScreen(name='dashboard'))
        sm.add_widget(AboutScreen(name='about'))
        return sm


if __name__ == '__main__':
    SmartFactoryApp().run()
