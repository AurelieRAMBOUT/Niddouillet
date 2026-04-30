from .regression import predict


def expected_price(alpha: float, beta: float, surface: float) -> float:
    """Estime le prix attendu d'un bien a partir de sa surface."""
    return predict(alpha, beta, surface)


def quartier_coefficient(
    quartier: str | None,
    quartier_stats: dict[str, dict] | None,
    ville_pm2_median: float | None,
    smoothing: int = 10,
) -> float:
    """
    Calcule un coefficient multiplicateur de prix pour un quartier.

    Le coefficient est lisse vers 1.0 pour eviter de surponderer
    les quartiers peu representes.
    """
    if not quartier or not quartier_stats or not ville_pm2_median or ville_pm2_median <= 0:
        return 1.0

    stats = quartier_stats.get(quartier)
    if not stats:
        return 1.0

    pm2_median = stats.get("pm2_median")
    n_annonces = int(stats.get("n_annonces", 0) or 0)

    if pm2_median is None or pm2_median <= 0 or n_annonces <= 0:
        return 1.0

    raw_ratio = float(pm2_median) / float(ville_pm2_median)
    weight = n_annonces / (n_annonces + smoothing)
    return (weight * raw_ratio) + ((1 - weight) * 1.0)


def expected_price_with_quartier(
    alpha: float,
    beta: float,
    surface: float,
    quartier: str | None,
    quartier_stats: dict[str, dict] | None,
    ville_pm2_median: float | None,
    smoothing: int = 10,
) -> float:
    """Estime le prix attendu en tenant compte de la surface et du quartier."""
    base_price = expected_price(alpha, beta, surface)
    coefficient = quartier_coefficient(
        quartier=quartier,
        quartier_stats=quartier_stats,
        ville_pm2_median=ville_pm2_median,
        smoothing=smoothing,
    )
    return base_price * coefficient


def opportunity_score(expected_price: float, listed_price: float) -> float:
    """
    Calcule un score d'opportunite.
    Score > 0 : bien moins cher que prevu
    Score < 0 : bien plus cher que prevu
    """
    if listed_price <= 0:
        raise ValueError("Le prix affiche doit etre positif")

    return (expected_price - listed_price) / listed_price


def classify_property(expected_price_value: float, listed_price: float, threshold: float = 0.10) -> str:
    """Classe un bien en opportunite, prix marche ou surevalue."""
    score = opportunity_score(expected_price_value, listed_price)

    if score > threshold:
        return "Opportunité"
    elif score < -threshold:
        return "Surévalué"
    else:
        return "Prix marché"
