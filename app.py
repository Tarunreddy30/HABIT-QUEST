"""
HabitQuest - A gamified daily habit tracker
Run with: python app.py
Data is persisted in data.json (no database needed).
"""

import json
import os
import calendar as cal
from datetime import date, timedelta
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")

# ---------------------------------------------------------------------------
# GAME CONFIG  (all the "rules" of the game live here, in plain Python)
# ---------------------------------------------------------------------------

DIFFICULTY_META = {
    "easy":      {"icon": "\U0001F7E2", "label": "Easy",      "xp": (10, 20),  "coins": (5, 10)},
    "medium":    {"icon": "\U0001F7E1", "label": "Medium",    "xp": (30, 50),  "coins": (15, 25)},
    "hard":      {"icon": "\U0001F534", "label": "Hard",      "xp": (60, 100), "coins": (30, 50)},
    "legendary": {"icon": "\U0001F7E3", "label": "Legendary", "xp": (150, 220), "coins": (75, 110)},
}

CATEGORY_META = {
    "study":    {"icon": "\U0001F4DA", "label": "Study"},
    "coding":   {"icon": "\U0001F4BB", "label": "Coding"},
    "fitness":  {"icon": "\U0001F3C3", "label": "Fitness"},
    "learning": {"icon": "\U0001F9E0", "label": "Learning"},
    "morning":  {"icon": "\U0001F305", "label": "Morning"},
    "night":    {"icon": "\U0001F319", "label": "Night"},
    "reading":  {"icon": "\U0001F4D6", "label": "Reading"},
    "health":   {"icon": "\U0001F4A7", "label": "Health"},
    "personal": {"icon": "\u26A1",     "label": "Personal"},
}

# Cumulative XP required to REACH each level. Level 1 starts at 0 XP.
LEVEL_THRESHOLDS = [0]
_diff = 100
for _ in range(2, 101):
    LEVEL_THRESHOLDS.append(LEVEL_THRESHOLDS[-1] + _diff)
    _diff += 50

LEVEL_TITLES = {
    1: "Beginner", 2: "Starter", 3: "Learner", 5: "Disciplined",
    10: "Warrior", 20: "Elite", 30: "Master", 50: "Legend",
}

BADGES = [
    {"id": "fire_starter",       "name": "Fire Starter",       "icon": "\U0001F525", "rarity": "common",
     "desc": "Reach a 7-day streak.",               "type": "streak", "value": 7},
    {"id": "discipline_warrior", "name": "Discipline Warrior", "icon": "\u2694\uFE0F", "rarity": "uncommon",
     "desc": "Reach a 14-day streak.",               "type": "streak", "value": 14},
    {"id": "consistency_king",   "name": "Consistency King",   "icon": "\U0001F451", "rarity": "rare",
     "desc": "Reach a 30-day streak.",               "type": "streak", "value": 30},
    {"id": "habit_master",       "name": "Habit Master",       "icon": "\U0001F409", "rarity": "epic",
     "desc": "Reach a 60-day streak.",               "type": "streak", "value": 60},
    {"id": "legendary_human",    "name": "Legendary Human",    "icon": "\U0001F48E", "rarity": "mythic",
     "desc": "Reach a 100-day streak.",              "type": "streak", "value": 100},
    {"id": "early_bird",         "name": "Early Bird",         "icon": "\U0001F305", "rarity": "common",
     "desc": "Complete a morning quest 7 times.",    "type": "category", "cat": "morning", "value": 7},
    {"id": "knowledge_seeker",   "name": "Knowledge Seeker",   "icon": "\U0001F4DA", "rarity": "uncommon",
     "desc": "Complete study quests 10 times.",      "type": "category", "cat": "study", "value": 10},
    {"id": "code_warrior",       "name": "Code Warrior",       "icon": "\U0001F4BB", "rarity": "rare",
     "desc": "Complete coding quests 20 times.",     "type": "category", "cat": "coding", "value": 20},
    {"id": "fitness_starter",    "name": "Fitness Starter",    "icon": "\U0001F3C3", "rarity": "common",
     "desc": "Complete fitness quests 7 times.",     "type": "category", "cat": "fitness", "value": 7},
    {"id": "warrior",            "name": "Warrior",            "icon": "\u2694\uFE0F", "rarity": "rare",
     "desc": "Complete 100 total missions.",         "type": "missions", "value": 100},
    {"id": "unstoppable",        "name": "Unstoppable",        "icon": "\U0001F680", "rarity": "epic",
     "desc": "Reach a 50-day streak.",               "type": "streak", "value": 50},
    {"id": "perfectionist",      "name": "Perfectionist",      "icon": "\U0001F3AF", "rarity": "rare",
     "desc": "Complete 10 perfect days.",            "type": "perfect_days", "value": 10},
    {"id": "diamond_discipline", "name": "Diamond Discipline", "icon": "\U0001F48E", "rarity": "epic",
     "desc": "Complete 20 perfect days.",            "type": "perfect_days", "value": 20},
    {"id": "legendary",          "name": "Legendary",          "icon": "\U0001F409", "rarity": "mythic",
     "desc": "Reach Level 50.",                      "type": "level", "value": 50},
]

