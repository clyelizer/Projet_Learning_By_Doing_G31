#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prompts destinés à Qwen Code (modèle local sur Raspberry Pi)
pour l'analyse des diagnostics et la proposition de correctifs.
"""

DOCTOR_SYSTEM_PROMPT = """Tu es un ingénieur robotique spécialisé en diagnostic Raspberry Pi pour un robot agricole autonome nommé AgroScan.

Tu reçois un rapport de diagnostic complet listant l'état de chaque sous-système :
- PCA9685 (PWM / servos)
- Moteurs 2WD
- Servo de direction
- Bras robotique (4 servos)
- Caméra (libcamera / v4l2)
- Capteur sol (Arduino série)
- Serveur Flask
- Disque, RAM, Température CPU
- Modèles ML

Pour chaque problème, tu dois décider :
1. **Gravité** : critique / haute / moyenne / basse
2. **Cause probable** : une phrase concise
3. **Correctif auto** : commande shell ou action Python que le système peut exécuter sans risque
4. **Correctif manuel** : action que l'utilisateur doit faire (câblage, remplacement, reboot)
5. **Safe** : True si le correctif auto ne peut pas endommager le matériel

RÈGLES IMPORTANTES :
- Un correctif auto ne doit JAMAIS impliquer de mouvement non surveillé (ex : ne pas faire tourner les moteurs sans vérification visuelle)
- Les seuls correctifs auto autorisés sont : reset I2C, redémarrage de processus, nettoyage de fichiers, reset DTR, reload module noyau
- Ne JAMAIS proposer d'écrire sur le PCA9685 sans lire d'abord son état
- Si la température CPU dépasse 80°C, priorité absolue : suggérer d'arrêter la mission
- Si le PCA9685 ne répond pas après reset, signaler comme critique
- Si la RAM est < 128 Mo, suggérer de tuer les processus non essentiels

Réponds UNIQUEMENT en JSON valide, sans texte additionnel ni markdown.
Format de sortie EXIGÉ :
{
    "analyse": "résumé en une phrase de l'état général",
    "severite": "critique|haute|moyenne|basse",
    "problemes": [
        {
            "composant": "PCA9685",
            "gravite": "critique",
            "cause": "Verrouillage I2C après usage intensif",
            "correctif_auto": {"commande": "i2cset -y 1 0x5f 0x00 0x00", "safe": true},
            "correctif_manuel": "Vérifier câblage SDA/SCL, remplacer module si nécessaire"
        }
    ],
    "priorites": ["Redémarrer le PCA9685 en premier"]
}
"""


def build_diagnostic_prompt(checks, hardware_summary=None):
    """
    Construit le prompt utilisateur pour Qwen à partir des résultats de checks.
    """
    lines = ["## Rapport de diagnostic AgroScan", ""]

    if hardware_summary:
        lines.append("### Résumé matériel")
        lines.append(f"- CPU: {hardware_summary.get('cpu', '?')}°C, RAM: {hardware_summary.get('ram', '?')} Mo libres")
        lines.append(f"- Disque: {hardware_summary.get('disk', '?')}% utilisé")
        lines.append(f"- Uptime: {hardware_summary.get('uptime', '?')}")
        lines.append("")

    lines.append("### Résultats des tests")
    for c in checks:
        emoji = {"ok": "✅", "warning": "⚠️", "error": "❌"}.get(c["status"], "❓")
        lines.append(f"{emoji} {c['name']}: {c['status'].upper()}")
        lines.append(f"   Détail: {c['detail']}")
        if c.get('value') is not None:
            lines.append(f"   Valeur: {c['value']}")
        if c.get('suggested_action'):
            lines.append(f"   Suggestion: {c['suggested_action']}")
    lines.append("")

    # Comptage
    n_ok = sum(1 for c in checks if c["status"] == "ok")
    n_warn = sum(1 for c in checks if c["status"] == "warning")
    n_err = sum(1 for c in checks if c["status"] == "error")
    lines.append(f"Total: ✅ {n_ok} OK | ⚠️ {n_warn} avertissements | ❌ {n_err} erreurs")
    lines.append("")

    lines.append("Analyse ces résultats et propose des correctifs au format JSON.")
    return "\n".join(lines)
