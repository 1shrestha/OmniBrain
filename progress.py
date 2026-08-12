"""
components/progress.py — animated-feeling status step lists.

Streamlit has no native step tracker, so this renders a simple
checklist where each step is one of: done | active | pending.
"""

import time
import streamlit as st

ICONS = {"done": "✅", "active": "🔵", "pending": "⚪"}


def render_steps(steps: list[dict], placeholder=None) -> None:
    """
    steps: [{"label": "URL Validated", "state": "done"}, ...]
    state is one of: done, active, pending
    """
    target = placeholder or st
    rows = []
    for step in steps:
        state = step["state"]
        css_class = {"done": "ob-step-done", "active": "ob-step-active", "pending": "ob-step-pending"}[state]
        rows.append(
            f'<div class="ob-step-row {css_class}">'
            f'<span class="ob-step-icon">{ICONS[state]}</span> {step["label"]}'
            f"</div>"
        )
    target.markdown("\n".join(rows), unsafe_allow_html=True)


def run_pipeline_animation(placeholder, step_labels: list[str], delay: float = 0.55) -> None:
    """Reveal each step one at a time to fake real-time progress feedback."""
    for i in range(len(step_labels)):
        steps = []
        for j, label in enumerate(step_labels):
            if j < i:
                state = "done"
            elif j == i:
                state = "active"
            else:
                state = "pending"
            steps.append({"label": label, "state": state})
        render_steps(steps, placeholder)
        time.sleep(delay)
    render_steps([{"label": lbl, "state": "done"} for lbl in step_labels], placeholder)
