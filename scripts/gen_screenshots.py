"""Generate AI-style mockup screenshots for the GitHub README."""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = "screenshots"
os.makedirs(OUT, exist_ok=True)

W, H = 1280, 800
SW = 240  # sidebar width

C = {
    "bg":      "#F1F5F9", "sidebar": "#0F172A", "side2": "#1E293B",
    "white":   "#FFFFFF",  "blue":   "#3B82F6", "blue_d": "#1D4ED8",
    "blue_l":  "#EFF6FF",  "green":  "#10B981", "green_l": "#ECFDF5",
    "purple":  "#8B5CF6",  "purp_l": "#F5F3FF", "orange": "#F59E0B",
    "org_l":   "#FFFBEB",  "red":    "#EF4444", "red_l":  "#FEF2F2",
    "text":    "#0F172A",  "text2":  "#475569", "text3":  "#94A3B8",
    "border":  "#E2E8F0", "hover": "#F8FAFC",
}


def font(size, bold=False):
    candidates = (
        ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/calibrib.ttf",
         "C:/Windows/Fonts/arialbd.ttf"]
        if bold else
        ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/calibri.ttf",
         "C:/Windows/Fonts/arial.ttf"]
    )
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def rr(d, x, y, w, h, r=8, fill=None, outline=None, ow=1):
    d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=fill,
                         outline=outline, width=ow)


