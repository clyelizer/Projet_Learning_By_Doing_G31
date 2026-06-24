#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Doctor — Moteur de diagnostic et d'auto-réparation.

Expose une seule fonction :
    run_diagnostic(with_llm=False, auto_heal=False)
        → dict { status, checks, issues, healing, report }
"""
from .engine import run_diagnostic
