using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace RobRun.Security
{
    public struct PlayerTelemetry
    {
        public string PlayerId;
        public Vector3 Position;
        public Vector2 ViewAngle; // X = Yaw, Y = Pitch
        public float Timestamp;
        public bool IsInVehicle;
    }

    public class PlayerSecurityProfile
    {
        public string PlayerId { get; }
        public float TrustScore { get; set; } = 100f;
        public List<string> Flags { get; } = new List<string>();
        public List<float> ReactionTimesMs { get; } = new List<float>();
        public PlayerTelemetry? LastTelemetry { get; set; }

        public PlayerSecurityProfile(string playerId)
        {
            PlayerId = playerId;
        }
    }

    public enum AntiCheatAction
    {
        Clean,
        IncreaseAuditFrequency,
        ShadowPoolOrDelayedBan
    }

    public struct ValidationResult
    {
        public string PlayerId;
        public float TrustScore;
        public AntiCheatAction Action;
        public string[] RecentFlags;
    }

    /// <summary>
    /// Prototipo de validación Server-Authoritative y Heurística para Unity
    /// Optimizado para servidores masivos (5.000+ jugadores) con bajo impacto en GC/CPU.
    /// </summary>
    public class RobRunAntiCheatValidator
    {
        private const float MaxRunSpeed = 8.5f;         // m/s a pie
        private const float MaxVehicleSpeed = 45.0f;    // m/s en vehículo
        private const float LatencyBuffer = 1.20f;      // 20% margen por jitter/lag
        private const float MaxHumanTurnRate = 720.0f;  // grados/segundo

        private readonly Dictionary<string, PlayerSecurityProfile> _profiles = new Dictionary<string, PlayerSecurityProfile>();

        public PlayerSecurityProfile GetOrCreateProfile(string playerId)
        {
            if (!_profiles.TryGetValue(playerId, out var profile))
            {
                profile = new PlayerSecurityProfile(playerId);
                _profiles[playerId] = profile;
            }
            return profile;
        }

        public ValidationResult ValidateTick(PlayerTelemetry current)
        {
            var profile = GetOrCreateProfile(current.PlayerId);

            if (!profile.LastTelemetry.HasValue)
            {
                profile.LastTelemetry = current;
                return BuildResult(profile);
            }

            var prev = profile.LastTelemetry.Value;
            float dt = current.Timestamp - prev.Timestamp;

            if (dt <= 0f)
                return BuildResult(profile);

            // 1. DETECCIÓN DE SPEEDHACK / TELEPORT (Validación Física)
            float distance = Vector3.Distance(prev.Position, current.Position);
            float speed = distance / dt;
            float maxAllowed = (current.IsInVehicle ? MaxVehicleSpeed : MaxRunSpeed) * LatencyBuffer;

            if (speed > maxAllowed)
            {
                profile.Flags.Add($"SPEEDHACK_DETECTED: {speed:F2} m/s (Max: {maxAllowed:F2} m/s)");
                profile.TrustScore -= 35f;
            }

            // 2. DETECCIÓN DE AIMBOT (Análisis Angular de Cámara)
            float yawDiff = Mathf.Abs(Mathf.DeltaAngle(prev.ViewAngle.x, current.ViewAngle.x));
            float pitchDiff = Mathf.Abs(current.ViewAngle.y - prev.ViewAngle.y);
            
            float angularDistance = Mathf.Sqrt(yawDiff * yawDiff + pitchDiff * pitchDiff);
            float angularVelocity = angularDistance / dt;

            if (angularVelocity > MaxHumanTurnRate)
            {
                profile.Flags.Add($"AIMBOT_SNAP_DETECTED: {angularVelocity:F1} deg/s");
                profile.TrustScore -= 40f;
            }

            profile.LastTelemetry = current;
            return BuildResult(profile);
        }

        public void LogCombatReaction(string playerId, float reactionMs)
        {
            var profile = GetOrCreateProfile(playerId);
            profile.ReactionTimesMs.Add(reactionMs);

            if (profile.ReactionTimesMs.Count >= 5)
            {
                float avgReaction = profile.ReactionTimesMs.Average();
                if (avgReaction < 90f)
                {
                    profile.Flags.Add($"TRIGGERBOT_DETECTED: Avg reaction {avgReaction:F1}ms");
                    profile.TrustScore -= 50f;
                }
            }
        }

        private ValidationResult BuildResult(PlayerSecurityProfile profile)
        {
            AntiCheatAction action = AntiCheatAction.Clean;

            if (profile.TrustScore <= 0f)
                action = AntiCheatAction.ShadowPoolOrDelayedBan;
            else if (profile.TrustScore < 60f)
                action = AntiCheatAction.IncreaseAuditFrequency;

            return new ValidationResult
            {
                PlayerId = profile.PlayerId,
                TrustScore = Mathf.Max(0f, profile.TrustScore),
                Action = action,
                RecentFlags = profile.Flags.Skip(Math.Max(0, profile.Flags.Count - 2)).ToArray()
            };
        }
    }
}
