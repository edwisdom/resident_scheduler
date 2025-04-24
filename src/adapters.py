from pathlib import Path

import pandas as pd

from base.shift import Shift


def read_shifts(filename: Path) -> list[Shift]:
    pd.read_csv(filename)
