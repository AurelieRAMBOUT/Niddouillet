"""
Fonctions statistiques from scratch.
Reference : Joel Grus, "Data Science From Scratch", chapitre 5.

IMPORTANT : N'importez pas numpy, pandas ou statistics pour ces fonctions.
Implementez-les avec du Python pur (listes, boucles, math).
"""

import math

def mean(xs: list[float]) -> float:
    """Retourne la moyenne d'une liste de nombres."""
    if not xs:
        raise ValueError("La liste ne peut pas être vide")
    return sum(xs) / len(xs)


def median(xs: list[float]) -> float:
    """Retourne la mediane d'une liste de nombres."""
    #Si la liste n'est pas vide, on la trie, on calcule le nombre du milieu en prenant en compte le fait que ce soit pair ou impair)
    if not xs:
        raise ValueError("La liste ne peut pas être vide")
    
    sorted_xs = sorted(xs)
    n = len(sorted_xs)
    mid = n // 2

    if n % 2 == 1:
        return sorted_xs[mid]
    return (sorted_xs[mid - 1] + sorted_xs[mid]) / 2
    

def variance(xs: list[float]) -> float:
    """Retourne la variance d'une liste de nombres."""
    #La variance mesure à quel point les valeurs sont dispersées autour de la moyenne
    if not xs:
        raise ValueError("La liste ne peut pas être vide")
    
    mo = mean(xs)
    return sum((x - mo) ** 2 for x in xs) / len(xs)

def standard_deviation(xs: list[float]) -> float:
    """Retourne l'ecart-type d'une liste de nombres."""
    # =racine carrée de la variance

    if not xs:
        raise ValueError("La liste ne peut pas être vide")
    
    return math.sqrt(variance(xs))


def covariance(xs: list[float], ys: list[float]) -> float:
    """Retourne la covariance entre deux series."""
    #Mesure si deux séries évoluent ensemble

    # 1 : vérifie si la liste n'est pas vide et si les 2 listes ont la même longueur
    # 2 : calcule la moyenne des 2 listes
    # 3 : calule la covariance 
    # formule : somme((xs[i] - mean_x) * (ys[i] - mean_y)) / len(xs)
    
    if not xs or not ys:
        raise ValueError("Les listes ne peuvent pas être vides")
    
    if len(xs) != len(ys):
        raise ValueError("Les listes doivent avoir la même longueur")

    mean_x = mean(xs)
    mean_y = mean(ys)

    total = 0
    for i in range(len(xs)):
        total += (xs[i] - mean_x) * (ys[i] - mean_y)

    return total / len(xs)

def correlation(xs: list[float], ys: list[float]) -> float:
    """
    Retourne le coefficient de correlation de Pearson entre deux series.
    Retourne 0 si l'une des series a un ecart-type nul.
    """
    # La corrélation n’a pas d’unité et est toujours comprise entre-1 (anti-corrélation parfaite) 
    # et+1(corrélation parfaite)

    if not xs or not ys:
        raise ValueError("Les listes ne peuvent pas être vides")

    if len(xs) != len(ys):
        raise ValueError("Les listes doivent avoir la même longueur")

    #Calcul des écarts-type
    std_x = standard_deviation(xs)
    std_y = standard_deviation(ys)

    #Vérification que la série ne varie pas (sinon la corrélation n'a pas de sens)
    if std_x == 0 or std_y == 0:
        return 0

    return covariance(xs, ys) / (std_x * std_y)