"""Reuse the complete first-batch audit for the frozen remaining-star batch."""

import inspect

import coverage_continuation as continuation
import export_coverage_pilot as original

PUBLIC_PLAN_COMMIT = "9e299b7039aaf825c551c0a7723beef566e4ba4a"


def main():
    continuation.pilot.REPORT = continuation.REPORT
    namespace = dict(
        vars(original),
        REPORT=continuation.REPORT,
        PUBLIC_PLAN_COMMIT=PUBLIC_PLAN_COMMIT,
        __file__=__file__,
    )
    source = inspect.getsource(original.main)
    old = '":reports/coverage_pilot/plan.json"'
    if source.count(old) != 1:
        raise ValueError("Expected exactly one public selection path in original audit")
    source = source.replace(old, '":reports/coverage_continuation/plan.json"')
    exec(compile(source, "<remaining-coverage-audit>", "exec"), namespace)
    namespace["main"]()


if __name__ == "__main__":
    main()
