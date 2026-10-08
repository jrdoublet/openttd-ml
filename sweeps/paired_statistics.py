"""Shared deterministic paired statistics, standard library only."""
import math
import random
import statistics


def wilcoxon_signed_rank_statistic(values):
    """Composantes du test des rangs signés de Wilcoxon.

    Les zéros sont écartés. Les ex æquo d'une même valeur absolue reçoivent
    le rang moyen. ``w_plus`` somme les rangs des valeurs strictement
    positives ; ``expectation`` est son espérance sous H0 (moitié de la
    somme des rangs). ``p`` est le p bilatéral exact, ou None s'il ne reste
    aucune valeur non nulle.

    La loi nulle est une programmation dynamique sur les rangs doublés :
    un rang moyen demi-entier devient un entier, et chaque assignation de
    signes est comptée une fois (support ``2**n``).
    """
    observed = []
    for value in values:
        if value is None:
            continue
        number = float(value)
        if number == 0.0:
            continue
        observed.append(number)
    n = len(observed)
    empty = {
        "n": 0,
        "w_plus": None,
        "total_ranks": None,
        "expectation": None,
        "p": None,
    }
    if n == 0:
        return empty
    order = sorted(range(n), key=lambda index: abs(observed[index]))
    doubled = [0] * n
    start = 0
    while start < n:
        end = start
        anchor = abs(observed[order[start]])
        while end + 1 < n and abs(observed[order[end + 1]]) == anchor:
            end += 1
        # Rangs 1-based start+1..end+1. La moyenne (start+end+2)/2, doublée,
        # reste entière quand des ex æquo produisent un demi-rang.
        doubled_rank = start + end + 2
        for cursor in range(start, end + 1):
            doubled[order[cursor]] = doubled_rank
        start = end + 1
    positive = sum(doubled[index] for index in range(n) if observed[index] > 0)
    total_doubled = sum(doubled)
    counts = [0] * (total_doubled + 1)
    counts[0] = 1
    for rank in doubled:
        for score in range(total_doubled - rank, -1, -1):
            count = counts[score]
            if count:
                counts[score + rank] += count
    smaller = min(positive, total_doubled - positive)
    tail = sum(counts[:smaller + 1])
    total_ranks = total_doubled / 2.0
    return {
        "n": n,
        "w_plus": positive / 2.0,
        "total_ranks": total_ranks,
        "expectation": total_ranks / 2.0,
        "p": min(1.0, 2.0 * tail / (2 ** n)),
    }


def exact_wilcoxon_signed_rank_p(values):
    """p bilatéral exact du test des rangs signés, ou None si tout est nul."""
    return wilcoxon_signed_rank_statistic(values)["p"]


def bootstrap_mean_ci(values, *, confidence=0.95, resamples=20000, seed=0):
    """Intervalle percentile de la moyenne, bootstrap avec remise.

    ``random.Random(seed)`` rend deux appels identiques bit à bit. Les indices
    suivent ``Random.choices`` (``floor(random() * n)``) et la moyenne est
    ``statistics.mean``. Un échantillon constant a la même moyenne dans tout
    rééchantillonnage : l'intervalle est cette constante, sans tirage. Une
    série vide renvoie ``(None, None)``.
    """
    sample = []
    for value in values:
        if value is None:
            continue
        sample.append(float(value))
    if not sample:
        return (None, None)
    if resamples < 1:
        raise ValueError("resamples doit être >= 1")
    if not 0.0 < float(confidence) < 1.0:
        raise ValueError("confidence doit être dans (0, 1)")
    constant = sample[0]
    if all(value == constant for value in sample):
        return (constant, constant)
    generator = random.Random(seed)
    width = float(len(sample))
    draw = generator.random
    floor = math.floor
    count = len(sample)
    means = [
        statistics.mean(sample[floor(draw() * width)] for _ in range(count))
        for _ in range(int(resamples))
    ]
    means.sort()
    tail = (1.0 - float(confidence)) / 2.0
    lower_index = int(tail * resamples)
    upper_index = int((1.0 - tail) * resamples)
    if upper_index >= resamples:
        upper_index = resamples - 1
    return (means[lower_index], means[upper_index])
