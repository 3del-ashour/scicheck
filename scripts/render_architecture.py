"""Render the SciCheck architecture diagram to PNG + SVG.

Outputs:
    docs/architecture.png   (≥ 1920x1080 for the Word report)
    docs/architecture.svg   (vector — for the slide deck)

Usage:
    python scripts/render_architecture.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# ---------------------------------------------------------------------------
# Layout constants — figure is 100 wide × 56.25 tall (16:9)
# ---------------------------------------------------------------------------
PIPE_FILL = "#E3E8F0"
PIPE_EDGE = "#4A6FA5"
SAFETY_FILL = "#FFE9CE"
SAFETY_EDGE = "#D97706"
RAG_FILL = "#D5F0DA"
RAG_EDGE = "#059669"
ENDPOINT_FILL = "#E5DCFB"
ENDPOINT_EDGE = "#646CFF"
ARROW_COLOR = "#374151"
TEXT_COLOR = "#1F2937"
SUB_COLOR = "#6B7280"


def draw_box(ax, x, y, w, h, fill, edge, label, sub=None) -> None:
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.45,rounding_size=0.6",
        linewidth=2.0,
        edgecolor=edge,
        facecolor=fill,
    )
    ax.add_patch(box)
    cx, cy = x + w / 2, y + h / 2
    ax.text(
        cx,
        cy + (1.0 if sub else 0),
        label,
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color=TEXT_COLOR,
    )
    if sub:
        ax.text(
            cx,
            cy - 1.7,
            sub,
            ha="center",
            va="center",
            fontsize=9,
            style="italic",
            color=SUB_COLOR,
        )


def arrow(ax, start, end, *, style="-|>", linestyle="-", color=ARROW_COLOR, lw=2.0):
    a = FancyArrowPatch(
        start,
        end,
        arrowstyle=style,
        mutation_scale=22,
        linestyle=linestyle,
        color=color,
        linewidth=lw,
        shrinkA=2,
        shrinkB=2,
    )
    ax.add_patch(a)


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(19.2, 10.8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 56.25)
    ax.set_aspect("equal")
    ax.axis("off")

    # Title
    fig.text(
        0.5,
        0.94,
        "SciCheck — Multi-Agent Pipeline Architecture",
        ha="center",
        fontsize=24,
        fontweight="bold",
        color="#111827",
    )
    fig.text(
        0.5,
        0.905,
        "RAG-grounded scientific fact-checking with bias & hallucination monitoring",
        ha="center",
        fontsize=13,
        color=SUB_COLOR,
        style="italic",
    )

    # Safety Monitor (top, spanning the agent row)
    draw_box(
        ax,
        x=22,
        y=42,
        w=60,
        h=8,
        fill=SAFETY_FILL,
        edge=SAFETY_EDGE,
        label="Safety Monitor — Risk & Bias Oversight",
        sub="Citation grounding · Bias detection · Refusal triggers · LLM judge   (M5)",
    )

    # Endpoints
    draw_box(ax, 1, 25, 13, 8, ENDPOINT_FILL, ENDPOINT_EDGE, "User /\nStreamlit UI", sub="Input claim   (M6)")
    draw_box(ax, 86, 25, 13, 8, ENDPOINT_FILL, ENDPOINT_EDGE, "Verdict\nOutput", sub="Supported / Refuted / NEI")

    # Pipeline agents (left → right)
    draw_box(ax, 17, 25, 13, 8, PIPE_FILL, PIPE_EDGE, "Claim\nExtractor", sub="M3")
    draw_box(ax, 33, 25, 13, 8, PIPE_FILL, PIPE_EDGE, "Evidence\nRetriever", sub="M4")
    draw_box(ax, 49, 25, 13, 8, PIPE_FILL, PIPE_EDGE, "Source Credibility\nAnalyzer", sub="M3")
    draw_box(ax, 65, 25, 13, 8, PIPE_FILL, PIPE_EDGE, "Verdict\nSynthesizer", sub="M4")

    # ChromaDB (below the retriever)
    draw_box(ax, 33, 8, 13, 8, RAG_FILL, RAG_EDGE, "ChromaDB", sub="5,183 SciFact abstracts   (M2)")

    # Solid arrows along the main flow
    arrow(ax, (14, 29), (17, 29))
    arrow(ax, (30, 29), (33, 29))
    arrow(ax, (46, 29), (49, 29))
    arrow(ax, (62, 29), (65, 29))
    arrow(ax, (78, 29), (86, 29))

    # RAG bidirectional link (retriever ↔ Chroma)
    arrow(ax, (39.5, 25), (39.5, 16), style="<|-|>", color=RAG_EDGE)

    # Safety dashed arrows down to each pipeline node
    for x_center in [23.5, 39.5, 55.5, 71.5]:
        arrow(
            ax,
            (x_center, 42),
            (x_center, 33),
            linestyle=(0, (5, 4)),
            color=SAFETY_EDGE,
            lw=1.6,
        )

    # Orchestrator caption (bottom-left, subtle)
    ax.text(
        50,
        2,
        "LangGraph-style orchestrator (M1) wires the pipeline · trace_id propagated via structlog contextvars",
        ha="center",
        va="center",
        fontsize=10,
        color=SUB_COLOR,
        style="italic",
    )

    # Output
    png_path = out_dir / "architecture.png"
    svg_path = out_dir / "architecture.svg"
    plt.savefig(png_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.savefig(svg_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"Wrote {png_path}")
    print(f"Wrote {svg_path}")


if __name__ == "__main__":
    main()
