"""OpenTTD 15.3 source model for the City Airport shared runway.

This is deliberately not fitted to C117/C121 observations.  It mirrors the
relevant pieces of ``aircraft_cmd.cpp``, ``vehicle.cpp`` and
``table/airport_movement.h`` for the base aircraft set used by the project.

The useful quantity is the time during which ``AirportBlock::RunwayInOut`` is
actually held at ``AT_LARGE``.  The block is acquired before moving 8->9 on
take-off and 13->14 on landing, and released when the aircraft reaches the
first position outside that block (11 and 17 respectively).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache


TICKS_PER_DAY = 74.0
PLANE_SPEED = 4
AIRCRAFT_ENGINE_BASE = 215

# OpenTTD 15.3 src/table/engines.h, _orig_aircraft_vehicle_info.
AIRCRAFT_OLD_SPEED = [
    37, 37, 74, 181, 37, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74,
    74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 181, 74, 181, 37,
    37, 74, 74, 181, 25, 40, 25,
]
AIRCRAFT_ACCELERATION = [
    18, 20, 35, 50, 20, 40, 35, 40, 40, 40, 35, 40, 40, 40, 40, 40, 40,
    40, 40, 40, 40, 40, 50, 40, 40, 40, 40, 40, 40, 40, 40, 40, 50, 18,
    20, 40, 40, 50, 20, 20, 20,
]

# Direction enum from direction_type.h.
N, NE, E, SE, S, SW, W, NW = range(8)


@dataclass(frozen=True)
class MovingData:
    x: int
    y: int
    direction: int = N
    exact: bool = False
    no_speed_clamp: bool = False
    hold: bool = False
    slow_turn: bool = False
    land: bool = False
    brake: bool = False


# City Airport moving data used by the runway path and by one steady holding
# orbit. Coordinates are copied from OpenTTD 15.3 airport_movement.h.
CITY = {
    2: MovingData(26, 41, SW, exact=True),
    3: MovingData(56, 22, SE, exact=True),
    4: MovingData(38, 8, SW, exact=True),
    5: MovingData(65, 6),
    6: MovingData(80, 27),
    7: MovingData(44, 63),
    8: MovingData(58, 71),
    9: MovingData(72, 85),
    10: MovingData(89, 85, NE, exact=True),
    11: MovingData(3, 85, no_speed_clamp=True),
    13: MovingData(177, 87, hold=True, slow_turn=True),
    14: MovingData(89, 87, hold=True, land=True),
    15: MovingData(20, 87, no_speed_clamp=True, brake=True),
    17: MovingData(36, 71),
    18: MovingData(160, 87, hold=True, slow_turn=True),
    20: MovingData(257, 1, hold=True, slow_turn=True),
    21: MovingData(273, 49, hold=True, slow_turn=True),
    25: MovingData(145, 1, hold=True, slow_turn=True),
}

_DX = (-1, -1, -1, 0, 1, 1, 1, 0)
_DY = (-1, 0, 1, 1, 1, 0, -1, -1)
_NEW_DIRECTION_TABLE = (N, NW, W, NE, SE, SW, E, SE, S)


@dataclass
class PlaneState:
    x: int
    y: int
    direction: int
    max_speed: int
    acceleration: int
    cur_speed: int = 0
    subspeed: int = 0
    progress: int = 0
    turn_counter: int = 0
    last_direction: int = N
    consecutive_turns: int = 0


def _dir_difference(d0: int, d1: int) -> int:
    return (d0 - d1) % 8


def _direction_towards(v: PlaneState, x: int, y: int) -> int:
    i = 0
    if y >= v.y:
        if y != v.y:
            i += 3
        i += 3
    if x >= v.x:
        if x != v.x:
            i += 1
        i += 1
    desired = _NEW_DIRECTION_TABLE[i]
    diff = _dir_difference(desired, v.direction)
    if diff == 0:
        return v.direction
    return (v.direction + (7 if diff > 4 else 1)) % 8


def _move_one(v: PlaneState) -> None:
    v.x += _DX[v.direction]
    v.y += _DY[v.direction]


def _update_speed(v: PlaneState, speed_limit: int, hard_limit: bool) -> int:
    """Mirror UpdateAircraftSpeed and return pixel updates for one call."""
    limit = speed_limit * PLANE_SPEED
    if v.max_speed < limit:
        if v.cur_speed < limit:
            hard_limit = False
        limit = v.max_speed

    accel = v.acceleration * 77
    old_subspeed = v.subspeed
    v.subspeed = (old_subspeed + (accel & 0xFF)) & 0xFF

    if not hard_limit and v.cur_speed > limit:
        decel = max(1, ((v.cur_speed * v.cur_speed) // 16384) // PLANE_SPEED)
        limit = v.cur_speed - decel

    v.cur_speed = min(
        v.cur_speed + (accel >> 8) + (1 if v.subspeed < old_subspeed else 0),
        limit,
    )

    speed = v.cur_speed // PLANE_SPEED
    if not (v.direction & 1):
        speed = speed * 3 // 4
    speed += v.progress
    v.progress = speed & 0xFF
    return speed >> 8


def _controller(v: PlaneState, target: MovingData) -> bool:
    """Mirror the x/y part of AircraftController for one invocation."""
    dist = abs(target.x - v.x) + abs(target.y - v.y)
    if not target.exact and dist <= (8 if target.slow_turn else 4):
        return True

    if dist == 0:
        diff = _dir_difference(target.direction, v.direction)
        if diff == 0:
            v.cur_speed = 0
            return True
        if _update_speed(v, 50, True) == 0:
            return False
        v.direction = (v.direction + (7 if diff > 4 else 1)) % 8
        v.cur_speed >>= 1
        return False

    speed_limit, hard_limit = 50, True
    if target.no_speed_clamp:
        speed_limit = 65535
    if target.hold:
        speed_limit, hard_limit = 425, False
    if target.land:
        speed_limit, hard_limit = 230, False
    if target.brake:
        speed_limit, hard_limit = 50, False

    count = _update_speed(v, speed_limit, hard_limit)
    if count == 0:
        return False

    nudge = count + 3 > dist
    if v.turn_counter:
        v.turn_counter -= 1

    for _ in range(count):
        if nudge or target.land:
            if v.x != target.x:
                v.x += 1 if target.x > v.x else -1
            if v.y != target.y:
                v.y += 1 if target.y > v.y else -1
            continue

        new_direction = _direction_towards(v, target.x, target.y)
        if new_direction != v.direction:
            if target.slow_turn and v.consecutive_turns < 8:
                if v.turn_counter == 0 or new_direction == v.last_direction:
                    if new_direction == v.last_direction:
                        v.consecutive_turns = 0
                    else:
                        v.consecutive_turns += 1
                    v.turn_counter = 2 * PLANE_SPEED
                    v.last_direction = v.direction
                    v.direction = new_direction
                _move_one(v)
            else:
                v.cur_speed >>= 1
                v.direction = new_direction
        else:
            v.consecutive_turns = 0
            _move_one(v)
    return False


def _reach(v: PlaneState, position: int) -> int:
    calls = 0
    while True:
        calls += 1
        if _controller(v, CITY[position]):
            return calls
        if calls > 100000:
            raise RuntimeError(f"City Airport source simulation did not reach {position}")


def _new_plane(index: int, position: int) -> PlaneState:
    md = CITY[position]
    return PlaneState(
        x=md.x,
        y=md.y,
        direction=md.direction,
        max_speed=(AIRCRAFT_OLD_SPEED[index] * 128) // 10,
        acceleration=AIRCRAFT_ACCELERATION[index],
        last_direction=md.direction,
    )


def _takeoff_calls(index: int, terminal: int = 2) -> int:
    v = _new_plane(index, terminal)
    pre_runway = {
        2: (7, 8),
        3: (6, 7, 8),
        4: (5, 6, 7, 8),
    }[terminal]
    for position in pre_runway:
        _reach(v, position)

    # AirportSetBlocks acquires RunwayInOut while changing logical 8 -> 9.
    calls = _reach(v, 9)
    calls += _reach(v, 10)
    # TAKEOFF state handler changes state but leaves logical position at 10;
    # the next controller invocation reaches the already attained exact point.
    calls += _reach(v, 10)
    calls += _reach(v, 11)
    # AirportClearBlock releases RunwayInOut upon reaching logical position 11.
    return calls


def _warm_hold(index: int, cycles: int = 4) -> PlaneState:
    v = _new_plane(index, 13)
    v.cur_speed = min(v.max_speed, 425 * PLANE_SPEED)
    for _ in range(cycles):
        for position in (18, 25, 20, 21, 13):
            _reach(v, position)
    return v


def _landing_calls(index: int) -> int:
    v = _warm_hold(index)
    # FLYING at 13 chooses LANDING and AirportSetBlocks acquires RunwayInOut.
    calls = _reach(v, 14)
    # LANDING -> ENDLANDING state handler keeps logical position 14 once.
    calls += _reach(v, 14)
    calls += _reach(v, 15)
    calls += _reach(v, 17)
    # AirportClearBlock releases RunwayInOut upon reaching position 17.
    return calls


def _hold_retry_calls(index: int) -> int:
    v = _warm_hold(index)
    calls = 0
    for position in (18, 25, 20, 21, 13):
        calls += _reach(v, position)
    return calls


@lru_cache(maxsize=None)
def at_large_runway_profile(engine_id: int) -> dict | None:
    """Return source-derived City Airport runway timings for a base engine."""
    index = int(engine_id) - AIRCRAFT_ENGINE_BASE
    if index < 0 or index >= 38:  # 38..40 are helicopters.
        return None
    takeoff_calls = _takeoff_calls(index)
    landing_calls = _landing_calls(index)
    hold_calls = _hold_retry_calls(index)
    calls_per_day = 2.0 * TICKS_PER_DAY
    return {
        "engine": int(engine_id),
        "old_speed": AIRCRAFT_OLD_SPEED[index],
        "acceleration": AIRCRAFT_ACCELERATION[index],
        "takeoff_days": takeoff_calls / calls_per_day,
        "landing_days": landing_calls / calls_per_day,
        "service_days": (takeoff_calls + landing_calls) / calls_per_day,
        "hold_retry_days": hold_calls / calls_per_day,
        "takeoff_calls": takeoff_calls,
        "landing_calls": landing_calls,
        "hold_retry_calls": hold_calls,
    }


def base_aircraft_runway_profiles() -> list[dict]:
    return [at_large_runway_profile(AIRCRAFT_ENGINE_BASE + i) for i in range(38)]
