"""pvp.py - 6 game modes (Normal, Crazy, Double, Double Crazy, Triple, Triple Crazy) & Matchmaking."""
import time
from dataclasses import dataclass, field

MODES = {
    "normal":       dict(rolls=1, keep=1, low=False, label="Normal"),
    "crazy":        dict(rolls=1, keep=1, low=True,  label="Crazy"),
    "double":       dict(rolls=2, keep=2, low=False, label="Double"),
    "double_crazy": dict(rolls=2, keep=2, low=True,  label="Double Crazy"),
    "triple":       dict(rolls=3, keep=3, low=False, label="Triple"),
    "triple_crazy": dict(rolls=3, keep=3, low=True,  label="Triple Crazy"),
}


def round_score(rolls: list[int], mode: str) -> int:
    m = MODES[mode]
    return sum(sorted(rolls, reverse=not m["low"])[:m["keep"]])


def round_winner(a_rolls: list[int], b_rolls: list[int], mode: str):
    """0 = player A wins the round, 1 = player B, None = tie (replay)."""
    a, b = round_score(a_rolls, mode), round_score(b_rolls, mode)
    if a == b:
        return None
    return 0 if (a < b) == MODES[mode]["low"] else 1


@dataclass
class Match:
    game: str
    mode: str
    target: int                 # points to win: 1, 2 or 3
    stake: int                  # cents, per player
    players: tuple              # (uid_a, uid_b); uid_b == 0 means the bot
    score: list = field(default_factory=lambda: [0, 0])

    @property
    def rolls_needed(self) -> int:
        return MODES[self.mode]["rolls"]

    @property
    def winner(self):
        for i in (0, 1):
            if self.score[i] >= self.target:
                return i
        return None

    def play_round(self, a_rolls: list[int], b_rolls: list[int]):
        w = round_winner(a_rolls, b_rolls, self.mode)
        if w is not None:
            self.score[w] += 1
        return w


class Matchmaker:
    def __init__(self, ttl: float = 120):
        self.ttl = ttl
        self.queues: dict[tuple, list] = {}

    def join(self, key: tuple, uid: int, now: float = None):
        now = time.time() if now is None else now
        q = [(u, t) for u, t in self.queues.get(key, []) if now - t < self.ttl]
        for i, (u, _) in enumerate(q):
            if u != uid:
                q.pop(i)
                self.queues[key] = q
                return u
        if not any(u == uid for u, _ in q):
            q.append((uid, now))
        self.queues[key] = q
        return None

    def cancel(self, uid: int) -> bool:
        hit = False
        for key, q in self.queues.items():
            kept = [(u, t) for u, t in q if u != uid]
            hit |= len(kept) != len(q)
            self.queues[key] = kept
        return hit

    def expired(self, now: float = None) -> list:
        now = time.time() if now is None else now
        out = []
        for key, q in self.queues.items():
            out += [(key, u) for u, t in q if now - t >= self.ttl]
            self.queues[key] = [(u, t) for u, t in q if now - t < self.ttl]
        return out