#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrateur Doctor.
Checks → (optionnel Qwen Code pour analyse LLM) → auto-heal → rapport.
"""

import json
import os
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

from . import checks
from . import healer
from . import prompts
from . import state as state_module


def run_diagnostic(with_llm=False, auto_heal=False, doctor_dir=None):
    """
    Exécute un diagnostic complet.

    Args:
        with_llm: si True, tente d'appeler Qwen Code local pour analyse
        auto_heal: si True, exécute les correctifs automatiques
        doctor_dir: dossier où sauvegarder le rapport (defaut: PROJECT_DIR)

    Returns:
        dict avec status, checks, healing, llm_analysis, timestamp, report_path
    """
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    timestamp = time.time()

    # 1. État système pour contexte
    system_state = state_module.capture_state()

    # 2. Checks
    check_results = checks.run_all_checks()

    # 3. Statistiques
    n_ok = sum(1 for c in check_results if c["status"] == "ok")
    n_warn = sum(1 for c in check_results if c["status"] == "warning")
    n_err = sum(1 for c in check_results if c["status"] == "error")
    n_total = len(check_results)

    # 4. Niveau global
    if n_err > 0:
        global_status = "error"
    elif n_warn > 0:
        global_status = "warning"
    else:
        global_status = "ok"

    # 5. Auto-heal (optionnel)
    healing_results = []
    if auto_heal:
        healing_results = healer.auto_heal(check_results)

    # 6. LLM (optionnel)
    llm_analysis = None
    if with_llm:
        llm_analysis = _call_qwen(check_results, system_state)

    # 7. Rapport texte
    report_text = _build_report(check_results, healing_results, llm_analysis, ts,
                                system_state, global_status)

    # 8. Sauvegarde du rapport
    doctor_dir = doctor_dir or PROJECT_DIR
    report_dir = Path(doctor_dir) / "data" / "doctor"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"diagnostic_{int(timestamp)}.md"

    # Lien "latest"
    latest_path = report_dir / "latest.md"
    report_path.write_text(report_text)
    if latest_path.exists():
        latest_path.unlink()
    latest_path.symlink_to(report_path.name)

    return {
        "status": global_status,
        "timestamp": ts,
        "summary": {
            "total": n_total,
            "ok": n_ok,
            "warning": n_warn,
            "error": n_err,
        },
        "checks": check_results,
        "healing": healing_results,
        "llm_analysis": llm_analysis,
        "system": {
            "cpu_temp_c": system_state["cpu"]["temp_c"],
            "ram_available_mb": system_state["memory"]["available_mb"] if system_state["memory"] else None,
            "disk_used_pct": system_state["disk"]["used_pct"] if system_state["disk"] else None,
            "uptime": system_state["uptime"]["human"] if system_state["uptime"] else None,
        },
        "report_path": str(report_path),
    }


def _call_qwen(check_results, system_state):
    """
    Appelle Qwen Code local via subprocess pour analyse LLM.
    Qwen doit être accessible en ligne de commande.
    """
    # Essayer différents binaires possibles
    qwen_binaries = ["qwen", "qwen-code", "ollama", "qwen2.5-coder"]

    for binary in qwen_binaries:
        try:
            import subprocess as sp
            # Vérifier si le binaire existe
            rc = sp.run(["which", binary], capture_output=True, timeout=2)
            if rc.returncode != 0:
                continue

            # Construire le prompt
            user_prompt = prompts.build_diagnostic_prompt(check_results, {
                "cpu": system_state["cpu"]["temp_c"],
                "ram": system_state["memory"]["available_mb"] if system_state["memory"] else None,
                "disk": system_state["disk"]["used_pct"] if system_state["disk"] else None,
                "uptime": system_state["uptime"]["human"] if system_state["uptime"] else None,
            })
            full_input = prompts.DOCTOR_SYSTEM_PROMPT + "\n\n" + user_prompt

            # Appel Qwen
            if binary == "ollama":
                # ollama run qwen2.5-coder
                proc = sp.run(
                    ["ollama", "run", "qwen2.5-coder"],
                    input=full_input,
                    capture_output=True, text=True, timeout=60
                )
            else:
                # qwen / qwen-code --stdin
                proc = sp.run(
                    [binary, "--stdin"],
                    input=full_input,
                    capture_output=True, text=True, timeout=60
                )

            if proc.returncode == 0 and proc.stdout.strip():
                # Tenter de parser le JSON
                out = proc.stdout.strip()
                # Nettoyer les marqueurs markdown éventuels
                if "```json" in out:
                    out = out.split("```json")[1].split("```")[0].strip()
                elif "```" in out:
                    out = out.split("```")[1].split("```")[0].strip()
                parsed = json.loads(out)
                parsed["model"] = f"{binary}/qwen2.5-coder"
                return parsed

        except FileNotFoundError:
            continue
        except json.JSONDecodeError:
            return {"error": "Réponse Qwen non-JSON", "raw": proc.stdout[:500]}
        except subprocess.TimeoutExpired:
            return {"error": "Qwen a timeout (60s)"}
        except Exception as e:
            return {"error": str(e)}

    # Aucun LLM disponible → fallback rules
    return _fallback_analysis(check_results)


def _fallback_analysis(check_results):
    """Analyse par règles si Qwen n'est pas disponible."""
    errors = [c for c in check_results if c["status"] == "error"]
    warnings = [c for c in check_results if c["status"] == "warning"]

    problemes = []
    for c in errors:
        problemes.append({
            "composant": c["name"],
            "gravite": "critique",
            "cause": c["detail"][:200],
            "correctif_auto": {
                "commande": str(c.get("suggested_action", "")),
                "safe": True,
            } if c.get("suggested_action") else None,
            "correctif_manuel": c.get("suggested_action", "Diagnostic manuel requis"),
        })

    priorites = []
    # Ordre de priorité
    for comp in ["PCA9685", "Moteurs", "Direction", "Bras", "Caméra", "Capteur sol"]:
        if any(c["name"] == comp for c in errors):
            priorites.append(f"Résoudre {comp} en priorité")

    return {
        "analyse": f"{len(errors)} erreur(s), {len(warnings)} avertissement(s)",
        "severite": "critique" if errors else ("moyenne" if warnings else "basse"),
        "problemes": problemes,
        "priorites": priorites if priorites else ["Aucun problème critique"],
        "model": "fallback-rules",
    }


