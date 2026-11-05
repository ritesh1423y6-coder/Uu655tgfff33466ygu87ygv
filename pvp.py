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


@dataclass
class Match:
    game: str
    mode: str
    target: int                 # points to win: 1, 2 or 3
    stake: float                # Changed to float for correct bot compatibility (e.g. 1.50)
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
        """0 = player A wins the round, 1 = player B, None = tie (replay)."""
        
        # Helper function to evaluate score based on the specific game
        def evaluate(rolls: list[int]) -> int:
            game_name = self.game.lower()
            if game_name in ["basket", "bask"]:
                # Goals: 4, 5. Miss/Stuck: 1, 2, 3
                return sum(1 for r in rolls if r >= 4)
            elif game_name == "football":
                # Goals: 3, 4, 5. Miss: 1, 2
                return sum(1 for r in rolls if r >= 3)
            else:
                # Dice, Dart, Bowl: Sum the raw values (e.g. pins knocked down, dart points)
                return sum(rolls)
                
        # Get point values for this round
        v1 = evaluate(a_rolls)
        v2 = evaluate(b_rolls)
        
        res = None
        if v1 > v2: 
            res = 0
        elif v2 > v1: 
            res = 1
        
        # Invert winner if mode is Crazy (lowest wins)
        if res is not None and MODES[self.mode]["low"]:
            res = 1 if res == 0 else 0
            
        # Add point to the winner (if not tied)
        if res == 0:
            self.score[0] += 1
        elif res == 1:
            self.score[1] += 1
            
        return res


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