ACHIEVEMENTS = [
    {"id": "m10",  "name": "Getting Started",  "icon": "\U0001F3C6", "desc": "Complete 10 missions.",   "type": "missions", "target": 10},
    {"id": "m50",  "name": "On a Roll",        "icon": "\U0001F3C6", "desc": "Complete 50 missions.",   "type": "missions", "target": 50},
    {"id": "m100", "name": "Century Club",     "icon": "\U0001F3C6", "desc": "Complete 100 missions.",  "type": "missions", "target": 100},
    {"id": "l10",  "name": "Rising Star",      "icon": "\U0001F3C6", "desc": "Reach Level 10.",         "type": "level", "target": 10},
    {"id": "l25",  "name": "Seasoned Player",  "icon": "\U0001F3C6", "desc": "Reach Level 25.",         "type": "level", "target": 25},
    {"id": "s7",   "name": "Week Warrior",     "icon": "\U0001F3C6", "desc": "Maintain a 7-day streak.", "type": "streak", "target": 7},
    {"id": "s30",  "name": "Iron Will",        "icon": "\U0001F3C6", "desc": "Maintain a 30-day streak.", "type": "streak", "target": 30},
    {"id": "p5",   "name": "Flawless Five",    "icon": "\U0001F3C6", "desc": "Complete 5 perfect days.", "type": "perfect_days", "target": 5},
    {"id": "p10",  "name": "Perfect Ten",      "icon": "\U0001F3C6", "desc": "Complete 10 perfect days.", "type": "perfect_days", "target": 10},
]

REWARD_SHOP = [
    {"id": "r1", "name": "30 minutes gaming",     "icon": "\U0001F3AE", "cost": 100},
    {"id": "r2", "name": "Favorite snack",        "icon": "\U0001F355", "cost": 200},
    {"id": "r3", "name": "Watch a movie",         "icon": "\U0001F3AC", "cost": 300},
    {"id": "r4", "name": "Extra relaxation time", "icon": "\U0001F634", "cost": 250},
    {"id": "r5", "name": "Custom reward",         "icon": "\U0001F381", "cost": 500},
]

DAILY_CHALLENGES = [
    {"text": "Complete all your missions before 8 PM.", "xp": 100, "coins": 50},
    {"text": "Complete 5 quests today.",                 "xp": 80,  "coins": 40},
    {"text": "Study for at least 2 hours today.",        "xp": 90,  "coins": 45},
    {"text": "Wake up early and start strong.",          "xp": 70,  "coins": 35},
    {"text": "Exercise for 30 minutes today.",            "xp": 80,  "coins": 40},
    {"text": "Read 20 pages today.",                      "xp": 70,  "coins": 35},
    {"text": "Have a perfect quest day.",                 "xp": 120, "coins": 60},
]

