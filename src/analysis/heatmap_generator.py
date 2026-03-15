"""
Heatmap generator — paper signature figures.
Generates 4×4 pairwise heatmaps: VP ratio, trade acceptance, exploitation index.

STATUS: STUB — framework defined pre-registration. Visual polish in M004/S02.
"""

import numpy as np
from pathlib import Path

FAMILIES = ["llama", "deepseek", "gemini", "mistral"]
PAIRINGS = [
    ("llama", "deepseek"),
    ("llama", "gemini"),
    ("llama", "mistral"),
    ("deepseek", "gemini"),
    ("deepseek", "mistral"),
    ("gemini", "mistral"),
]


def build_vp_ratio_matrix(results: dict) -> np.ndarray:
    """
    Build 4×4 matrix of VP ratios from pairwise results.
    Matrix[i][j] = mean VP(family_i) / mean VP(family_j) in their matchup.
    Diagonal = 1.0 (monoculture, by definition).
    Upper triangle = pairwise ratio. Lower triangle = 1/upper (symmetric).
    """
    n = len(FAMILIES)
    matrix = np.ones((n, n))

    fam_idx = {fam: i for i, fam in enumerate(FAMILIES)}

    for fam_a, fam_b in PAIRINGS:
        i, j = fam_idx[fam_a], fam_idx[fam_b]
        key = f"{fam_a}_{fam_b}"
        if key in results:
            ratio = results[key]["mean_vp_ratio"]  # vp_a / vp_b
            matrix[i][j] = ratio
            matrix[j][i] = 1 / ratio if ratio != 0 else 0

    return matrix


def plot_heatmap(
    matrix: np.ndarray,
    title: str,
    output_path: Path,
    families: list[str] = FAMILIES,
    cmap: str = "RdYlGn",
    center: float = 1.0,
) -> None:
    """
    Generate a seaborn heatmap and save to output_path.
    TODO: implement in M004/S02.
    """
    try:
        import seaborn as sns
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError("pip install seaborn matplotlib")

    fig, ax = plt.subplots(figsize=(8, 7))

    # TODO: implement with actual data
    # sns.heatmap(
    #     matrix,
    #     xticklabels=families,
    #     yticklabels=families,
    #     annot=True,
    #     fmt=".2f",
    #     cmap=cmap,
    #     center=center,
    #     ax=ax,
    # )
    # ax.set_title(title, fontsize=14, fontweight="bold")
    # fig.tight_layout()
    # fig.savefig(output_path, dpi=300, bbox_inches="tight")
    # plt.close(fig)
    raise NotImplementedError("TODO: implement in M004/S02")


def generate_all_heatmaps(results: dict, output_dir: Path) -> None:
    """
    Generate all 3 paper heatmaps:
    1. VP ratio matrix
    2. Trade acceptance rate matrix
    3. Exploitation index matrix
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # TODO: build matrices from results and generate plots
    raise NotImplementedError("TODO: implement in M004/S02 once Phase 2 data is collected")


if __name__ == "__main__":
    print("Heatmap Generator Stub")
    print("Families:", FAMILIES)
    print("Pairings:", PAIRINGS)
    print("Pre-registration timestamp:", __import__("datetime").datetime.utcnow().isoformat())