def tc(d, text, cx, cy, f, fill):
    bb = d.textbbox((0, 0), text, font=f)
    d.text((cx - (bb[2] - bb[0]) // 2, cy), text, font=f, fill=fill)


def draw_sidebar(d, active=0):
    d.rectangle([0, 0, SW, H], fill=C["sidebar"])
    # logo
    rr(d, 14, 14, SW - 28, 56, 10, C["side2"])
    d.text((28, 24), "BusinessBot", font=font(14, True), fill="#FFFFFF")
    d.text((28, 44), "AI Assistant Platform", font=font(10), fill=C["text3"])
    rr(d, SW - 46, 22, 28, 20, 4, C["blue"])
    tc(d, "v2", SW - 32, 25, font(9, True), "#FFFFFF")

    nav = [("📊", "Overview"), ("📚", "Knowledge"), ("💬", "Conversations"),
           ("📈", "Analytics"), ("⚙️", "Settings"), ("👑", "Super Admin")]
    for i, (ic, lb) in enumerate(nav):
        y = 88 + i * 52
        if i == active:
            rr(d, 10, y, SW - 20, 40, 8, C["blue"])
            d.text((26, y + 10), ic, font=font(14), fill="#FFFFFF")
            d.text((52, y + 13), lb, font=font(13, True), fill="#FFFFFF")
        else:
            d.text((26, y + 10), ic, font=font(14), fill=C["text3"])
            d.text((52, y + 13), lb, font=font(12), fill=C["text3"])

    # user card
    rr(d, 10, H - 70, SW - 20, 52, 8, C["side2"])
    d.ellipse([22, H - 58, 48, H - 34], fill=C["blue"])
    tc(d, "A", 35, H - 54, font(14, True), "#FFFFFF")
    d.text((56, H - 58), "Admin", font=font(12, True), fill="#FFFFFF")
    d.text((56, H - 40), "admin@example.com", font=font(10), fill=C["text3"])


def draw_topbar(d, title, subtitle=""):
    d.rectangle([SW, 0, W, 64], fill=C["white"])
    d.line([SW, 64, W, 64], fill=C["border"], width=1)
    d.text((SW + 24, 14), title, font=font(18, True), fill=C["text"])
    if subtitle:
        d.text((SW + 24, 40), subtitle, font=font(12), fill=C["text2"])
    # notification + avatar
    rr(d, W - 100, 18, 32, 28, 14, C["bg"])
    d.text((W - 90, 22), "🔔", font=font(14), fill=C["text2"])
    d.ellipse([W - 56, 14, W - 12, 50], fill=C["blue"])
    tc(d, "A", W - 34, 22, font(16, True), "#FFFFFF")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Dashboard Overview
# ─────────────────────────────────────────────────────────────────────────────
def make_dashboard():
    img = Image.new("RGB", (W, H), C["bg"])
    d = ImageDraw.Draw(img)
    draw_sidebar(d, 0)
    draw_topbar(d, "Overview", "Welcome back, Admin 👋")

    # Quick action bar
    qy = 82
    for i, (lbl, col) in enumerate([
        ("🤖  Create Chatbot", C["blue"]),
        ("📚  Add Knowledge", C["green"]),
        ("⚙️  Settings", C["purple"]),
    ]):
        bx = SW + 24 + i * 182
        rr(d, bx, qy, 170, 38, 8, col)
        d.text((bx + 14, qy + 11), lbl, font=font(12, True), fill="#FFFFFF")

    # Stat cards
    stats = [
        ("2", "Active Chatbots", C["blue"], C["blue_l"]),
        ("1,247", "Conversations", C["green"], C["green_l"]),
        ("483", "KB Documents", C["purple"], C["purp_l"]),
        ("482K", "Tokens Left", C["orange"], C["org_l"]),
    ]
    for i, (val, lbl, acc, bg) in enumerate(stats):
        cx = SW + 24 + i * 258
        rr(d, cx, 134, 242, 98, 12, bg, C["border"], 1)
        d.text((cx + 18, cx + 134 - cx + 134 - 134 + 16), val,
               font=font(26, True), fill=C["text"])
        # simpler positioning:
        rr(d, cx, 134, 242, 98, 12, bg, C["border"], 1)
        d.text((cx + 18, 152), val, font=font(26, True), fill=C["text"])
        d.text((cx + 18, 186), lbl, font=font(11), fill=C["text2"])
        rr(d, cx + 18, 205, 58, 18, 9, acc)
        tc(d, "↑ 12%", cx + 47, 207, font(9, True), "#FFFFFF")

    # Chatbots table
    ty = 256
    d.text((SW + 24, ty), "Your Chatbots", font=font(14, True), fill=C["text"])
    rr(d, SW + 24, ty + 26, W - SW - 48, 32, 6, C["blue_l"])
    for j, (col_txt, ox) in enumerate([
        ("Name", 16), ("Status", 230), ("KB Docs", 380),
        ("Conversations", 510), ("Actions", 700)
    ]):
        d.text((SW + 24 + ox, ty + 34), col_txt,
               font=font(11, True), fill=C["blue_d"])

    bots = [
        ("Customer Support Bot", "Active",  "312", "847"),
        ("Sales Assistant",      "Active",  "171", "400"),
    ]
    for k, (name, st, docs, convs) in enumerate(bots):
        ry = ty + 62 + k * 54
        rr(d, SW + 24, ry, W - SW - 48, 46, 8, C["white"], C["border"], 1)
        d.ellipse([SW + 40, ry + 11, SW + 62, ry + 33], fill=C["blue_l"])
        d.text((SW + 44, ry + 13), "🤖", font=font(14), fill=C["blue"])
        d.text((SW + 70, ry + 14), name, font=font(13, True), fill=C["text"])
        rr(d, SW + 246, ry + 13, 58, 20, 10, C["green_l"])
        d.text((SW + 254, ry + 16), "● Active", font=font(10), fill=C["green"])
        d.text((SW + 396, ry + 16), docs, font=font(12), fill=C["text"])
        d.text((SW + 526, ry + 16), convs, font=font(12), fill=C["text"])
        rr(d, SW + 712, ry + 12, 68, 24, 6, C["blue"])
        tc(d, "Manage →", SW + 746, ry + 16, font(10, True), "#FFFFFF")

    # Recent conversations
    rc_y = 396
    d.text((SW + 24, rc_y), "Recent Conversations", font=font(14, True), fill=C["text"])
    rows = [
        ("👤 User #1042", "How do I enroll in your AI course?", "2m ago", C["green"]),
        ("👤 User #1041", "What is the price of the certification program?", "8m ago", C["green"]),
        ("👤 User #1040", "Can I speak to a human agent please?", "15m ago", C["orange"]),
        ("👤 User #1039", "What are your office hours?", "1h ago", C["text3"]),
        ("👤 User #1038", "How long does the course take to complete?", "2h ago", C["text3"]),
    ]
    for m, (usr, msg, ago, dot) in enumerate(rows):
        ry2 = rc_y + 28 + m * 56
        if ry2 + 48 > H - 10:
            break
        rr(d, SW + 24, ry2, W - SW - 48, 48, 8, C["white"], C["border"], 1)
        d.text((SW + 38, ry2 + 10), usr, font=font(12, True), fill=C["text"])
        d.text((SW + 38, ry2 + 28), (msg[:58] + "…") if len(msg) > 58 else msg,
               font=font(11), fill=C["text2"])
        d.ellipse([W - 90, ry2 + 20, W - 78, ry2 + 32], fill=dot)
        d.text((W - 72, ry2 + 20), ago, font=font(10), fill=C["text3"])

    img.save(f"{OUT}/01_dashboard_overview.png", "PNG")
    print("✓ 01_dashboard_overview.png")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Knowledge Base Management
# ─────────────────────────────────────────────────────────────────────────────
def make_knowledge():
    img = Image.new("RGB", (W, H), C["bg"])
    d = ImageDraw.Draw(img)
    draw_sidebar(d, 1)
    draw_topbar(d, "Knowledge Base", "Manage Q&A pairs, documents and training data")

    # KB selector tabs
    ty = 80
    for i, (tab, active) in enumerate([
        ("📋 Q&A Pairs", True), ("📄 Documents", False), ("🔗 Sources", False)
    ]):
        bx = SW + 24 + i * 150
        if active:
            rr(d, bx, ty, 140, 36, 8, C["blue"])
            tc(d, tab, bx + 70, ty + 10, font(12, True), "#FFFFFF")
        else:
            rr(d, bx, ty, 140, 36, 8, C["white"], C["border"], 1)
            tc(d, tab, bx + 70, ty + 10, font(12), C["text2"])

    # Action buttons right side
    rr(d, W - 240, ty, 100, 36, 8, C["green"])
    tc(d, "📤 Upload CSV", W - 190, ty + 10, font(11, True), "#FFFFFF")
    rr(d, W - 130, ty, 100, 36, 8, C["blue"])
    tc(d, "+ Add Q&A", W - 80, ty + 10, font(11, True), "#FFFFFF")

    # Stats row
    sy = 134
    for i, (val, lbl, acc, bg) in enumerate([
        ("1,247", "Total Q&A Pairs", C["blue"], C["blue_l"]),
        ("1,198", "Embedded / Indexed", C["green"], C["green_l"]),
        ("49", "Pending Embedding", C["orange"], C["org_l"]),
        ("6", "Categories", C["purple"], C["purp_l"]),
    ]):
        cx = SW + 24 + i * 258
        rr(d, cx, sy, 242, 72, 10, bg, C["border"], 1)
        d.text((cx + 16, sy + 12), val, font=font(22, True), fill=C["text"])
        d.text((cx + 16, sy + 40), lbl, font=font(10), fill=C["text2"])

    # Search bar
    rr(d, SW + 24, 224, W - SW - 170, 40, 8, C["white"], C["border"], 1)
    d.text((SW + 44, 234), "🔍  Search Q&A pairs…", font=font(13), fill=C["text3"])
    rr(d, W - 136, 224, 112, 40, 8, C["white"], C["border"], 1)
    d.text((W - 126, 234), "Category ▾", font=font(12), fill=C["text2"])

    # Table header
    rr(d, SW + 24, 278, W - SW - 48, 34, 6, C["blue_l"])
    for col, ox in [("#", 16), ("Question", 60), ("Category", 490),
                    ("Answer Preview", 620), ("Actions", 870)]:
        d.text((SW + 24 + ox, 286), col, font=font(11, True), fill=C["blue_d"])

    # Q&A rows
    qa_data = [
        ("1", "What services do you offer?", "General",
         "We provide AI-powered business automation solutions…", C["green"]),
        ("2", "How much does the Pro plan cost?", "Pricing",
         "The Professional plan starts at $49/month and includes…", C["green"]),
        ("3", "How do I get started?", "Onboarding",
         "Getting started is easy! Sign up at our website and…", C["green"]),
        ("4", "What languages do you support?", "Technical",
         "Our platform supports 80+ languages including Bengali…", C["green"]),
        ("5", "Can I cancel my subscription?", "Billing",
         "Yes, you can cancel your subscription at any time from…", C["green"]),
        ("6", "What is your refund policy?", "Billing",
         "We offer a 30-day money-back guarantee for all plans…", C["green"]),
        ("7", "How do I contact support?", "Support",
         "You can reach our support team via email, live chat…", C["green"]),
        ("8", "Is there a free trial available?", "Pricing",
         "Yes! We offer a 14-day free trial with full access…", C["orange"]),
    ]
    for k, (num, q, cat, ans, emb) in enumerate(qa_data):
        ry = 316 + k * 52
        if ry + 44 > H - 50:
            break
        bg = C["hover"] if k % 2 == 0 else C["white"]
        rr(d, SW + 24, ry, W - SW - 48, 46, 0, bg, C["border"], 1)
        d.text((SW + 40, ry + 14), num, font=font(11), fill=C["text3"])
        d.text((SW + 84, ry + 14), (q[:44] + "…") if len(q) > 44 else q,
               font=font(12, True), fill=C["text"])
        # category badge
        rr(d, SW + 510, ry + 12, 80, 22, 11, C["blue_l"])
        tc(d, cat, SW + 550, ry + 14, font(10), C["blue_d"])
        d.text((SW + 636, ry + 14),
               (ans[:32] + "…") if len(ans) > 32 else ans,
               font=font(11), fill=C["text2"])
        # embedded badge
        emb_col = C["green"] if emb == C["green"] else C["orange"]
        emb_bg = C["green_l"] if emb == C["green"] else C["org_l"]
        emb_txt = "✓ Indexed" if emb == C["green"] else "⏳ Pending"
        rr(d, SW + 882, ry + 12, 72, 22, 11, emb_bg)
        tc(d, emb_txt, SW + 918, ry + 14, font(10), emb_col)
        # action dots
        d.text((W - 64, ry + 14), "✏  🗑", font=font(13), fill=C["text3"])

    # Pagination
    pg_y = H - 46
    rr(d, SW + 24, pg_y, W - SW - 48, 36, 8, C["white"], C["border"], 1)
    d.text((SW + 40, pg_y + 10), "Showing 1–8 of 1,247 pairs", font=font(11), fill=C["text3"])
    for pi, lbl in enumerate(["‹ Prev", "1", "2", "3", "…", "156", "Next ›"]):
        px = W - 320 + pi * 44
        active_pg = lbl == "1"
        rr(d, px, pg_y + 6, 36, 24, 6,
           C["blue"] if active_pg else C["white"],
           None if active_pg else C["border"], 1)
        tc(d, lbl, px + 18, pg_y + 10,
           font(10, True), "#FFFFFF" if active_pg else C["text2"])

    img.save(f"{OUT}/02_knowledge_base.png", "PNG")
    print("✓ 02_knowledge_base.png")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Chat Widget (user-facing)
# ─────────────────────────────────────────────────────────────────────────────
def make_chat_widget():
    img = Image.new("RGB", (W, H), "#E8F4FD")
    d = ImageDraw.Draw(img)

    # Background "website" simulation
    d.rectangle([0, 0, W, 60], fill="#1E293B")
    for i, nav in enumerate(["Home", "Courses", "About", "Contact"]):
        d.text((120 + i * 100, 22), nav, font=font(13), fill="#94A3B8")
    d.text((28, 18), "YourBusiness.com", font=font(16, True), fill="#FFFFFF")
    rr(d, W - 150, 14, 120, 32, 8, C["blue"])
    tc(d, "Get Started →", W - 90, 20, font(12, True), "#FFFFFF")

    # Page content
    d.rectangle([0, 60, W, H], fill="#F0F9FF")
    d.text((80, 110), "Welcome to Our Platform", font=font(36, True), fill="#0F172A")
    d.text((80, 162), "Intelligent AI assistance available 24/7 for all your questions",
           font=font(16), fill="#475569")
    rr(d, 80, 206, 160, 44, 10, C["blue"])
    tc(d, "Learn More →", 160, 216, font(14, True), "#FFFFFF")

    # Chat window (bottom right)
    cw, ch = 380, 560
    cx = W - cw - 32
    cy = H - ch - 32

    # Shadow
    for s in range(8, 0, -1):
        rr(d, cx - s, cy + s, cw + s * 2, ch + s * 2, 18,
           f"#{'%02x%02x%02x' % (200-s*10, 210-s*10, 220-s*10)}")

    rr(d, cx, cy, cw, ch, 16, C["white"])

    # Chat header
    rr(d, cx, cy, cw, 64, 16, C["blue"])
    d.rectangle([cx, cy + 48, cx + cw, cy + 64], fill=C["blue"])
    d.ellipse([cx + 14, cy + 12, cx + 44, cy + 52], fill="#FFFFFF")
    d.text((cx + 18, cy + 20), "🤖", font=font(20), fill=C["blue"])
    d.text((cx + 54, cy + 14), "AI Assistant", font=font(14, True), fill="#FFFFFF")
    d.text((cx + 54, cy + 34), "● Online · Typically replies instantly",
           font=font(10), fill="#BFDBFE")
    d.text((cx + cw - 36, cy + 20), "✕", font=font(16, True), fill="#FFFFFF")

    # Messages area
    msg_area_y = cy + 64
    d.rectangle([cx, msg_area_y, cx + cw, cy + ch - 60], fill="#F8FAFC")

    messages = [
        ("bot",  "👋 Hello! I'm your AI assistant. How can I help you today?", False),
        ("user", "What courses do you offer?", False),
        ("bot",  "We offer several professional courses:\n\n• AI Engineer Certification\n• Full Stack Development\n• Data Science & ML\n• Digital Marketing\n\nAll courses include live sessions and a certificate upon completion. Which one interests you?", False),
        ("user", "How much does the AI course cost?", False),
        ("bot",  "The Professional AI Engineer course is priced at $299, which includes:\n✓ 12 live sessions\n✓ Hands-on projects\n✓ Certificate\n✓ Lifetime access\n\nWould you like to enroll? 🎓", True),
    ]

    my = msg_area_y + 12
    for role, text, is_last in messages:
        is_bot = role == "bot"
        lines = text.split("\n")
        line_h = 18
        padding = 12
        max_w = int(cw * 0.72)

        # measure total height
        total_h = padding * 2
        for line in lines:
            bb = d.textbbox((0, 0), line if line else " ", font=font(12))
            total_h += max(line_h, bb[3] - bb[1] + 2)

        if is_bot:
            bx = cx + 14
        else:
            bx = cx + cw - max_w - 14

        bg = C["white"] if is_bot else C["blue"]
        txt_col = C["text"] if is_bot else "#FFFFFF"

        rr(d, bx, my, max_w, total_h, 10, bg,
           C["border"] if is_bot else None, 1)

        ty2 = my + padding
        for line in lines:
            d.text((bx + padding, ty2), line if line else "",
                   font=font(12), fill=txt_col)
            bb = d.textbbox((0, 0), line if line else " ", font=font(12))
            ty2 += max(line_h, bb[3] - bb[1] + 2)

        if is_last and is_bot:
            # Suggestion chips
            chips = ["Enroll Now", "More Courses", "Contact Us"]
            chip_y = my + total_h + 6
            chip_x = bx
            for chip in chips:
                rr(d, chip_x, chip_y, 90, 26, 13, C["blue_l"], C["blue"], 1)
                tc(d, chip, chip_x + 45, chip_y + 7, font(10), C["blue_d"])
                chip_x += 98
            my += total_h + 42
        else:
            my += total_h + 8

        if my > cy + ch - 120:
            break

    # Typing indicator
    rr(d, cx + 14, cy + ch - 124, 80, 32, 16, C["white"], C["border"], 1)
    for dot_i in range(3):
        dx = cx + 30 + dot_i * 20
        d.ellipse([dx, cy + ch - 114, dx + 10, cy + ch - 104], fill=C["text3"])

    # Input box
    rr(d, cx, cy + ch - 60, cw, 60, 16, C["white"])
    d.line([cx, cy + ch - 60, cx + cw, cy + ch - 60], fill=C["border"], width=1)
    rr(d, cx + 14, cy + ch - 48, cw - 76, 36, 18, C["bg"], C["border"], 1)
    d.text((cx + 28, cy + ch - 38), "Type a message…", font=font(12), fill=C["text3"])
    rr(d, cx + cw - 54, cy + ch - 48, 40, 36, 18, C["blue"])
    tc(d, "➤", cx + cw - 34, cy + ch - 40, font(14, True), "#FFFFFF")

    # FAB button (partially visible)
    d.ellipse([W - 90, H - 90, W - 20, H - 20], fill=C["blue"])
    tc(d, "💬", W - 55, H - 78, font(28), "#FFFFFF")

    img.save(f"{OUT}/03_chat_widget.png", "PNG")
    print("✓ 03_chat_widget.png")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Settings — Persona & Configuration
# ─────────────────────────────────────────────────────────────────────────────
def make_settings():
    img = Image.new("RGB", (W, H), C["bg"])
    d = ImageDraw.Draw(img)
    draw_sidebar(d, 4)
    draw_topbar(d, "Settings", "Configure your chatbot persona, theme and integrations")

    # Settings tabs
    tabs = ["Persona & Chat", "Theme", "Integrations", "AI Providers", "Billing"]
    tx = SW + 24
    ty = 80
    for i, tab in enumerate(tabs):
        active = i == 0
        rr(d, tx + i * 164, ty, 155, 38, 8,
           C["blue"] if active else C["white"],
           None if active else C["border"], 1)
        tc(d, tab, tx + i * 164 + 77, ty + 11,
           font(12, True if active else False),
           "#FFFFFF" if active else C["text2"])

    # Main form card
    rr(d, SW + 24, 132, W - SW - 200, H - 152, 12, C["white"], C["border"], 1)

    # Form fields
    fy = 156
    fx = SW + 48
    fw = W - SW - 250

    def field(label, value, y, height=40, is_area=False, hint=None, required=False):
        req = " *" if required else ""
        d.text((fx, y - 22), label + req, font=font(12, True), fill=C["text"])
        if hint:
            bb = d.textbbox((0, 0), label + req, font=font(12, True))
            d.text((fx + bb[2] + 8, y - 22), hint, font=font(11), fill=C["text3"])
        rr(d, fx, y, fw, height, 8, C["bg"], C["border"], 1)
        d.text((fx + 14, y + (height // 2) - 9 if not is_area else y + 12),
               value, font=font(12), fill=C["text"])
        if is_area and height > 50:
            # cursor line
            lines = value.split("\n")
            for li, line in enumerate(lines[:5]):
                d.text((fx + 14, y + 12 + li * 20), line, font=font(11), fill=C["text"])

    field("Persona Name", "Aria", fy, required=True)
    field("Default Language", "English (en)", fy + 76)
    field("Personality / Tone",
          "Professional, friendly, helpful and concise", fy + 152)
    field("Greeting Message",
          "Hello! 👋 I'm Aria, your AI assistant. How can I help you today?",
          fy + 228)

    # System Prompt (textarea)
    sp_y = fy + 314
    d.text((fx, sp_y - 22), "System Prompt", font=font(12, True), fill=C["text"])
    rr(d, fx, sp_y - 2, fw, 5, 0, C["blue"])  # accent line
    rr(d, fx, sp_y + 3, fw, 148, 8, C["bg"], C["border"], 1)
    prompt_lines = [
        "You are Aria, a helpful AI assistant for [YourBusiness].",
        "Your role is to answer questions about our products and services,",
        "guide users through onboarding, and provide accurate information.",
        "",
        "Rules:",
        "- Always be friendly and professional",
        "- If unsure, offer to connect the user with a human agent",
        "- Only answer questions related to our business",
    ]
    for li, line in enumerate(prompt_lines):
        d.text((fx + 14, sp_y + 12 + li * 17), line,
               font=font(11), fill=C["text"] if line else C["text3"])

    # Save button
    by = fy + 474
    rr(d, fx, by, 140, 44, 10, C["blue"])
    tc(d, "💾  Save Changes", fx + 70, by + 13, font(13, True), "#FFFFFF")
    rr(d, fx + 156, by, 100, 44, 10, C["white"], C["border"], 1)
    tc(d, "Reset", fx + 206, by + 13, font(13), C["text2"])

    # Right panel — preview card
    px = W - 164
    py = 132
    rr(d, px, py, 140, H - 152, 12, C["white"], C["border"], 1)
    d.text((px + 14, py + 14), "Preview", font=font(12, True), fill=C["text"])
    d.line([px + 14, py + 34, px + 126, py + 34], fill=C["border"], width=1)
    # mini chat preview
    rr(d, px + 10, py + 44, 120, 44, 8, C["blue"])
    d.ellipse([px + 18, py + 52, px + 36, py + 70], fill="#FFFFFF")
    d.text((px + 22, py + 56), "🤖", font=font(10), fill=C["blue"])
    d.text((px + 42, py + 56), "Aria", font=font(11, True), fill="#FFFFFF")
    d.text((px + 42, py + 70), "● Online", font=font(9), fill="#BFDBFE")

    rr(d, px + 10, py + 100, 120, 42, 8, C["white"], C["border"], 1)
    d.text((px + 18, py + 110), "👋 Hello! I'm",
           font=font(9), fill=C["text"])
    d.text((px + 18, py + 124), "Aria. How can I",
           font=font(9), fill=C["text"])
    d.text((px + 18, py + 138), "help you today?",
           font=font(9), fill=C["text"])

    rr(d, px + 10, py + 154, 120, 28, 14, C["blue"])
    tc(d, "Type a message…", px + 70, py + 161, font(9), "#BFDBFE")

    img.save(f"{OUT}/04_settings_persona.png", "PNG")
    print("✓ 04_settings_persona.png")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Super Admin — Tenant Management
# ─────────────────────────────────────────────────────────────────────────────
def make_superadmin():
    img = Image.new("RGB", (W, H), C["bg"])
    d = ImageDraw.Draw(img)
    draw_sidebar(d, 5)
    draw_topbar(d, "Super Admin", "Manage all organizations and platform settings")

    # Warning banner
    rr(d, SW + 24, 80, W - SW - 48, 36, 8, "#FEF9C3", "#EAB308", 1)
    d.text((SW + 40, 89), "⚠️  Super Admin access — changes affect all tenants on the platform",
           font=font(12), fill="#854D0E")

    # Stats
    for i, (val, lbl, acc, bg) in enumerate([
        ("6", "Total Organizations", C["blue"], C["blue_l"]),
        ("5", "Active Tenants", C["green"], C["green_l"]),
        ("1", "Suspended", C["red"], C["red_l"]),
        ("2.4M", "Total Tokens Issued", C["purple"], C["purp_l"]),
    ]):
        cx = SW + 24 + i * 258
        rr(d, cx, 130, 242, 72, 10, bg, C["border"], 1)
        d.text((cx + 16, 146), val, font=font(22, True), fill=C["text"])
        d.text((cx + 16, 174), lbl, font=font(10), fill=C["text2"])

    # Toolbar
    rr(d, SW + 24, 218, 300, 38, 8, C["white"], C["border"], 1)
    d.text((SW + 40, 228), "🔍  Search organizations…", font=font(12), fill=C["text3"])
    rr(d, W - 168, 218, 144, 38, 8, C["blue"])
    tc(d, "+ New Organization", W - 96, 229, font(12, True), "#FFFFFF")

    # Table
    rr(d, SW + 24, 270, W - SW - 48, 32, 6, C["blue_l"])
    for col, ox in [("Organization", 16), ("Status", 250), ("Plan", 360),
                    ("Token Balance", 470), ("Members", 620), ("Actions", 720)]:
        d.text((SW + 24 + ox, 278), col, font=font(11, True), fill=C["blue_d"])

    orgs = [
        ("Acme Corporation",   "Active",    "Professional", "482,000",  "8"),
        ("TechStart Inc.",     "Active",    "Starter",      "124,500",  "3"),
        ("Global Retail Co.",  "Active",    "Enterprise",   "1,240,000","24"),
        ("Innovate Labs",      "Active",    "Professional", "58,200",   "5"),
        ("QuickShop BD",       "Active",    "Starter",      "89,400",   "2"),
        ("OldCo Systems",      "Suspended", "Starter",      "0",        "1"),
    ]
    plan_colors = {
        "Professional": (C["blue_l"],   C["blue_d"]),
        "Starter":      (C["green_l"],  C["green"]),
        "Enterprise":   (C["purp_l"],   C["purple"]),
    }
    for k, (name, status, plan, tokens, members) in enumerate(orgs):
        ry = 306 + k * 54
        bg = C["red_l"] if status == "Suspended" else (C["hover"] if k % 2 else C["white"])
        rr(d, SW + 24, ry, W - SW - 48, 46, 0, bg, C["border"], 1)
        # org icon
        d.ellipse([SW + 38, ry + 11, SW + 60, ry + 33], fill=C["blue_l"])
        tc(d, name[0], SW + 49, ry + 15, font(12, True), C["blue_d"])
        d.text((SW + 68, ry + 14), name, font=font(13, True), fill=C["text"])

        st_col = C["green"] if status == "Active" else C["red"]
        st_bg = C["green_l"] if status == "Active" else C["red_l"]
        rr(d, SW + 262, ry + 12, 72, 22, 11, st_bg)
        tc(d, "● " + status, SW + 298, ry + 14, font(10), st_col)

        pc = plan_colors.get(plan, (C["bg"], C["text2"]))
        rr(d, SW + 372, ry + 12, 76, 22, 11, pc[0])
        tc(d, plan, SW + 410, ry + 14, font(10), pc[1])

        d.text((SW + 482, ry + 14),
               tokens + " tkns" if tokens != "0" else "—",
               font=font(11), fill=C["text"] if tokens != "0" else C["text3"])
        d.text((SW + 632, ry + 14), members, font=font(12), fill=C["text"])

        # Action buttons
        for ai, (albl, acol) in enumerate([
            ("⚙", C["blue"]), ("🔋", C["green"]),
            ("Suspend" if status == "Active" else "Activate",
             C["orange"] if status == "Active" else C["green"])
        ]):
            abx = SW + 732 + ai * 80
            rr(d, abx, ry + 12, 66, 22, 6, acol)
            tc(d, albl, abx + 33, ry + 14, font(10, True), "#FFFFFF")

    img.save(f"{OUT}/05_super_admin.png", "PNG")
    print("✓ 05_super_admin.png")


make_dashboard()
make_knowledge()
make_chat_widget()
make_settings()
make_superadmin()
print("\nAll 5 screenshots generated in screenshots/")