DAILY_COMPLETE_BONUS = {"xp": 100, "coins": 100}
STREAK_7_BONUS = {"xp": 200, "coins": 100}
STREAK_30_BONUS = {"xp": 1000, "coins": 500}
LEVEL_UP_BONUS_COINS = 50

# ---------------------------------------------------------------------------
# DATA HELPERS
# ---------------------------------------------------------------------------

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def today_str():
    return date.today().isoformat()


def all_quests(data):
    return data["quests"] + data["custom_quests"]


def find_quest(data, quest_id):
    for q in all_quests(data):
        if q["id"] == quest_id:
            return q
    return None


def ensure_today(data):
    """Make sure today's history entry exists, snapshotting today's quest count."""
    t = today_str()
    if t not in data["history"]:
        data["history"][t] = {"completed": [], "total": len(all_quests(data)), "perfect": False}
    return data["history"][t]


def level_from_xp(xp):
    level = 1
    for i in range(1, len(LEVEL_THRESHOLDS)):
        if xp >= LEVEL_THRESHOLDS[i]:
            level = i + 1
        else:
            break
    level = min(level, len(LEVEL_THRESHOLDS))
    current_base = LEVEL_THRESHOLDS[level - 1]
    next_base = LEVEL_THRESHOLDS[level] if level < len(LEVEL_THRESHOLDS) else current_base + 5000
    return level, xp - current_base, next_base - current_base


def get_title(level):
    applicable = [k for k in LEVEL_TITLES if k <= level]
    return LEVEL_TITLES[max(applicable)] if applicable else "Beginner"


def compute_streak(data):
    """Count consecutive 'perfect' days ending today or yesterday."""
    hist = data["history"]
    d = date.today()
    streak = 0
    if hist.get(d.isoformat(), {}).get("perfect"):
        streak += 1
    d -= timedelta(days=1)
    while hist.get(d.isoformat(), {}).get("perfect"):
        streak += 1
        d -= timedelta(days=1)
    return streak


def check_badges(data):
    """Check all badge conditions, unlock any newly-earned ones, return the new ones."""
    u = data["user"]
    unlocked_now = []
    cat_counts = u.get("category_counts", {})
    for b in BADGES:
        if b["id"] in u["badges_unlocked"]:
            continue
        earned = False
        if b["type"] == "streak" and u["longest_streak"] >= b["value"]:
            earned = True
        elif b["type"] == "missions" and u["total_missions_completed"] >= b["value"]:
            earned = True
        elif b["type"] == "perfect_days" and u["perfect_days"] >= b["value"]:
            earned = True
        elif b["type"] == "category" and cat_counts.get(b["cat"], 0) >= b["value"]:
            earned = True
        elif b["type"] == "level":
            level, _, _ = level_from_xp(u["total_xp"])
            if level >= b["value"]:
                earned = True
        if earned:
            u["badges_unlocked"].append(b["id"])
            unlocked_now.append(b)
    return unlocked_now


def week_range(d=None):
    d = d or date.today()
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def weekly_missions_count(data):
    monday, sunday = week_range()
    total = 0
    d = monday
    while d <= sunday:
        entry = data["history"].get(d.isoformat())
        if entry:
            total += len(entry["completed"])
        d += timedelta(days=1)
    return total


def public_user_state(data):
    u = data["user"]
    level, xp_into, xp_needed = level_from_xp(u["total_xp"])
    return {
        "username": u["username"],
        "title": get_title(level),
        "level": level,
        "xp_into_level": xp_into,
        "xp_needed_for_level": xp_needed,
        "total_xp": u["total_xp"],
        "coins": u["coins"],
        "current_streak": compute_streak(data),
        "longest_streak": u["longest_streak"],
        "total_missions_completed": u["total_missions_completed"],
        "perfect_days": u["perfect_days"],
        "badge_count": len(u["badges_unlocked"]),
    }


# ---------------------------------------------------------------------------
# ROUTES - PAGE
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# ROUTES - API
# ---------------------------------------------------------------------------

