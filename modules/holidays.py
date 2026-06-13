from datetime import date, timedelta


US_MARKET_HOLIDAYS_2026 = [
    date(2026, 1, 1),    # New Year's Day
    date(2026, 1, 19),   # Martin Luther King Jr. Day
    date(2026, 2, 16),   # Presidents' Day
    date(2026, 4, 3),    # Good Friday
    date(2026, 5, 25),   # Memorial Day
    date(2026, 6, 19),   # Juneteenth
    date(2026, 7, 3),    # Independence Day (observed)
    date(2026, 9, 7),    # Labor Day
    date(2026, 11, 26),  # Thanksgiving Day
    date(2026, 12, 25),  # Christmas Day
]

US_MARKET_HOLIDAYS_2027 = [
    date(2027, 1, 1),    # New Year's Day
    date(2027, 1, 18),   # Martin Luther King Jr. Day
    date(2027, 2, 15),   # Presidents' Day
    date(2027, 3, 26),   # Good Friday
    date(2027, 5, 31),   # Memorial Day
    date(2027, 6, 18),   # Juneteenth (observed)
    date(2027, 7, 5),    # Independence Day (observed)
    date(2027, 9, 6),    # Labor Day
    date(2027, 11, 25),  # Thanksgiving Day
    date(2027, 12, 24),  # Christmas (observed)
    date(2027, 12, 31),  # New Year's (observed)
]


def get_holidays() -> list[date]:
    return US_MARKET_HOLIDAYS_2026 + US_MARKET_HOLIDAYS_2027


def is_market_open(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    return d not in get_holidays()


def next_holiday(d: date = None) -> tuple[date | None, str]:
    if d is None:
        d = date.today()
    for h in sorted(get_holidays()):
        if h >= d:
            names = {
                date(2026, 1, 1): "元旦",
                date(2026, 1, 19): "马丁·路德·金纪念日",
                date(2026, 2, 16): "总统日",
                date(2026, 4, 3): "耶稣受难日",
                date(2026, 5, 25): "阵亡将士纪念日",
                date(2026, 6, 19): "六月节",
                date(2026, 7, 3): "独立日（调休）",
                date(2026, 9, 7): "劳动节",
                date(2026, 11, 26): "感恩节",
                date(2026, 12, 25): "圣诞节",
                date(2027, 1, 1): "元旦",
                date(2027, 1, 18): "马丁·路德·金纪念日",
                date(2027, 2, 15): "总统日",
                date(2027, 3, 26): "耶稣受难日",
                date(2027, 5, 31): "阵亡将士纪念日",
                date(2027, 6, 18): "六月节（调休）",
                date(2027, 7, 5): "独立日（调休）",
                date(2027, 9, 6): "劳动节",
                date(2027, 11, 25): "感恩节",
                date(2027, 12, 24): "圣诞节（调休）",
                date(2027, 12, 31): "元旦前夕",
            }
            return h, names.get(h, "休市日")
    return None, ""


def next_market_day(d: date = None) -> date:
    if d is None:
        d = date.today()
    d += timedelta(days=1)
    while not is_market_open(d):
        d += timedelta(days=1)
    return d
