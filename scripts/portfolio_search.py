"""Freeze a larger set from one unchanged training refinement pass."""

import inspect

import numpy as np

from qualified_seeds import make_search
import repeated_search


def transit_mask(signal, training):
    period = signal["period_days"]
    phase = (training.time.to_numpy() - signal["epoch_btjd"] + period / 2) % period - period / 2
    return abs(phase) < signal["duration_days"] / 2


def redundant(mask, retained):
    count = np.count_nonzero(mask)
    return any(
        np.count_nonzero(mask & old) > 0.5 * min(count, np.count_nonzero(old)) for old in retained
    )


def make_portfolio_search(metric="leave_one_out_snr"):
    source = inspect.getsource(repeated_search.select_training)
    loop = "for iteration in range(1, max_signals + 1):"
    marker = "        if not accepted:\n"
    if source.count(loop) != 1 or source.count(marker) != 1:
        raise ValueError("Training helper changed; review adapter")
    source = source.replace(loop, "for iteration in range(1, 2):")
    source = (
        source.split(marker, 1)[0]
        + """
        accepted.sort(key=lambda item: (-item[0]["event_ranking"][metric], item[0]["training_peak_rank"]))
        retained_masks = []
        for signal, index in accepted:
            mask = transit_mask(signal, training)
            if redundant(mask, retained_masks):
                diagnostics[index]["duplicate_fit"] = True
                continue
            diagnostics[index]["accepted"] = True
            signals.append(signal)
            retained_masks.append(mask)
            if len(signals) >= max_signals:
                break
    return signals, diagnostics
"""
    )
    namespace = dict(vars(repeated_search), transit_mask=transit_mask, redundant=redundant)
    exec(compile(source, "<portfolio-training-selection>", "exec"), namespace)
    selection = namespace["select_training"]
    adapted = make_search(qualified=True)

    def selector(*args, **kwargs):
        return selection(*args, **kwargs, metric=metric)

    adapted.__globals__["select_training"] = selector

    def run(df, star, output_folder, max_signals=32):
        return adapted(df, star, output_folder, max_signals=max_signals)

    return run
