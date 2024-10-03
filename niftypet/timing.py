import time
import json
from pathlib import Path
from typing import List, Dict, TypeVar
from datetime import timedelta, datetime
from copy import deepcopy
from math import sqrt
from collections import defaultdict

T = TypeVar("T")

class ReconMetadata:
    """Utility class to easily time different parts of the reconstruction,
    store some metadata and in the end store it to a json logfile.

    Usage:
        At the beginning of processing set up a global instance of this class
        and call the `start` method.

        Start each frame by calling `start_frame` and end it with `end_frame`.
        Log as many block durations as you want with `start_block` and `end_block`.

        In the end call the `end` method and save the processing statistics using `save`.
        This will create a json file in the specified directory called `%Y-%m-%d-%H-%M_metadata_{id}.json`,
        where the first part indicates the current date and time and
        `id` is the identifier passed to the ReconMetadata constructor.
    """

    def __init__(self, identifier: str = "") -> None:
        self._current_times = defaultdict(dict)
        self._previous_times = []
        self._identifier = identifier
        self._metadata = dict()
        self.add_metadatum("identifier", identifier)

    def start(self) -> None:
        """Set overall start to current time"""
        self.start_time = time.time()

    def end(self) -> None:
        """Set overall end to current time"""
        self.end_time = time.time()

    def start_block(self, block_name: str) -> None:
        """Set start time of a task within the reconstruction"""
        self._current_times[block_name]["start"] = time.time()

    def end_block(self, block_name: str) -> None:
        """Set end time of a task within the reconstruction"""
        if block_name not in self._current_times:
            raise RuntimeError(f"Block '{block_name}' was not started!")
        self._current_times[block_name]["end"] = time.time()

    @property
    def total_duration(self) -> timedelta:
        return timedelta(seconds=self.end_time - self.start_time)

    def _calc_durations(self) -> List[Dict[str, float]]:
        return [
            {
                block_key: timings[block_key]["end"] - timings[block_key]["start"]
                for block_key in timings.keys()
            }
            for timings in self._previous_times
        ]

    @staticmethod
    def _calc_averages(durations: List[Dict[str, float]]) -> Dict[str, float]:
        return {
            key: sum([el[key] for el in durations]) / len(durations)
            for key in durations[0].keys()
        }

    @staticmethod
    def _calc_deviations(
        durations: List[Dict[str, float]], averages: Dict[str, float]
    ) -> Dict[str, float]:
        return {
            key: sqrt(
                sum([(el[key] - averages[key]) ** 2 for el in durations])
                / len(durations)
            )
            for key in durations[0].keys()
        }

    def save(self, outdir: Path):
        durations = self._calc_durations()
        averages = self._calc_averages(durations)
        std_deviations = self._calc_deviations(durations, averages)

        with open(outdir / "metadata.json", "w") as f:
            json.dump(
                {
                    "metadata": self._metadata,
                    "averages": averages,
                    "std_deviations": std_deviations,
                    "total_seconds": self.total_duration.seconds,
                },
                f,
            )

    def start_frame(self) -> None:
        self.start_block("frame")

    def end_frame(self) -> None:
        self.end_block("frame")
        frame_time = (
            self._current_times["frame"]["end"] - self._current_times["frame"]["start"]
        )
        assigned_time = sum(
            [
                value["end"] - value["start"]
                for key, value in self._current_times.items()
                if key != "frame"
            ]
        )
        self._current_times["unassigned"]["start"] = 0
        self._current_times["unassigned"]["end"] = frame_time - assigned_time

        self._previous_times.append(deepcopy(self._current_times))
        print(
            f"Finished frame nr {len(self._previous_times)}. "
            f"Took {self._current_times['frame']['end'] - self._current_times['frame']['start']} seconds."
        )

        self._current_times = defaultdict(dict)

    def add_metadatum(self, key: str, value: T) -> T:
        """Add a metadata to save to the logfile.

        :return: Value for easier assignment
        """
        self._metadata[key] = str(value)
        return value
