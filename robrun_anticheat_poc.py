import math
import time
from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class PlayerTelemetry:
    player_id: str
    position: Tuple[float, float, float]  # (x, y, z)
    view_angle: Tuple[float, float]       # (yaw, pitch) en grados
    timestamp: float
    is_in_vehicle: bool = False

@dataclass
class PlayerSecurityProfile:
    player_id: str
    trust_score: float = 100.0
    flags: List[str] = field(default_factory=list)
    reaction_times_ms: List[float] = field(default_factory=list)
    last_telemetry: PlayerTelemetry = None

class RobRunAntiCheatValidator:
    """
    Prototipo de validación Server-Authoritative y Heurística
    diseñado para servidores masivos (5.000+ jugadores) con bajo impacto en CPU.
    """
    MAX_RUN_SPEED = 8.5          # metros/segundo (máximo permitido a pie)
    MAX_VEHICLE_SPEED = 45.0     # metros/segundo (máximo en auto)
    LATENCY_BUFFER = 1.20        # 20% de margen para evitar falsos positivos por lag
    MAX_HUMAN_TURN_RATE = 720.0  # grados/segundo (giro de cámara humanamente posible)

    def __init__(self):
        self.profiles = {}

    def get_or_create_profile(self, player_id: str) -> PlayerSecurityProfile:
        if player_id not in self.profiles:
            self.profiles[player_id] = PlayerSecurityProfile(player_id=player_id)
        return self.profiles[player_id]

    def validate_tick(self, current: PlayerTelemetry) -> dict:
        profile = self.get_or_create_profile(current.player_id)
        
        if profile.last_telemetry is None:
            profile.last_telemetry = current
            return {"status": "INITIALIZED", "trust_score": profile.trust_score}

        prev = profile.last_telemetry
        dt = current.timestamp - prev.timestamp

        if dt <= 0:
            return {"status": "IGNORED_DUPLICATE_TICK", "trust_score": profile.trust_score}

        # 1. DETECCIÓN DE SPEEDHACK / TELEPORT (Validación Física)
        distance = math.dist(prev.position, current.position)
        speed = distance / dt
        max_allowed = (self.MAX_VEHICLE_SPEED if current.is_in_vehicle else self.MAX_RUN_SPEED) * self.LATENCY_BUFFER

        if speed > max_allowed:
            violation = f"SPEEDHACK_DETECTED: {speed:.2f} m/s (Max: {max_allowed:.2f} m/s)"
            profile.flags.append(violation)
            profile.trust_score -= 35.0

        # 2. DETECCIÓN DE AIMBOT (Análisis Angular de Cámara)
        yaw_diff = abs(current.view_angle[0] - prev.view_angle[0])
        if yaw_diff > 180:
            yaw_diff = 360 - yaw_diff  # Ajuste de ángulo circular
        pitch_diff = abs(current.view_angle[1] - prev.view_angle[1])
        
        angular_distance = math.hypot(yaw_diff, pitch_diff)
        angular_velocity = angular_distance / dt

        if angular_velocity > self.MAX_HUMAN_TURN_RATE:
            violation = f"AIMBOT_SNAP_DETECTED: {angular_velocity:.1f} deg/s"
            profile.flags.append(violation)
            profile.trust_score -= 40.0

        profile.last_telemetry = current
        return self._evaluate_action(profile)

    def log_combat_reaction(self, player_id: str, reaction_ms: float):
        """
        Detecta tiempos de reacción robóticos (ej. disparar exactamente 15ms después
        de que un enemigo entra en línea de visión).
        """
        profile = self.get_or_create_profile(player_id)
        profile.reaction_times_ms.append(reaction_ms)

        if len(profile.reaction_times_ms) >= 5:
            avg_reaction = sum(profile.reaction_times_ms) / len(profile.reaction_times_ms)
            # La media humana en shooters competitivos ronda los 180-250ms
            if avg_reaction < 90.0:
                profile.flags.append(f"TRIGGERBOT_DETECTED: Avg reaction {avg_reaction:.1f}ms")
                profile.trust_score -= 50.0

    def _evaluate_action(self, profile: PlayerSecurityProfile) -> dict:
        if profile.trust_score <= 0:
            action = "SHADOW_POOL_OR_DELAYED_BAN"
        elif profile.trust_score < 60:
            action = "INCREASE_AUDIT_FREQUENCY"  # Auditar cada tick en lugar de por lotes
        else:
            action = "CLEAN"

        return {
            "player_id": profile.player_id,
            "trust_score": max(0.0, profile.trust_score),
            "action": action,
            "flags": profile.flags[-2:]  # Últimas alertas registradas
        }

# ==========================================
# SIMULACIÓN DE PRUEBA (JUGADOR NORMAL VS CHEATER)
# ==========================================
if __name__ == "__main__":
    anticheat = RobRunAntiCheatValidator()
    base_time = time.time()

    print("--- 1. Simulando Jugador Legítimo ---")
    anticheat.validate_tick(PlayerTelemetry("LegitPlayer_AR", (0, 0, 0), (90.0, 0.0), base_time))
    # Se mueve 8 metros en 1 segundo y gira la cámara 45 grados
    res_legit = anticheat.validate_tick(PlayerTelemetry("LegitPlayer_AR", (8.0, 0, 0), (135.0, 5.0), base_time + 1.0))
    print(res_legit)

    print("\n--- 2. Simulando Cheater (Speedhack + Aimbot Snap) ---")
    anticheat.validate_tick(PlayerTelemetry("Cheater_99", (100, 100, 0), (10.0, 0.0), base_time))
    # En 0.1 segundos recorre 15 metros (150 m/s) y gira 175 grados instantáneamente (1750 deg/s)
    res_cheater = anticheat.validate_tick(PlayerTelemetry("Cheater_99", (115.0, 100, 0), (185.0, -12.0), base_time + 0.1))
    print(res_cheater)

    # Simula 5 disparos con tiempos de reacción de Triggerbot (~45ms)
    for rt in [45.0, 42.0, 48.0, 44.0, 46.0]:
        anticheat.log_combat_reaction("Cheater_99", rt)
    
    final_status = anticheat._evaluate_action(anticheat.get_or_create_profile("Cheater_99"))
    print("Estado tras análisis de combate:", final_status)
