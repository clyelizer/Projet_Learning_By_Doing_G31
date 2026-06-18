# Rotation Fix Plan — Car-Style Arc Turn for 2WD Chassis

## Problem

The robot is a **2WD car with front servo steering** (Ackermann geometry). The current
`rotate_left()` and `rotate_right()` methods in [`src/executor.py`](src/executor.py:100-118)
attempt a **tank turn** (left wheel backward + right wheel forward), which is mechanically
impossible on this chassis. The front passive wheels resist sideways movement, resulting
in barely any rotation.

The [`README.md`](README.md:10) already states: *"Virage sur place : ❌ Impossible (doit avancer en courbe)"*

## Design Decision: Forward Arc Turn (Option A)

For car-style turning, replace tank spin with **servo steering + both motors forward**:

```
rotate_left():  servo = left,  both rear motors = forward → robot drives in left arc
rotate_right(): servo = right, both rear motors = forward → robot drives in right arc
```

This is the simplest approach and respects the project rule: *"Simplicité avant tout. Pas de sur-engineering."*

## Files to Modify

| File | Change | Impact |
|------|--------|--------|
| `src/executor.py` | Replace `rotate_left()` / `rotate_right()` with servo-based arc turns | **Core fix** |
| `config/calibration.json` | Add comment/doc about recalibrating `deg_per_sec` | Advisory |
| `CLAUDE.md` | Update rotation description to car-style turning | Documentation |

## Files NOT Modified

| File | Reason |
|------|--------|
| `src/planner.py` | Command interface unchanged — same `{type, direction, duration}` format |
| `src/main.py` | Calls `executor.run()` unchanged |
| `README.md` | Already states *"Virage sur place : ❌ Impossible"* |

## Step-by-Step Changes

### 1. `src/executor.py` — `rotate_left()` (lines 100-108)

**Before (tank spin):**
```python
def rotate_left(self):
    self.center_steering()              # ❌ servo centered
    self._set_motor('left_rear', 'backward')   # ❌ left backward
    self._set_motor('right_rear', 'forward')   # ❌ right forward
```

**After (car arc turn):**
```python
def rotate_left(self):
    self._set_steering('left')          # ✅ servo turned left
    self._set_motor('left_rear', 'forward')    # ✅ both forward
    self._set_motor('right_rear', 'forward')
```

### 2. `src/executor.py` — `rotate_right()` (lines 110-118)

Same pattern: servo to `right`, both motors `forward`.

### 3. `src/executor.py` — `run()` function (lines 137-168)

**No changes needed.** The command interface stays the same:
```python
{'type': 'rotate', 'direction': 'left', 'angle_deg': 45.0, 'duration': 1.25}
```

### 4. `config/calibration.json` — Recalibration note

`deg_per_sec: 36` was measured for the old tank-spin approach. After the fix,
the user MUST re-measure this value because the robot now turns in an arc (wider,
slower heading change per second).

**How to recalibrate:**
1. Place robot on flat ground
2. Run: `rotate_left()` for exactly 2 seconds
3. Measure how many degrees the robot's heading changed
4. Divide by 2 → new `deg_per_sec`

### 5. `CLAUDE.md` — Update rotation description

Change the executor section to clarify that rotation is arc-based (servo + forward),
not spin-in-place. Add a rule that `rotate_left`/`rotate_right` must NOT use
opposite motor directions.

## Interface Compatibility

```
┌──────────┐    {'type':'rotate',     ┌─────────────┐
│ planner  │─── 'direction':'left',──▶│  executor   │
│          │    'duration': 1.25}     │  .run()     │
└──────────┘                          └──────┬──────┘
                                             │
                                    ┌────────▼──────────┐
                                    │ MotorController    │
                                    │ .rotate_left()    │
                                    │  servo=left        │
                                    │  both motors=fwd   │
                                    └───────────────────┘
```

The external interface is unchanged — only the internal implementation differs.

## Risks

- **`deg_per_sec` recalibration**: The new value will be significantly lower than 36°/s
  because arc turns cover more ground per degree of heading change. If not recalibrated,
  rotation commands will be too short.
- **Space requirement**: Arc turns need forward space (the robot moves in a curve).
  The planner may need to account for this — but that can be deferred to a later iteration.
- **Steering PWM values**: `left: 200` and `right: 460` may need adjustment for the desired
  turn radius. These are hardware-specific and must be tuned per robot.
