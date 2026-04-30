"""
Regression lineaire simple from scratch.
Reference : Joel Grus, "Data Science From Scratch", chapitre 14.

IMPORTANT : N'importez pas, numpy ou scipy pour ces fonctions.
"""

from .stats import mean, variance, covariance


def predict(alpha: float, beta: float, x_i: float) -> float:
    """Predit y pour une valeur x : y = alpha + beta * x."""
    
    return alpha + beta * x_i


def error(alpha: float, beta: float, x_i: float, y_i: float) -> float:
    """Calcule l'erreur de prediction pour un point."""
    
    return y_i - predict(alpha, beta, x_i)


def sum_of_sqerrors(alpha: float, beta: float, x: list, y: list) -> float:
    """Somme des erreurs au carre sur tous les points. = Erreur quadratique moyenne(mean squared error)"""
    #Pourquoi au carré ?
    # pour éviter que les erreurs positives et négatives s’annulent
    # pour pénaliser davantage les grosses erreurs

    if len(x) != len(y):
        raise ValueError("x et y doivent avoir la même longueur")

    total = 0
    for i in range(len(x)):
        total += error(alpha, beta, x[i], y[i]) ** 2

    return total


def least_squares_fit(x: list[float], y: list[float]) -> tuple[float, float]:
    """
    Trouve alpha et beta qui minimisent la somme des erreurs au carre.
    Retourne (alpha, beta) tels que y ≈ alpha + beta * x. = Méthode des moindres carrés
    """
    
    if not x or not y:
        raise ValueError("x et y ne doivent pas être vides")

    if len(x) != len(y):
        raise ValueError("x et y doivent avoir la même longueur")

    var_x = variance(x)
    if var_x == 0:
        raise ValueError("La variance de x ne peut pas être nulle")

    beta = covariance(x, y) / var_x
    alpha = mean(y) - beta * mean(x)

    return alpha, beta
   
    # Indices : beta = covariance(x, y) / variance(x)
    #           alpha = mean(y) - beta * mean(x)

def r_squared(alpha: float, beta: float, x: list, y: list) -> float:
    """
    Coefficient de determination R².
    R² = 1 - (SS_res / SS_tot)
    1.0 = ajustement parfait, 0.0 = le modele n'explique rien.
    """
    
    if len(x) != len(y):
        raise ValueError("x et y doivent avoir la même longueur")

    ss_res = sum_of_sqerrors(alpha, beta, x, y)

    mean_y = mean(y)
    ss_tot = 0
    for y_i in y:
        ss_tot += (y_i - mean_y) ** 2

    if ss_tot == 0:
        return 1.0

    return 1 - (ss_res / ss_tot)
