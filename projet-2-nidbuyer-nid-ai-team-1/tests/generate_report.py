"""
Génère un rapport markdown depuis les résultats JUnit XML.
Appelé en fin de workflow eval.yml — le rapport apparaît dans le Job Summary GitHub.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

SUITES = [
    {
        "label": "Fichiers obligatoires",
        "xml": "results_eval.xml",
        "pts_max": 5,
        "filter": "TestFichiersObligatoires",
    },
    {
        "label": "Tests scoring",
        "xml": "results_scoring.xml",
        "pts_max": 10,
        "filter": None,
    },
    {
        "label": "Tests RAG",
        "xml": "results_rag.xml",
        "pts_max": 10,
        "filter": None,
    },
    {
        "label": "API démarre",
        "xml": "results_eval.xml",
        "pts_max": 5,
        "filter": "TestAPIDemarre",
    },
    {
        "label": "URL déployée",
        "xml": "results_deployment.xml",
        "pts_max": 5,
        "filter": None,
    },
    {
        "label": "Git hygiene (PRs)",
        "xml": "results_prs.xml",
        "pts_max": 5,
        "filter": None,
    },
]


def parse_junit(xml_path: Path, class_filter: str | None = None) -> tuple[int, int, list[str]]:
    """Retourne (nb_pass, nb_total, liste_erreurs)."""
    if not xml_path.exists():
        return 0, 0, [f"Fichier de résultats absent : {xml_path.name}"]

    tree = ET.parse(xml_path)
    root = tree.getroot()
    cases = root.findall(".//testcase")

    if class_filter:
        cases = [c for c in cases if class_filter in (c.get("classname") or "")]

    total = len(cases)
    failures = []
    for case in cases:
        fail = case.find("failure") or case.find("error")
        if fail is not None:
            name = case.get("name", "?")
            msg = (fail.get("message") or fail.text or "")[:200]
            failures.append(f"`{name}` — {msg}")

    return total - len(failures), total, failures


def score_suite(passed: int, total: int, pts_max: int) -> float:
    if total == 0:
        return 0.0
    return round(pts_max * passed / total, 1)


def main():
    lines = [
        "# Résultats auto-évaluation — NidBuyer",
        f"*Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC*",
        "",
        "| Critère | Résultat | Points |",
        "|---|:---:|:---:|",
    ]

    total_pts = 0.0
    total_max = 0
    details = []

    for suite in SUITES:
        xml_path = Path(suite["xml"])
        passed, total, errors = parse_junit(xml_path, suite.get("filter"))
        pts_max = suite["pts_max"]
        pts = score_suite(passed, total, pts_max)
        total_pts += pts
        total_max += pts_max

        if total == 0:
            status = "⚪ n/a"
        elif passed == total:
            status = "✅ pass"
        elif passed == 0:
            status = "❌ fail"
        else:
            status = f"⚠️ {passed}/{total}"

        lines.append(f"| {suite['label']} | {status} | {pts}/{pts_max} |")

        if errors:
            details.append(f"\n### {suite['label']} — erreurs\n")
            for e in errors[:5]:
                details.append(f"- {e}")

    lines += [
        "",
        f"**Total automatique : {total_pts:.0f} / {total_max} pts**",
        "",
        "> Les 20 pts restants (qualité LLM, prompt engineering, R&D Vision) sont évalués en soutenance.",
    ]

    if details:
        lines += ["", "---"] + details

    report = "\n".join(lines)
    Path("evaluation_report.md").write_text(report, encoding="utf-8")
    print(report)

    # Exit code non-nul si score < 50% pour signaler un échec dans le workflow
    if total_max > 0 and total_pts / total_max < 0.5:
        sys.exit(1)


if __name__ == "__main__":
    main()