@app.route("/api/state")
def api_state():
    data = load_data()
    today_entry = ensure_today(data)
    save_data(data)

    quests = all_quests(data)
    today_completed = set(today_entry["completed"])
    quest_list = []
    for q in quests:
        meta = DIFFICULTY_META.get(q["difficulty"], DIFFICULTY_META["easy"])
        cat_meta = CATEGORY_META.get(q["category"], {"icon": "\u2B50", "label": q["category"].title()})
        quest_list.append({
            **q,
            "completed_today": q["id"] in today_completed,
            "difficulty_icon": meta["icon"],
            "difficulty_label": meta["label"],
            "category_icon": cat_meta["icon"],
            "category_label": cat_meta["label"],
        })

    badge_list = []
    for b in BADGES:
        badge_list.append({**b, "unlocked": b["id"] in data["user"]["badges_unlocked"]})

    u = data["user"]
    level, _, _ = level_from_xp(u["total_xp"])
    achievement_list = []
    for a in ACHIEVEMENTS:
        if a["type"] == "missions":
            current = u["total_missions_completed"]
        elif a["type"] == "level":
            current = level
        elif a["type"] == "streak":
            current = u["longest_streak"]
        elif a["type"] == "perfect_days":
            current = u["perfect_days"]
        else:
            current = 0
        achievement_list.append({**a, "current": min(current, a["target"])})

    weekday = date.today().weekday()
    daily_challenge = DAILY_CHALLENGES[weekday % len(DAILY_CHALLENGES)]
    daily_challenge_done = today_entry.get("perfect", False)

    weekly_current = weekly_missions_count(data)
    weekly_target = 25

    shop = []
    for r in REWARD_SHOP:
        shop.append({**r, "affordable": u["coins"] >= r["cost"]})

    return jsonify({
        "user": public_user_state(data),
        "quests": quest_list,
        "today_progress": {
            "completed": len(today_completed),
            "total": len(quests),
            "perfect": today_entry.get("perfect", False),
        },
        "badges": badge_list,
        "achievements": achievement_list,
        "daily_challenge": {**daily_challenge, "completed": daily_challenge_done},
        "weekly_challenge": {"current": min(weekly_current, weekly_target), "target": weekly_target},
        "shop": shop,
        "redeemed": data["redeemed_rewards"],
        "categories": CATEGORY_META,
        "difficulties": DIFFICULTY_META,
        "calendar": build_calendar(data, date.today().year, date.today().month),
    })


@app.route("/api/complete_task", methods=["POST"])
def api_complete_task():
    data = load_data()
    quest_id = request.json.get("quest_id")
    quest = find_quest(data, quest_id)
    if not quest:
        return jsonify({"error": "Quest not found"}), 404

    entry = ensure_today(data)
    if quest_id in entry["completed"]:
        return jsonify({"error": "Already completed today"}), 400

    u = data["user"]
    result = {"xp_gained": quest["xp"], "coins_gained": quest["coins"], "bonuses": [], "newly_unlocked_badges": []}

    entry["completed"].append(quest_id)
    u["total_xp"] += quest["xp"]
    u["coins"] += quest["coins"]
    u["total_missions_completed"] += 1

    cat_counts = u.setdefault("category_counts", {})
    cat_counts[quest["category"]] = cat_counts.get(quest["category"], 0) + 1

    level_before, _, _ = level_from_xp(u["total_xp"] - quest["xp"])

    # Perfect day check
    entry["total"] = len(all_quests(data))
    if len(entry["completed"]) >= entry["total"] and not entry["perfect"]:
        entry["perfect"] = True
        u["perfect_days"] += 1
        u["total_xp"] += DAILY_COMPLETE_BONUS["xp"]
        u["coins"] += DAILY_COMPLETE_BONUS["coins"]
        result["bonuses"].append({"label": "Perfect Day!", **DAILY_COMPLETE_BONUS})

        new_streak = compute_streak(data)
        u["longest_streak"] = max(u["longest_streak"], new_streak)
        if new_streak == 7:
            u["total_xp"] += STREAK_7_BONUS["xp"]
            u["coins"] += STREAK_7_BONUS["coins"]
            result["bonuses"].append({"label": "7-Day Streak Bonus!", **STREAK_7_BONUS})
        if new_streak == 30:
            u["total_xp"] += STREAK_30_BONUS["xp"]
            u["coins"] += STREAK_30_BONUS["coins"]
            result["bonuses"].append({"label": "30-Day Streak Bonus!", **STREAK_30_BONUS})

    u["last_active_date"] = today_str()

    level_after, _, _ = level_from_xp(u["total_xp"])
    if level_after > level_before:
        u["coins"] += LEVEL_UP_BONUS_COINS
        result["leveled_up"] = True
        result["new_level"] = level_after
        result["new_title"] = get_title(level_after)
    else:
        result["leveled_up"] = False

    result["newly_unlocked_badges"] = check_badges(data)

    save_data(data)
    result["user"] = public_user_state(data)
    result["today_progress"] = {
        "completed": len(entry["completed"]),
        "total": entry["total"],
        "perfect": entry["perfect"],
    }
    return jsonify(result)


