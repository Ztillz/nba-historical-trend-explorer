from __future__ import annotations

import logging
import random
import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats


class AdvancedTeamStatsClient:
    """
    Download and cache NBA.com season-level advanced team statistics.
    """

    def __init__(
        self,
        raw_data_directory: Path,
        logger: logging.Logger,
        timeout_seconds: int = 60,
        max_retries: int = 4,
        base_retry_delay_seconds: float = 5.0,
    ) -> None:
        self.raw_data_directory = raw_data_directory
        self.logger = logger
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.base_retry_delay_seconds = base_retry_delay_seconds

        self.raw_data_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def get_season_stats(
        self,
        season: str,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        raw_file = self.raw_data_directory / f"{season}.csv"

        if raw_file.exists() and not force_refresh:
            self.logger.info(
                "Loading cached advanced stats: %s",
                raw_file,
            )

            return pd.read_csv(
                raw_file,
                dtype={
                    "TEAM_ID": "int64",
                },
            )

        dataframe = self._download_with_retries(
            season=season,
        )

        if dataframe.empty:
            raise ValueError(
                f"Advanced endpoint returned zero rows for {season}."
            )

        dataframe.to_csv(
            raw_file,
            index=False,
        )

        self.logger.info(
            "Saved %s advanced rows to %s",
            len(dataframe),
            raw_file,
        )

        return dataframe

    def _download_with_retries(
        self,
        season: str,
    ) -> pd.DataFrame:
        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.info(
                    "Downloading advanced stats for %s. "
                    "Attempt %s of %s.",
                    season,
                    attempt,
                    self.max_retries,
                )

                response = (
                    leaguedashteamstats.LeagueDashTeamStats(
                        season=season,
                        season_type_all_star="Regular Season",
                        measure_type_detailed_defense="Advanced",
                        per_mode_detailed="PerGame",
                        timeout=self.timeout_seconds,
                    )
                )

                dataframes = response.get_data_frames()

                if not dataframes:
                    raise ValueError(
                        "Advanced endpoint returned no datasets."
                    )

                dataframe = dataframes[0].copy()

                self.logger.info(
                    "Advanced endpoint returned %s rows and %s columns.",
                    len(dataframe),
                    len(dataframe.columns),
                )

                return dataframe

            except Exception as exc:
                last_exception = exc

                self.logger.warning(
                    "Advanced request failed for %s on attempt %s: %s",
                    season,
                    attempt,
                    exc,
                )

                if attempt == self.max_retries:
                    break

                delay = (
                    self.base_retry_delay_seconds
                    * (2 ** (attempt - 1))
                    + random.uniform(0.5, 2.0)
                )

                self.logger.info(
                    "Retrying after %.1f seconds.",
                    delay,
                )

                time.sleep(delay)

        raise RuntimeError(
            f"Unable to download advanced stats for {season}."
        ) from last_exception