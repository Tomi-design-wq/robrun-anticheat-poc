markdown
# ROB RUN — Scalable Anti-Cheat Architecture (PoC)

A lightweight, server-authoritative anti-cheat proof-of-concept designed for high-density, Free-to-Play extraction & open-world multiplayer servers (5,000+ concurrent players) like **ROB RUN**.

## 📦 Repository Contents
* **`RobRunAntiCheatValidator.cs` (C# / Unity):** Production-oriented server implementation utilizing Unity's `Vector3` and `Mathf.DeltaAngle` along with value-type `structs` to minimize Garbage Collection (GC) overhead on high-tick servers.
* **`robrun_anticheat_poc.py` (Python 3):** Standalone, zero-dependency simulation script demonstrating legit vs. cheater telemetry evaluation.

## 🎯 Problem Statement
High-concurrency F2P games with weekly wipe economies face three major security bottlenecks:
1. **CPU & GC Overhead at Scale:** Running heavy physics and combat validation on every single server tick for 5,000 players degrades server tick rates.
2. **High-Latency False Positives:** Global player bases experience network jitter; overly strict movement checks unfairly penalize legitimate players.
3. **Disposable Accounts:** Instant account creation renders traditional account bans ineffective without behavioral isolation and delayed enforcement.

## 🛡️ Proposed Architecture

This prototype demonstrates a low-overhead validation pipeline built around four core principles:

* **Adaptive Tick Auditing (`TrustScore`):** Clean players are audited via randomized batch sampling to save CPU cycles. If anomalous behavior lowers a player's `TrustScore`, the server dynamically switches them to per-tick high-frequency auditing (`IncreaseAuditFrequency`).
* **Latency-Buffered Physics Validation:** Detects speedhacks and teleportation by comparing displacement over delta time (`dt`), incorporating a configurable latency buffer (`1.20x`) to prevent false positives caused by packet loss or ping spikes.
* **Combat & Camera Heuristics:** Tracks angular camera velocity (`deg/s`) to flag inhuman aimbot snaps, alongside reaction-time profiling (`ms`) to identify triggerbots.
* **Shadow Pools & Delayed Bans:** Instead of kicking cheaters immediately (which helps cheat developers reverse-engineer detection thresholds), flagged accounts are routed to isolated matchmaking pools (`ShadowPoolOrDelayedBan`) for ban waves.

## 🚀 Quick Start (Python Simulation)

No external dependencies are required to run the standalone simulation:

```bash
git clone https://github.com
cd robrun-anticheat-poc
python robrun_anticheat_poc.py
```

## 📊 Sample Output

```text
--- 1. Simulando Jugador Legítimo ---
{'player_id': 'LegitPlayer_AR', 'trust_score': 100.0, 'action': 'CLEAN', 'flags': []}

--- 2. Simulando Cheater (Speedhack + Aimbot Snap) ---
{'player_id': 'Cheater_99', 'trust_score': 25.0, 'action': 'INCREASE_AUDIT_FREQUENCY', 'flags': ['SPEEDHACK_DETECTED: 150.00 m/s (Max: 10.20 m/s)', 'AIMBOT_SNAP_DETECTED: 1754.1 deg/s']}
Estado tras análisis de combate: {'player_id': 'Cheater_99', 'trust_score': 0.0, 'action': 'SHADOW_POOL_OR_DELAYED_BAN', 'flags': ['AIMBOT_SNAP_DETECTED: 1754.1 deg/s', 'TRIGGERBOT_DETECTED: Avg reaction 45.0ms']}
```

## 🔮 Future Roadmap (Production Scale)
* **Server-Side Occlusion (Fog of War):** Stripping entity coordinates from network packets when outside valid line-of-sight to neutralize memory-based wallhacks.
* **HWID + TPM 2.0 Fingerprinting:** Binding bans to hardware identifiers to deter ban evasion.
* **Server-Side Honeypots:** Placing invisible decoy loot/entities inside solid geometry to catch ESP/wallhack users with zero false positives.