@app.route("/api/create_task", methods=["POST"])
def api_create_task():
    data = load_data()
    body = request.json or {}
    name = (body.get("name") or "").strip()
    category = body.get("category") or "personal"
    difficulty = body.get("difficulty") or "easy"
    icon = body.get("icon") or "\u2B50"

    if not name:
        return jsonify({"error": "Task name is required"}), 400
    if difficulty not in DIFFICULTY_META:
        difficulty = "easy"

    xp_lo, xp_hi = DIFFICULTY_META[difficulty]["xp"]
    coins_lo, coins_hi = DIFFICULTY_META[difficulty]["coins"]
    new_quest = {
        "id": "c" + str(int(date.today().strftime("%Y%m%d")) * 1000 + len(data["custom_quests"])),
        "name": name,
        "icon": icon,
        "category": category,
        "difficulty": difficulty,
        "xp": round((xp_lo + xp_hi) / 2),
        "coins": round((coins_lo + coins_hi) / 2),
    }
    data["custom_quests"].append(new_quest)
    save_data(data)
    return jsonify({"quest": new_quest})


@app.route("/api/redeem_reward", methods=["POST"])
def api_redeem_reward():
    data = load_data()
    reward_id = request.json.get("reward_id")
    reward = next((r for r in REWARD_SHOP if r["id"] == reward_id), None)
    if not reward:
        return jsonify({"error": "Reward not found"}), 404
    u = data["user"]
    if u["coins"] < reward["cost"]:
        return jsonify({"error": "Not enough coins"}), 400
    u["coins"] -= reward["cost"]
    data["redeemed_rewards"].append({
        "reward_id": reward["id"], "name": reward["name"], "date": today_str(),
    })
    save_data(data)
    return jsonify({"user": public_user_state(data), "redeemed": data["redeemed_rewards"]})


def build_calendar(data, year, month):
    hist = data["history"]
    days_in_month = cal.monthrange(year, month)[1]
    today = date.today()
    days = []
    for day_num in range(1, days_in_month + 1):
        d = date(year, month, day_num)
        entry = hist.get(d.isoformat())
        if d > today:
            status = "future"
        elif entry is None:
            status = "missed" if d < today else "none"
        else:
            completed = len(entry["completed"])
            total = entry.get("total", 1) or 1
            if completed == 0:
                status = "missed" if d < today else "none"
            elif completed >= total:
                status = "full"
            else:
                status = "partial"
        days.append({
            "date": d.isoformat(),
            "day": day_num,
            "status": status,
            "completed": entry["completed"] if entry else [],
        })
    return {"year": year, "month": month, "days": days, "month_name": cal.month_name[month]}


@app.route("/api/calendar/<int:year>/<int:month>")
def api_calendar(year, month):
    data = load_data()
    return jsonify(build_calendar(data, year, month))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