def _build_report(checks, healing, llm, ts, system_state, global_status):
    """Génère un rapport Markdown lisible."""
    lines = []
    lines.append(f"# 🩺 Rapport Diagnostic — {ts}")
    lines.append(f"**Statut global** : {'✅' if global_status == 'ok' else '⚠️' if global_status == 'warning' else '❌'} {global_status.upper()}")
    lines.append("")

    # Système
    lines.append("## 💻 État système")
    if system_state:
        s = system_state
        lines.append(f"- CPU: {s['cpu']['temp_c']}°C, usage {s['cpu']['usage_pct']}%")
        if s["memory"]:
            lines.append(f"- RAM: {s['memory']['available_mb']} Mo libre / {s['memory']['total_mb']} Mo total")
        if s["disk"]:
            lines.append(f"- Disque: {s['disk']['used_pct']}% utilisé ({s['disk']['available_mb']} Mo libre)")
        if s["uptime"]:
            lines.append(f"- Uptime: {s['uptime']['human']}")
        if s.get("network"):
            for iface in s["network"].get("interfaces", []):
                lines.append(f"- Réseau: {iface['name']} → {iface['ip']}")
    lines.append("")

    # Checks
    lines.append(f"## ✅ Checks ({len(checks)} tests)")
    for c in checks:
        emoji = {"ok": "✅", "warning": "⚠️", "error": "❌"}.get(c["status"], "❓")
        lines.append(f"{emoji} **{c['name']}** — {c['status'].upper()}")
        lines.append(f"   _{c['detail']}_")
        if c.get("suggested_action"):
            lines.append(f"   💡 {c['suggested_action']}")
    lines.append("")

    # Healing
    if healing:
        lines.append(f"## 🔧 Auto-healing ({len(healing)} actions)")
        for h in healing:
            emoji_h = "✅" if h["status"] == "ok" else "❌"
            safe = "🔒" if h.get("safe") else "⚠️ MANUEL"
            lines.append(f"{emoji_h} [{safe}] {h.get('check_name', '?')}: {h['detail']}")
        lines.append("")

    # LLM
    if llm:
        lines.append("## 🤖 Analyse LLM")
        if "error" in llm:
            lines.append(f"⚠️ LLM non disponible: {llm['error']}")
        else:
            lines.append(f"**Analyse**: {llm.get('analyse', 'N/A')}")
            lines.append(f"**Sévérité**: {llm.get('severite', 'N/A')}")
            if llm.get("priorites"):
                lines.append("**Priorités**:")
                for p in llm["priorites"]:
                    lines.append(f"- {p}")
            if llm.get("problemes"):
                lines.append("\n**Problèmes détectés**:")
                for p in llm["problemes"]:
                    lines.append(f"- ❌ {p.get('composant')} ({p.get('gravite')}): {p.get('cause')}")
                    if p.get("correctif_auto"):
                        lines.append(f"  → Auto: `{p['correctif_auto'].get('commande', '')}`")
                    if p.get("correctif_manuel"):
                        lines.append(f"  → Manuel: {p['correctif_manuel']}")
            lines.append(f"\n_Modèle: {llm.get('model', 'N/A')}_")
        lines.append("")

    lines.append("---")
    lines.append(f"_Généré par Robot Doctor — {ts}_")
    return "\n".join(lines)
